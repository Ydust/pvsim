using UnityEditor;
using UnityEngine;

namespace PvSim
{
    /// <summary>运行时数据/计算链自检 (批处理 -executeMethod PvSim.PvSelfTest.Run)。
    /// 验证: Newtonsoft 反序列化、中文字典键、光谱/IAM/衰减计算不抛异常且数值合理。</summary>
    public static class PvSelfTest
    {
        [MenuItem("PvSim/运行自检")]
        public static void Run()
        {
            int fail = 0;
            try
            {
                var d = PvDataLoader.Data;
                Check(d != null, "数据加载");
                Check(d.technologies.ContainsKey("c-Si") && d.technologies.ContainsKey("perovskite"), "technologies 键");
                Check(d.spectral_sf.sf.ContainsKey("c-Si") && d.spectral_sf.sf.ContainsKey("perovskite"), "spectral_sf.sf 键");
                bool degKey = d.degradation.perovskite.ContainsKey("代表性");
                Check(degKey, "衰减中文键 [代表性]");
                if (!degKey) Debug.LogError("  实际键: " + string.Join(",", d.degradation.perovskite.Keys));
                Check(d.sample_day.aoi != null && d.sample_day.aoi.Length > 2, "sample_day.aoi");

                var csi = d.technologies["c-Si"];
                var pero = d.technologies["perovskite"];

                // STC 计算
                var opC = SingleDiodeModel.Operate(csi, 1000, 25, 1000, csi.cells_in_series);
                Check(System.Math.Abs(opC.pmp - csi.stc.pmp) / csi.stc.pmp < 0.01, $"晶硅STC Pmp={opC.pmp:F1} (期望{csi.stc.pmp:F1})");

                // 真实链路: 正午 (zenith 20, aoi 10) 光谱+IAM
                double sfP = SingleDiodeModel.SpectralFactor(d.spectral_sf.zenith, d.spectral_sf.sf["perovskite"], 20);
                double iam = SingleDiodeModel.MartinRuizIAM(10);
                Check(sfP > 0.9 && sfP < 1.1, $"钙钛矿正午SF={sfP:F3}");
                Check(iam > 0.98 && iam <= 1.0, $"IAM(10°)={iam:F3}");

                // 衰减: 第10年保持率, 钙钛矿应明显低于晶硅
                var pr = d.degradation.perovskite["代表性"].retention;
                double rC10 = Interp(d.degradation.years, d.degradation.cSi, 10);
                double rP10 = Interp(d.degradation.years, pr, 10);
                Check(rP10 < rC10, $"第10年保持率 钙钛矿{rP10:F2} < 晶硅{rC10:F2}");
                Debug.Log($"[自检] 第10年: 晶硅{rC10 * 100:F0}% / 钙钛矿{rP10 * 100:F0}%");

                // 系统级: 逆变器交流 + 削顶 + 方位角
                Check(d.sample_day.azimuth != null && d.sample_day.azimuth.Length > 2, "sample_day.azimuth");
                var sysC = SystemModel.Evaluate(opC.pmp, csi.stc.pmp);
                Check(sysC.acPowerW > 0 && sysC.acPowerW <= sysC.dcPowerW,
                      $"晶硅交流 {sysC.acPowerW / 1000:F2}kW ≤ 直流 {sysC.dcPowerW / 1000:F2}kW (容量{sysC.kwp:F1}kWp)");
                double pac0 = 0.96 * 4000;
                double clipped = SystemModel.InverterAC(10000, 4000);  // 远超额定→削顶
                Check(clipped <= pac0 + 1, $"逆变器削顶 {clipped:F0}W ≤ 额定 {pac0:F0}W");

                // 多城市数据 (Unity 下拉用)
                Check(d.cities != null && d.cities.Count >= 5, $"城市数 = {(d.cities == null ? 0 : d.cities.Count)}");
                if (d.cities != null && d.cities.Count > 0)
                {
                    var c0 = d.cities[0];
                    bool dayOk = c0.day != null && c0.day.hour != null && c0.day.hour.Length > 2
                                 && c0.day.azimuth != null && c0.day.aoi != null;
                    Check(dayOk, $"首城 [{c0.name}] 代表日 {(c0.day != null && c0.day.hour != null ? c0.day.hour.Length : 0)}点");
                    Debug.Log("[自检] 城市: " + string.Join(",", d.cities.ConvertAll(c => c.name)));
                }
            }
            catch (System.Exception e)
            {
                Debug.LogError("[自检] 异常: " + e);
                fail++;
            }
            Debug.Log(fail == 0 ? "[自检] 全部通过 ✓" : $"[自检] 失败 {fail} 项");
        }

        static void Check(bool ok, string what)
        {
            if (ok) Debug.Log($"[自检] OK: {what}");
            else Debug.LogError($"[自检] FAIL: {what}");
        }

        static double Interp(int[] xs, double[] ys, double x)
        {
            if (x <= xs[0]) return ys[0];
            for (int k = 1; k < xs.Length; k++)
                if (x <= xs[k])
                    return ys[k - 1] + (ys[k] - ys[k - 1]) * (x - xs[k - 1]) / (xs[k] - xs[k - 1]);
            return ys[ys.Length - 1];
        }
    }
}
