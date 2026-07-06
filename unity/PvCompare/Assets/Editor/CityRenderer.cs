using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Text;
using UnityEditor;
using UnityEngine;
using UnityEngine.Rendering;

namespace PvSim
{
    /// <summary>批处理逐帧渲染精致 3D 光伏电站：程序化天空盒(组件反射天空)+草地+多排纵深阵列+
    /// 玻璃质感反光组件(晶硅蓝栅格/钙钛矿红褐薄膜)+倾斜支架+逆变器+MSAA抗锯齿+受热泛红+发光出力柱。
    /// 物理与运行时一致, 逐城逐帧渲 PNG + meta.csv。批处理: -executeMethod PvSim.CityRenderer.Render</summary>
    public static class CityRenderer
    {
        const int W = 880, H = 495, FRAMES = 30;
        static readonly Dictionary<string, string> PICK = new Dictionary<string, string>
        {
            { "哈尔滨", "harbin" }, { "上海", "shanghai" }, { "海口", "haikou" },
        };

        static Material Std(Color c, float metallic = 0f, float smooth = 0.3f)
        {
            var m = new Material(Shader.Find("Standard")) { color = c };
            m.SetFloat("_Metallic", metallic); m.SetFloat("_Glossiness", smooth);
            return m;
        }

        static Texture2D CrystallineTex()
        {
            int tw = 384, th = 256, cols = 6, rows = 4;
            var t = new Texture2D(tw, th) { filterMode = FilterMode.Point, wrapMode = TextureWrapMode.Clamp };
            Color cell = new Color(0.05f, 0.09f, 0.30f), cell2 = new Color(0.08f, 0.13f, 0.38f);
            Color gap = new Color(0.02f, 0.03f, 0.08f), bus = new Color(0.80f, 0.82f, 0.88f);
            int cw = tw / cols, ch = th / rows, gp = 3;
            var px = new Color[tw * th];
            for (int y = 0; y < th; y++)
                for (int x = 0; x < tw; x++)
                {
                    int cx = x % cw, cy = y % ch; Color c;
                    if (cx < gp || cy < gp) c = gap;
                    else { c = ((x / cw + y / ch) % 2 == 0) ? cell : cell2;
                           if (cx == cw / 3 || cx == 2 * cw / 3) c = bus;
                           if (cy % 9 == 0) c = Color.Lerp(c, bus, 0.5f); }
                    px[y * tw + x] = c;
                }
            t.SetPixels(px); t.Apply(); return t;
        }

        static Texture2D PerovskiteTex()
        {
            int tw = 384, th = 256;
            var t = new Texture2D(tw, th) { filterMode = FilterMode.Bilinear, wrapMode = TextureWrapMode.Clamp };
            Color baseC = new Color(0.32f, 0.15f, 0.12f), scribe = new Color(0.15f, 0.07f, 0.06f);
            var px = new Color[tw * th];
            for (int y = 0; y < th; y++)
                for (int x = 0; x < tw; x++)
                {
                    float g = 0.85f + 0.15f * Mathf.Sin(x * 0.05f);
                    Color c = baseC * g; if (x % 7 == 0) c = scribe;
                    px[y * tw + x] = c;
                }
            t.SetPixels(px); t.Apply(); return t;
        }

        static Texture2D GrassTex()
        {
            int s = 256; var t = new Texture2D(s, s) { wrapMode = TextureWrapMode.Repeat };
            Random.InitState(7);
            Color dark = new Color(0.16f, 0.26f, 0.11f), light = new Color(0.30f, 0.42f, 0.18f);
            var px = new Color[s * s];
            for (int y = 0; y < s; y++)
                for (int x = 0; x < s; x++)
                {
                    float n = Mathf.PerlinNoise(x * 0.05f, y * 0.05f);
                    Color c = Color.Lerp(dark, light, n) + (Random.value - 0.5f) * 0.05f * Color.white;
                    px[y * s + x] = c;
                }
            t.SetPixels(px); t.Apply(); return t;
        }

