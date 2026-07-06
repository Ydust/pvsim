"""器件参数库：早期晶硅 (c-Si) 与单结钙钛矿 (perovskite)。

所有参数取自公开文献的代表性数值（见每个字段的注释来源），用于单二极管模型。
两种技术刻意归一到**相同的器件面积**，以便公平对比"同样大小的一块光伏器件"。

单二极管 5 参数 (De Soto) 的参考值按**单个电池 (single cell)** 给出；
组件级 (module) 通过串联 N 个电池缩放（见 module.py）。

温度系数 (alpha/beta/gamma) 在这里只作为"目标/校核值"列出——本模型用物理化的
I0(T)=I0_ref*(T/Tref)^3*exp(...) 定律自然产生温度行为，calibrate.py 会核对模型
输出是否落在这些文献区间内。
"""

from __future__ import annotations

from dataclasses import dataclass, field

# 物理常数
Q = 1.602176634e-19      # 元电荷 C
K_B = 1.380649e-23       # 玻尔兹曼常数 J/K
T_REF = 298.15           # 参考温度 (STC) K = 25 °C
G_REF = 1000.0           # 参考辐照 (STC) W/m^2


@dataclass
class SpectralResponse:
    """电池的光谱响应 (外量子效率 EQE) 简化模型。

    用一个梯形/截止形状近似：在 lambda_min..lambda_max 之间 EQE≈eqe_peak，
    在带隙对应波长 lambda_gap 附近快速截止。钙钛矿在 ~800nm 锐截止、吃不到近红外，
    晶硅可延伸到 ~1180nm —— 这是两者光谱响应差异的根源。
    """

    lambda_min: float          # nm，短波起始（受前电极/玻璃吸收限制）
    lambda_gap: float          # nm，带隙截止波长 (~1240/Eg[eV])
    eqe_peak: float            # 平台区平均外量子效率 (0-1)
    edge_width: float = 40.0   # nm，带隙截止的过渡宽度
    blue_rolloff: float = 60.0 # nm，短波端衰减宽度


@dataclass
class CellTechnology:
    """一种光伏电池技术的完整参数集合。"""

    name: str
    name_cn: str

    # --- 几何 ---
    area_cm2: float                 # 单电池受光面积 cm^2
    cells_in_series: int            # 组件内串联电池数

    # --- 单二极管 (De Soto) 参考参数，按单电池给出 @STC ---
    I_L_ref: float                  # 光生电流 A (≈Isc)
    I_o_ref: float                  # 二极管反向饱和电流 A
    R_s: float                      # 串联电阻 Ω (单电池)
    R_sh_ref: float                 # 并联(分流)电阻 Ω (单电池) @1000 W/m^2
    n_ideality: float               # 二极管理想因子
    alpha_sc: float                 # Isc 温度系数 A/K (绝对值)
    EgRef: float                    # 光学带隙 eV @25°C（决定光谱截止）
    dEgdT: float                    # 带隙温度系数 eV/K（晶硅为负、钙钛矿为正！）
    Ea_recomb: float                # 复合激活能 eV（决定 I0(T)→Voc 温度依赖）
                                    # 与光学带隙解耦：钙钛矿陷阱/界面复合 Ea<Eg，
                                    # 这是其温度系数小的物理根源。由温度系数标定得到。

    # --- 文献温度系数（校核目标，%/°C）---
    gamma_pmax_lit: float           # 最大功率温度系数
    beta_voc_lit: float             # 开路电压温度系数
    alpha_isc_lit: float            # 短路电流温度系数

    # --- 热模型 ---
    noct: float                     # 标称工作温度 °C

    # --- 光谱响应 ---
    spectral: SpectralResponse

    # --- 衰减/寿命 ---
    degradation_rate: float         # 年线性衰减率 (/yr)，如 0.007 = 0.7%/yr
    burn_in_loss: float             # 初期 burn-in 总损失 (一次性，比例)
    burn_in_years: float            # burn-in 完成所需年数

    # --- I-V 迟滞 (仅钙钛矿) ---
    hysteresis_index: float         # 迟滞指数 HI = (P_rev - P_fwd)/P_rev

    # --- 双面 ---
    bifaciality: float              # 双面率 (背面/正面响应比)，单面=0

    # --- 经济性 (用于 LCOE) ---
    capex_per_wp: float             # 单位装机成本 $/Wp
    lifetime_years: float           # 设计寿命 yr

    notes: str = ""


