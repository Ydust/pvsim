"""Electricity tariff schedules."""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd


@dataclass
class Tariff:
    peak_price: float = 1.20
    flat_price: float = 0.75
    valley_price: float = 0.35
    feed_in_price: float = 0.30


    peak_hours: tuple = (8, 11, 18, 21)
    valley_hours: tuple = (23, 24, 0, 7)

    def _period_of(self, h: int) -> str:
        ph = self.peak_hours
        if (ph[0] <= h < ph[1]) or (ph[2] <= h < ph[3]):
            return "peak"

        if h >= self.valley_hours[0] or h < self.valley_hours[3]:
            return "valley"
        return "flat"

    def price_of(self, h: int) -> float:
        return {"peak": self.peak_price, "flat": self.flat_price,
                "valley": self.valley_price}[self._period_of(h)]


def buy_price_series(times: pd.DatetimeIndex, tariff: Tariff | None = None) -> pd.Series:

    tariff = tariff or Tariff()
    times = pd.DatetimeIndex(times)
    prices = np.array([tariff.price_of(int(h)) for h in times.hour])
    return pd.Series(prices, index=times, name="buy_price")


def period_series(times: pd.DatetimeIndex, tariff: Tariff | None = None) -> pd.Series:

    tariff = tariff or Tariff()
    times = pd.DatetimeIndex(times)
    labs = [tariff._period_of(int(h)) for h in times.hour]
    return pd.Series(labs, index=times, name="period")
