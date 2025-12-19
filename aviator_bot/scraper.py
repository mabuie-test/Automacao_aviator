"""Selenium scraper that mirrors the C# bot behaviour.

The scraper reuses an existing Chrome session started with the
``--remote-debugging-port`` flag. This matches the legacy workflow where the
user manually signs in before letting automation take over.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Generator, List

from selenium import webdriver
from selenium.common.exceptions import (
    NoSuchElementException,
    StaleElementReferenceException,
    TimeoutException,
)
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from . import config


MULTIPLIER_SELECTOR = ".bubble-multiplier.font-weight-bold"
BET_HEADER_XPATH = "/html/body/app-root/app-game/div/div[1]/div[2]/div/div[1]/app-bets-widget/div/app-all-bets-tab/div/app-header/div[1]/div[1]/div[2]"
IFRAME_XPATH = "//*[@id='casino']/main/div/div/div[2]/div/iframe"


LOGGER = logging.getLogger("aviator-bot")


@dataclass
class ScraperState:
    last_multipliers: List[str] = field(default_factory=list)


class MultiplierScraper:
    def __init__(self, wait_timeout: int = 20, settings=None) -> None:
        self.settings = settings or config.get_settings()
        options = Options()
        if self.settings.chrome_binary:
            options.binary_location = self.settings.chrome_binary
        if self.settings.attach_to_existing and self.settings.chrome_debug_port:
            options.debugger_address = f"{self.settings.chrome_debug_host}:{self.settings.chrome_debug_port}"
            LOGGER.info(
                "Reutilizando navegador existente em %s:%s",
                self.settings.chrome_debug_host,
                self.settings.chrome_debug_port,
            )
        else:
            options.add_argument("--remote-allow-origins=*")
            LOGGER.info("Abrindo nova janela do navegador para %s", self.settings.aviator_url)

        self.driver = webdriver.Chrome(options=options)
        self.wait = WebDriverWait(self.driver, wait_timeout)
        self.state = ScraperState()
        if not self.settings.attach_to_existing:
            self.driver.get(self.settings.aviator_url)

    def __enter__(self) -> "MultiplierScraper":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def _update_final_endpoint(self) -> None:
        """Persiste o endpoint final resolvido pelo navegador aberto."""

        try:
            current = self.driver.current_url
        except Exception:
            return
        if current and current != self.settings.aviator_url:
            self.settings = config.update_and_persist(aviator_url=current)

    def _try_fill_credentials(self) -> None:
        if not (self.settings.platform_user or self.settings.platform_password):
            return
        try:
            user_field = None
            for selector in ["input[type='email']", "input[type='text']"]:
                matches = self.driver.find_elements(By.CSS_SELECTOR, selector)
                if matches:
                    user_field = matches[0]
                    break
            if user_field and self.settings.platform_user:
                user_field.clear()
                user_field.send_keys(self.settings.platform_user)

            pass_field = None
            for selector in ["input[type='password']", "input[type='tel']"]:
                matches = self.driver.find_elements(By.CSS_SELECTOR, selector)
                if matches:
                    pass_field = matches[0]
                    break
            if pass_field and self.settings.platform_password:
                pass_field.clear()
                pass_field.send_keys(self.settings.platform_password)
        except Exception:
            # login pode variar; ignore falhas silenciosamente
            pass

    def ensure_on_game(self) -> None:
        self.driver.get(self.settings.aviator_url)
        self.wait.until(EC.frame_to_be_available_and_switch_to_it((By.XPATH, IFRAME_XPATH)))
        self._update_final_endpoint()

    def wait_for_manual_session(self) -> None:
        """Espera o usuário finalizar o login e expor o formulário de aposta."""

        self.driver.switch_to.default_content()
        self.ensure_on_game()
        self._try_fill_credentials()
        try:
            WebDriverWait(self.driver, self.settings.session_ready_timeout).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, self.settings.session_ready_selector)),
                message="Aguardando sessão logada e formulário habilitado",
            )
        except TimeoutException as exc:
            raise TimeoutException(
                "O navegador aberto não parece estar autenticado ou com o jogo carregado. "
                "Finalize o login manualmente e verifique se o formulário de aposta está ativo."
            ) from exc
        self._update_final_endpoint()

    def _read_header_value(self) -> str:
        element = self.wait.until(EC.presence_of_element_located((By.XPATH, BET_HEADER_XPATH)))
        return element.text

    def _get_current_multipliers(self) -> List[str]:
        for attempt in range(3):
            try:
                elements = self.wait.until(
                    EC.presence_of_all_elements_located((By.CSS_SELECTOR, MULTIPLIER_SELECTOR))
                )
                return [e.text for e in elements if e.text]
            except StaleElementReferenceException:
                time.sleep(1)
        raise NoSuchElementException("Unable to read current multipliers after retries")

    def stream_multipliers(self, timeout: float = 30.0) -> Generator[List[float], None, None]:
        """Yield new multiplier batches as soon as the round encerra.

        Uses the header value to detect a finished round (value equals "0") and
        waits for DOM updates to avoid busy looping.
        """

        while True:
            try:
                self.wait.until(lambda _: self._read_header_value() == "0")
                raw_multipliers = self._get_current_multipliers()
                if raw_multipliers != self.state.last_multipliers:
                    raw_multipliers.reverse()
                    self.state.last_multipliers = list(raw_multipliers)
                    yield [float(item.rstrip("x")) for item in raw_multipliers]
            except TimeoutException:
                # Resync frame in case the game reloads
                try:
                    self.driver.switch_to.default_content()
                    self.ensure_on_game()
                except Exception:
                    pass
            time.sleep(0.5)

    def place_bet(self, amount: float, cashout_target: float) -> bool:
        """Attempt to set the bet amount and trigger a bet/cashout.

        Returns True if elements were found and clicked; False otherwise.
        """

        try:
            self.driver.switch_to.default_content()
            self.wait.until(EC.frame_to_be_available_and_switch_to_it((By.XPATH, IFRAME_XPATH)))

            amount_input = self.wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, self.settings.bet_input_selector))
            )
            amount_input.clear()
            amount_input.send_keys(str(amount))
            amount_input.send_keys(Keys.TAB)

            bet_button = self.wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, self.settings.bet_button_selector))
            )
            bet_button.click()

            cashout_button = self.wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, self.settings.cashout_button_selector))
            )
            cashout_button.send_keys(str(cashout_target))
            return True
        except Exception:
            return False

    def close(self) -> None:
        self.driver.quit()