# ---------------------------------------------------------------------------
# 早期晶硅 (代表 ~2005-2010 年量产水平, 组件效率 ~15-16%)
# 来源: De Soto et al. 2006 (单二极管参数量级); ITRPV 历史数据;
#       Dupré et al. 2015 (温度系数); 典型 156mm 多晶/单晶 BSF 电池。
# ---------------------------------------------------------------------------
CSI_EARLY = CellTechnology(
    name="c-Si",
    name_cn="早期晶硅",
    area_cm2=243.36,            # 156.75mm 准方形电池
    cells_in_series=60,         # 典型 60 片组件
    I_L_ref=8.05,              # Jsc≈33 mA/cm^2 (早期水平, 偏低)
    I_o_ref=2.7e-9,
    R_s=0.0052,                # 单电池串联电阻 Ω → FF≈0.76
    R_sh_ref=8.0,              # 单电池并联电阻 Ω
    n_ideality=1.10,
    alpha_sc=8.05 * 0.0005,    # +0.05 %/°C × Isc
    EgRef=1.121,               # Si 光学带隙 @25°C
    dEgdT=-0.0002677,          # Si 带隙随温升下降 (De Soto)
    Ea_recomb=1.0816,          # 复合激活能 (由 γ_Pmax=-0.45%/°C 标定; 接近 Eg → 带间复合主导)
    gamma_pmax_lit=-0.45,
    beta_voc_lit=-0.33,
    alpha_isc_lit=+0.05,
    noct=45.0,
    spectral=SpectralResponse(
        lambda_min=350.0, lambda_gap=1110.0, eqe_peak=0.92,
        edge_width=50.0, blue_rolloff=80.0,
    ),
    degradation_rate=0.007,    # 0.7%/yr (早期组件略快于现代 0.5%)
    burn_in_loss=0.02,         # 首年 LID ~2%
    burn_in_years=1.0,
    hysteresis_index=0.0,      # 晶硅无 I-V 迟滞
    bifaciality=0.0,           # 早期为单面 Al-BSF
    capex_per_wp=1.0,          # 归一参考值 ($/Wp)，可按需调整
    lifetime_years=25.0,
    notes="早期量产晶硅, 组件效率~15.6%, 稳定但温度敏感、无弱光优势。",
)


