"""中国 31 省 (含直辖市) 代表城市表 — 用于省级物理仿真扩展.

每省取一个代表城市 (省会优先), 含 lat/lon/alt 用于 PVGIS TMY 拉取.
12 已有 (复用 cities.py 缓存), 19 个新增. 首次运行会自动拉取 PVGIS 数据.

资源带划分:
  辐照带: 西部高原戈壁(I) > 西北中部(II) > 华北华南(III) > 川黔重雾(IV)
  气候带: 寒冷北方/中部/南方亚热带/热带
"""

from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class Province:
    name: str          # 省份中文
    city: str          # 代表城市
    key: str           # PVGIS 缓存 key (拼音)
    lat: float
    lon: float
    alt: float         # m
    region: str        # 行政地理分区
    res_band: str      # 太阳能资源带 I/II/III/IV (国家电网划分)


PROVINCES = [
    # 已有 12 个 (复用 PVGIS 缓存)
    Province("北京",   "北京",   "beijing",    39.90, 116.41,   50, "华北", "III"),
    Province("黑龙江", "哈尔滨", "harbin",     45.75, 126.63,  150, "东北", "III"),
    Province("湖北",   "武汉",   "wuhan",      30.59, 114.30,   30, "华中", "IV"),
    Province("上海",   "上海",   "shanghai",   31.23, 121.47,   10, "华东", "III"),
    Province("广东",   "广州",   "guangzhou",  23.13, 113.26,   20, "华南", "III"),
    Province("海南",   "海口",   "haikou",     20.04, 110.32,   15, "华南", "III"),
    Province("四川",   "成都",   "chengdu",    30.67, 104.07,  500, "西南", "IV"),
    Province("云南",   "昆明",   "kunming",    25.04, 102.71, 1890, "西南", "II"),
    Province("西藏",   "拉萨",   "lhasa",      29.65,  91.14, 3650, "西部", "I"),
    Province("宁夏",   "银川",   "yinchuan",   38.49, 106.23, 1110, "西北", "II"),
    Province("新疆",   "乌鲁木齐", "urumqi",   43.83,  87.62,  900, "西北", "II"),
    Province("甘肃",   "敦煌",   "dunhuang",   40.14,  94.66, 1140, "西北", "I"),

    # 新增 19 个 (首次运行将从 PVGIS 拉取)
    Province("天津",   "天津",   "tianjin",    39.13, 117.20,    5, "华北", "III"),
    Province("河北",   "石家庄", "shijiazhuang", 38.04, 114.51,  80, "华北", "III"),
    Province("山西",   "太原",   "taiyuan",    37.87, 112.55,  780, "华北", "II"),
    Province("内蒙古", "呼和浩特", "hohhot",    40.84, 111.75, 1064, "华北", "II"),
    Province("辽宁",   "沈阳",   "shenyang",   41.80, 123.43,   50, "东北", "III"),
    Province("吉林",   "长春",   "changchun",  43.82, 125.32,  220, "东北", "III"),
    Province("江苏",   "南京",   "nanjing",    32.05, 118.79,   20, "华东", "III"),
    Province("浙江",   "杭州",   "hangzhou",   30.27, 120.15,   10, "华东", "III"),
    Province("安徽",   "合肥",   "hefei",      31.83, 117.23,   30, "华东", "III"),
    Province("福建",   "福州",   "fuzhou",     26.07, 119.30,   15, "华东", "III"),
    Province("江西",   "南昌",   "nanchang",   28.68, 115.86,   25, "华中", "III"),
    Province("山东",   "济南",   "jinan",      36.65, 117.00,   50, "华东", "III"),
    Province("河南",   "郑州",   "zhengzhou",  34.75, 113.62,  100, "华中", "III"),
    Province("湖南",   "长沙",   "changsha",   28.20, 112.97,   40, "华中", "IV"),
    Province("广西",   "南宁",   "nanning",    22.82, 108.36,   80, "华南", "III"),
    Province("重庆",   "重庆",   "chongqing",  29.55, 106.55,  240, "西南", "IV"),
    Province("贵州",   "贵阳",   "guiyang",    26.65, 106.63, 1100, "西南", "IV"),
    Province("陕西",   "西安",   "xian",       34.27, 108.93,  400, "西北", "III"),
    Province("青海",   "西宁",   "xining",     36.62, 101.78, 2260, "西北", "II"),
]

