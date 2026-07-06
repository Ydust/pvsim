# 投稿前科学性加固清单

目标:把当前 `NEWFig1-5` 主线从“有投稿潜力的预稿”推进到“Joule-plus 标准的可防守投稿稿”。

更高标准的缺口审计见 `docs/JOULE_PLUS_GAP_AUDIT.md`。

---

## 当前判断

| 维度 | 状态 | 投前要求 |
|---|---|---|
| 主问题与创新性 | 已成型 | 保持“地理反转 + 双机制 + 市场尺子 + 寿命门控 + 陆域部署错配”五步主线。 |
| 模型透明度 | 基本合格 | SI 加流程图、参数表、反事实开关定义和参数订正记录。 |
| 数值验证 | 强 | 保留 pvlib 0.0007% 与 C# 逐比特复现。 |
| 真实机队验证 | 有力但需降调 | 已写成系统级空间锚定; 已生成 bias、RMSE/MAE/MAPE、损失校正前后结果。 |
| 0.1° 网格 | 可用但需限定 | 已写成气候态空间型态图; 优势验证 R²≈0.38、RMSE≈0.96 个百分点, 只能支撑空间型态/区域排序。 |
| 光谱机制 | 物理上可讲 | 明确 SPECTRL2 为晴空谱, 光谱项归因于大气质量, 不归因于云致蓝移。 |
| 机制特异性 | 已增强 | 省级-only 偏相关保持预期方向, 温度项与 cell temperature partial r = 0.957, 光谱项与 air mass partial r = -0.931。 |
| 器件基准稳健性 | 已增强 | HJT、TOPCon、PERC 硅基准和钙钛矿 gamma/光谱响应 stress test 都保持反转方向。 |
| 可迁移性边界 | 已补边界图 | 已给出 `Tcell × air mass` 机制相图; 这不是全球验证, 但能防止过度外推。 |
| 经济替代 | 可作情景分析 | 写成 LCOE 交叉情景分布; 补 MC 参数表、先验来源、敏感性排序。 |
| 期刊定位 | 目标已上调为 Joule-plus | 不再以较低可接受线作为判断标准。已补全国聚合实测 sanity check、国家能源局区域光伏发电利用率层、国家统计局逐省总发电量层、三峡能源经营地区 PV 绝对发电量样本、31 行官方装机出处和 62 行官方源数据证据矩阵。完整政府逐省 PV 绝对发电量清单仍作为未来更强验证目标, 不能在正文中越界声称。 |

---

## 必须完成

1. **机队验证统计表**
   - 省级 clean-physics yield vs NEA utilisation hours。
   - 报告 `r`、bias、RMSE、MAE、MAPE。
   - 报告扣除统一系统损失后的统计。
   - 图注说明 residual 不是模型误差的唯一来源, 还包括弃光、BOS、调度、运维。

2. **降阶网格验证表**
   - 31 省 full 8760h 模型 vs reduced-order/grid 模型。
   - 当前优势变量验证为 `R²≈0.38`、`RMSE≈0.96` 个百分点; 必须报告误差分布和省级异常点。
   - 明确 Fig 1 支撑的是空间反转和区域排序。

3. **光谱边界说明**
   - SI Methods 写清 SPECTRL2 clear-sky。
   - 将“多云西南”的语义限定为低辐照/温热地理背景, 不是云致光谱机制。

4. **Monte Carlo 参数与校准**
   - 表列学习率、成本下限、寿命突破年、最终寿命、退化、softmax 温度。
   - 每个参数给出来源或锚点、选择理由和压力测试角色。
   - 历史 multi→mono 校准图报告残差, 不只报 `R²=0.83`。

5. **引用补全**
   - 删除 “energy-yield studies 2020-2025” 这类占位引用。
   - 补全 NEA/CPIA、ITRPV、BNEF、ERA5-Land、PVGIS、GEM、NREL Cordell、Wagner 等数据/参数来源。

---

## 已生成的防守表

| 文件 | 用途 |
|---|---|
| `docs/SI_SCIENTIFIC_DEFENSE_TABLES.md` | SI-ready 汇总表。 |
| `outputs/si_fleet_validation_summary.csv` | 机队锚定统计: raw r=0.889; 扣除 15.3% 系统损失后 RMSE=102 kWh/kWp、MAPE=7.1%。 |
| `outputs/si_grid_reduced_validation_summary.csv` | 0.1° 降阶优势验证: R²=0.377、RMSE=0.962 个百分点、网格 GHI 与优势的相关 r=-0.514。 |
| `outputs/si_substitution_calibration_summary.csv` | 历史 multi→mono 校准: R²=0.829、RMSE=11.9 个百分点。 |
| `outputs/si_mc_parameters.csv` | 主 Fig 4 Monte Carlo 参数、来源锚点和压力测试角色。 |
| `docs/SI_MECHANISM_SPECIFICITY.md` | 省级-only 偏相关机制防守表。 |
| `docs/SI_SILICON_BASELINE_SENSITIVITY.md` | HJT、TOPCon、PERC 现代晶硅基准敏感性。 |
| `docs/SI_PEROVSKITE_PARAMETER_SENSITIVITY.md` | 钙钛矿 gamma 和光谱响应强度 stress test。 |
| `docs/SI_TRANSFERABILITY_BOUNDARY.md` | 可迁移性机制相图, 给出零优势边界和中国锚点包络。 |
| `docs/SI_NATIONAL_EXTERNAL_VALIDATION.md` | 国家统计局全国聚合太阳能发电和装机 sanity check。 |
| `docs/SI_PV_UTILIZATION_EXTERNAL_VALIDATION.md` | 国家能源局区域光伏发电利用率空间层。 |
| `docs/EXTERNAL_VALIDATION_AUDIT.md` | 本地外部实测数据可用性审计, 当前已有 PV 空间运行层和逐省绝对总发电量背景层。 |
| `docs/SI_SOURCE_AUDIT_STATUS.md` | 源数据 release gate, 31 行官方装机和 31 行官方 PV 发电利用率均完成。 |
| `docs/SI_PROVINCIAL_SOURCE_EVIDENCE_MATRIX.md` | 62 行省级官方源数据逐行证据矩阵, 62 行完成。 |
| `docs/SI_NBS_SPATIAL_GENERATION_VALIDATION.md` | 国家统计局逐省总发电量层, 作为绝对发电量空间背景, 不作为逐省 PV 发电量校验。 |
| `docs/SI_CTGR_SPATIAL_PV_GENERATION_VALIDATION.md` | 三峡能源经营地区 PV 发电量和上网电量样本, 作为带空间轴的 PV 绝对发电量实测层。 |
| `docs/RELEASE_MANIFEST.md` | 文件级 SHA256 release manifest。 |

---

## 可选增强

| 增强项 | 价值 |
|---|---|
| 省级 31 点技术排序表 | 防止审稿人质疑均值掩盖区域异质性。 |
| 多变量气候扰动 | 进一步防守机制唯一性, 尤其是湿度、云量和风速协变量。 |
| 全球气象重跑 | 将可迁移性边界升级为真正全球验证。 |
| 绝对发电量与输电/消纳边界讨论 | 强化部署建议, 尤其面向 Joule。 |
| 碳和铟 appendix | 对能源/材料审稿人有帮助, 但不应进入主线。 |
