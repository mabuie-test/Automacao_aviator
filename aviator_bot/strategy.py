"""Simple risk and staking strategy for Aviator automation.

The strategy scales the stake based on model confidence and caps exposure to
avoid runaway losses. It does not guarantee winnings but provides a consistent
decision surface for the runner to act on.
"""

from __future__ import annotations

from dataclasses import dataclass
from statistics import mean, pstdev
from typing import Sequence


@dataclass
class StrategyDecision:
    prediction: float
    confidence: float
    stake: float
    cashout_target: float
    should_bet: bool
    rationale: str


class RiskManager:
    def __init__(
        self,
        base_bet: float = 1.0,
        max_bet: float = 25.0,
        confidence_floor: float = 0.35,
        kelly_scale: float = 0.35,
        streak_window: int = 8,
    ) -> None:
        self.base_bet = base_bet
        self.max_bet = max_bet
        self.confidence_floor = confidence_floor
        self.kelly_scale = kelly_scale
        self.streak_window = max(3, streak_window)

    def decide(
        self, prediction: float, confidence: float, recent_history: Sequence[float]
    ) -> StrategyDecision:
        tail = list(recent_history)[-max(self.streak_window * 2, 1) :]
        volatility = pstdev(tail) if len(tail) > 1 else 0.0

        dynamic_floor = self.confidence_floor + (0.05 if volatility > 0.75 else 0)
        should_bet = confidence >= dynamic_floor and prediction >= 1.15
        if not should_bet:
            return StrategyDecision(
                prediction=prediction,
                confidence=confidence,
                stake=0.0,
                cashout_target=max(1.0, prediction),
                should_bet=False,
                rationale="Confiança abaixo do piso ou previsão baixa",
            )

        streak_tail = tail[-self.streak_window :]
        midpoint = len(streak_tail) // 2 or 1
        early_avg = mean(streak_tail[:midpoint]) if streak_tail else 1.0
        late_avg = mean(streak_tail[midpoint:]) if streak_tail else 1.0
        trend_bias = late_avg - early_avg

        busts = [value for value in streak_tail if value < 1.5]
        bust_ratio = len(busts) / len(streak_tail) if streak_tail else 0.0

        # Kelly-inspired sizing: higher confidence increases exposure but capped
        edge = max(0.0, confidence - self.confidence_floor)
        fraction = min(1.0, self.kelly_scale * edge / max(1e-3, 1 - self.confidence_floor))
        trend_multiplier = 1.0 + (0.18 if trend_bias > 0 else -0.12)
        volatility_brake = 1.0 - min(0.35, volatility / 4)
        bust_brake = 1.0 - min(0.25, bust_ratio)

        stake = max(
            self.base_bet,
            min(
                self.max_bet,
                self.base_bet
                * (1 + fraction * 4)
                * trend_multiplier
                * volatility_brake
                * bust_brake,
            ),
        )

        # Ajusta o cashout conforme a tendência recente: sobe um pouco em alta
        # e aproxima em queda para proteger capital.
        cashout_target = prediction
        if trend_bias > 0:
            cashout_target = max(1.2, prediction * 1.08)
        elif trend_bias < 0 or bust_ratio > 0.3:
            cashout_target = max(1.2, prediction * 0.85)
        if volatility > 0.8:
            cashout_target = max(1.3, cashout_target * 0.95)

        return StrategyDecision(
            prediction=max(1.0, prediction),
            confidence=confidence,
            stake=round(stake, 2),
            cashout_target=max(1.2, round(cashout_target, 2)),
            should_bet=True,
            rationale=(
                "Stake ajustado por confiança/kelly + tendência (freio volatilidade/busts)"
                if trend_bias >= 0
                else "Stake reduzido por queda ou busts recentes"
            ),
        )
