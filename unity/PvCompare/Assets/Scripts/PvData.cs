using System.Collections.Generic;

namespace PvSim
{
    // 与 pvdata.json 对应的数据结构 (用 Newtonsoft Json.NET 反序列化)。

    public class StcValues
    {
        public double isc, voc, pmp, ff, eff;
    }

    public class TechParams
    {
        public string name;
        public string name_cn;
        public string color;
        public double area_cm2;
        public int cells_in_series;

        // 单二极管参考参数 (实时计算)
        public double I_L_ref, I_o_ref, R_s, R_sh_ref, n_ideality;
        public double alpha_sc, EgRef, Ea_recomb, noct;

        // 光谱响应形状
        public double lambda_min, lambda_gap, eqe_peak, edge_width, blue_rolloff;

        // 其他
        public double bifaciality, lifetime_years, capex_per_wp, hysteresis_index;

        public StcValues stc;
    }

    public class SpectralTable
    {
        public double[] zenith;
        public Dictionary<string, double[]> sf;
    }

    public class PerovskiteScenario
    {
        public double[] retention;
        public double t80;
    }

    public class DegradationData
    {
        public int[] years;

        [Newtonsoft.Json.JsonProperty("c-Si")]
        public double[] cSi;

        public Dictionary<string, PerovskiteScenario> perovskite;
    }

    public class TandemData
    {
        public double[] bandgap;
        public double[] efficiency;
        public double best_eg, best_eff, tandem_eff;
        public double single_csi_eff, single_pero_eff;
        public double current_mismatch, voc;
    }

    public class SampleDay
    {
        public string location;
        public double[] hour;
        public double[] poa;
        public double[] temp_air;
        public double[] zenith;
        public double[] azimuth;
        public double[] aoi;
        public double[] wind_speed;
    }

    public class CityDay
    {
        public string name;
        public string note;
        public SampleDay day;
        public SampleDay winter_day;
    }

    public class PvData
    {
        public Dictionary<string, object> meta;
        public Dictionary<string, TechParams> technologies;
        public SpectralTable spectral_sf;
        public DegradationData degradation;
        public TandemData tandem;
        public SampleDay sample_day;
        public List<CityDay> cities;
    }
}