        static Transform BuildArray(Vector3 pos, Material surf, Material frameMat, Material legMat,
                                    float scale, bool extras, Color gaugeColor, float gaugeX)
        {
            float tilt = -28f;
            var parent = new GameObject("array").transform;
            parent.position = pos; parent.rotation = Quaternion.Euler(tilt, 0, 0);
            parent.localScale = Vector3.one * scale;

            int cols = 3, rows = 2; float mw = 0.52f, md = 0.34f, gx = 0.04f, gz = 0.04f;
            for (int r = 0; r < rows; r++)
                for (int c = 0; c < cols; c++)
                {
                    float lx = (c - (cols - 1) / 2f) * (mw + gx), lz = (r - (rows - 1) / 2f) * (md + gz);
                    var fr = GameObject.CreatePrimitive(PrimitiveType.Cube);
                    fr.transform.SetParent(parent, false);
                    fr.transform.localPosition = new Vector3(lx, -0.005f, lz);
                    fr.transform.localScale = new Vector3(mw + 0.04f, 0.02f, md + 0.04f);
                    fr.GetComponent<Renderer>().sharedMaterial = frameMat;
                    var mod = GameObject.CreatePrimitive(PrimitiveType.Cube);
                    mod.transform.SetParent(parent, false);
                    mod.transform.localPosition = new Vector3(lx, 0.006f, lz);
                    mod.transform.localScale = new Vector3(mw, 0.02f, md);
                    mod.GetComponent<Renderer>().sharedMaterial = surf;
                }

            float aw = cols * (mw + gx) * scale;
            foreach (float sx in new[] { -aw / 2 + 0.2f, aw / 2 - 0.2f })
            {
                MakePost(new Vector3(pos.x + sx, 0, pos.z + 0.35f * scale), pos.y + 0.22f, legMat);
                MakePost(new Vector3(pos.x + sx, 0, pos.z - 0.35f * scale), pos.y - 0.28f, legMat);
            }
            var beam = GameObject.CreatePrimitive(PrimitiveType.Cylinder);
            beam.transform.position = pos + new Vector3(0, -0.05f, 0);
            beam.transform.rotation = Quaternion.Euler(0, 0, 90);
            beam.transform.localScale = new Vector3(0.05f, aw / 2, 0.05f);
            beam.GetComponent<Renderer>().sharedMaterial = legMat;

            Transform gauge = null;
            if (extras)
            {
                var inv = GameObject.CreatePrimitive(PrimitiveType.Cube);
                inv.transform.position = new Vector3(pos.x + (gaugeX > 0 ? 1.1f : -1.1f), 0.3f, pos.z - 0.95f);
                inv.transform.localScale = new Vector3(0.28f, 0.6f, 0.2f);
                inv.GetComponent<Renderer>().sharedMaterial = Std(new Color(0.82f, 0.84f, 0.87f), 0.5f, 0.6f);

                gauge = GameObject.CreatePrimitive(PrimitiveType.Cube).transform;
                var gm = Std(gaugeColor); gm.EnableKeyword("_EMISSION"); gm.SetColor("_EmissionColor", gaugeColor * 0.9f);
                gauge.GetComponent<Renderer>().sharedMaterial = gm;
                var bs = GameObject.CreatePrimitive(PrimitiveType.Cube);
                bs.transform.position = new Vector3(gaugeX, 0.04f, pos.z + 0.5f);
                bs.transform.localScale = new Vector3(0.5f, 0.08f, 0.5f);
                bs.GetComponent<Renderer>().sharedMaterial = legMat;
            }
            return gauge;
        }

        static void MakePost(Vector3 basePos, float h, Material m)
        {
            h = Mathf.Max(h, 0.2f);
            var p = GameObject.CreatePrimitive(PrimitiveType.Cylinder);
            p.transform.position = basePos + new Vector3(0, h / 2, 0);
            p.transform.localScale = new Vector3(0.06f, h / 2, 0.06f);
            p.GetComponent<Renderer>().sharedMaterial = m;
        }

