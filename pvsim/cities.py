"""中国代表城市表（运行测试 + Unity 共用）。

覆盖不同太阳能资源区与气候带：高原/西北戈壁/东北寒冷/华北/盆地/华中/东部/南方/热带。
字段: 中文名, 缓存键(拼音), 纬度, 经度, 海拔(m), 特点。倾角默认取纬度(最优近似)。
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class City:
    name: str        # 中文名
    key: str         # 缓存/文件名(拼音)
    lat: float
    lon: float
    alt: float       # 海拔 m
    note: str        # 特点


CITIES = [
    City("拉萨", "lhasa", 29.65, 91.14, 3650, "高原·强辐照冷凉"),
    City("乌鲁木齐", "urumqi", 43.83, 87.62, 900, "西北·大陆性"),
    City("敦煌", "dunhuang", 40.14, 94.66, 1140, "西北戈壁·辐照强"),
    City("银川", "yinchuan", 38.49, 106.23, 1110, "宁夏·干燥多晴"),
    City("哈尔滨", "harbin", 45.75, 126.63, 150, "东北·高纬寒冷"),
    City("北京", "beijing", 39.90, 116.41, 50, "华北·四季分明"),
    City("成都", "chengdu", 30.67, 104.07, 500, "盆地·多云寡照"),
    City("武汉", "wuhan", 30.59, 114.30, 30, "华中·夏季湿热"),
    City("上海", "shanghai", 31.23, 121.47, 10, "东部·湿热夏季"),
    City("昆明", "kunming", 25.04, 102.71, 1890, "高原·四季如春"),
    City("广州", "guangzhou", 23.13, 113.26, 20, "南方·全年高温"),
    City("海口", "haikou", 20.04, 110.32, 15, "热带·全年最热"),
]
