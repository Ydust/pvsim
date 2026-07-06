# 支撑材料

论文：钙钛矿在弱日照区收益最高

最后更新：2026-07-01

文件状态：完整中文支撑材料，已与论文主体分离

## S0 范围、数据来源和源数据边界

本研究评估中国陆域光伏部署。范围包括地面集中式电站、屋顶和分布式光伏。海上和水面漂浮光伏不作为独立技术情景建模，因为它们的热边界、腐蚀和湿热暴露、平台、运行和成本不同于陆域系统。

源数据层级分为观测输入、官方验证层、系统级锚点、模型输出和情景参数。省级装机、官方光伏发电利用率和机队利用小时都是并网聚合层，不拆分为地面电站、屋顶、漂浮或海上子机队。

表 S0.1 源表和用途。

| 表 | 文件 | 用途 | 状态 |
| --- | --- | --- | --- |
| S0.1 | `data/source_tables/provincial_pv_capacity_2024.csv` | 容量加权和部署错配 | 国家能源局 31 省官方行 |
| S0.2 | `data/source_tables/provincial_fleet_hours_2024.csv` | 系统级空间锚点 | 版本化锚点，不作为官方逐行 release 证据 |
| S0.3 | `data/source_tables/nea_pv_utilization_rate_2024.csv` | 官方光伏运行验证 | 国家能源局官方逐行证据 |
| S0.4 | `data/source_tables/nbs_provincial_total_power_generation_2024.csv` | 官方绝对发电量背景 | 总发电量，不是 PV-specific |
| S0.5 | `data/source_tables/ctgr_pv_generation_by_region_2024.csv` | PV-specific 绝对发电量样本 | 交易所披露公司经营地区样本 |
| S0.6 | `outputs/provincial_source_evidence_matrix.csv` | 逐行源证据矩阵 | 62 行官方记录完整 |
| S0.7 | `outputs/government_pv_generation_inventory_validation.csv` | 完整政府 PV 发电量候选表门控 | 未通过，因为没有官方候选表 |

国家能源局省级装机行合计 885.673 GW，新疆生产建设兵团并入新疆。模型保留官方省级份额，并统一缩放到 2024 年全国 PV 总量 886.6 GW。

完整政府逐省 PV 绝对发电量清单尚未取得。`scripts/validate_government_pv_generation_inventory.py` 会拒绝由装机推算、由利用率推算、公司样本、规上工业子口径和部分覆盖表组成的候选表。当前候选状态未通过，因为 `data/source_tables/provincial_pv_generation_2024_official.csv` 不存在。

## S1 模型结构和反事实开关

数字孪生是模块化链条，因此每个物理假设都可测试和开关。

表 S1.1 模型链条。

| 阶段 | 输入 | 模型步骤 | 输出 |
| --- | --- | --- | --- |
| 天气驱动 | PVGIS TMY、ERA5-Land 气候态、经纬度 | 太阳几何和天气协调 | GHI、DNI、DHI、气温、风速和天顶角 |
| 组件面辐照 | 水平辐照和安装几何 | 转置到组件平面 | 宽带 POA 辐照 |
| 光学修正 | POA 辐照和入射角 | Martin-Ruiz IAM、可选双面增益和 DC 光学损失 | 光学有效辐照 |
| 光谱响应 | 天顶角、空气质量和 EQE 曲线 | SPECTRL2 晴空光谱因子 | 各技术光谱乘子 |
| 电池温度 | POA 辐照、气温和风速 | Faiman 传热模型 | 电池温度 |
| 电学模型 | 有效辐照和电池温度 | De Soto 五参数单二极管模型，用 Lambert W 求解 | IV 曲线、最大功率和 DC 功率 |
| 系统输出 | DC 阵列功率和逆变器设置 | PVWatts 逆变器、削峰和系统损失 | AC 功率和年度比发电量 |
| 退化和经济性 | 首年发电量和技术参数 | 退化、初期衰减、折现发电量和 LCOE | LCOE 轨迹 |
| 替代情景 | LCOE 路径和 Monte Carlo 抽样 | Softmax merit-order 分配 | 新增装机份额和交叉年份 |

光谱模块使用晴空光谱物理。云量通过宽带辐照和温度进入模型，而不是通过显式云光谱颜色项进入模型。

表 S1.2 反事实开关。

