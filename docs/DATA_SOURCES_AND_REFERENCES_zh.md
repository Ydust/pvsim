# 数据来源与引用文件系统梳理

最后更新：2026-07-05

文件用途：本文档系统整理本研究全部主要数据来源、源表、验证层、引用文档和审计边界。它是论文主体、支撑材料和复现包之间的数据索引。

## 一、总原则

本研究把数据分成五类。

| 类别 | 含义 | 是否作为输入 | 是否可直接支撑主结论 |
| --- | --- | --- | --- |
| 观测和官方统计数据 | 气象、装机、官方发电量、官方利用率、价格和份额历史 | 是 | 可支撑输入、校验和尺度约束 |
| 文献物理参数 | 器件效率、温度系数、带隙、退化、寿命、材料强度 | 是 | 可支撑物理建模 |
| 模型计算输出 | 年发电量、优势、分解、LCOE、替代路径 | 否 | 是研究结果，不是源数据 |
| 前瞻情景参数 | 学习率、成本下限、寿命突破、未来装机、脱碳路径 | 是 | 只能支撑情景分布，不能写成预测 |
| 审计和门控文件 | 源出处矩阵、外部验证审计、发布清单、测试 | 否 | 支撑可复现性和投稿可信度 |

最重要的边界是：完整政府逐省 PV 绝对发电量清单尚未取得。当前可用的是官方全国太阳能发电量、官方区域 PV 发电利用率、官方逐省总发电量和三峡能源公司资产 PV 发电样本。正文和支撑材料不能把这些层写成完整政府逐省 PV 发电量清单。

## 二、投稿直接使用的核心文档

| 文件 | 作用 | 投稿位置 |
| --- | --- | --- |
| `docs/PAPER_MAIN_COMPLETE.md` | 英文完整论文主体 | 主文稿 |
| `docs/PAPER_MAIN_COMPLETE_zh.md` | 中文完整论文主体 | 中文审读和内部修改 |
| `docs/SUPPORTING_INFORMATION_COMPLETE.md` | 英文完整支撑材料 | SI |
| `docs/SUPPORTING_INFORMATION_COMPLETE_zh.md` | 中文完整支撑材料 | 中文审读和内部修改 |
| `docs/RELEASE_MANIFEST.md` | 文件级发布清单和 SHA256 | 数据和代码可用性 |
| `outputs/release_manifest.csv` | 机器可读发布清单 | 归档清单 |

旧版文件 `docs/PAPER_C_draft.md`、`docs/PAPER_C_draft_zh.md` 和 `docs/SUPPORTING_INFORMATION_DRAFT.md` 保留为历史草稿。最终审读应优先看 complete 文件。

## 三、官方和观测类源数据

| 数据层 | 文件或位置 | 来源 | 用途 | 边界 |
| --- | --- | --- | --- | --- |
| 省级 2024 PV 装机 | `data/source_tables/provincial_pv_capacity_2024.csv` | 国家能源局 2024 年光伏建设官方表 | 容量加权、Fig 5 部署错配 | 源值合计 885.673 GW，统一缩放到 886.6 GW |
| NEA PV 发电利用率 | `data/source_tables/nea_pv_utilization_rate_2024.csv` | 国家能源局 2024 年可再生能源电力发展监测评价结果 | 官方 PV-specific 空间运行验证 | 是利用率，不是绝对发电量 |
| 省级机队利用小时 | `data/source_tables/provincial_fleet_hours_2024.csv` | 版本化系统级锚定表 | 机队级空间锚定 | 不作为官方逐行 release 证据 |
| 全国太阳能发电量和年末装机 | `outputs/si_national_external_validation.csv` | 国家统计局 2024 年统计公报 | 全国聚合 sanity check | 无空间轴 |
| 逐省总发电量 | `data/source_tables/nbs_provincial_total_power_generation_2024.csv` | 国家统计局中国统计年鉴 2025 表 9-19 | 官方空间绝对发电量背景 | 总发电量，不是 PV 发电量 |
| 三峡能源 PV 发电量 | `data/source_tables/ctgr_pv_generation_by_region_2024.csv` | 三峡能源 2024 年报，上交所披露 | PV-specific 绝对发电量样本 | 公司资产样本，不是全国政府清单 |
| PVGIS TMY 气象 | `data/tmy_cache/` | JRC PVGIS | 31 省锚点和代表城市逐时仿真 | 卫星反演和再分析驱动 |
| ERA5-Land 气象 | `data/era5_cache/` | ECMWF ERA5-Land | 0.1 degree 空间格局 | 只支撑空间型态和区域排序 |
| NASA POWER 气象 | `data/power_cache/` | NASA POWER | 网格稳健性和对照 | 粗分辨率辅助层 |
| ASTM G173 光谱 | 代码内参考和 pvlib 参考 | ASTM 和 NREL | AM1.5G 归一化 | 标准参考谱 |
| 2015 至 2024 装机历史 | 脚本和政策数据模块 | 国家能源局年度数据 | 替代模型校准 | 历史输入 |
| 组件价格和单晶份额 | `pvsim/policy_data.py` 和相关输出 | BNEF 和 ITRPV | 学习曲线和替代校准 | 前瞻外推需要情景化 |
| 电站坐标和容量 | GEM 数据层 | Global Energy Monitor | 真实部署分布参考 | 不提供实测发电量 |
| 电网排放因子 | 政策数据模块 | 生态环境部 | 碳背景和情景 | 非主线物理结论 |
| 铟和银材料数据 | 参数表和 SI | USGS 与文献 | 材料边界 | 主要作为 SI 边界 |

