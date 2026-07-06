using UnityEngine;
using UnityEngine.UI;

namespace PvSim
{
    /// <summary>实时仿真主控：读取滑块(辐照/气温/风速)，调用单二极管模型计算两种电池的
    /// I-V 曲线、最大功率、效率、电池温度，并更新 UI 文本、I-V/P-V 图与 3D 设备出力。</summary>
    public class SimulationController : MonoBehaviour
    {
        [Header("输入滑块")]
        public Slider irradianceSlider;   // 辐照 0..1200 W/m^2
        public Slider tempSlider;         // 气温 -10..45 °C
        public Slider windSlider;         // 风速 0..8 m/s
        public Slider yearsSlider;        // 运行年数 0..25 (衰减)

        [Header("数值标签")]
        public Text irradianceLabel, tempLabel, windLabel, yearsLabel;

        // 太阳几何 (由 DayPlayer 在播放时更新；默认接近 AM1.5 参考)
        [HideInInspector] public double currentZenith = 48.0;
        [HideInInspector] public double currentAoi = 0.0;

        [Header("读数面板 (晶硅 / 钙钛矿)")]
        public Text csiReadout;
        public Text peroReadout;

        [Header("曲线图")]
        public RawImage ivImage;          // I-V 曲线
        public RawImage pvImage;          // P-V 曲线

        [Header("3D 设备出力条")]
        public Transform csiBar;          // 晶硅出力条 (按 Pmax 缩放高度)
        public Transform peroBar;         // 钙钛矿出力条
        public Renderer csiPanel;         // 设备表面 (按温度着色)
        public Renderer peroPanel;

        TechParams csi, pero;
        TexturePlotter ivPlot, pvPlot;
        int nsC, nsP;
        double pmaxStcC, pmaxStcP;
        // 光谱表 / 衰减表
        double[] specZen, specC, specP;
        int[] degYears;
        double[] degC, degP;

        void Start()
        {
            SetupChineseFont();
            var data = PvDataLoader.Data;
            if (data == null) { Debug.LogError("数据未加载"); enabled = false; return; }
            csi = data.technologies["c-Si"];
            pero = data.technologies["perovskite"];
            nsC = csi.cells_in_series; nsP = pero.cells_in_series;
            pmaxStcC = csi.stc.pmp; pmaxStcP = pero.stc.pmp;

            // 光谱失配表 + 衰减表 (代表性钙钛矿情景)
            specZen = data.spectral_sf.zenith;
            specC = data.spectral_sf.sf["c-Si"];
            specP = data.spectral_sf.sf["perovskite"];
            degYears = data.degradation.years;
            degC = data.degradation.cSi;
            degP = data.degradation.perovskite["代表性"].retention;

            ivPlot = new TexturePlotter(460, 300);
            pvPlot = new TexturePlotter(460, 300);
            if (ivImage) ivImage.texture = ivPlot.Texture;
            if (pvImage) pvImage.texture = pvPlot.Texture;

            if (irradianceSlider) { irradianceSlider.minValue = 0; irradianceSlider.maxValue = 1200; irradianceSlider.value = 1000; irradianceSlider.onValueChanged.AddListener(_ => Recompute()); }
            if (tempSlider) { tempSlider.minValue = -10; tempSlider.maxValue = 45; tempSlider.value = 25; tempSlider.onValueChanged.AddListener(_ => Recompute()); }
            if (windSlider) { windSlider.minValue = 0; windSlider.maxValue = 8; windSlider.value = 1.5f; windSlider.onValueChanged.AddListener(_ => Recompute()); }
            if (yearsSlider) { yearsSlider.minValue = 0; yearsSlider.maxValue = 25; yearsSlider.value = 0; yearsSlider.onValueChanged.AddListener(_ => Recompute()); }

            Recompute();
        }

