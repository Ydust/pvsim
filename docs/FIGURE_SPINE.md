# C 路线论文 — 主线与图谱, Figure Spine

**目标标准**: Joule-plus 内部标准

**题目**: Perovskite gains most where sunlight is weakest: a physics-resolved reassessment of
China's solar transition

**当前决定, 2026-06-30**: 正文采用最新 `NEWFig1-5`。旧 `MainFig1_twin_and_devices` 不再做主图,
而是作为验证/SI 支撑; 铟约束降为 Discussion/SI 背景, 不再承担主线图位。

---

## 一句话主线

> 作者用验证过的物理孪生证明: Fig 1 显示钙钛矿相对现代晶硅的每 kWp 优势在弱光/西南最大而非西北,
> Fig 2 解释这个反转由温度和光谱两个独立机制组成, Fig 3 显示标称效率会误判每 kWp 与每 m²
> 两种市场排序, Fig 4 表明替代受寿命/退化/capex 门控并表现为情景分布,
> 因而陆域部署应按物理分区: 西南/南方陆上地面集中式钙钛矿、屋顶叠层、
> Fig 5 则把结论落到西北/低优势陆上地面集中式守晶硅。

主线的重心是**从物理优势到陆域部署决策**: 先证明优势在哪里, 再解释为什么, 再把技术排序和经济时机
落到陆上地面集中式、屋顶与区域分工。海上/水面漂浮光伏不进入主图模型, 只在局限中说明。

---

## 主图序列, NEWFig1-5

| # | 文件 | 标题 | 论证环节 | 必须让读者记住的数字 |
|---|---|---|---|---|
| **Fig 1** | `NEWFig1_inversion.png` | 地理反转: sunlight weakest, gain largest | 空间头条 | ~95k 陆地格点气候态空间型态; 年辐照反相关 r=-0.51; 西南最大、西北最小 |
| **Fig 2** | `NEWFig2_mechanisms.png` | 两个独立机制: 温度项 + 光谱项 | 机理解释 | 温度 r=+0.98; 光谱 r=-0.85; 温度夏季、光谱全年 |
| **Fig 3** | `NEWFig3_segmentation.png` | 效率不等于发电: 换尺子排序翻转 | 市场分段 | 钙钛矿 0.88x 效率但 1.03x/kWp、0.90x/m²; 叠层 1.30x/m² |
| **Fig 4** | `NEWFig4_economics_timing.png` | 寿命经济门控: 情景交叉而非点预测 | 时间/经济 | yield edge 只值 +0.07 cents/kWh; P10/P50/P90=2030/2032/2039; 2.7% 到 2050 年仍未交叉 |
| **Fig 5** | `NEWFig5_deployment.png` | 按物理部署: 陆上决策平面 + 装机错配 | 落点/政策 | 高优势三分位仅 24% 2024 装机; 高纬陆上土地惩罚 r=0.98 |

---

## 图间逻辑

1. **Fig 1 先抛结论**: 钙钛矿不是在太阳最强的地方最有相对价值, 而是在弱光、热、低纬的西南最大。
2. **Fig 2 解释反直觉来源**: 温度收益和蓝光谱收益是两条独立物理链, 不是同一个地理变量的重复表达。
3. **Fig 3 防止误读技术优劣**: 每 kWp 是陆上地面集中式电站的尺子, 每 m² 是屋顶的尺子; 钙钛矿和叠层各有市场。
4. **Fig 4 把物理优势放回经济现实**: 优势存在, 但替代时机主要被寿命、退化和 capex 门控。
5. **Fig 5 给部署答案**: 现有装机重心和物理优势错配, 因而建议不是“一刀切替代”, 而是陆上地面集中式/屋顶的区域分工。

---

## SI 与支撑图

详细补充清单见 `docs/SUPPORTING_MATERIALS_PLAN.md`。最小 SI 版本应优先保留模型验证、反转稳健性、
机制深挖、替代校准和土地惩罚这五组证据。
Joule-plus 缺口审计见 `docs/JOULE_PLUS_GAP_AUDIT.md`。

| 图 | 角色 | 支撑哪一环 |
|---|---|---|
| `MainFig1_twin_and_devices.png` | 数值验证 + 8760h 运行物理 + 退化直觉 | 方法可信度; 支撑 Fig 1-4 |
| `MainFigV_fleet_validation.png` | 真实机队系统级锚定 | 方法可信度; fleet r=0.89; 扣除 15.3% 系统损失后 RMSE=102 kWh/kWp |
| `MainFig3x_temporal_fingerprint.png` | 温度/光谱时间指纹深挖 | Fig 2 |
| `MainFig3y_tandem_decomposition.png` | 解释叠层为什么是面积技术 | Fig 3 / Fig 5 |
| `MainFig4x_degradation_risk.png` | 寿命风险地理 | Fig 4 |
| `MainFig4y_substitution_timing_geo.png` | 替代时机地理的条件性 | Fig 4 / Fig 5 |
| `MainFig3b`, `MainFig3c` | 对抗场景与 0.1° 网格稳健性 | Fig 1 |
| `MainFig4_indium_constraint.png` | 全球性材料约束背景 | Discussion / SI |

---

## 已降级或替换

| 旧位置/文件 | 当前处理 | 原因 |
|---|---|---|
| `MainFig1_twin_and_devices` | 主图降为 SI 验证支撑 | 作为 Fig 1 会把结果主线延后; 验证重要但不是 headline |
| `MainFig2_yield_segmentation` | 被 `NEWFig3_segmentation` 替换 | 保留“效率≠发电”, 但版面更直接服务市场分段 |
| `MainFig3_geographic_inversion` | 被 `NEWFig1_inversion` + `NEWFig2_mechanisms` 拆分 | 地理反转太关键, 需要 Fig 1 先打出; 机理另给 Fig 2 |
| `MainFig4_economics_timing` | 被 `NEWFig4_economics_timing` 替换 | 已做视觉降噪: LCOE 区间带、delta-LCOE、中央路径加蒙卡区间带、2050 后尾部 |
| `MainFig5_deployment_map` | 被 `NEWFig5_deployment` 替换 | 改为陆上地面集中式优势×土地惩罚决策平面、优势三分位装机统计和高纬土地惩罚来源三者联动 |
| `Fig 6` / 铟主线图位 | 不进主图 | 铟是全球长期约束, 不是本文五图叙事的主轴 |

---

## 读者动线检验

读者读完 5 张主图后, 应能复述:

> 钙钛矿的相对优势在中国不是随太阳资源增强, 而是在弱光、热、低纬地区最大; 这个优势由温度和光谱
> 两个独立机制驱动。效率排名不能直接外推到发电排名, 因为陆上地面集中式看每 kWp、屋顶看每 m²。
> 真正的替代时间又被寿命和退化门控, 所以陆域部署策略应按物理分区, 不是按现有西北大基地惯性一刀切。

若这句话能被复述, 五图主线就是清楚的。