## 四、文献参数和引用基础

| 参数或模型 | 采用内容 | 主要引用 | 文件位置 |
| --- | --- | --- | --- |
| De Soto 单二极管模型 | 五参数电池模型 | De Soto 2006 | `pvsim/cell.py` |
| Faiman 温度模型 | 组件温度模型 | Faiman 2008 | `pvsim/temperature.py` |
| 光谱能量产出 | 光谱对不同 PV 技术的影响 | Dirnberger 2015 | `pvsim/spectral.py` |
| 温度系数物理 | 温度系数解释 | Dupre 2015 | `pvsim/materials.py` |
| 钙钛矿温度系数 | 单结钙钛矿中心参数 | Moot 2021 | `pvsim/materials.py` |
| 叠层温度系数 | 叠层温度参数 | Babics 2023 | `pvsim/materials.py` |
| 叠层技术经济 | 叠层 capex 和成本边界 | Cordell 2025 | `pvsim/economic_priors.py` |
| 多太瓦材料边界 | 铟和银强度 | Wagner 2024 | SI 材料边界 |
| 现代硅基准 | TOPCon、PERC、HJT 相关效率和温度系数 | ITRPV 2023 和 2024 | `docs/SI_SILICON_BASELINE_SENSITIVITY.md` |
| embodied carbon | PV 生命周期碳 | Fraunhofer ISE 和 IPCC AR6 | 碳边界图 |

引用审计见 `docs/REFERENCE_AUDIT.md`。核心 DOI 已进入引用检查表。

## 五、外部验证和审计文件

| 文件 | 作用 | 当前结论 |
| --- | --- | --- |
| `docs/SI_NATIONAL_EXTERNAL_VALIDATION.md` | 全国太阳能发电量外部校验 | NBS 2024 全国太阳能发电量 839.04 TWh |
| `docs/SI_PV_UTILIZATION_EXTERNAL_VALIDATION.md` | NEA 区域 PV 利用率验证 | 全国 2024 PV 利用率 96.8 percent，最低省级值 68.6 percent |
| `docs/SI_NBS_SPATIAL_GENERATION_VALIDATION.md` | NBS 逐省总发电量空间背景 | 31 省总发电量合计与全国表值闭合 |
| `docs/SI_CTGR_SPATIAL_PV_GENERATION_VALIDATION.md` | 三峡能源 PV 发电样本 | 25 个经营地区合计 25.40083 TWh |
| `docs/GOVERNMENT_PV_GENERATION_INVENTORY_AUDIT.md` | 完整政府逐省 PV 发电量清单获取审计 | 尚未取得 |
| `docs/SI_GOVERNMENT_PV_GENERATION_INVENTORY_VALIDATION.md` | 候选政府清单验证门控 | 当前 submission ready 为 False |
| `docs/NBS_MANUAL_EXPORT_PROTOCOL.md` | 国家统计局手动导出协议 | 等待官方导出表 |
| `docs/EXTERNAL_VALIDATION_AUDIT.md` | 本地外部验证可用性审计 | 有 PV 空间运行层和公司样本绝对发电层 |
| `docs/EXTERNAL_VALIDATION_REQUIREMENTS.md` | 外部验证要求 | 规定可接受字段和不能越界的证据层 |

