# 支撑材料补充清单

当前正文主线采用 `NEWFig1-5`。支撑材料的任务不是重复主图, 而是替五张主图保留三类证据:
模型可信度、稳健性/反事实过程、以及被主线降级但审稿人可能追问的边界条件。

可投递的 SI 草稿见 `docs/SUPPORTING_INFORMATION_DRAFT.md`。其中 S0 到 S6 已落稿,
S7 保留为可选背景材料入口。

范围边界: 本研究支撑的是中国陆域光伏, 包括陆上地面集中式与屋顶/分布式。海上或水面漂浮光伏
不进入主模型, 只作为 Discussion / limitations 说明。

---

## 投稿前科学性防守优先级

| 审稿人可能追问 | 当前风险 | 必须补的证据或措辞 |
|---|---|---|
| 真实机队 r=0.89 是否真的验证了器件物理? | 省级利用小时含 BOS、弃光、调度与运维, 不能等同纯器件验证。 | 明确称为**系统级空间锚定**; SI 报告 bias、RMSE/MAE/MAPE、系统损失校正前后相关性, 并解释残差地图。 |
| 0.1° 格点是否是逐点预测? | 降阶网格模型在优势变量上 R²≈0.38、RMSE≈0.96 个百分点, 容易被质疑夸大分辨率。 | 明确称为**气候态空间型态图**; SI 放降阶模型验证、误差分布和“pattern not point forecast”说明。 |
| 光谱项是否把“多云”当成光谱机制? | SPECTRL2 是晴空谱, 不含云致蓝移。 | 正文和 SI 均说明光谱项归因于太阳几何/大气质量; 云量只通过宽谱辐照和温度进入。 |
| 2030/2032/2039 是否是产业预测? | 替代模型是情景模型, 由多晶→单晶校准, 不能当确定预报。 | 称为 **LCOE 交叉情景分布**; SI 放 MC 参数表、先验来源、校准残差和敏感性排序。 |
| 现代晶硅基准是否公平? | 钙钛矿优势很依赖基准。 | SI 保留早期/现代晶硅对照和参数审计, 说明换基准只缩小幅度、不改变反转。 |

---

## 建议的 SI 结构

| SI 模块 | 支撑主图 | 目的 | 优先级 |
|---|---|---|---|
| S0 数据源表与 source appendix | Fig 1-5 | 记录省级装机、利用小时和源表校验, 防止审稿人质疑数据口径 | 必须 |
| S1 模型验证与计算链 | Fig 1-4 | 证明数字孪生可复现、算得对、对得上真实机队 | 必须 |
| S2 地理反转稳健性 | Fig 1 | 证明 `sunlight weakest, gain largest` 不是场景/网格假象 | 已写入 SI S2 |
| S3 机制分解过程 | Fig 2 | 证明温度项与光谱项可分、独立、不是同一变量重复 | 已写入 SI S3 |
| S4 效率/市场尺子的省级明细 | Fig 3 | 让 31 省散点和 per-kWp/per-m² 排序可审查 | 已写入 SI S4 |
| S5 经济与替代模型校准 | Fig 4 | 证明 2030s 时机不是任意外推 | 已写入 SI S5 |
| S6 陆域部署错配与土地惩罚 | Fig 5 | 补足容量数据、优势三分位和陆上高纬土地惩罚来源 | 已写入 SI S6 |
| S7 降级背景: 铟、碳、带隙 | Discussion | 保留边界结论, 但不干扰五图主线 | 选择性 |

---

## 必须补进支撑材料的图/细节

