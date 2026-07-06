using System;

namespace PvSim
{
    /// <summary>组件→系统级：阵列直流 → 逆变器(含削顶) → 交流上网功率。
    /// 与 Python pvsim/system.py 一致 (PVWatts 逆变器模型 + 系统损耗)。</summary>
    public static class SystemModel
    {
        // 系统配置 (对应 system.py 的 SystemConfig 默认值)
        public const int N_MODULES = 20;          // 组件数
        public const double DC_AC_RATIO = 1.2;    // 直流/交流容量比
        public const double INVERTER_ETA_NOM = 0.96;
        public const double DC_LOSS = 0.05;        // 直流侧损失(污渍/线损)
        public const double MISMATCH_LOSS = 0.02;  // 组件间失配

        /// <summary>PVWatts 逆变器模型：直流功率(W) → 交流功率(W)，超额定削顶。</summary>
        public static double InverterAC(double pdc, double pdc0,
                                        double etaNom = INVERTER_ETA_NOM)
        {
            if (pdc <= 0 || pdc0 <= 0) return 0.0;
            const double etaRef = 0.9637;
            double pac0 = etaNom * pdc0;                 // 最大交流输出
            double zeta = pdc / pdc0;
            double eta = (etaNom / etaRef) *
                         (-0.0162 * zeta - 0.0059 / Math.Max(zeta, 1e-6) + 0.9858);
            double pac = eta * pdc;
            return Math.Min(Math.Max(pac, 0.0), pac0);   // 削顶
        }

        public struct SystemResult
        {
            public double kwp;          // 阵列额定容量
            public double dcPowerW;     // 阵列直流功率
            public double acPowerW;     // 交流上网功率
            public bool clipping;       // 是否削顶
        }

        /// <summary>由单组件 Pmax 与额定，算整阵列交流上网功率。</summary>
        public static SystemResult Evaluate(double modulePmpW, double moduleStcW)
        {
            double kwp = N_MODULES * moduleStcW / 1000.0;
            double dc = N_MODULES * modulePmpW * (1.0 - MISMATCH_LOSS) * (1.0 - DC_LOSS);
            double pdc0 = kwp * 1000.0 / DC_AC_RATIO;
            double ac = InverterAC(dc, pdc0);
            bool clip = dc * INVERTER_ETA_NOM > INVERTER_ETA_NOM * pdc0 + 1e-6;
            return new SystemResult { kwp = kwp, dcPowerW = dc, acPowerW = ac, clipping = clip };
        }
    }
}
