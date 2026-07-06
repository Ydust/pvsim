using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.UI;
using UnityEngine.EventSystems;
using System.IO;

namespace PvSim
{
    /// <summary>一键构建仿真场景：3D 设备 + 滑块 + I-V/P-V 图 + 读数面板，并自动接线。
    /// 菜单: PvSim ▸ 构建仿真场景。</summary>
    public static class SceneBuilder
    {
        [MenuItem("PvSim/构建仿真场景")]
        public static void Build()
        {
            var scene = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);

            // --- 相机 ---
            var camGO = new GameObject("Main Camera");
            var cam = camGO.AddComponent<Camera>();
            camGO.tag = "MainCamera";
            cam.clearFlags = CameraClearFlags.SolidColor;
            cam.backgroundColor = new Color(0.12f, 0.14f, 0.18f);
            camGO.transform.position = new Vector3(0, 2.2f, -6f);
            camGO.transform.rotation = Quaternion.Euler(12, 0, 0);

            // --- 太阳光 ---
            var lightGO = new GameObject("Sun");
            var light = lightGO.AddComponent<Light>();
            light.type = LightType.Directional;
            light.intensity = 1.1f;
            lightGO.transform.rotation = Quaternion.Euler(50, -30, 0);

            // --- 地面 ---
            var ground = GameObject.CreatePrimitive(PrimitiveType.Plane);
            ground.name = "Ground";
            ground.transform.localScale = new Vector3(3, 1, 3);
            ground.GetComponent<Renderer>().sharedMaterial.color = new Color(0.2f, 0.22f, 0.25f);

            // --- 两台设备 + 出力条 ---
            var csiPanel = MakePanel("晶硅设备", new Vector3(-2.2f, 0.6f, 0), new Color(0.3f, 0.5f, 0.9f));
            var peroPanel = MakePanel("钙钛矿设备", new Vector3(2.2f, 0.6f, 0), new Color(0.95f, 0.45f, 0.25f));
            var csiBar = MakeBar(new Vector3(-3.4f, 0, 0.8f), new Color(0.31f, 0.43f, 0.7f));
            var peroBar = MakeBar(new Vector3(3.4f, 0, 0.8f), new Color(0.89f, 0.39f, 0.12f));

            // --- UI Canvas ---
            var canvasGO = new GameObject("Canvas", typeof(Canvas), typeof(CanvasScaler), typeof(GraphicRaycaster));
            var canvas = canvasGO.GetComponent<Canvas>();
            canvas.renderMode = RenderMode.ScreenSpaceOverlay;
            var scaler = canvasGO.GetComponent<CanvasScaler>();
            scaler.uiScaleMode = CanvasScaler.ScaleMode.ScaleWithScreenSize;
            scaler.referenceResolution = new Vector2(1280, 720);

            if (Object.FindObjectOfType<EventSystem>() == null)
                new GameObject("EventSystem", typeof(EventSystem), typeof(StandaloneInputModule));

            var t = canvasGO.transform;
            MakeText(t, "标题", "晶硅 vs 钙钛矿 光伏运行仿真 (拖滑块实时计算 / ▶ 播放一整天)",
                     new Vector2(0, -8), new Vector2(1000, 32), 20, TextAnchor.UpperCenter, new Vector2(0.5f, 1));

            // 输入滑块区 (左上)
            var sIrr = MakeSlider(t, "辐照", new Vector2(20, -44));
            var sTemp = MakeSlider(t, "气温", new Vector2(20, -88));
            var sWind = MakeSlider(t, "风速", new Vector2(20, -132));

            // 播放一整天控制 (左, 滑块下方)
            var playTog = MakeToggle(t, "播放开关", "▶ 播放一整天", new Vector2(20, -180));
            var timeLbl = MakeText(t, "时刻标签", "时刻 --:--", new Vector2(200, -180),
                                   new Vector2(220, 24), 16, TextAnchor.UpperLeft, new Vector2(0, 1));
            var sTime = MakeSlider(t, "进度", new Vector2(20, -206));
            sTime.label.text = "一天进度";

            // 运行年数 (衰减可视化)
            var sYears = MakeSlider(t, "运行年数", new Vector2(20, -250));

