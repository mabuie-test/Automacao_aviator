"""Configuration helpers for the Aviator bot Python rewrite.

Todas as configurações agora vivem no JSON ``~/.aviator_bot/settings.json`` e
são editadas pela própria GUI. Variáveis de ambiente não são mais necessárias.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Mapping, Optional


CONFIG_PATH = Path.home() / ".aviator_bot" / "settings.json"
DATA_PATH = Path.home() / ".aviator_bot" / "multipliers.json"


@dataclass(frozen=True)
class Settings:
    aviator_url: str = "https://1whpc.com/casino/play/aviator"
    attach_to_existing: bool = False
    chrome_debug_host: str = ""
    chrome_debug_port: Optional[int] = None
    chrome_binary: Optional[str] = None
    data_path: str = str(DATA_PATH)
    platform_user: str = ""
    platform_password: str = ""
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
    def from_mapping(cls, data: Mapping[str, object]) -> "Settings":
        """Build settings from a mapping (e.g., loaded JSON)."""

        def get(name: str, default):
            return data.get(name, default)

        return cls(
            aviator_url=str(get("aviator_url", cls.aviator_url)),
            attach_to_existing=bool(get("attach_to_existing", cls.attach_to_existing)),
            chrome_debug_host=str(get("chrome_debug_host", cls.chrome_debug_host)),
            chrome_debug_port=(
                int(get("chrome_debug_port", cls.chrome_debug_port))
                if get("chrome_debug_port", cls.chrome_debug_port) not in (None, "")
                else None
            ),
            chrome_binary=str(get("chrome_binary", "")) or None,
            data_path=str(get("data_path", cls.data_path)),
            platform_user=str(get("platform_user", cls.platform_user)),
            platform_password=str(get("platform_password", cls.platform_password)),
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
        if not str(self.data_path).strip():
            raise ValueError("DATA_PATH não pode ser vazio")
        if self.attach_to_existing and not self.chrome_debug_host:
            raise ValueError("Informe o host de depuração ou desative 'usar sessão existente'")
        if self.attach_to_existing and not self.chrome_debug_port:
            raise ValueError("Informe a porta de depuração ou desative 'usar sessão existente'")
        return self

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2)


_SETTINGS: Settings = Settings().validate()


def get_settings() -> Settings:
    return _SETTINGS


def set_settings(settings: Settings) -> None:
    global _SETTINGS
    _SETTINGS = settings.validate()


def load_persisted_settings() -> Settings:
    base = Settings().validate()
    if not CONFIG_PATH.exists():
        return base
    raw = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    return Settings.from_mapping(raw).validate()


def persist_settings(settings: Settings) -> None:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(settings.to_json(), encoding="utf-8")


def update_and_persist(**updates: object) -> Settings:
    """Helper to update the active settings in-place and persist to disk."""

    current = get_settings()
    data = asdict(current)
    data.update(updates)
    new_settings = Settings.from_mapping(data).validate()
    set_settings(new_settings)
    persist_settings(new_settings)
    return new_settings


# Carrega configurações persistidas na importação para que a GUI seja a fonte de verdade
set_settings(load_persisted_settings())
