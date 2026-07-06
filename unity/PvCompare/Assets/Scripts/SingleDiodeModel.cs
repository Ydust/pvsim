using System;

namespace PvSim
{
    /// <summary>单二极管电池模型 (De Soto + Lambert W)，C# 实时版。
    /// 与 Python pvsim/cell.py 一致：随辐照/温度平移参数，解析求 I-V、Pmax、效率。</summary>
    public static class SingleDiodeModel
    {
        const double Q = 1.602176634e-19;
        const double KB = 1.380649e-23;
        const double T_REF = 298.15;
        const double G_REF = 1000.0;
        const double K_EV = 8.617333262e-5;

        public struct DiodeParams { public double IL, I0, Rs, Rsh, nNsVth; }

        public struct OpPoint
        {
            public double isc, voc, imp, vmp, pmp, ff, eff;
            public double[] v, i;   // I-V 曲线 (绘图用)
        }

        public static DiodeParams Translate(TechParams t, double effIrr, double tcellC, int ns)
        {
            double geff = Math.Max(effIrr, 1e-6);
            double tK = tcellC + 273.15;
            double IL = (geff / G_REF) * (t.I_L_ref + t.alpha_sc * (tK - T_REF));
            double I0 = t.I_o_ref * Math.Pow(tK / T_REF, 3.0)
                        * Math.Exp(t.Ea_recomb / K_EV * (1.0 / T_REF - 1.0 / tK));
            double Rsh = t.R_sh_ref * (G_REF / geff);
            double aCell = t.n_ideality * KB * tK / Q;
            return new DiodeParams
            {
                IL = IL,
                I0 = I0,
                Rs = t.R_s * ns,
                Rsh = Rsh * ns,
                nNsVth = aCell * ns,
            };
        }

        public static double IFromV(double v, DiodeParams p)
        {
            double Gsh = 1.0 / p.Rsh;
            double A = 1.0 + p.Rs * Gsh;
            double a = p.nNsVth;
            double c = p.Rs * p.I0 / (A * a);
            double d = (p.Rs * (p.IL + p.I0) + v) / (A * a);
            double arg = c * Math.Exp(Math.Min(Math.Max(d, -700.0), 700.0));
            double w = LambertW.W0(arg);
            double u = a * (d - w);
            return (u - v) / p.Rs;
        }

        static double FindVoc(DiodeParams p)
        {
            double vocEst = p.nNsVth * Math.Log(p.IL / p.I0 + 1.0);
            int n = 400;
            double prevV = 0.0, prevI = IFromV(0.0, p);
            for (int k = 1; k <= n; k++)
            {
                double v = 1.5 * vocEst * k / n;
                double i = IFromV(v, p);
                if (i <= 0.0)
                {
                    // 线性插值过零
                    return prevV - prevI * (v - prevV) / (i - prevI);
                }
                prevV = v; prevI = i;
            }
            return 1.5 * vocEst;
        }

        /// <summary>计算工况下的工作点 + I-V 曲线。
        /// irradiance: 宽谱 POA (效率分母)；effIrr: 有效辐照 (产生电流)。</summary>
        public static OpPoint Operate(TechParams t, double irradiance, double tcellC,
                                      double effIrr, int ns, int npts = 160)
        {
            var p = Translate(t, effIrr, tcellC, ns);
            double isc = IFromV(0.0, p);
            double voc = FindVoc(p);
            var op = new OpPoint();
            if (voc <= 0 || isc <= 0)
            {
                op.v = new double[] { 0 }; op.i = new double[] { 0 };
                return op;
            }

            double[] vv = new double[npts];
            double[] ii = new double[npts];
            int kmax = 0; double pmax = -1;
            for (int k = 0; k < npts; k++)
            {
                double v = voc * k / (npts - 1);
                double cur = Math.Max(IFromV(v, p), 0.0);
                vv[k] = v; ii[k] = cur;
                double pw = v * cur;
                if (pw > pmax) { pmax = pw; kmax = k; }
            }
            // 抛物线精修 MPP
            double vmp = vv[kmax];
            if (kmax > 0 && kmax < npts - 1)
            {
                double y0 = vv[kmax - 1] * ii[kmax - 1];
                double y1 = vv[kmax] * ii[kmax];
                double y2 = vv[kmax + 1] * ii[kmax + 1];
                double denom = (y0 - 2 * y1 + y2);
                if (denom != 0)
                    vmp = vv[kmax] - 0.5 * (vv[kmax + 1] - vv[kmax - 1]) * (y2 - y0) / denom / 2.0;
            }
            double imp = Math.Max(IFromV(vmp, p), 0.0);
            double pmp = vmp * imp;
            double ff = (voc * isc > 0) ? pmp / (voc * isc) : 0.0;
            double areaM2 = ns * t.area_cm2 / 1e4;
            double eff = (irradiance > 0) ? pmp / (areaM2 * irradiance) : 0.0;

            op.isc = isc; op.voc = voc; op.imp = imp; op.vmp = vmp;
            op.pmp = pmp; op.ff = ff; op.eff = eff; op.v = vv; op.i = ii;
            return op;
        }

        /// <summary>Faiman 电池温度模型 (与 pvsim/temperature.py 一致)。</summary>
        public static double CellTemperature(double poa, double tair, double wind,
                                             double u0 = 25.0, double u1 = 6.84)
        {
            return tair + poa / (u0 + u1 * wind);
        }

        /// <summary>Martin-Ruiz 入射角修正 IAM (与 pvsim/optics.py 一致)。aoi 度。</summary>
        public static double MartinRuizIAM(double aoiDeg, double ar = 0.16)
        {
            if (aoiDeg >= 90.0 || aoiDeg < 0.0) return Math.Max(0.0, Math.Cos(aoiDeg * Math.PI / 180.0));
            double c = Math.Cos(aoiDeg * Math.PI / 180.0);
            return (1.0 - Math.Exp(-c / ar)) / (1.0 - Math.Exp(-1.0 / ar));
        }

        /// <summary>由天顶角插值光谱失配因子 SF。</summary>
        public static double SpectralFactor(double[] zenith, double[] sf, double zen)
        {
            if (zenith == null || sf == null || zenith.Length == 0) return 1.0;
            zen = Math.Min(Math.Max(zen, zenith[0]), zenith[zenith.Length - 1]);
            for (int k = 1; k < zenith.Length; k++)
            {
                if (zen <= zenith[k])
                {
                    double f = (zen - zenith[k - 1]) / (zenith[k] - zenith[k - 1]);
                    return sf[k - 1] + f * (sf[k] - sf[k - 1]);
                }
            }
            return sf[sf.Length - 1];
        }
    }
}