| 量 | 开关或运行对 | 解释 |
| --- | --- | --- |
| 光谱分量 | 完整运行减去 `apply_spectral=False` 的平坦光谱运行 | 隔离带隙和空气质量光谱响应 |
| 温度分量 | 功率温度系数差作用于相对 25 C 的能量加权电池温度偏离 | 隔离温度系数机制 |
| IAM 残差 | 无光谱运行减去无光谱无 IAM 运行 | 捕捉入射角光学残差 |
| 降阶网格层 | 省级完整 8760 小时锚点校准月尺度 ERA5-Land 降阶运行 | 支撑空间格局和排序 |

## S2 数值验证和机队锚定

单二极管实现与 pvlib De Soto 和 singlediode 计算对比。跨标准测试、热高辐照、低光和冷高辐照工况，Pmp、Voc、Isc 和填充因子的全局最大偏差为 0.0007 percent。

机队锚定将清洁物理现代硅发电量与省级机队利用小时比较。原始空间相关性为 r = 0.889。统一平均系统损失 15.3 percent 修正后，RMSE 为 102 kWh per kWp，MAPE 为 7.1 percent。该验证是系统级验证，因为机队小时包含系统损失、弃光、调度和运维。

表 S2.1 验证钩子。

| 检查 | 命令或文件 | 当前结果 |
| --- | --- | --- |
| 数值基准 | `.venv\Scripts\python.exe -m scripts.validate_against_pvlib` | 最大偏差 0.0007 percent |
| 机队验证 | `outputs/si_fleet_validation_summary.csv` | r = 0.889，修正后 RMSE = 102 kWh per kWp |
| 数据完整性 | `.venv\Scripts\python.exe -m pytest -q` | 63 passed |
| 源审计门控 | `.venv\Scripts\python.exe -m scripts.source_audit_gate --strict` | 62 行官方记录完整 |
| 发布清单 | `.venv\Scripts\python.exe -m scripts.release_manifest` | 文件级 SHA256 清单完整 |

## S3 空间反转稳健性

主要空间结果是，钙钛矿相对现代硅的单位装机优势在低辐照的华南和西南更大，而不是在高辐照西北更大。

降阶 ERA5-Land 网格包含 94,998 个陆域格点，并用 31 个省级完整 8760 小时锚点校准。优势变量验证得到 R2 = 0.377，RMSE = 0.962 percentage points。网格尺度辐照和优势关系仍为负，r = -0.514。

表 S3.1 网格不确定性。

| 指标 | 数值 |
| --- | ---: |
| 完整省级锚点 | 31 |
| ERA5-Land 陆域格点 | 94,998 |
| 降阶 R2 | 0.377 |
| 降阶 RMSE | 0.962 percentage points |
| 中位绝对误差 | 0.703 percentage points |
| P90 绝对误差 | 1.444 percentage points |
| 最大省级误差 | 2.532 percentage points |
| 网格辐照和优势关系 | r = -0.514 |

因此，降阶网格是空间格局和排序图层，不是场站点预测。省级数值结论使用完整 8760 小时锚点。

现代硅基准敏感性保留反转。HJT-like、TOPCon-like 和 PERC-like 硅情景下，钙钛矿中位优势分别为 2.90 percent、3.43 percent 和 3.87 percent。辐照关系仍为负，r 从 -0.603 到 -0.500。

钙钛矿参数敏感性同样保留反转。九组压力测试覆盖 -0.10 到 -0.25 percent per C 的温度系数，以及 0.7 到 1.3 的光谱响应缩放。所有情景均保持资源带 IV 高于资源带 I。最弱中位情景仍有 1.84 percent 优势。

## S4 机制特异性

优势被分解为温度项、光谱项和光学残差。温度项来自钙钛矿较小功率温度系数在真实电池温度上的作用。光谱项来自低空气质量下宽带隙响应增强。

省级偏相关支持可分离机制归因。在控制辐照、空气质量和电池温度后，温度分量与加权电池温度的偏相关为 r = 0.957。光谱分量与空气质量的偏相关为 r = -0.931。

时间指纹分离了两条机制。温度分量集中于夏季，光谱分量全年以正午带存在。这避免了把共同正午峰误判为单一隐藏辐照驱动。

叠层结构是单结光谱机制的负对照。叠层硅底电池吸收钙钛矿顶电池透过的红光，因此更接近全光谱吸收器。在当前器件组中，叠层具有强面积发电量优势，但相对现代硅几乎没有单位装机光谱优势。

云光谱边界检查在保持宽带辐照不变的情况下，对晴空光谱施加平滑蓝移和红移扰动。所有压力情景均保留相对空气质量和钙钛矿光谱优势之间的负关系。因此，正文将主要光谱项归因于空气质量和太阳几何，而不是云颜色。