            // 城市选择下拉 (顶部中段)
            MakeText(t, "城市标签", "城市 (真实气象)", new Vector2(440, -154),
                     new Vector2(200, 22), 15, TextAnchor.UpperLeft, new Vector2(0, 1));
            var cityDrop = MakeDropdown(t, "城市下拉", new Vector2(440, -178), new Vector2(180, 30));

            // 曲线图 (中下, 两图并排)
            var ivImg = MakeRawImage(t, "IVImage", new Vector2(20, -298), new Vector2(400, 232));
            var pvImg = MakeRawImage(t, "PVImage", new Vector2(440, -298), new Vector2(400, 232));

            // 读数面板 (右侧)
            var csiTxt = MakeText(t, "晶硅读数", "", new Vector2(-20, -44), new Vector2(330, 250),
                                  18, TextAnchor.UpperLeft, new Vector2(1, 1));
            var peroTxt = MakeText(t, "钙钛矿读数", "", new Vector2(-20, -310), new Vector2(330, 250),
                                   18, TextAnchor.UpperLeft, new Vector2(1, 1));

            // --- 主控并接线 ---
            var simGO = new GameObject("Simulation");
            var sim = simGO.AddComponent<SimulationController>();
            sim.irradianceSlider = sIrr.slider; sim.irradianceLabel = sIrr.label;
            sim.tempSlider = sTemp.slider; sim.tempLabel = sTemp.label;
            sim.windSlider = sWind.slider; sim.windLabel = sWind.label;
            sim.yearsSlider = sYears.slider; sim.yearsLabel = sYears.label;
            sim.ivImage = ivImg; sim.pvImage = pvImg;
            sim.csiReadout = csiTxt; sim.peroReadout = peroTxt;
            sim.csiBar = csiBar; sim.peroBar = peroBar;
            sim.csiPanel = csiPanel.GetComponent<Renderer>();
            sim.peroPanel = peroPanel.GetComponent<Renderer>();

            // --- 播放一整天 并接线 ---
            var dayGO = new GameObject("DayPlayer");
            var day = dayGO.AddComponent<DayPlayer>();
            day.sim = sim;
            day.irradianceSlider = sIrr.slider;
            day.tempSlider = sTemp.slider;
            day.windSlider = sWind.slider;
            day.playToggle = playTog;
            day.timeSlider = sTime.slider;
            day.timeLabel = timeLbl;
            day.cityDropdown = cityDrop;
            day.sunTransform = lightGO.transform;

            Directory.CreateDirectory("Assets/Scenes");
            EditorSceneManager.SaveScene(scene, "Assets/Scenes/PvCompare.unity");
            Debug.Log("[PvSim] 场景已构建并保存到 Assets/Scenes/PvCompare.unity");
            if (!Application.isBatchMode)
                EditorUtility.DisplayDialog("PvSim", "场景已构建并保存到 Assets/Scenes/PvCompare.unity\n点击 ▶ 运行即可。", "好");
        }

        static GameObject MakePanel(string name, Vector3 pos, Color color)
        {
            var go = GameObject.CreatePrimitive(PrimitiveType.Cube);
            go.name = name;
            go.transform.position = pos;
            go.transform.localScale = new Vector3(2.0f, 0.08f, 1.3f);
            go.transform.rotation = Quaternion.Euler(-25, 0, 0);
            var mat = new Material(Shader.Find("Standard")) { color = color };
            go.GetComponent<Renderer>().sharedMaterial = mat;
            return go;
        }

        static Transform MakeBar(Vector3 basePos, Color color)
        {
            var go = GameObject.CreatePrimitive(PrimitiveType.Cube);
            go.name = "PowerBar";
            go.transform.localScale = new Vector3(0.4f, 1f, 0.4f);
            go.transform.position = basePos + new Vector3(0, 0.5f, 0);
            var mat = new Material(Shader.Find("Standard")) { color = color };
            go.GetComponent<Renderer>().sharedMaterial = mat;
            return go.transform;
        }

