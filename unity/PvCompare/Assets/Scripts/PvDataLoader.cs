using System.IO;
using UnityEngine;
using Newtonsoft.Json;

namespace PvSim
{
    /// <summary>从 StreamingAssets/pvdata.json 载入由 pvsim 模型导出的数据。</summary>
    public static class PvDataLoader
    {
        static PvData _data;

        public static PvData Data
        {
            get { if (_data == null) Load(); return _data; }
        }

        public static void Load()
        {
            string path = Path.Combine(Application.streamingAssetsPath, "pvdata.json");
            if (!File.Exists(path))
            {
                Debug.LogError($"找不到数据文件: {path}\n请先运行 python -m scripts.export_unity_data 生成。");
                _data = null;
                return;
            }
            string json = File.ReadAllText(path);
            _data = JsonConvert.DeserializeObject<PvData>(json);
        }
    }
}
