using System;

namespace PvSim
{
    /// <summary>Lambert W 函数主分支 W0 (实数, x >= 0)，Halley 迭代。
    /// 用于单二极管 I-V 方程的闭式解 (与 Python scipy.special.lambertw 对应)。</summary>
    public static class LambertW
    {
        public static double W0(double x)
        {
            if (double.IsNaN(x)) return double.NaN;
            if (x <= 0.0) return 0.0;            // 本应用中 arg 恒为正
            // 大参数用渐近式避免 exp 溢出
            if (x > 1e8)
            {
                double l1 = Math.Log(x);
                double l2 = Math.Log(l1);
                return l1 - l2 + l2 / l1;
            }
            double w = Math.Log(1.0 + x);        // 全局初值 (x>=0 适用)
            for (int i = 0; i < 60; i++)
            {
                double ew = Math.Exp(w);
                double f = w * ew - x;
                double wp1 = w + 1.0;
                double dw = f / (ew * wp1 - (w + 2.0) * f / (2.0 * wp1));
                w -= dw;
                if (Math.Abs(dw) < 1e-13 * (1.0 + Math.Abs(w))) break;
            }
            return w;
        }
    }
}