        // ---- UI 辅助 ----
        static DefaultControls.Resources _res;
        static DefaultControls.Resources Res()
        {
            if (_res.standard == null)
            {
                _res.standard = Sprite("UI/Skin/UISprite.psd");
                _res.background = Sprite("UI/Skin/Background.psd");
                _res.knob = Sprite("UI/Skin/Knob.psd");
                _res.checkmark = Sprite("UI/Skin/Checkmark.psd");
                _res.dropdown = Sprite("UI/Skin/DropdownArrow.psd");
                _res.mask = Sprite("UI/Skin/UIMask.psd");
                _res.inputField = Sprite("UI/Skin/InputFieldBackground.psd");
            }
            return _res;
        }
        static Sprite Sprite(string p) => AssetDatabase.GetBuiltinExtraResource<Sprite>(p);

        static Text MakeText(Transform parent, string name, string txt, Vector2 anchoredPos,
                             Vector2 size, int fontSize, TextAnchor align, Vector2 anchor)
        {
            var go = new GameObject(name, typeof(RectTransform), typeof(CanvasRenderer), typeof(Text));
            go.transform.SetParent(parent, false);
            var rt = go.GetComponent<RectTransform>();
            rt.anchorMin = rt.anchorMax = anchor;
            rt.pivot = anchor;
            rt.sizeDelta = size;
            rt.anchoredPosition = anchoredPos;
            var t = go.GetComponent<Text>();
            t.text = txt; t.fontSize = fontSize; t.alignment = align;
            t.color = Color.white; t.supportRichText = true;
            t.horizontalOverflow = HorizontalWrapMode.Overflow;
            t.verticalOverflow = VerticalWrapMode.Overflow;
            return t;
        }

        struct SliderRef { public Slider slider; public Text label; }

        static SliderRef MakeSlider(Transform parent, string name, Vector2 pos)
        {
            var label = MakeText(parent, name + "标签", name, pos, new Vector2(360, 24),
                                 16, TextAnchor.UpperLeft, new Vector2(0, 1));
            var go = DefaultControls.CreateSlider(Res());
            go.name = name + "Slider";
            go.transform.SetParent(parent, false);
            var rt = go.GetComponent<RectTransform>();
            rt.anchorMin = rt.anchorMax = rt.pivot = new Vector2(0, 1);
            rt.sizeDelta = new Vector2(360, 20);
            rt.anchoredPosition = pos + new Vector2(0, -24);
            return new SliderRef { slider = go.GetComponent<Slider>(), label = label };
        }

        static Toggle MakeToggle(Transform parent, string name, string label, Vector2 pos)
        {
            var go = DefaultControls.CreateToggle(Res());
            go.name = name;
            go.transform.SetParent(parent, false);
            var rt = go.GetComponent<RectTransform>();
            rt.anchorMin = rt.anchorMax = rt.pivot = new Vector2(0, 1);
            rt.sizeDelta = new Vector2(170, 22);
            rt.anchoredPosition = pos;
            var lbl = go.GetComponentInChildren<Text>();
            if (lbl)
            {
                lbl.text = label; lbl.fontSize = 16; lbl.color = Color.white;
                lbl.horizontalOverflow = HorizontalWrapMode.Overflow;
            }
            return go.GetComponent<Toggle>();
        }

        static Dropdown MakeDropdown(Transform parent, string name, Vector2 pos, Vector2 size)
        {
            var go = DefaultControls.CreateDropdown(Res());
            go.name = name;
            go.transform.SetParent(parent, false);
            var rt = go.GetComponent<RectTransform>();
            rt.anchorMin = rt.anchorMax = rt.pivot = new Vector2(0, 1);
            rt.sizeDelta = size;
            rt.anchoredPosition = pos;
            return go.GetComponent<Dropdown>();
        }

        static RawImage MakeRawImage(Transform parent, string name, Vector2 pos, Vector2 size)
        {
            var go = new GameObject(name, typeof(RectTransform), typeof(CanvasRenderer), typeof(RawImage));
            go.transform.SetParent(parent, false);
            var rt = go.GetComponent<RectTransform>();
            rt.anchorMin = rt.anchorMax = rt.pivot = new Vector2(0, 1);
            rt.sizeDelta = size;
            rt.anchoredPosition = pos;
            return go.GetComponent<RawImage>();
        }
    }
}