        void SetupChineseFont()
        {
            // 旧版 UI Text 的内置字体不含中文字形，运行时换成系统中文动态字体。
            var dyn = Font.CreateDynamicFontFromOSFont(
                new[] { "Microsoft YaHei", "SimHei", "DengXian" }, 16);
            if (dyn == null) return;
            // 含未激活对象 (下拉菜单的模板项), 否则展开时中文显示为方块
            foreach (var txt in FindObjectsOfType<Text>(true)) txt.font = dyn;
        }

        void Recompute()
        {
            if (csi == null || pero == null) return;   // 数据未就绪 (防外部提前触发)
            double G = irradianceSlider ? irradianceSlider.value : 1000.0;
            double tair = tempSlider ? tempSlider.value : 25.0;
            double wind = windSlider ? windSlider.value : 1.5;

            double years = yearsSlider ? yearsSlider.value : 0.0;

            if (irradianceLabel) irradianceLabel.text = $"辐照  {G:0} W/m²";
            if (tempLabel) tempLabel.text = $"气温  {tair:0.0} °C";
            if (windLabel) windLabel.text = $"风速  {wind:0.0} m/s";
            if (yearsLabel) yearsLabel.text = $"运行  {years:0} 年";

            // 真实运行链路: 有效辐照 = 宽谱POA × 光谱失配(随太阳天顶角) × 入射角修正IAM
            double sfC = SingleDiodeModel.SpectralFactor(specZen, specC, currentZenith);
            double sfP = SingleDiodeModel.SpectralFactor(specZen, specP, currentZenith);
            double iam = SingleDiodeModel.MartinRuizIAM(currentAoi);
            double effC = G * sfC * iam;
            double effP = G * sfP * iam;

            // Faiman 由辐照+气温+风速算电池温度
            double tcell = SingleDiodeModel.CellTemperature(G, tair, wind);

            var opC = SingleDiodeModel.Operate(csi, G, tcell, effC, nsC);
            var opP = SingleDiodeModel.Operate(pero, G, tcell, effP, nsP);

            // 多年衰减: 按运行年数的性能保持率derate (晶硅慢、钙钛矿快)
            double retC = Retention(degYears, degC, years);
            double retP = Retention(degYears, degP, years);
            Derate(ref opC, retC);
            Derate(ref opP, retP);

            // 系统级: 阵列直流 → 逆变器(削顶) → 交流上网
            var sysC = SystemModel.Evaluate(opC.pmp, pmaxStcC);
            var sysP = SystemModel.Evaluate(opP.pmp, pmaxStcP);

            if (csiReadout) csiReadout.text = Readout("早期晶硅", opC, tcell, pmaxStcC, retC, years, sysC);
            if (peroReadout) peroReadout.text = Readout("钙钛矿", opP, tcell, pmaxStcP, retP, years, sysP);

            UpdateBar(csiBar, opC.pmp, pmaxStcC);
            UpdateBar(peroBar, opP.pmp, pmaxStcP);
            TintByTemp(csiPanel, tcell);
            TintByTemp(peroPanel, tcell);

            DrawPlots(opC, opP);
        }

        string Readout(string name, SingleDiodeModel.OpPoint op, double tcell,
                       double pstc, double retention, double years,
                       SystemModel.SystemResult sys)
        {
            double relStc = pstc > 0 ? op.pmp / pstc * 100.0 : 0;
            string ageLine = years > 0
                ? $"运行 {years:0} 年衰减保持 = {retention * 100:0.0} %\n"
                : "";
            string clip = sys.clipping ? "  <color=#ff6666>[削顶]</color>" : "";
            return $"<b>{name}</b>  (单组件)\n" +
                   $"最大功率 Pmax = {op.pmp:0.0} W\n" +
                   $"Voc = {op.voc:0.0} V   Isc = {op.isc:0.00} A   FF = {op.ff:0.000}\n" +
                   $"效率 η = {op.eff * 100:0.0} %   电池温度 = {tcell:0.0} °C\n" +
                   ageLine +
                   $"相对STC功率 = {relStc:0.0} %\n" +
                   $"<b>整阵列 ({SystemModel.N_MODULES}块, {sys.kwp:0.0} kWp):</b>\n" +
                   $"直流 {sys.dcPowerW / 1000:0.00} kW → 交流上网 {sys.acPowerW / 1000:0.00} kW{clip}";
        }

