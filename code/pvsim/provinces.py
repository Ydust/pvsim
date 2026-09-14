"""Provincial representative cities and PV capacity."""

from __future__ import annotations

from pvsim.labels import label as _text_label
from dataclasses import dataclass


@dataclass(frozen=True)
class Province:
    name: str
    city: str
    key: str
    lat: float
    lon: float
    alt: float         # m
    region: str
    res_band: str


PROVINCES = [

    Province(_text_label('beijing'),   _text_label('beijing'),   "beijing",    39.90, 116.41,   50, _text_label('provinces_text'), "III"),
    Province(_text_label('heilongjiang'), _text_label('haerbin'), "harbin",     45.75, 126.63,  150, _text_label('provinces_text_2'), "III"),
    Province(_text_label('hubei'),   _text_label('wuhan'),   "wuhan",      30.59, 114.30,   30, _text_label('provinces_text_3'), "IV"),
    Province(_text_label('shanghai'),   _text_label('shanghai'),   "shanghai",   31.23, 121.47,   10, _text_label('provinces_text_4'), "III"),
    Province(_text_label('guangdong'),   _text_label('guangzhou'),   "guangzhou",  23.13, 113.26,   20, _text_label('provinces_text_5'), "III"),
    Province(_text_label('hainan'),   _text_label('haikou'),   "haikou",     20.04, 110.32,   15, _text_label('provinces_text_5'), "III"),
    Province(_text_label('sichuan'),   _text_label('chengdu'),   "chengdu",    30.67, 104.07,  500, _text_label('provinces_text_6'), "IV"),
    Province(_text_label('yunnan'),   _text_label('kunming'),   "kunming",    25.04, 102.71, 1890, _text_label('provinces_text_6'), "II"),
    Province(_text_label('tibet'),   _text_label('lhasa'),   "lhasa",      29.65,  91.14, 3650, _text_label('provinces_text_7'), "I"),
    Province(_text_label('ningxia'),   _text_label('yinchuan'),   "yinchuan",   38.49, 106.23, 1110, _text_label('provinces_text_8'), "II"),
    Province(_text_label('xinjiang'),   _text_label('urumqi'), "urumqi",   43.83,  87.62,  900, _text_label('provinces_text_8'), "II"),
    Province(_text_label('gansu'),   _text_label('dunhuang'),   "dunhuang",   40.14,  94.66, 1140, _text_label('provinces_text_8'), "I"),


    Province(_text_label('tianjin'),   _text_label('tianjin'),   "tianjin",    39.13, 117.20,    5, _text_label('provinces_text'), "III"),
    Province(_text_label('hebei'),   _text_label('shijiazhuang'), "shijiazhuang", 38.04, 114.51,  80, _text_label('provinces_text'), "III"),
    Province(_text_label('shanxi'),   _text_label('taiyuan'),   "taiyuan",    37.87, 112.55,  780, _text_label('provinces_text'), "II"),
    Province(_text_label('nei_mongol'), _text_label('hohhot'), "hohhot",    40.84, 111.75, 1064, _text_label('provinces_text'), "II"),
    Province(_text_label('liaoning'),   _text_label('shenyang'),   "shenyang",   41.80, 123.43,   50, _text_label('provinces_text_2'), "III"),
    Province(_text_label('jilin'),   _text_label('changchun'),   "changchun",  43.82, 125.32,  220, _text_label('provinces_text_2'), "III"),
    Province(_text_label('jiangsu'),   _text_label('nanjing'),   "nanjing",    32.05, 118.79,   20, _text_label('provinces_text_4'), "III"),
    Province(_text_label('zhejiang'),   _text_label('hangzhou'),   "hangzhou",   30.27, 120.15,   10, _text_label('provinces_text_4'), "III"),
    Province(_text_label('anhui'),   _text_label('hefei'),   "hefei",      31.83, 117.23,   30, _text_label('provinces_text_4'), "III"),
    Province(_text_label('fujian'),   _text_label('fuzhou'),   "fuzhou",     26.07, 119.30,   15, _text_label('provinces_text_4'), "III"),
    Province(_text_label('jiangxi'),   _text_label('nanchang'),   "nanchang",   28.68, 115.86,   25, _text_label('provinces_text_3'), "III"),
    Province(_text_label('shandong'),   _text_label('jinan'),   "jinan",      36.65, 117.00,   50, _text_label('provinces_text_4'), "III"),
    Province(_text_label('henan'),   _text_label('zhengzhou'),   "zhengzhou",  34.75, 113.62,  100, _text_label('provinces_text_3'), "III"),
    Province(_text_label('hunan'),   _text_label('changsha'),   "changsha",   28.20, 112.97,   40, _text_label('provinces_text_3'), "IV"),
    Province(_text_label('guangxi'),   _text_label('nanning'),   "nanning",    22.82, 108.36,   80, _text_label('provinces_text_5'), "III"),
    Province(_text_label('chongqing'),   _text_label('chongqing'),   "chongqing",  29.55, 106.55,  240, _text_label('provinces_text_6'), "IV"),
    Province(_text_label('guizhou'),   _text_label('guiyang'),   "guiyang",    26.65, 106.63, 1100, _text_label('provinces_text_6'), "IV"),
    Province(_text_label('shaanxi'),   _text_label('xi_an'),   "xian",       34.27, 108.93,  400, _text_label('provinces_text_8'), "III"),
    Province(_text_label('qinghai'),   _text_label('xining'),   "xining",     36.62, 101.78, 2260, _text_label('provinces_text_8'), "II"),
]