# ---------------------------------------------------------------------------
# 单结钙钛矿 (代表近年高效水平, 单结效率 ~20%)
# 来源: NREL 效率表; Green et al. Solar cell efficiency tables;
#       钙钛矿温度系数 ~ -0.1~-0.3 %/°C (Moot et al. 2021);
#       MAPbI3 dEg/dT ≈ +0.3 meV/K (带隙随温升上升, 与晶硅相反)。
# 衰减率不确定性极大 (随封装/组分差异从小时级到数千小时), 这里取代表性较快值,
# 并在 degradation.py 提供乐观/悲观情景。
# ---------------------------------------------------------------------------
PEROVSKITE = CellTechnology(
    name="perovskite",
    name_cn="钙钛矿",
    area_cm2=243.36,           # 归一到与晶硅相同面积, 便于公平对比
    cells_in_series=60,
    I_L_ref=5.48,             # Jsc≈22.5 mA/cm^2 (带隙宽→吃不到近红外, 电流低)
    I_o_ref=9.5e-12,          # 高 Voc → 极小 I0
    R_s=0.016,                # 单电池串联电阻 Ω → FF≈0.78
    R_sh_ref=30.0,            # 高并联电阻 → 弱光性能好
    n_ideality=1.60,          # 钙钛矿理想因子偏高
    alpha_sc=5.48 * 0.0002,   # +0.02 %/°C
    EgRef=1.55,               # 钙钛矿光学带隙 (可调, 取~1.55)
    dEgdT=+0.0003,            # 带隙随温升**上升** (与晶硅相反, 部分抵消温度损失)
    Ea_recomb=0.8258,         # 复合激活能 (由 γ_Pmax=-0.15%/°C 标定; <Eg → 陷阱/界面
                              #            复合主导, 这是钙钛矿温度系数小的物理根源)
    gamma_pmax_lit=-0.15,
    beta_voc_lit=-0.15,
    alpha_isc_lit=+0.02,
    noct=44.0,
    spectral=SpectralResponse(
        lambda_min=350.0, lambda_gap=800.0, eqe_peak=0.90,
        edge_width=25.0, blue_rolloff=60.0,   # ~800nm 锐截止, 蓝光响应好
    ),
    degradation_rate=0.030,    # 3%/yr (代表性, 远快于晶硅; 见情景设置)
    burn_in_loss=0.10,         # 初期 burn-in 较大 (~10%)
    burn_in_years=1.0,
    hysteresis_index=0.04,     # 正反扫描功率差 ~4% (代表性)
    bifaciality=0.0,           # 单结不透明假设为单面
    capex_per_wp=0.8,          # 潜在更低材料/工艺成本 (示意值)
    lifetime_years=15.0,       # 设计寿命短于晶硅
    notes="单结钙钛矿, 效率~20%, 温度/弱光优势明显, 但衰减快、寿命短、有迟滞。",
)


# ---------------------------------------------------------------------------
# 钙钛矿/晶硅两端叠层 (Perov/Si 2-T tandem, 商业目标效率 ~28-30%)
# 物理: 顶电池(钙钛矿 Eg=1.68eV)吃可见光, 底电池(晶硅 Eg=1.12eV)吃透过的近红外,
#       电流匹配 (j_matched=min(j_top,j_bot) ~19 mA/cm²), 电压相加 (~1.84V/cell).
# 来源: Cordell et al. (NREL 2025, OSTI 2481281) 25-35% efficiency TEA;
#       LONGi 2024 实验室 33% 记录; Oxford PV 商业 26.9% 组件;
#       温度系数 γ_Pmax ~-0.28~-0.35 %/°C (Babics et al. 2023 ACS Energy Letters).
# 退化: 2T 串联架构寿命受顶电池限制, 但封装成熟后可达 25y (Oxford PV 设计目标).
# ---------------------------------------------------------------------------
TANDEM_2T = CellTechnology(
    name="tandem",
    name_cn="叠层",
    area_cm2=243.36,            # 与 c-Si/钙钛矿同面积, 公平对比
    cells_in_series=60,
    I_L_ref=4.62,              # j_matched ~19 mA/cm² × 243 cm² (current-matched)
    I_o_ref=1.3e-15,           # 极小, 对应 Voc/cell ~1.84V
    R_s=0.025,                 # 略高 (两个 junction 串联界面)
    R_sh_ref=50.0,             # 高分流电阻
    n_ideality=2.0,            # 两个二极管串联的有效理想因子
    alpha_sc=4.62 * 0.00025,   # +0.025%/°C, 受电流匹配限制
    EgRef=1.68,                # 顶电池(钙钛矿宽带隙)
    dEgdT=+0.0001,             # 介于 perov (+) 和 c-Si (-) 之间
    Ea_recomb=1.5087,          # 标定到 γ_Pmax = -0.30%/°C (Babics 2023 ACS Energy Lett.).
                               # [订正] 旧值 0.95 实际只产生 γ=-0.06 (n_ideality=2.0 压低了温度敏感性);
                               # 经 operating_point 重标定为 1.5087 命中 -0.30. STC 效率不受影响(25°C 时 I0(T) 指数项=1)。
    gamma_pmax_lit=-0.30,      # Babics 2023 ACS Energy Lett.
    beta_voc_lit=-0.24,
    alpha_isc_lit=+0.025,
    noct=45.0,
    spectral=SpectralResponse(
        lambda_min=350.0, lambda_gap=1110.0, eqe_peak=0.85,  # 综合双结响应
        edge_width=50.0, blue_rolloff=70.0,
    ),
    degradation_rate=0.012,    # 1.2%/yr, 介于 c-Si(0.7) 和 perov(3) 之间
    burn_in_loss=0.04,         # 适中 burn-in
    burn_in_years=1.0,
    hysteresis_index=0.01,     # 钙钛矿层小残留滞回
    bifaciality=0.0,           # 2T 单面 (背接触不透光)
    capex_per_wp=1.13,         # NREL Cordell cell $0.428 + BOS $0.70 (2025 baseline)
    lifetime_years=25.0,
    notes="钙钛矿/晶硅 2T 叠层, 效率~28%, 兼顾温度系数+宽光谱; 学习速度最快.",
)