        [MenuItem("PvSim/渲染城市动画帧")]
        public static void Render()
        {
            var data = PvDataLoader.Data;
            if (data == null || data.cities == null) { Debug.LogError("数据缺失"); return; }
            var csi = data.technologies["c-Si"]; var pero = data.technologies["perovskite"];
            int nsC = csi.cells_in_series, nsP = pero.cells_in_series;
            double pstcC = csi.stc.pmp, pstcP = pero.stc.pmp;
            double[] zt = data.spectral_sf.zenith;
            double[] sfCt = data.spectral_sf.sf["c-Si"], sfPt = data.spectral_sf.sf["perovskite"];

            // 相机
            var cam = new GameObject("CapCam").AddComponent<Camera>();
            cam.fieldOfView = 40; cam.allowMSAA = true;
            cam.transform.position = new Vector3(0, 4.6f, -9.2f);
            cam.transform.LookAt(new Vector3(0, 0.7f, 1.6f));

            // 太阳
            var sun = new GameObject("Sun").AddComponent<Light>();
            sun.type = LightType.Directional; sun.intensity = 1.05f; sun.shadows = LightShadows.Soft;

            // 程序化天空盒 (太阳跟随平行光; 组件反射天空)
            var sky = new Material(Shader.Find("Skybox/Procedural"));
            sky.SetFloat("_SunSize", 0.045f); sky.SetFloat("_AtmosphereThickness", 1.1f);
            sky.SetColor("_SkyTint", new Color(0.45f, 0.58f, 0.80f));
            sky.SetColor("_GroundColor", new Color(0.32f, 0.33f, 0.30f));
            RenderSettings.skybox = sky; RenderSettings.sun = sun;
            RenderSettings.ambientMode = AmbientMode.Skybox;
            RenderSettings.defaultReflectionMode = DefaultReflectionMode.Skybox;
            cam.clearFlags = CameraClearFlags.Skybox;
            DynamicGI.UpdateEnvironment();

            // 草地
            var ground = GameObject.CreatePrimitive(PrimitiveType.Plane);
            ground.transform.localScale = new Vector3(8, 1, 8);
            var gmat = Std(Color.white, 0, 0.05f); gmat.mainTexture = GrassTex();
            gmat.mainTextureScale = new Vector2(20, 20);
            ground.GetComponent<Renderer>().sharedMaterial = gmat;

            // 两技术共享表面材质 (玻璃质感反光 + 受热发光)
            var surfC = Std(Color.white, 0.05f, 0.78f); surfC.mainTexture = CrystallineTex(); surfC.EnableKeyword("_EMISSION");
            var surfP = Std(Color.white, 0.05f, 0.72f); surfP.mainTexture = PerovskiteTex(); surfP.EnableKeyword("_EMISSION");
            var frameMat = Std(new Color(0.66f, 0.68f, 0.72f), 0.7f, 0.7f);
            var legMat = Std(new Color(0.34f, 0.35f, 0.39f), 0.7f, 0.4f);

            // 纵深多排 (前排带出力柱/逆变器, 后排只摆阵列)
            var gC = BuildArray(new Vector3(-1.7f, 0.85f, 0f), surfC, frameMat, legMat, 1.0f, true, new Color(0.12f, 0.45f, 0.78f), -4.0f);
            var gP = BuildArray(new Vector3(1.7f, 0.85f, 0f), surfP, frameMat, legMat, 1.0f, true, new Color(0.92f, 0.45f, 0.12f), 4.0f);
            for (int row = 1; row <= 2; row++)
            {
                float z = row * 1.8f; float sc = 1.0f - row * 0.05f;
                BuildArray(new Vector3(-1.7f, 0.85f, z), surfC, frameMat, legMat, sc, false, default, 0);
                BuildArray(new Vector3(1.7f, 0.85f, z), surfP, frameMat, legMat, sc, false, default, 0);
            }

            // 出力柱材质引用(用于高亮领先方)
            var gmC = gC ? gC.GetComponent<Renderer>().sharedMaterial : null;
            var gmP = gP ? gP.GetComponent<Renderer>().sharedMaterial : null;
            Color baseGC = new Color(0.12f, 0.45f, 0.78f), baseGP = new Color(0.92f, 0.45f, 0.12f);

            var rt = new RenderTexture(W, H, 24) { antiAliasing = 8 };
            cam.targetTexture = rt;
            var tex = new Texture2D(W, H, TextureFormat.RGB24, false);
            string outRoot = Path.GetFullPath(Path.Combine(Application.dataPath, "../../../outputs/anim_frames"));

            foreach (var city in data.cities)
            {
                if (!PICK.ContainsKey(city.name)) continue;
                string key = PICK[city.name];
                var day = city.winter_day != null ? city.winter_day : city.day;  // 冬日: 城市差异最明显
                int n = day.hour.Length;
                string dir = Path.Combine(outRoot, key); Directory.CreateDirectory(dir);
                var meta = new StringBuilder("frame,hour,poa,tcell,pmpC,pmpP,cfC,cfP\n");

                for (int k = 0; k < FRAMES; k++)
                {
                    double fk = (double)k / (FRAMES - 1) * (n - 1);
                    int i = Mathf.Clamp((int)fk, 0, n - 2); double f = fk - i;
                    double G = Lerp(day.poa, i, f), Tair = Lerp(day.temp_air, i, f);
                    double Wd = Lerp(day.wind_speed, i, f), Z = Lerp(day.zenith, i, f);
                    double Az = Lerp(day.azimuth, i, f), A = Lerp(day.aoi, i, f), Hr = Lerp(day.hour, i, f);

                    double tcell = SingleDiodeModel.CellTemperature(G, Tair, Wd);
                    double sfC = SingleDiodeModel.SpectralFactor(zt, sfCt, Z);
                    double sfP = SingleDiodeModel.SpectralFactor(zt, sfPt, Z);
                    double iam = SingleDiodeModel.MartinRuizIAM(A);
                    var opC = SingleDiodeModel.Operate(csi, G, tcell, G * sfC * iam, nsC, 100);
                    var opP = SingleDiodeModel.Operate(pero, G, tcell, G * sfP * iam, nsP, 100);

                    float heat = Mathf.SmoothStep(0, 1, Mathf.InverseLerp(32f, 58f, (float)tcell));
                    float cold = Mathf.SmoothStep(0, 1, Mathf.InverseLerp(28f, 2f, (float)tcell));
                    Color glow = new Color(1f, 0.18f, 0.06f) * (heat * 0.40f);
                    Color tint = Color.Lerp(Color.white, new Color(0.70f, 0.85f, 1.08f), cold * 0.5f);  // 凉→冰蓝
                    surfC.color = tint; surfP.color = tint;
                    surfC.SetColor("_EmissionColor", glow); surfP.SetColor("_EmissionColor", glow);
                    SetGauge(gC, -4.0f, opC.pmp / pstcC); SetGauge(gP, 4.0f, opP.pmp / pstcP);
                    // 高亮领先方: 赢家柱大幅提亮, 输家变暗
                    bool peroWins = (opP.pmp / pstcP) >= (opC.pmp / pstcC);
                    if (gmC != null) gmC.SetColor("_EmissionColor", baseGC * (peroWins ? 0.45f : 2.8f));
                    if (gmP != null) gmP.SetColor("_EmissionColor", baseGP * (peroWins ? 2.8f : 0.45f));

                    float elev = Mathf.Clamp((float)(90 - Z), 2f, 89f) * Mathf.Deg2Rad;
                    float az = (float)Az * Mathf.Deg2Rad;
                    var d3 = new Vector3(Mathf.Sin(az) * Mathf.Cos(elev), Mathf.Sin(elev), Mathf.Cos(az) * Mathf.Cos(elev));
                    sun.transform.rotation = Quaternion.LookRotation(-d3);
                    sun.intensity = Mathf.Lerp(0.55f, 1.15f, Mathf.Sin(elev));

                    cam.Render();
                    RenderTexture.active = rt;
                    tex.ReadPixels(new Rect(0, 0, W, H), 0, 0); tex.Apply();
                    RenderTexture.active = null;
                    File.WriteAllBytes(Path.Combine(dir, $"frame_{k:000}.png"), tex.EncodeToPNG());
                    meta.AppendFormat(CultureInfo.InvariantCulture,
                        "{0},{1:F2},{2:F0},{3:F1},{4:F1},{5:F1},{6:F3},{7:F3}\n",
                        k, Hr, G, tcell, opC.pmp, opP.pmp, opC.pmp / pstcC, opP.pmp / pstcP);
                }
                File.WriteAllText(Path.Combine(dir, "meta.csv"), meta.ToString());
                Debug.Log($"[城市渲染] {city.name} -> {dir} ({FRAMES}帧)");
            }
            cam.targetTexture = null;
            Debug.Log("[城市渲染] 完成");
        }

        static void SetGauge(Transform g, float x, double ratio)
        {
            if (g == null) return;
            float h = Mathf.Clamp((float)ratio, 0f, 1.3f) * 2.6f + 0.05f;
            g.localScale = new Vector3(0.34f, h, 0.34f);
            g.position = new Vector3(x, 0.08f + h / 2f, 0.5f);
        }

        static double Lerp(double[] a, int i, double f) => a[i] + (a[i + 1] - a[i]) * f;
    }
}