PROVINCE_EN = {
    _text_label('beijing'): "Beijing", _text_label('tianjin'): "Tianjin", _text_label('hebei'): "Hebei", _text_label('shanxi'): "Shanxi",
    _text_label('nei_mongol'): "Nei Mongol", _text_label('liaoning'): "Liaoning", _text_label('jilin'): "Jilin", _text_label('heilongjiang'): "Heilongjiang",
    _text_label('shanghai'): "Shanghai", _text_label('jiangsu'): "Jiangsu", _text_label('zhejiang'): "Zhejiang", _text_label('anhui'): "Anhui",
    _text_label('fujian'): "Fujian", _text_label('jiangxi'): "Jiangxi", _text_label('shandong'): "Shandong", _text_label('henan'): "Henan",
    _text_label('hubei'): "Hubei", _text_label('hunan'): "Hunan", _text_label('guangdong'): "Guangdong", _text_label('guangxi'): "Guangxi",
    _text_label('hainan'): "Hainan", _text_label('chongqing'): "Chongqing", _text_label('sichuan'): "Sichuan", _text_label('guizhou'): "Guizhou",
    _text_label('yunnan'): "Yunnan", _text_label('tibet'): "Tibet", _text_label('shaanxi'): "Shaanxi", _text_label('gansu'): "Gansu",
    _text_label('qinghai'): "Qinghai", _text_label('ningxia'): "Ningxia", _text_label('xinjiang'): "Xinjiang",
}
PROVINCE_CODE = {
    _text_label('beijing'): "BJ", _text_label('tianjin'): "TJ", _text_label('hebei'): "HE", _text_label('shanxi'): "SX", _text_label('nei_mongol'): "NM",
    _text_label('liaoning'): "LN", _text_label('jilin'): "JL", _text_label('heilongjiang'): "HL", _text_label('shanghai'): "SH", _text_label('jiangsu'): "JS",
    _text_label('zhejiang'): "ZJ", _text_label('anhui'): "AH", _text_label('fujian'): "FJ", _text_label('jiangxi'): "JX", _text_label('shandong'): "SD",
    _text_label('henan'): "HA", _text_label('hubei'): "HB", _text_label('hunan'): "HN", _text_label('guangdong'): "GD", _text_label('guangxi'): "GX",
    _text_label('hainan'): "HI", _text_label('chongqing'): "CQ", _text_label('sichuan'): "SC", _text_label('guizhou'): "GZ", _text_label('yunnan'): "YN",
    _text_label('tibet'): "XZ", _text_label('shaanxi'): "SN", _text_label('gansu'): "GS", _text_label('qinghai'): "QH", _text_label('ningxia'): "NX",
    _text_label('xinjiang'): "XJ",
}


NATIONAL_PV_2024_GW = 886.6
RAW_PROVINCE_PV_2024_GW = {
    _text_label('shandong'): 76.134, _text_label('hebei'): 72.024, _text_label('jiangsu'): 61.647, _text_label('zhejiang'): 47.275,
    _text_label('shanxi'): 34.768, _text_label('nei_mongol'): 48.109, _text_label('xinjiang'): 56.748, _text_label('ningxia'): 26.240,
    _text_label('qinghai'): 36.420, _text_label('gansu'): 31.388, _text_label('shaanxi'): 34.330, _text_label('henan'): 43.491,
    _text_label('anhui'): 43.113, _text_label('guangdong'): 41.155, _text_label('fujian'): 12.583, _text_label('jiangxi'): 25.639,
    _text_label('hunan'): 18.734, _text_label('hubei'): 35.100, _text_label('guangxi'): 20.523, _text_label('hainan'): 7.408,
    _text_label('yunnan'): 37.230, _text_label('guizhou'): 19.856, _text_label('sichuan'): 10.823, _text_label('chongqing'): 3.098,
    _text_label('liaoning'): 12.139, _text_label('jilin'): 5.830, _text_label('heilongjiang'): 7.171,
    _text_label('beijing'): 1.303, _text_label('tianjin'): 7.241, _text_label('shanghai'): 4.114, _text_label('tibet'): 4.039,
}
PROVINCE_PV_2024_SCALE = NATIONAL_PV_2024_GW / sum(RAW_PROVINCE_PV_2024_GW.values())
PROVINCE_PV_2024_GW = {
    prov: gw * PROVINCE_PV_2024_SCALE
    for prov, gw in RAW_PROVINCE_PV_2024_GW.items()
}
