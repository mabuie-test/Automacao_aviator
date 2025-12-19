"""Prediction model that mirrors the legacy FastTree approach using scikit-learn."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Sequence, Tuple

import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split


@dataclass
class MultiplierModel:
    time_steps: int = 10
    n_estimators: int = 50
    random_state: int = 42

    def __post_init__(self) -> None:
        self._model = RandomForestRegressor(
            n_estimators=self.n_estimators,
            random_state=self.random_state,
        )

    def _build_windows(self, multipliers: Sequence[float]) -> Tuple[np.ndarray, np.ndarray]:
        series = np.array(multipliers, dtype=float)
        if len(series) <= self.time_steps:
            raise ValueError("Not enough multipliers to build training windows")

        features: List[np.ndarray] = []
        labels: List[float] = []

        for start in range(len(series) - self.time_steps):
            window = series[start : start + self.time_steps]
            target = series[start + self.time_steps]
            features.append(window)
            labels.append(target)

        return np.vstack(features), np.array(labels)

    def fit(self, multipliers: Sequence[float]) -> None:
        X, y = self._build_windows(multipliers)
        X_train, _, y_train, _ = train_test_split(
            X, y, test_size=0.2, random_state=self.random_state
        )
        self._model.fit(X_train, y_train)

    def predict_next(self, recent_multipliers: Sequence[float]) -> Tuple[float, float]:
        if len(recent_multipliers) < self.time_steps:
            return 1.0, 0.0

        window = np.array(list(recent_multipliers)[-self.time_steps :], dtype=float)
        prediction = float(self._model.predict([window])[0])

        # Confidence is inversely proportional to the spread in the window.
        spread = float(window.max() - window.min()) or 1.0
        confidence = max(0.0, min(1.0, 1 - spread / max(window.mean(), 1.0)))
        return max(1.0, prediction), confidence

    def fit_and_predict(self, multipliers: Sequence[float], recent_multipliers: Sequence[float]) -> Tuple[float, float]:
        self.fit(multipliers)
        return self.predict_next(recent_multipliers)