# 省份中英文 / GB 2 字母代码 (英文图用)
PROVINCE_EN = {
    "北京": "Beijing", "天津": "Tianjin", "河北": "Hebei", "山西": "Shanxi",
    "内蒙古": "Nei Mongol", "辽宁": "Liaoning", "吉林": "Jilin", "黑龙江": "Heilongjiang",
    "上海": "Shanghai", "江苏": "Jiangsu", "浙江": "Zhejiang", "安徽": "Anhui",
    "福建": "Fujian", "江西": "Jiangxi", "山东": "Shandong", "河南": "Henan",
    "湖北": "Hubei", "湖南": "Hunan", "广东": "Guangdong", "广西": "Guangxi",
    "海南": "Hainan", "重庆": "Chongqing", "四川": "Sichuan", "贵州": "Guizhou",
    "云南": "Yunnan", "西藏": "Tibet", "陕西": "Shaanxi", "甘肃": "Gansu",
    "青海": "Qinghai", "宁夏": "Ningxia", "新疆": "Xinjiang",
}
PROVINCE_CODE = {
    "北京": "BJ", "天津": "TJ", "河北": "HE", "山西": "SX", "内蒙古": "NM",
    "辽宁": "LN", "吉林": "JL", "黑龙江": "HL", "上海": "SH", "江苏": "JS",
    "浙江": "ZJ", "安徽": "AH", "福建": "FJ", "江西": "JX", "山东": "SD",
    "河南": "HA", "湖北": "HB", "湖南": "HN", "广东": "GD", "广西": "GX",
    "海南": "HI", "重庆": "CQ", "四川": "SC", "贵州": "GZ", "云南": "YN",
    "西藏": "XZ", "陕西": "SN", "甘肃": "GS", "青海": "QH", "宁夏": "NX",
    "新疆": "XJ",
}

# 省级 2024 光伏并网容量, 来自国家能源局 2024 年光伏发电建设情况。
# 原表单位为万千瓦, 此处转换为 GW。
# 新疆值合并原表中的新疆和新疆兵团, 以保持 31 省口径。
# 主文图件使用同一省级分布, 并统一缩放到全国总量, 以保证容量加权闭合。
NATIONAL_PV_2024_GW = 886.6
RAW_PROVINCE_PV_2024_GW = {
    "山东": 76.134, "河北": 72.024, "江苏": 61.647, "浙江": 47.275,
    "山西": 34.768, "内蒙古": 48.109, "新疆": 56.748, "宁夏": 26.240,
    "青海": 36.420, "甘肃": 31.388, "陕西": 34.330, "河南": 43.491,
    "安徽": 43.113, "广东": 41.155, "福建": 12.583, "江西": 25.639,
    "湖南": 18.734, "湖北": 35.100, "广西": 20.523, "海南": 7.408,
    "云南": 37.230, "贵州": 19.856, "四川": 10.823, "重庆": 3.098,
    "辽宁": 12.139, "吉林": 5.830, "黑龙江": 7.171,
    "北京": 1.303, "天津": 7.241, "上海": 4.114, "西藏": 4.039,
}
PROVINCE_PV_2024_SCALE = NATIONAL_PV_2024_GW / sum(RAW_PROVINCE_PV_2024_GW.values())
PROVINCE_PV_2024_GW = {
    prov: gw * PROVINCE_PV_2024_SCALE
    for prov, gw in RAW_PROVINCE_PV_2024_GW.items()
}