        static void Derate(ref SingleDiodeModel.OpPoint op, double r)
        {
            op.pmp *= r; op.isc *= r; op.imp *= r; op.eff *= r;
            if (op.i != null)
                for (int k = 0; k < op.i.Length; k++) op.i[k] *= r;
        }

        static double Retention(int[] years, double[] ret, double y)
        {
            if (ret == null || years == null || ret.Length == 0) return 1.0;
            if (y <= 0) return 1.0;
            if (y <= years[0]) return 1.0 + (ret[0] - 1.0) * (y / years[0]);
            for (int k = 1; k < years.Length; k++)
                if (y <= years[k])
                {
                    double f = (y - years[k - 1]) / (double)(years[k] - years[k - 1]);
                    return ret[k - 1] + (ret[k] - ret[k - 1]) * f;
                }
            return ret[ret.Length - 1];
        }

        void UpdateBar(Transform bar, double pmp, double pstc)
        {
            if (!bar) return;
            float h = pstc > 0 ? Mathf.Clamp((float)(pmp / pstc), 0f, 1.3f) : 0f;
            var s = bar.localScale; s.y = 0.05f + 3f * h; bar.localScale = s;
            var p = bar.localPosition; p.y = s.y / 2f; bar.localPosition = p;
        }

        void TintByTemp(Renderer r, double tcell)
        {
            if (!r) return;
            float t = Mathf.InverseLerp(15f, 70f, (float)tcell);   // 冷蓝→热红
            r.material.color = Color.Lerp(new Color(0.3f, 0.5f, 0.9f), new Color(0.95f, 0.35f, 0.2f), t);
        }

        void DrawPlots(SingleDiodeModel.OpPoint c, SingleDiodeModel.OpPoint p)
        {
            Color32 bg = new Color32(250, 250, 252, 255);
            Color32 axis = new Color32(60, 60, 60, 255);
            Color32 grid = new Color32(220, 220, 220, 255);
            Color32 colC = new Color32(31, 111, 178, 255);     // 晶硅蓝
            Color32 colP = new Color32(226, 100, 30, 255);     // 钙钛矿橙

            double vmax = Mathf.Max((float)c.voc, (float)p.voc) * 1.05f + 1e-6f;
            double imax = Mathf.Max((float)c.isc, (float)p.isc) * 1.1f + 1e-6f;
            ivPlot.Clear(bg); ivPlot.Axes(vmax, imax, axis, grid);
            ivPlot.Curve(c.v, c.i, vmax, imax, colC);
            ivPlot.Curve(p.v, p.i, vmax, imax, colP);
            ivPlot.Marker(c.vmp, c.imp, vmax, imax, colC);
            ivPlot.Marker(p.vmp, p.imp, vmax, imax, colP);
            ivPlot.Apply();

            double pmax = Mathf.Max((float)c.pmp, (float)p.pmp) * 1.15f + 1e-6f;
            double[] pc = PowerCurve(c), pp = PowerCurve(p);
            pvPlot.Clear(bg); pvPlot.Axes(vmax, pmax, axis, grid);
            pvPlot.Curve(c.v, pc, vmax, pmax, colC);
            pvPlot.Curve(p.v, pp, vmax, pmax, colP);
            pvPlot.Marker(c.vmp, c.pmp, vmax, pmax, colC);
            pvPlot.Marker(p.vmp, p.pmp, vmax, pmax, colP);
            pvPlot.Apply();
        }

        static double[] PowerCurve(SingleDiodeModel.OpPoint op)
        {
            if (op.v == null) return null;
            var pw = new double[op.v.Length];
            for (int k = 0; k < pw.Length; k++) pw[k] = op.v[k] * op.i[k];
            return pw;
        }
    }
}