| 建议编号 | 文件或内容 | 放入理由 | 建议图注关键词 |
|---|---|---|---|
| **Fig S1** | `outputs/figures/MainFig1_twin_and_devices.png` | 主图 1 已改为地理反转, 但验证图不能丢; 它解释 pvlib 0.0007%、8760h 运行直觉和退化曲线。 | numerical validation; 126 conditions; 8760-h Wuhan heatmap; degradation/lifetime |
| **Fig S2** | `outputs/figures/MainFigV_fleet_validation.png` + `outputs/si_fleet_validation_summary.csv` | 这是最强现实锚点, 但必须写成系统级空间验证: 干净物理 yield 与 31 省真实利用小时 r=0.89; 扣除 15.3% 系统损失后 RMSE=102 kWh/kWp、MAPE=7.1%。 | fleet-anchored validation; NEA utilisation hours; bias/RMSE/MAPE; BOS loss; curtailment residual |
| **Fig S3** | `outputs/figures/MainFig3b_inversion_robustness.png` | Fig 1 的反转必须防守场景扰动: 双面、安装方式、散热假设下相关系数仍全负。 | five adversarial scenarios; r=-0.46 to -0.63; inversion holds |
| **Fig S4** | `outputs/figures/MainFig3c_era5_grid_inversion.png` + `outputs/si_grid_reduced_validation_summary.csv` | 补 Fig 1 的 0.1° 网格来源和降阶模型验证。优势变量 R²≈0.38、RMSE≈0.96 个百分点, 必须表述为“空间型态稳健”而非逐点精确预测。 | ERA5-Land 0.1°; ~95k cells; reduced-order validation; pattern not point forecast |
| **Fig S5** | `outputs/figures/MainFig3x_temporal_fingerprint.png` | Fig 2 面板只放月尺度, SI 应保留 8760h 的 day × solar-hour 过程图。 | temperature seasonal; spectral year-round; time decoupling |
| **Fig S6** | `outputs/figures/MainFig3y_tandem_decomposition.png` | 支撑 Fig 3/Fig 5 中“叠层是面积技术而不是每 kWp 技术”的判断。 | tandem spectral component near zero; full-spectrum absorber; area value |
| **Fig S7** | `outputs/figures/MainFig6_substitution_validation.png` + `outputs/si_substitution_calibration_summary.csv` + `outputs/si_mc_parameters.csv` | NEWFig4 展示替代结果, 但校准过程被压缩; SI 必须放历史 multi→mono 校准 R²=0.83、RMSE=11.9 个百分点、残差、MC 参数表, 并称为情景交叉而非确定预测。 | historical calibration; softmax merit order; scenario crossover; Monte Carlo P10-P90 |
| **Fig S8** | `outputs/figures/53_backcast_2015_2024.png` | 支撑学习曲线参数不是随意假设; 可作为替代模型的第二层校准证据。 | Wright backcast; module price history; R²=0.887 |
| **Fig S9** | `outputs/figures/MainFig4x_degradation_risk.png` | NEWFig4 说 lifetime gate, SI 应显示“哪个地方最怕寿命不达标”。 | tolerable degradation; Southwest robust; Northwest fragile |
| **Fig S10** | `outputs/figures/MainFig4y_substitution_timing_geo.png` | 避免把“西南先替代”夸大; 说明时机地理只在近平价时展开。 | conditional timing geography; r=-0.95; small spread under central cost |
| **Fig S11** | `outputs/figures/diag_land_use_latitude.png` | NEWFig5 的土地惩罚面板信息密度高, SI 应保留完整图或推导, 说明这是陆上地面集中式、技术无关的几何惩罚。 | row-spacing penalty; latitude; GCR=0.4; r=0.98 |

---

## 建议补表或方法框, 不一定补图

