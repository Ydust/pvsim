using System;
using System.IO;
using System.Text.Json;

namespace PvSim
{
    // SingleDiodeModel 需要的最小 TechParams (字段名与 PvData.cs 一致, 此处独立定义以脱离 Unity)。
    public class StcValues { public double isc, voc, pmp, ff, eff; }

    public class TechParams
    {
        public string name, name_cn, color;
        public double area_cm2;
        public int cells_in_series;
        public double I_L_ref, I_o_ref, R_s, R_sh_ref, n_ideality;
        public double alpha_sc, EgRef, Ea_recomb, noct;
        public double lambda_min, lambda_gap, eqe_peak, edge_width, blue_rolloff;
        public double bifaciality, lifetime_years, capex_per_wp, hysteresis_index;
        public StcValues stc;
    }

    static class Program
    {
        static TechParams FromJson(JsonElement e)
        {
            var t = new TechParams();
            t.area_cm2 = e.GetProperty("area_cm2").GetDouble();
            t.cells_in_series = e.GetProperty("cells_in_series").GetInt32();
            t.I_L_ref = e.GetProperty("I_L_ref").GetDouble();
            t.I_o_ref = e.GetProperty("I_o_ref").GetDouble();
            t.R_s = e.GetProperty("R_s").GetDouble();
            t.R_sh_ref = e.GetProperty("R_sh_ref").GetDouble();
            t.n_ideality = e.GetProperty("n_ideality").GetDouble();
            t.alpha_sc = e.GetProperty("alpha_sc").GetDouble();
            t.Ea_recomb = e.GetProperty("Ea_recomb").GetDouble();
            t.stc = new StcValues
            {
                isc = e.GetProperty("stc").GetProperty("isc").GetDouble(),
                voc = e.GetProperty("stc").GetProperty("voc").GetDouble(),
                pmp = e.GetProperty("stc").GetProperty("pmp").GetDouble(),
                ff = e.GetProperty("stc").GetProperty("ff").GetDouble(),
                eff = e.GetProperty("stc").GetProperty("eff").GetDouble(),
            };
            return t;
        }

        static int Main()
        {
            string path = "../PvCompare/Assets/StreamingAssets/pvdata.json";
            var doc = JsonDocument.Parse(File.ReadAllText(path));
            var techs = doc.RootElement.GetProperty("technologies");

            int fails = 0;
            foreach (var key in new[] { "c-Si", "perovskite" })
            {
                var t = FromJson(techs.GetProperty(key));
                var op = SingleDiodeModel.Operate(t, 1000.0, 25.0, 1000.0, t.cells_in_series, npts: 400);
                Console.WriteLine($"=== {key} (Ns={t.cells_in_series}) ===");
                Console.WriteLine($"  C#   : Isc={op.isc:F3} Voc={op.voc:F3} Pmp={op.pmp:F2} FF={op.ff:F4} eff={op.eff * 100:F2}%");
                Console.WriteLine($"  Py(STC): Isc={t.stc.isc:F3} Voc={t.stc.voc:F3} Pmp={t.stc.pmp:F2} FF={t.stc.ff:F4} eff={t.stc.eff * 100:F2}%");
                double dP = Math.Abs(op.pmp - t.stc.pmp) / t.stc.pmp * 100;
                double dV = Math.Abs(op.voc - t.stc.voc) / t.stc.voc * 100;
                double dI = Math.Abs(op.isc - t.stc.isc) / t.stc.isc * 100;
                Console.WriteLine($"  偏差: Pmp {dP:F3}%  Voc {dV:F3}%  Isc {dI:F3}%");
                bool ok = dP < 0.5 && dV < 0.5 && dI < 0.5;
                Console.WriteLine(ok ? "  -> 一致 OK\n" : "  -> 偏差过大 FAIL\n");
                if (!ok) fails++;
            }
            // 温度行为抽查: 60°C 下 c-Si 应比钙钛矿掉得多
            var csi = FromJson(techs.GetProperty("c-Si"));
            var pero = FromJson(techs.GetProperty("perovskite"));
            double pc25 = SingleDiodeModel.Operate(csi, 1000, 25, 1000, 60).pmp;
            double pc60 = SingleDiodeModel.Operate(csi, 1000, 60, 1000, 60).pmp;
            double pp25 = SingleDiodeModel.Operate(pero, 1000, 25, 1000, 60).pmp;
            double pp60 = SingleDiodeModel.Operate(pero, 1000, 60, 1000, 60).pmp;
            Console.WriteLine($"温度抽查 25→60°C 功率保持: 晶硅 {pc60 / pc25 * 100:F1}%, 钙钛矿 {pp60 / pp25 * 100:F1}% (钙钛矿应更高)");
            if (!(pp60 / pp25 > pc60 / pc25)) fails++;

            Console.WriteLine(fails == 0 ? "\n全部通过：C# 物理核心与 Python 一致。" : $"\n{fails} 项未通过。");
            return fails == 0 ? 0 : 1;
        }
    }
}
