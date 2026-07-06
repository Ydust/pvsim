"""把三城 Unity 3D 帧拼成"同一白天进度"的并排对比动画 (GIF)。

左→右按 冷→温→热 排 (哈尔滨/上海/海口), 同一帧=同一白天进度, 各列标本地时刻/温度/功率/领先%。
直观看: 越往右(越热), 钙钛矿(橙)领先晶硅(蓝)越多。播放速度放慢。
运行: python -m scripts.combine_city_anim
输出: outputs/animations/cities_compare.gif (+ _peak.png)
"""

import os
import sys
import glob

import pandas as pd
from PIL import Image, ImageDraw, ImageFont

from pvsim.cities import CITIES

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

FRAMES_ROOT = "outputs/anim_frames"
OUT = "outputs/animations/cities_compare.gif"
ORDER = ["harbin", "shanghai", "haikou"]   # 冷→温→热
FONT = "C:/Windows/Fonts/msyh.ttc"
CW, PAD, HEADER, CAPTION = 460, 12, 54, 90   # CAPTION 加高, 避免第三行被裁
DURATION_MS = 190                          # 放慢播放


def font(sz, bold=False):
    try:
        return ImageFont.truetype("C:/Windows/Fonts/msyhbd.ttc" if bold else FONT, sz)
    except Exception:
        return ImageFont.load_default()


def load_city(key):
    fdir = os.path.join(FRAMES_ROOT, key)
    files = sorted(glob.glob(os.path.join(fdir, "frame_*.png")))
    meta = pd.read_csv(os.path.join(fdir, "meta.csv"))
    return files, meta


def main():
    by_key = {c.key: c for c in CITIES}
    cities = [(k, by_key[k], *load_city(k)) for k in ORDER]
    nframes = min(len(files) for _, _, files, _ in cities)
    sample = Image.open(cities[0][2][0])
    ch = round(CW * sample.height / sample.width)
    canvas_w = len(cities) * CW + (len(cities) + 1) * PAD
    canvas_h = HEADER + ch + CAPTION

    fH, fName, fL, fG = font(22, True), font(20, True), font(17), font(19, True)
    fBadge = font(28, True)

    def compose(k):
        img = Image.new("RGB", (canvas_w, canvas_h), (18, 22, 28))
        d = ImageDraw.Draw(img)
        pct = k / (nframes - 1) * 100
        title = f"清晰冬日·同一白天进度 {pct:.0f}%  —  冷城晶硅反超，热城钙钛矿领先"
        d.text((canvas_w // 2, 8), title, font=fH, fill=(255, 240, 180), anchor="ma")

        for ci, (key, city, files, meta) in enumerate(cities):
            x0 = PAD + ci * (CW + PAD)
            frame = Image.open(files[min(k, len(files) - 1)]).resize((CW, ch))
            img.paste(frame, (x0, HEADER))
            row = meta.iloc[min(k, len(meta) - 1)]
            cfC = row["cfC"] * 100; cfP = row["cfP"] * 100      # 产能比(相对各自额定)
            lead = cfP - cfC
            win = "钙钛矿" if lead >= 0 else "晶硅"
            wincol = (255, 180, 90) if lead >= 0 else (110, 180, 245)
            hh = int(row["hour"]); mm = int(round((row["hour"] - hh) * 60))
            cy = HEADER + ch + 4
            d.text((x0 + CW // 2, cy), f"{city.name}  {city.note}",
                   font=fName, fill=(235, 235, 235), anchor="ma")
            d.text((x0 + CW // 2, cy + 26),
                   f"本地{hh:02d}:{mm:02d}  电池温度{row['tcell']:.0f}°C",
                   font=fL, fill=(180, 195, 210), anchor="ma")
            d.text((x0 + CW // 2, cy + 46),
                   f"产能比 晶硅{cfC:.0f}% / 钙钛矿{cfP:.0f}%  → {win}高{abs(lead):.0f}pp",
                   font=fG, fill=wincol, anchor="ma")
            # 领先方"√领先"徽标: 晶硅赢→左侧蓝, 钙钛矿赢→右侧橙 (跳侧=翻转)
            bx = x0 + int((0.12 if win == "晶硅" else 0.88) * CW)
            by = HEADER + int(0.20 * ch)
            r = 22
            d.ellipse([bx - r, by - r, bx + r, by + r], fill=wincol, outline=(255, 255, 255), width=3)
            d.text((bx, by - 1), "√", font=fBadge, fill=(255, 255, 255), anchor="mm")
            d.text((bx, by + r + 12), "领先", font=fG, fill=wincol, anchor="mm")
        return img, pct

    frames, gaps = [], []
    for k in range(nframes):
        im, _ = compose(k)
        frames.append(im)
        # 记录该帧三城平均领先, 用于选峰值预览
        g = 0
        for _, _, _, meta in cities:
            r = meta.iloc[min(k, len(meta) - 1)]
            g += (r["pmpP"] - r["pmpC"]) / r["pmpC"] * 100 if r["pmpC"] > 1 else 0
        gaps.append(g)

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    frames[0].save(OUT, save_all=True, append_images=frames[1:],
                   duration=DURATION_MS, loop=0, optimize=True)
    peak = max(range(nframes), key=lambda i: gaps[i])
    frames[peak].save(OUT.replace(".gif", "_peak.png"))
    print(f"已生成 {OUT}  ({nframes}帧, {DURATION_MS}ms/帧, 峰值帧#{peak})")


if __name__ == "__main__":
    main()
