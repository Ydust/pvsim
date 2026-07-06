"""把 Unity 渲染的 3D 帧 (outputs/anim_frames/<key>/) 叠中文标注合成 GIF。

读取每城 frame_###.png + meta.csv, 用 PIL + 微软雅黑叠加: 城市/时刻/辐照/温度/两者功率/领先%,
并标出蓝=晶硅、橙=钙钛矿。输出 outputs/animations/unity_<key>.gif (+ _peak.png)。
运行: python -m scripts.assemble_city_anim
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
OUTDIR = "outputs/animations"
PICK = ["harbin", "shanghai", "haikou"]
FONT = "C:/Windows/Fonts/msyh.ttc"   # 微软雅黑


def font(sz):
    try:
        return ImageFont.truetype(FONT, sz)
    except Exception:
        return ImageFont.load_default()


def annotate(img, city, note, row):
    img = img.convert("RGBA")
    W, Hh = img.size
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)
    # 顶部半透明条
    d.rectangle([0, 0, W, 66], fill=(10, 14, 22, 180))
    f1, f2, f3 = font(22), font(20), font(16)
    cfC = row["cfC"] * 100; cfP = row["cfP"] * 100; lead = cfP - cfC
    win = "钙钛矿" if lead >= 0 else "晶硅"
    wincol = (255, 200, 110, 255) if lead >= 0 else (120, 190, 250, 255)
    hh = int(row["hour"]); mm = int(round((row["hour"] - hh) * 60))
    d.text((12, 6), f"{city} ({note})  清晰冬日·3D   {hh:02d}:{mm:02d}   "
                    f"辐照 {row['poa']:.0f} W/m²   电池温度 {row['tcell']:.0f}°C",
           font=f2, fill=(255, 255, 255, 255))
    d.text((12, 36), f"产能比(相对各自额定)  晶硅 {cfC:.0f}%   钙钛矿 {cfP:.0f}%   "
                     f"→ {win}高 {abs(lead):.0f}pp", font=f1, fill=wincol)
    # 底部 图例
    d.text((40, Hh - 28), "● 晶硅(蓝柱)", font=f3, fill=(80, 150, 220, 255))
    d.text((W - 170, Hh - 28), "钙钛矿(橙柱) ●", font=f3, fill=(235, 150, 70, 255))
    # 领先方"√领先"徽标 (晶硅赢→左侧蓝, 钙钛矿赢→右侧橙)
    fBadge = font(30)
    bx = int((0.10 if win == "晶硅" else 0.90) * W); by = int(0.24 * Hh); r = 26
    d.ellipse([bx - r, by - r, bx + r, by + r], fill=wincol, outline=(255, 255, 255, 255), width=3)
    d.text((bx, by - 1), "√", font=fBadge, fill=(255, 255, 255, 255), anchor="mm")
    d.text((bx, by + r + 13), "领先", font=f3, fill=wincol, anchor="mm")
    out = Image.alpha_composite(img, overlay).convert("RGB")
    return out


def build(key, city):
    fdir = os.path.join(FRAMES_ROOT, key)
    metap = os.path.join(fdir, "meta.csv")
    files = sorted(glob.glob(os.path.join(fdir, "frame_*.png")))
    if not files or not os.path.exists(metap):
        print(f"  跳过 {key}: 无帧/meta"); return None
    meta = pd.read_csv(metap)
    frames = []
    peak_i, peak_v = 0, -1
    for i, fp in enumerate(files):
        row = meta.iloc[min(i, len(meta) - 1)]
        frames.append(annotate(Image.open(fp), city.name, city.note, row))
        if row["pmpC"] + row["pmpP"] > peak_v:
            peak_v = row["pmpC"] + row["pmpP"]; peak_i = i
    os.makedirs(OUTDIR, exist_ok=True)
    gif = os.path.join(OUTDIR, f"unity_{key}.gif")
    frames[0].save(gif, save_all=True, append_images=frames[1:],
                   duration=110, loop=0, optimize=True)
    frames[peak_i].save(os.path.join(OUTDIR, f"unity_{key}_peak.png"))
    print(f"  {gif}  ({len(frames)}帧, 峰值帧#{peak_i})")
    return gif


def main():
    by_key = {c.key: c for c in CITIES}
    for key in PICK:
        build(key, by_key[key])
    print("完成。")


if __name__ == "__main__":
    main()
