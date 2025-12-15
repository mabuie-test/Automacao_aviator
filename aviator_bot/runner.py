"""Command-line entrypoint that wires the scraper, database and model together."""

from __future__ import annotations

import argparse
import logging
import sys
import time
import urllib.request
from typing import Iterable, List

from . import config, db
from .model import MultiplierModel
from .scraper import MultiplierScraper
from .strategy import RiskManager

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s %(name)s: %(message)s",
)
LOGGER = logging.getLogger("aviator-bot")


def backfill_from_files(paths: Iterable[str]) -> List[float]:
    multipliers: List[float] = []
    for path in paths:
        try:
            with open(path, "r", encoding="utf-8") as handle:
                contents = handle.read().strip().rstrip(",")
                if contents:
                    multipliers.extend(float(x.rstrip("x")) for x in contents.split(",") if x)
        except FileNotFoundError:
            LOGGER.warning("Arquivo %s não encontrado; ignorando", path)
    return multipliers


def ensure_browser_debug_port(host: str, port: int) -> None:
    url = f"http://{host}:{port}/json/version"
    try:
        with urllib.request.urlopen(url, timeout=3) as response:
            if response.status != 200:
                raise RuntimeError(f"Chrome respondeu com status {response.status} no debug endpoint")
    except Exception as exc:  # pylint: disable=broad-except
        raise RuntimeError(
            "Não foi possível comunicar com a sessão do navegador já aberta (Opera/Chrome/Edge). "
            "Inicie-o com --remote-debugging-port e mantenha a janela logada no jogo."
        ) from exc


def check_dependencies(settings=None) -> None:
    """Validate storage e sessão de navegador antes de iniciar."""

    cfg = settings or config.get_settings()
    LOGGER.info("Verificando arquivo de dados local (JSON) em %s", cfg.data_path)
    db.ping(cfg)
    LOGGER.info(
        "Verificando sessão do navegador em %s:%s",
        cfg.chrome_debug_host,
        cfg.chrome_debug_port,
    )
    ensure_browser_debug_port(cfg.chrome_debug_host, cfg.chrome_debug_port)


def run_loop(time_steps: int, warmup_seconds: int, settings=None) -> None:
    cfg = settings or config.get_settings()
    LOGGER.info("Checando armazenamento local e sessão do navegador antes de iniciar loop")
    check_dependencies(cfg)

    LOGGER.info("Inicializando arquivo de dados se necessário")
    db.initialize_schema(cfg)

    model = MultiplierModel(time_steps=time_steps)
    risk = RiskManager(
        base_bet=cfg.base_bet,
        max_bet=cfg.max_bet,
        confidence_floor=cfg.confidence_floor,
        streak_window=cfg.streak_window,
    )
    scraper = MultiplierScraper(settings=cfg)
    enforced_warmup = max(120, warmup_seconds)
    if enforced_warmup != warmup_seconds:
        LOGGER.warning(
            "Warmup ajustado para %ss para garantir pelo menos 2 minutos de coleta antes de apostar",
            enforced_warmup,
        )

    warmup_until = time.monotonic() + enforced_warmup
    try:
        LOGGER.info(
            "Aguardando você concluir o login no navegador aberto (timeout %ss)",
            cfg.session_ready_timeout,
        )
        scraper.wait_for_manual_session()
        LOGGER.info("Sessão confirmada; iniciando coleta e aquecimento de %ss", enforced_warmup)
        for new_values in scraper.stream_multipliers():
            inserted = db.insert_multipliers(new_values, cfg)
            LOGGER.info("Inseridos %s novos multiplicadores", inserted)

            history = db.fetch_recent_multipliers(limit=max(time_steps * 3, 50), settings=cfg)
            if len(history) > time_steps:
                prediction, confidence = model.fit_and_predict(history, history[-time_steps:])
                decision = risk.decide(
                    prediction,
                    confidence,
                    history[-max(cfg.streak_window * 2, time_steps) :],
                )
                LOGGER.info(
                    "Odd de colapso prevista para a próxima rodada: %.2fx (confiança %.2f)",
                    prediction,
                    confidence,
                )
                LOGGER.info(
                    "Próximo alvo: %.2fx (confiança %.2f) | Stake sugerido: %.2f | Racional: %s",
                    decision.prediction,
                    decision.confidence,
                    decision.stake,
                    decision.rationale,
                )

                in_warmup = time.monotonic() < warmup_until
                if in_warmup:
                    remaining = max(0, int(warmup_until - time.monotonic()))
                    LOGGER.info(
                        "Modo observação ativo por %ss restantes; nenhuma aposta automática será enviada",
                        remaining,
                    )
                elif decision.should_bet and cfg.auto_bet:
                    clicked = scraper.place_bet(decision.stake, decision.cashout_target)
                    LOGGER.info(
                        "Auto-bet %s (%.2f @ %.2f)",
                        "confirmado" if clicked else "falhou",
                        decision.stake,
                        decision.cashout_target,
                    )
    finally:
        scraper.close()


def cli(argv: List[str]) -> int:
    parser = argparse.ArgumentParser(description="Aviator bot em Python com armazenamento local")
    parser.add_argument(
        "--time-steps",
        type=int,
        default=10,
        help="Número de multiplicadores usados como janela de previsão",
    )
    parser.add_argument(
        "--seed-data",
        nargs="*",
        help="Arquivos de texto com multiplicadores para preencher o histórico local antes de rodar",
    )
    parser.add_argument(
        "--warmup-seconds",
        type=int,
        default=config.get_settings().warmup_seconds,
        help="Tempo em segundos apenas coletando dados antes de permitir auto-bet (mínimo 120s)",
    )
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Apenas valida o arquivo de dados e a sessão do navegador e encerra",
    )

    args = parser.parse_args(argv)

    if args.seed_data:
        seeds = backfill_from_files(args.seed_data)
        if seeds:
            cfg = config.get_settings()
            db.initialize_schema(cfg)
            inserted = db.insert_multipliers(seeds, cfg)
            LOGGER.info("Pré-carregados %s multiplicadores dos arquivos de treino", inserted)

    if args.check_only:
        check_dependencies(config.get_settings())
        LOGGER.info("Verificações concluídas com sucesso; encerrando por --check-only")
        return 0

    try:
        run_loop(args.time_steps, warmup_seconds=args.warmup_seconds, settings=config.get_settings())
    except KeyboardInterrupt:
        LOGGER.info("Encerrado pelo usuário")
    return 0


def main() -> None:
    raise SystemExit(cli(sys.argv[1:]))


if __name__ == "__main__":
    main()
