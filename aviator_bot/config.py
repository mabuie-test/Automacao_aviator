"""Configuration helpers for the Aviator bot Python rewrite.

Environment variables:
    MYSQL_HOST, MYSQL_PORT, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DATABASE:
        Connection settings for the backing MySQL instance.
    AVIATOR_URL:
        Target URL for the Aviator game. Defaults to the production URL used by the
        legacy bot.
    CHROME_DEBUG_PORT:
        Remote debugging port for the Selenium session. Defaults to 9222.
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Mapping, Optional


CONFIG_PATH = Path.home() / ".aviator_bot" / "settings.json"


def _parse_bool(raw: str | None, default: bool = False) -> bool:
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    mysql_host: str = "localhost"
    mysql_port: int = 3306
    mysql_user: str = "root"
    mysql_password: str = ""
    mysql_database: str = "aviator"
    aviator_url: str = "https://1whpc.com/casino/play/aviator"
    chrome_debug_host: str = "127.0.0.1"
    chrome_debug_port: int = 9222
    chrome_binary: Optional[str] = None
    auto_bet: bool = False
    base_bet: float = 1.0
    max_bet: float = 25.0
    confidence_floor: float = 0.35
    streak_window: int = 8
    bet_input_selector: str = "input[type='number']"
    bet_button_selector: str = "button.place-bet"
    cashout_button_selector: str = "button.cashout"
    warmup_seconds: int = 120
    session_ready_selector: str = "input[type='number']"
    session_ready_timeout: int = 90

    @classmethod
    def from_env(cls) -> "Settings":
        def getenv_int(name: str, default: int) -> int:
            raw = os.getenv(name)
            return int(raw) if raw and raw.isdigit() else default

        return cls(
            mysql_host=os.getenv("MYSQL_HOST", cls.mysql_host),
            mysql_port=getenv_int("MYSQL_PORT", cls.mysql_port),
            mysql_user=os.getenv("MYSQL_USER", cls.mysql_user),
            mysql_password=os.getenv("MYSQL_PASSWORD", cls.mysql_password),
            mysql_database=os.getenv("MYSQL_DATABASE", cls.mysql_database),
            aviator_url=os.getenv("AVIATOR_URL", cls.aviator_url),
            chrome_debug_host=os.getenv("CHROME_DEBUG_HOST", cls.chrome_debug_host),
            chrome_debug_port=getenv_int("CHROME_DEBUG_PORT", cls.chrome_debug_port),
            chrome_binary=os.getenv("CHROME_BINARY", cls.chrome_binary),
            auto_bet=_parse_bool(os.getenv("AUTO_BET"), default=cls.auto_bet),
            base_bet=float(os.getenv("BASE_BET", cls.base_bet)),
            max_bet=float(os.getenv("MAX_BET", cls.max_bet)),
            confidence_floor=float(os.getenv("CONFIDENCE_FLOOR", cls.confidence_floor)),
            streak_window=getenv_int("STREAK_WINDOW", cls.streak_window),
            bet_input_selector=os.getenv("BET_INPUT_SELECTOR", cls.bet_input_selector),
            bet_button_selector=os.getenv("BET_BUTTON_SELECTOR", cls.bet_button_selector),
            cashout_button_selector=os.getenv("CASHOUT_BUTTON_SELECTOR", cls.cashout_button_selector),
            warmup_seconds=getenv_int("WARMUP_SECONDS", cls.warmup_seconds),
            session_ready_selector=os.getenv("SESSION_READY_SELECTOR", cls.session_ready_selector),
            session_ready_timeout=getenv_int("SESSION_READY_TIMEOUT", cls.session_ready_timeout),
        )

    @classmethod
    def from_mapping(cls, data: Mapping[str, object]) -> "Settings":
        """Build settings from a mapping (e.g., loaded JSON)."""

        def get(name: str, default):
            return data.get(name, default)

        return cls(
            mysql_host=str(get("mysql_host", cls.mysql_host)),
            mysql_port=int(get("mysql_port", cls.mysql_port)),
            mysql_user=str(get("mysql_user", cls.mysql_user)),
            mysql_password=str(get("mysql_password", cls.mysql_password)),
            mysql_database=str(get("mysql_database", cls.mysql_database)),
            aviator_url=str(get("aviator_url", cls.aviator_url)),
            chrome_debug_host=str(get("chrome_debug_host", cls.chrome_debug_host)),
            chrome_debug_port=int(get("chrome_debug_port", cls.chrome_debug_port)),
            chrome_binary=str(get("chrome_binary", "")) or None,
            auto_bet=bool(get("auto_bet", cls.auto_bet)),
            base_bet=float(get("base_bet", cls.base_bet)),
            max_bet=float(get("max_bet", cls.max_bet)),
            confidence_floor=float(get("confidence_floor", cls.confidence_floor)),
            streak_window=int(get("streak_window", cls.streak_window)),
            bet_input_selector=str(get("bet_input_selector", cls.bet_input_selector)),
            bet_button_selector=str(get("bet_button_selector", cls.bet_button_selector)),
            cashout_button_selector=str(get("cashout_button_selector", cls.cashout_button_selector)),
            warmup_seconds=int(get("warmup_seconds", cls.warmup_seconds)),
            session_ready_selector=str(get("session_ready_selector", cls.session_ready_selector)),
            session_ready_timeout=int(get("session_ready_timeout", cls.session_ready_timeout)),
        )

    def validate(self) -> "Settings":
        if self.base_bet <= 0 or self.max_bet <= 0:
            raise ValueError("BASE_BET e MAX_BET devem ser valores positivos")
        if self.base_bet > self.max_bet:
            raise ValueError("BASE_BET não pode ser maior que MAX_BET")
        if not 0.0 <= self.confidence_floor <= 1.0:
            raise ValueError("CONFIDENCE_FLOOR deve estar entre 0 e 1")
        if self.streak_window < 3:
            raise ValueError("STREAK_WINDOW deve ser pelo menos 3 para medir tendência")
        if self.warmup_seconds < 120:
            raise ValueError("WARMUP_SECONDS deve ser de pelo menos 120 segundos para garantir coleta inicial")
        if self.session_ready_timeout < 10:
            raise ValueError("SESSION_READY_TIMEOUT deve ser de pelo menos 10 segundos")
        return self

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2)


_SETTINGS: Settings = Settings.from_env().validate()


def get_settings() -> Settings:
    return _SETTINGS


def set_settings(settings: Settings) -> None:
    global _SETTINGS
    _SETTINGS = settings.validate()


def load_persisted_settings() -> Settings:
    if not CONFIG_PATH.exists():
        return get_settings()
    raw = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    return Settings.from_mapping(raw).validate()


def persist_settings(settings: Settings) -> None:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(settings.to_json(), encoding="utf-8")
