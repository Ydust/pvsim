# Model And Source Data Audit

核查日期: 2026-07-01

## Verdict

核心物理结论目前仍由缓存结果支持: 省级 8,760 小时全模型显示钙钛矿相对现代晶硅的省级优势中位数约为 3.4%, ERA5-Land 网格层显示优势与年辐照负相关, r=-0.514, Fig 2 机制分解显示温度链和光谱链可分辨。

源数据封口和复现链条已在本轮加固。当前版本把 2024 省级装机闭合到全国总量, 把机队利用小时移入版本化源表, 并在仓库内建立可运行 Python 环境。

## Must Fix Before Submission

| Priority | Issue | Evidence | Action |
| --- | --- | --- | --- |
| Resolved | Python 环境不完整 | 已建立 `.venv`, 安装 `pytest` 与 `pvlib` | `pytest -q` 通过 29 项; `scripts.validate_against_pvlib` 全局最大偏差 0.0007% |
| Resolved | 省级 2024 装机表已补齐官方逐省出处 | 国家能源局官方逐省表合计 885.673 GW, 全国目标为 886.6 GW | 保留 `RAW_PROVINCE_PV_2024_GW`, 生成按全国总量缩放的 `PROVINCE_PV_2024_GW`; 源表见 `data/source_tables/provincial_pv_capacity_2024.csv` |
| Resolved | 机队利用小时表仍在脚本中 | 旧版 `scripts/fig_validation_fleet.py` 内嵌 `FLEET_HOURS` 字典 | 已移入 `data/source_tables/provincial_fleet_hours_2024.csv`; 脚本经 `pvsim.source_data.load_fleet_hours` 读取; 测试检查 31 省覆盖与来源字段 |
| P1 | ERA5 网格脚本依赖本机边界文件 | 旧脚本硬编码 `C:\Users\yuanq\new\geojson` | 已改为优先读取 `CHINA_GEOJSON`, 其次读取 `data/geojson`; 投稿包仍需放入或说明边界文件来源 |
| P1 | Fig 2 淡色散点来源容易被误读 | r=+0.98 与 r=-0.85 来自 31 省锚点和 334 个 PVGIS bbox 加密样本, 不是 95k ERA5 0.1° 格点 | 已把正文和图注改为 PVGIS 加密样本; 图源脚本已补 `lon` 字段和 `pvgis_bbox_sample` 标记 |
| P1 | 海上光伏未单独建模 | 当前省级装机、利用小时和气候驱动都按陆地省级锚点或陆地网格组织 | 已在正文方法范围中明确不单独提出海上部署结论; 如讨论沿海部署, SI 可加一个排除海上口径的敏感性说明 |

## Quantitative Checks

| Check | Result | Interpretation |
| --- | --- | --- |
| Province yield cache | 93 rows, 31 provinces x 3 technologies | 主省级产出表结构完整 |
| Provincial capacity sum | raw 885.673 GW; model input 886.6 GW | 官方逐省分布统一缩放, 图件容量权重与全国 2024 总量闭合 |
| ERA5 grid cache | 94,998 land cells | 可支撑气候态空间型态, 不应声称单格点精确预测 |
| ERA5 advantage | min -1.91%, P10 0.074%, median 2.084%, P90 3.655%, max 5.28% | 存在负值尾部, 正文不能写成所有地点都为正收益 |
| Grid irradiance relation | r=-0.514 | 反转方向稳健 |
| Reduced grid validation | R2=0.377, RMSE=0.962 percentage points | 足以支撑区域排序, 不足以支撑逐点发电量声明 |
| Fleet validation | r=0.889, corrected RMSE 102 h, MAPE 7.1% | 利用小时来自版本化源表, 作为系统级空间锚定 |
| Substitution calibration | R2=0.829, RMSE 11.9 percentage points | 历史软最大替代模型可作情景框架, 不应写成确定预测 |
| Fig 2 province-only correlations | temperature r=+0.941, spectrum r=-0.944 | 即使只用省级锚点, 两条机制仍成立 |
| Fig 2 combined correlations | temperature r=+0.979, spectrum r=-0.845 | 当前图中报告值来自省级锚点加 PVGIS 加密样本 |

## Model Risks That Are Acceptable With Clear Wording

1. ERA5 0.1° 图层是气候态空间型态图, 不是电站级或单格点预测。
2. SPECTRL2 光谱项采用晴空谱, 光谱归因来自太阳几何和大气质量, 不包含云致光谱蓝移。
3. Fig 4 的蒙特卡洛是成本交叉情景, 不是产业采纳率预测。
4. Fig 5 的土地惩罚和部署平面应解释为陆地集中式与屋顶应用的决策框架, 不覆盖海上光伏。
5. 缓存数据可支持当前图件, 但投稿复现包应包含原始数据清单、清洗脚本、版本日期和校验和。

## Cleanup Before Final Submission

1. 把 `CSI_EARLY` 脚本标为 legacy, 或移入 archive, 避免读者误用早期晶硅生成当前 NEWFig。
2. 后续测试可继续扩展到 `CSI_MODERN` 主基准、Fig 2 加密样本来源和 ERA5 reduced-order 校验。
3. 成本史、学习率和碳因子后续也应导出为 versioned CSV 或 JSON。
4. 重新生成所有主图时记录命令、依赖环境和输出校验和。
5. 投稿发布前运行 `.venv\Scripts\python.exe -m scripts.source_audit_gate --strict`, 确认 62 行 release-gated 官方源证据仍为完成状态。
