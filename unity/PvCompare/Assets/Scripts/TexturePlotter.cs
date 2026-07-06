using System.Collections.Generic;
using UnityEngine;

namespace PvSim
{
    /// <summary>把曲线绘制到 Texture2D，用于在 UI(RawImage) 中显示 I-V / P-V 图。</summary>
    public class TexturePlotter
    {
        readonly int W, H;
        readonly Color32[] buf;
        readonly Texture2D tex;
        const int PADL = 46, PADR = 12, PADT = 14, PADB = 30;

        public TexturePlotter(int w = 460, int h = 300)
        {
            W = w; H = h;
            tex = new Texture2D(W, H, TextureFormat.RGBA32, false);
            buf = new Color32[W * H];
        }

        public Texture2D Texture => tex;

        public void Clear(Color32 bg)
        {
            for (int i = 0; i < buf.Length; i++) buf[i] = bg;
        }

        void SetPx(int x, int y, Color32 c)
        {
            if (x < 0 || x >= W || y < 0 || y >= H) return;
            buf[y * W + x] = c;
        }

        void Line(int x0, int y0, int x1, int y1, Color32 c, int thick = 1)
        {
            int dx = Mathf.Abs(x1 - x0), dy = -Mathf.Abs(y1 - y0);
            int sx = x0 < x1 ? 1 : -1, sy = y0 < y1 ? 1 : -1;
            int err = dx + dy;
            while (true)
            {
                for (int ox = -thick + 1; ox < thick; ox++)
                    for (int oy = -thick + 1; oy < thick; oy++)
                        SetPx(x0 + ox, y0 + oy, c);
                if (x0 == x1 && y0 == y1) break;
                int e2 = 2 * err;
                if (e2 >= dy) { err += dy; x0 += sx; }
                if (e2 <= dx) { err += dx; y0 += sy; }
            }
        }

        int PX(double x, double xmax) => PADL + (int)((W - PADL - PADR) * Mathf.Clamp01((float)(x / xmax)));
        int PY(double y, double ymax) => (H - PADB) - (int)((H - PADT - PADB) * Mathf.Clamp01((float)(y / ymax)));

        public void Axes(double xmax, double ymax, Color32 axis, Color32 grid)
        {
            // 网格
            for (int g = 1; g < 5; g++)
            {
                int gx = PADL + (W - PADL - PADR) * g / 5;
                Line(gx, PADT, gx, H - PADB, grid);
                int gy = (H - PADB) - (H - PADT - PADB) * g / 5;
                Line(PADL, gy, W - PADR, gy, grid);
            }
            // 坐标轴
            Line(PADL, PADT, PADL, H - PADB, axis, 1);
            Line(PADL, H - PADB, W - PADR, H - PADB, axis, 1);
        }

        public void Curve(double[] xs, double[] ys, double xmax, double ymax, Color32 c, int thick = 2)
        {
            if (xs == null || ys == null) return;
            for (int k = 1; k < xs.Length; k++)
                Line(PX(xs[k - 1], xmax), PY(ys[k - 1], ymax),
                     PX(xs[k], xmax), PY(ys[k], ymax), c, thick);
        }

        public void Marker(double x, double y, double xmax, double ymax, Color32 c, int r = 4)
        {
            int cx = PX(x, xmax), cy = PY(y, ymax);
            for (int ox = -r; ox <= r; ox++)
                for (int oy = -r; oy <= r; oy++)
                    if (ox * ox + oy * oy <= r * r) SetPx(cx + ox, cy + oy, c);
        }

        public void Apply()
        {
            tex.SetPixels32(buf);
            tex.Apply(false);
        }
    }
}
