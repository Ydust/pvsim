"""Representative cities and geographic coordinates."""

from __future__ import annotations

from pvsim.labels import label as _text_label

from dataclasses import dataclass


@dataclass(frozen=True)
class City:
    name: str
    key: str
    lat: float
    lon: float
    alt: float
    note: str


CITIES = [
    City(_text_label('lhasa'), "lhasa", 29.65, 91.14, 3650, _text_label('cities_text')),
    City(_text_label('urumqi'), "urumqi", 43.83, 87.62, 900, _text_label('cities_text_2')),
    City(_text_label('dunhuang'), "dunhuang", 40.14, 94.66, 1140, _text_label('cities_text_3')),
    City(_text_label('yinchuan'), "yinchuan", 38.49, 106.23, 1110, _text_label('cities_text_4')),
    City(_text_label('haerbin'), "harbin", 45.75, 126.63, 150, _text_label('cities_text_5')),
    City(_text_label('beijing'), "beijing", 39.90, 116.41, 50, _text_label('cities_text_6')),
    City(_text_label('chengdu'), "chengdu", 30.67, 104.07, 500, _text_label('cities_text_7')),
    City(_text_label('wuhan'), "wuhan", 30.59, 114.30, 30, _text_label('cities_text_8')),
    City(_text_label('shanghai'), "shanghai", 31.23, 121.47, 10, _text_label('cities_text_9')),
    City(_text_label('kunming'), "kunming", 25.04, 102.71, 1890, _text_label('cities_text_10')),
    City(_text_label('guangzhou'), "guangzhou", 23.13, 113.26, 20, _text_label('cities_text_11')),
    City(_text_label('haikou'), "haikou", 20.04, 110.32, 15, _text_label('cities_text_12')),
]