可迁移性附录用中国导出的温度和光谱分量拟合机制相平面。拟合温度斜率为 0.186 percentage points per C，光谱斜率为 1.757 percentage points per unit blue-index。该相平面是边界说明，不是全球验证图。

## S5 效率标尺、经济性和部署

论文使用三种性能标尺。

表 S5.1 性能标尺。

| 标尺 | 回答的问题 | 市场含义 |
| --- | --- | --- |
| 标准测试效率 | 单位组件面积可容纳多少实验室额定功率 | 用于名义比较 |
| 年度单位装机发电量 | 额定瓦在场站中产生多少电量 | 陆域地面电站经济性 |
| 年度单位面积发电量 | 有限面积产生多少电量 | 屋顶和面积受限部署 |

单结钙钛矿的标准测试效率低于现代硅，但年度单位装机发电量更高。叠层的年度单位面积发电量最强。因此图 3 将陆域地面电站部署与屋顶部署分开。

替代模型是简化情景模型。它用 2015 到 2023 年多晶硅向单晶硅转型校准，R2 = 0.829，RMSE = 11.9 share percentage points。该模型支持情景时序，但不支持确定性采用预测。

Monte Carlo 先验覆盖学习率、成本下限、钙钛矿突破年份、突破后寿命和分配锐度。钙钛矿学习率中心约为 0.27，叠层约为 0.30，c-Si 约为 0.18。钙钛矿突破年份从 2028 到 2042 抽样，突破后寿命从 18 到 25 年抽样。

部署解释保持三条陈述分开。

表 S5.2 部署陈述。

| 陈述 | 证据 | 范围 |
| --- | --- | --- |
| 钙钛矿应首先进入炎热且高优势的华南和西南地面电站区域 | 图 1 和图 5 | 陆域地面电站单位装机部署 |
| 叠层价值在面积稀缺处最强 | 图 3 和叠层负对照 | 屋顶和面积受限部署 |
| 现代硅在优势较小或耐久性风险较高处仍有竞争力 | 图 4 和图 5 | 保守部署和可靠性门控 |

陆域地面电站行距惩罚与技术无关。它从海南的约 1.9 percent 上升到黑龙江的约 10.8 percent，并与纬度相关，r = 0.98。

## S6 外部验证层和边界

表 S6.1 外部验证层。

| 图层 | 证据 | 支撑内容 | 边界 |
| --- | --- | --- | --- |
| 国家统计局全国太阳能发电量 | 2024 年 839.04 TWh | 全国聚合合理性 | 无空间轴 |
| 国家能源局 PV 利用率 | 全国 96.8 percent，省级最低 68.6 percent | 官方 PV-specific 空间运行 | 利用率，不是绝对发电量 |
| 国家统计局逐省总发电量 | 31 省行，合计 100868.83 hundred million kWh | 官方绝对发电量背景 | 总发电量，不是 PV-specific |
| 三峡能源 PV 发电量 | 25 个经营地区，25.40083 TWh | PV-specific 绝对发电量样本 | 公司资产样本 |
| 候选政府 PV 清单 | 验证门控已建立 | 未来完整官方逐省 PV 表 | 未通过，因为没有官方候选文件 |

国家统计局全国聚合检查使用 2024 年统计公报。由于 2024 年太阳能装机快速增长，年末装机分母会给出偏低的观测比发电量。用推断年初装机和年末装机的简单平均值，观测比发电量为 1120.7 kWh per kW。损失修正后的模型值为 1265.4 kWh per kWp。差异反映年内新增装机、机队年龄、弃光、可用率、区域时序和源口径差异。

国家能源局 PV 利用率图层报告 2023 和 2024 年各地区光伏发电利用率。将内蒙古分区聚合到 31 省建模口径后，它是官方、PV-specific 且具有空间分辨率的运行验证层。它验证电网运行证据，但不能替代实测逐省发电量。

国家统计局逐省总发电量图层报告 2024 年各省总发电量。省级合计与全国参考值相差 0.02 hundred million kWh。它提供官方省级空间轴和绝对发电量，但不是 PV-specific。

三峡能源图层来自交易所披露年报，且为 PV-specific。它报告 25 个经营地区、254.0083 hundred million kWh 光伏发电量和 248.3109 hundred million kWh 上网电量，并与年报总量在四舍五入范围内闭合。它是样本验证层，而不是完整全国政府逐省清单。

