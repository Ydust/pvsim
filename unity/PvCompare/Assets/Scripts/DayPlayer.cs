using System.Collections.Generic;
using UnityEngine;
using UnityEngine.UI;

namespace PvSim
{
    /// <summary>"播放一整天"：用 pvdata.json 的 sample_day(逐时辐照/气温/风速) 自动驱动仿真。
    /// 通过设置三个输入滑块的值来驱动 SimulationController(其 onValueChanged 会触发重算)。
    /// 播放时推进时间滑块；也可手动拖时间滑块逐帧查看。</summary>
    public class DayPlayer : MonoBehaviour
    {
        [Header("仿真主控 (用于推送太阳几何)")]
        public SimulationController sim;

        [Header("3D 太阳光 (随一天移动)")]
        public Transform sunTransform;

        [Header("被驱动的输入滑块 (与 SimulationController 同一组)")]
        public Slider irradianceSlider;
        public Slider tempSlider;
        public Slider windSlider;

        [Header("播放控制")]
        public Toggle playToggle;     // 勾选=播放
        public Slider timeSlider;     // 0..1 一天进度
        public Text timeLabel;        // 当前时刻
        public Dropdown cityDropdown; // 城市选择

        [Tooltip("播放完一整天所需的真实秒数")]
        public float secondsPerDay = 12f;

        double[] hour, poa, tair, wind, zen, aoi, azim;
        List<CityDay> cities;
        bool playing;

        void Start()
        {
            var data = PvDataLoader.Data;
            if (data == null) { enabled = false; return; }
            cities = data.cities;

            // 先连好控件
            if (timeSlider)
            {
                timeSlider.minValue = 0f; timeSlider.maxValue = 1f; timeSlider.value = 0f;
                timeSlider.onValueChanged.AddListener(OnScrub);
            }
            if (playToggle) playToggle.onValueChanged.AddListener(v => playing = v);

            // 多城: 填充下拉并默认第0城; 否则退回单一 sample_day
            if (cities != null && cities.Count > 0)
            {
                if (cityDropdown)
                {
                    cityDropdown.ClearOptions();
                    var opts = new List<string>();
                    foreach (var c in cities) opts.Add(c.name);
                    cityDropdown.AddOptions(opts);
                    cityDropdown.onValueChanged.AddListener(SetCity);
                }
                LoadDay(cities[0].day);
            }
            else
            {
                var d = data.sample_day;
                if (d == null || d.hour == null || d.hour.Length < 2)
                {
                    Debug.LogWarning("[DayPlayer] 无城市/样例日数据，播放功能禁用。");
                    enabled = false; return;
                }
                LoadDay(d);
            }
            if (timeLabel) timeLabel.text = "时刻 --:--  (▶ 播放一整天)";
        }

        void LoadDay(SampleDay d)
        {
            hour = d.hour; poa = d.poa; tair = d.temp_air; wind = d.wind_speed;
            zen = d.zenith; aoi = d.aoi; azim = d.azimuth;
        }

        public void SetCity(int i)
        {
            if (cities == null || i < 0 || i >= cities.Count) return;
            LoadDay(cities[i].day);
            if (timeSlider) timeSlider.SetValueWithoutNotify(0f);
            ApplyAt(0f);    // 立即按新城市起点刷新
        }

        void Update()
        {
            if (!playing || timeSlider == null) return;
            float v = timeSlider.value + Time.deltaTime / Mathf.Max(secondsPerDay, 0.1f);
            if (v >= 1f) v -= 1f;       // 循环
            timeSlider.value = v;       // 触发 OnScrub → ApplyAt
        }

        void OnScrub(float t) => ApplyAt(t);

        void ApplyAt(float t)
        {
            int n = hour.Length;
            double fk = Mathf.Clamp01(t) * (n - 1);
            int k = Mathf.Clamp((int)fk, 0, n - 2);
            double f = fk - k;
            double G = Lerp(poa, k, f);
            double Ta = Lerp(tair, k, f);
            double W = Lerp(wind, k, f);
            double Hr = Lerp(hour, k, f);

            // 先推送太阳几何 (光谱失配 + 入射角), 再设辐照触发重算
            double Z = (zen != null) ? Lerp(zen, k, f) : 48.0;
            if (sim != null)
            {
                sim.currentZenith = Z;
                if (aoi != null) sim.currentAoi = Lerp(aoi, k, f);
            }
            // 3D 太阳随天顶角/方位角移动 (高度角=90-天顶角)
            if (sunTransform != null && azim != null)
            {
                float elev = Mathf.Clamp((float)(90.0 - Z), 1f, 89f);
                sunTransform.rotation = Quaternion.Euler(elev, (float)Lerp(azim, k, f), 0f);
            }

            // 设置滑块值会触发 SimulationController.Recompute
            if (irradianceSlider) irradianceSlider.value = Mathf.Clamp((float)G,
                irradianceSlider.minValue, irradianceSlider.maxValue);
            if (tempSlider) tempSlider.value = Mathf.Clamp((float)Ta,
                tempSlider.minValue, tempSlider.maxValue);
            if (windSlider) windSlider.value = Mathf.Clamp((float)W,
                windSlider.minValue, windSlider.maxValue);

            if (timeLabel)
            {
                int hh = (int)Hr, mm = (int)((Hr - hh) * 60);
                timeLabel.text = $"时刻 {hh:00}:{mm:00}";
            }
        }

        static double Lerp(double[] a, int k, double f) => a[k] + (a[k + 1] - a[k]) * f;
    }
}