| 内容 | 支撑点 | 建议位置 |
|---|---|---|
| 数字孪生流程表: 气象 → POA → IAM/双面/光谱/温度 → 单二极管 → AC → LCOE → 替代 | 让方法链一眼可见, 比文字 Methods 更容易审稿 | 已写入 `docs/SUPPORTING_INFORMATION_DRAFT.md` 的 S1.1 |
| 反事实分解开关表 | 温度项、光谱项、IAM 残差的定义 | 已写入 `docs/SUPPORTING_INFORMATION_DRAFT.md` 的 S1.2 |
| 31 省 per-kWp/per-m² 技术排序表 | Fig 3 的散点明细, 防止“均值掩盖省级差异” | Fig S6 后或 Data table |
| 机队验证统计表 | 相关系数、bias、RMSE/MAE/MAPE、系统损失校正前后结果 | Fig S2 前 |
| 降阶网格验证表 | 31 省锚点 full 8760h vs reduced-order 的 R²、bias、误差分布 | Fig S4 前 |
| Monte Carlo 参数表 | 学习率、成本下限、寿命突破年、退化、softmax 温度等, 并标注先验来源 | Fig S7 前 |
| 数据溯源分层表 | 区分真实观测、文献参数、模型输出、前瞻情景 | SI Data; 可直接引用 `docs/DATA_PROVENANCE.md` |
| Source appendix | 说明 2024 省级装机使用国家能源局官方逐省表合计 885.673 GW, 如何缩放到 886.6 GW, 以及利用小时表如何进入系统级锚定 | SI Data; 可直接引用 `docs/SOURCE_APPENDIX.md` |
| 参数订正记录 | 现代晶硅基准、叠层 `Ea_recomb` 重标定、铟强度订正 | SI Methods / Parameter audit |

---

## 可选背景图: 放 Discussion/SI, 不进主线

| 文件 | 建议处理 | 原因 |
|---|---|---|
| `outputs/figures/MainFig4_indium_constraint.png` | 放 Materials constraint appendix | 铟是全球多 TW 约束, 不是中国近期主线; 保留可避免审稿人追问资源瓶颈。 |
| `outputs/figures/45_carbon_payback.png` | 可放 Carbon appendix | 说明钙钛矿 embodied carbon 低、回收期短, 但不是本文五图核心。 |
| `outputs/figures/46_carbon_scenarios.png` | 可放 Carbon appendix | 若期刊强调 climate impact, 可作为额外价值而非主线证据。 |
| `outputs/figures/47_province_carbon_map.png` | 只在需要省级碳分布时放 | 容易分散“物理部署”主线, 优先级低于 Fig S1-S11。 |
| `outputs/figures/feas_optimal_bandgap.png` | 放 Limitations / negative result | 支撑“在中国气候范围内, 因地制宜带隙优化不明显”这一边界。 |

---

## 不建议再放进支撑材料的旧图

| 文件组 | 原因 |
|---|---|
| `28_portfolio_*` 到 `32_portfolio_*` | 早期组合框架已被 `NEWFig5_deployment` 的物理分区逻辑替代。 |
| `33_substitution_lcoe.png`, `34_substitution_share.png`, `35_substitution_operating.png` | 早期替代模型图, 与当前校准/MC 版本重复且可能引入旧口径。 |
| `40_physics_substitution_map.png` | 被 `40_physics_2050_landscape.png` / `NEWFig5_deployment` 覆盖。 |
| `51_yinyang_hexmap.png`, `52_pie_in_hex.png` | 可视化变体, 信息不如当前主图清楚。 |
| `MainFig1_physics_vs_cost.png`, `MainFig2_lifetime_gate.png` | 旧主线“成本 vs 寿命”叙事图, 可能把读者拉回旧论文结构。 |

---

## 最小可交付版本

如果时间有限, 支撑材料至少放:

1. `MainFig1_twin_and_devices.png`
2. `MainFigV_fleet_validation.png`
3. `MainFig3b_inversion_robustness.png`
4. `MainFig3c_era5_grid_inversion.png`
5. `MainFig3x_temporal_fingerprint.png`
6. `MainFig3y_tandem_decomposition.png`
7. `MainFig6_substitution_validation.png`
8. `MainFig4x_degradation_risk.png`
9. `MainFig4y_substitution_timing_geo.png`
10. `diag_land_use_latitude.png`

这 10 张足以支撑 NEWFig1-5 的全部关键断言; 其他内容用表格和方法说明补齐即可。