完整政府逐省 PV 发电量清单仍不可用。手动导出协议为 `docs/NBS_MANUAL_EXPORT_PROTOCOL.md`。验证门控为 `scripts/validate_government_pv_generation_inventory.py`。

## S7 支撑图和表清单

表 S7.1 主图和支撑图文件。

| 标签 | 文件 | 作用 |
| --- | --- | --- |
| 图 1 | `outputs/figures/NEWFig1_inversion.png` | 地理反转和资源带机制拆分 |
| 图 2 | `outputs/figures/NEWFig2_mechanisms.png` | 机制驱动和月度指纹 |
| 图 3 | `outputs/figures/NEWFig3_segmentation.png` | 效率标尺和市场分工 |
| 图 4 | `outputs/figures/NEWFig4_economics_timing.png` | 寿命门控经济性和交叉时序 |
| 图 5 | `outputs/figures/NEWFig5_deployment.png` | 部署错配和陆域地面电站决策平面 |
| 图 S1 | `outputs/figures/MainFigV_fleet_validation.png` | 机队锚定系统验证 |
| 图 S2 | `outputs/figures/MainFig3x_temporal_fingerprint.png` | 时间机制指纹 |
| 图 S3 | `outputs/figures/MainFig3y_tandem_decomposition.png` | 叠层负对照 |
| 图 S4 | `outputs/figures/MainFig4x_degradation_risk.png` | 寿命风险地理 |
| 图 S5 | `outputs/figures/MainFig4y_substitution_timing_geo.png` | 条件时序地理 |
| 图 S6 | `outputs/figures/SI_transferability_phase_plane.png` | 机制可迁移边界 |

表 S7.2 审计和验证文件。

| 文件 | 作用 |
| --- | --- |
| `docs/SI_SOURCE_AUDIT_STATUS.md` | 62 行官方源审计状态 |
| `docs/SI_PROVINCIAL_SOURCE_EVIDENCE_MATRIX.md` | 逐行官方证据矩阵 |
| `docs/SI_NATIONAL_EXTERNAL_VALIDATION.md` | 官方全国太阳能发电量 sanity check |
| `docs/SI_PV_UTILIZATION_EXTERNAL_VALIDATION.md` | 官方国家能源局 PV 利用率验证 |
| `docs/SI_NBS_SPATIAL_GENERATION_VALIDATION.md` | 官方国家统计局总发电量空间背景 |
| `docs/SI_CTGR_SPATIAL_PV_GENERATION_VALIDATION.md` | 三峡能源 PV 发电量样本 |
| `docs/GOVERNMENT_PV_GENERATION_INVENTORY_AUDIT.md` | 完整政府 PV 清单获取审计 |
| `docs/SI_GOVERNMENT_PV_GENERATION_INVENTORY_VALIDATION.md` | 候选清单验证状态 |
| `docs/RELEASE_MANIFEST.md` | 文件级 SHA256 发布清单 |

## S8 可复现性

已验证环境记录在 `requirements-lock.txt`，灵活安装文件为 `requirements.txt`。

表 S8.1 核心复现命令。

| 检查 | 命令 | 当前结果 |
| --- | --- | --- |
| 单元和数据完整性测试 | `.venv\Scripts\python.exe -m pytest -q` | 63 passed |
| 源审计门控 | `.venv\Scripts\python.exe -m scripts.source_audit_gate --strict` | 62 行官方记录完整 |
| 全国聚合验证 | `.venv\Scripts\python.exe -m scripts.national_external_validation` | 官方全国检查已写入 |
| PV 利用率验证 | `.venv\Scripts\python.exe -m scripts.pv_utilization_external_validation` | 官方 PV 运行层已写入 |
| 国家统计局空间背景 | `.venv\Scripts\python.exe -m scripts.nbs_spatial_generation_validation` | 官方总发电量背景已写入 |
| 三峡能源 PV 样本 | `.venv\Scripts\python.exe -m scripts.ctgr_spatial_pv_generation_validation` | 交易所披露 PV 样本已写入 |
| 政府 PV 清单门控 | `.venv\Scripts\python.exe -m scripts.validate_government_pv_generation_inventory` | Submission ready is False |
| 发布清单 | `.venv\Scripts\python.exe -m scripts.release_manifest` | 完整清单已写入 |

发布清单记录论文草稿、SI 证据、源表、主图、核心脚本、输出和测试的文件大小与 SHA256。它是文件包边界，不替代逐行源出处。