# ---------------------------------------------------------------------------
# 现代晶硅 (TOPCon/PERC 代表, ~2023-2024 量产, 组件效率 ~22%)
# 这是当前中国实际在装的主流晶硅; 作为"现实基准"对照钙钛矿/叠层 (早期晶硅降为历史对照)。
# 来源: ITRPV 2023/2024 (Jsc~40mA/cm², 组件 22%); TOPCon γ_Pmax ~-0.29~-0.33 %/°C.
# 参数经 calibrate: Ea_recomb 命中 γ=-0.32, I_L_ref 命中 STC 22%. 光谱响应同晶硅 (同带隙)。
# ---------------------------------------------------------------------------
CSI_MODERN = CellTechnology(
    name="c-Si-modern",
    name_cn="现代晶硅",
    area_cm2=243.36,
    cells_in_series=60,
    I_L_ref=11.0962,           # Jsc ~40 mA/cm² (现代水平, 高于早期 33)
    I_o_ref=4.0e-10,           # 更高 Voc (更好钝化)
    R_s=0.0040,
    R_sh_ref=15.0,
    n_ideality=1.02,
    alpha_sc=11.0962 * 0.000363,
    EgRef=1.121,
    dEgdT=-0.0002677,
    Ea_recomb=0.9957,          # 标定到 γ_Pmax = -0.32 %/°C (TOPCon/PERC)
    gamma_pmax_lit=-0.32,
    beta_voc_lit=-0.27,
    alpha_isc_lit=+0.04,
    noct=44.0,
    spectral=SpectralResponse(
        lambda_min=350.0, lambda_gap=1110.0, eqe_peak=0.95,
        edge_width=50.0, blue_rolloff=70.0,
    ),
    degradation_rate=0.005,    # 现代组件 0.5%/yr
    burn_in_loss=0.01,
    burn_in_years=1.0,
    hysteresis_index=0.0,
    bifaciality=0.0,
    capex_per_wp=1.0,
    lifetime_years=25.0,
    notes="现代 TOPCon/PERC 晶硅, 组件效率~22%, γ~-0.32; 现实基准。",
)


TECHNOLOGIES = {
    CSI_EARLY.name: CSI_EARLY,
    CSI_MODERN.name: CSI_MODERN,
    PEROVSKITE.name: PEROVSKITE,
    TANDEM_2T.name: TANDEM_2T,
}


def get_technology(name: str) -> CellTechnology:
    if name not in TECHNOLOGIES:
        raise KeyError(f"未知技术 '{name}', 可选: {list(TECHNOLOGIES)}")
    return TECHNOLOGIES[name]
