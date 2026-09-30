"""Состояние игры: очки, прогресс, история."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Level:
    """Один уровень Режима A."""
    name: str
    target_corr: float          # целевая |r0|, например 0.75
    hold_seconds: float         # сколько секунд удержать
    description: str


@dataclass
class GameState:
    """Общее состояние партии."""
    levels: list[Level]
    current: int = 0
    score: int = 0
    hold_progress: float = 0.0
    history: list[tuple[float, float]] = field(default_factory=list)
    finished: bool = False

    @property
    def active_level(self) -> Level:
        # защита от выхода за границы после победы
        idx = min(self.current, len(self.levels) - 1)
        return self.levels[idx]

    def update(self, corr: float, dt: float) -> str:
        """Обновить прогресс. Вернуть событие: 'hold', 'win', 'level_up', 'miss', 'done'."""
        if self.finished:
            return "done"

        lvl = self.active_level
        ok = abs(corr) >= lvl.target_corr

        if ok:
            self.hold_progress += dt
        else:
            self.hold_progress = max(0.0, self.hold_progress - dt * 0.5)

        if self.hold_progress >= lvl.hold_seconds:
            self.score += 100
            self.current += 1
            self.hold_progress = 0.0
            if self.current >= len(self.levels):
                self.finished = True
                return "win"
            return "level_up"
        return "hold" if ok else "miss"


def default_levels() -> list[Level]:
    return [
        Level("Разминка",    0.50, 2.0, "Свяжи датчики: удержи |r| ≥ 0.50 две секунды"),
        Level("Синхрон",     0.75, 3.0, "Удержи |r| ≥ 0.75 три секунды"),
        Level("Крепкая связь", 0.90, 2.0, "Доберись до |r| ≥ 0.90 и удержись"),
        Level("Обратный ход", 0.80, 3.0, "Не важно в какую сторону — главное крепко"),
    ]