## 六、源审计和逐行证据

| 文件 | 内容 | 状态 |
| --- | --- | --- |
| `docs/SI_SOURCE_AUDIT_STATUS.md` | release-gated 省级官方源审计状态 | 62 行官方记录完整 |
| `docs/SI_PROVINCIAL_SOURCE_EVIDENCE_MATRIX.md` | 31 行装机和 31 行 NEA PV 利用率逐行矩阵 | 62 行完整 |
| `outputs/si_source_audit_status.csv` | 机器可读源审计汇总 | 严格模式通过 |
| `outputs/provincial_source_evidence_matrix.csv` | 机器可读逐行证据矩阵 | 已纳入 release manifest |
| `scripts/source_audit_gate.py` | 源审计门控脚本 | `--strict` 通过 |
| `tests/test_source_audit_gate.py` | 源审计测试 | 通过 |

省级机队利用小时仍保留为系统级锚点，但不再写作官方逐行源表。

## 七、图件和输出数据来源

| 主图 | 文件 | 主要数据来源 | 主要脚本 |
| --- | --- | --- | --- |
| Fig 1 | `outputs/figures/NEWFig1_inversion.png` | ERA5-Land 网格、PVGIS 锚点、器件参数 | `scripts/portfolio_hexmap.py` 和相关图脚本 |
| Fig 2 | `outputs/figures/NEWFig2_mechanisms.png` | 机制分解输出、温度和空气质量驱动 | 机制图脚本 |
| Fig 3 | `outputs/figures/NEWFig3_segmentation.png` | 省级年发电量、STC 效率、面积发电量 | `scripts/fig_yield_segmentation.py` 或对应生成脚本 |
| Fig 4 | `outputs/figures/NEWFig4_economics_timing.png` | LCOE、Monte Carlo、替代模型 | 经济时序脚本 |
| Fig 5 | `outputs/figures/NEWFig5_deployment.png` | 省级装机、钙钛矿优势、土地惩罚 | `scripts/fig_deployment_map.py` |

支撑图、机制图、稳健性图和审计输出见 `docs/SUPPORTING_INFORMATION_COMPLETE.md` 与 `docs/SUPPORTING_INFORMATION_COMPLETE_zh.md` 的 S7。

## 八、不可越界表述

| 不能写成 | 正确写法 |
| --- | --- |
| 已取得完整政府逐省 PV 绝对发电量清单 | 尚未取得该清单，已建立验证门控 |
| NBS 逐省总发电量验证了逐省 PV 发电量 | NBS 层提供逐省总发电量背景，不是 PV-specific |
| NEA PV 利用率是逐省发电量 | NEA 层是 PV 发电利用率，验证消纳和运行，不是绝对电量 |
| CTGR 公司样本代表全国逐省清单 | CTGR 是交易所披露公司资产样本 |
| 0.1 degree 网格给出场站点预测 | 0.1 degree 网格支撑空间型态和区域排序 |
| 经济替代路径是预测 | 经济路径是 Monte Carlo 情景分布 |

## 九、复现和发布

当前关键命令如下。

| 命令 | 用途 | 当前状态 |
| --- | --- | --- |
| `.venv\Scripts\python.exe -m pytest -q` | 全量测试 | 63 passed |
| `.venv\Scripts\python.exe -m scripts.source_audit_gate --strict` | 严格源审计 | 通过 |
| `.venv\Scripts\python.exe -m scripts.validate_government_pv_generation_inventory` | 完整政府 PV 清单候选验证 | submission ready 为 False |
| `.venv\Scripts\python.exe -m scripts.release_manifest` | 生成发布清单 | 完整 |

发布包边界见 `docs/RELEASE_MANIFEST.md` 和 `outputs/release_manifest.csv`。
