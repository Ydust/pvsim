"""分时电价（峰/平/谷）+ 余电上网价。

算电费、算储能套利都要它。数值取中国工商业分时电价的代表量级(元/kWh)，
不同省份/年份差异大，这里给一组可改的典型值：
    峰 ~1.20、平 ~0.75、谷 ~0.35；余电上网(卖给电网) ~0.40。
谷电便宜→晚上充电池/充车划算；峰电贵→白天放电/自发自用划算——这是套利的来源。
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd


@dataclass
class Tariff:
    peak_price: float = 1.20         # 峰电价 元/kWh
    flat_price: float = 0.75         # 平电价
    valley_price: float = 0.35       # 谷电价
    feed_in_price: float = 0.30      # 余电上网价(卖电); 取 ≤ 谷电价, 否则优化器会
                                     # "谷段买电原价卖回"无限套利(现实中电表净计量, 不可能)
    # 时段划分(小时, 左闭右开)；其余为平段
    peak_hours: tuple = (8, 11, 18, 21)      # 8-11 与 18-21 为峰
    valley_hours: tuple = (23, 24, 0, 7)     # 23-次日7 为谷

    def _period_of(self, h: int) -> str:
        ph = self.peak_hours
        if (ph[0] <= h < ph[1]) or (ph[2] <= h < ph[3]):
            return "peak"
        # 谷: 23-24 或 0-7
        if h >= self.valley_hours[0] or h < self.valley_hours[3]:
            return "valley"
        return "flat"

    def price_of(self, h: int) -> float:
        return {"peak": self.peak_price, "flat": self.flat_price,
                "valley": self.valley_price}[self._period_of(h)]


def buy_price_series(times: pd.DatetimeIndex, tariff: Tariff | None = None) -> pd.Series:
    """逐时购电价 (元/kWh)。"""
    tariff = tariff or Tariff()
    times = pd.DatetimeIndex(times)
    prices = np.array([tariff.price_of(int(h)) for h in times.hour])
    return pd.Series(prices, index=times, name="buy_price")


def period_series(times: pd.DatetimeIndex, tariff: Tariff | None = None) -> pd.Series:
    """逐时时段标签(peak/flat/valley)，用于调度判断。"""
    tariff = tariff or Tariff()
    times = pd.DatetimeIndex(times)
    labs = [tariff._period_of(int(h)) for h in times.hour]
    return pd.Series(labs, index=times, name="period")
