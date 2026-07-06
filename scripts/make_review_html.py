"""把 PAPER_C 草稿渲染成带配图的自包含 HTML, 便于通读 / 打印成 PDF.

在每个"图 N / Figure N"图注块前内联嵌入对应主图 PNG (base64, 单文件自包含).
运行: python -m scripts.make_review_html
输出: docs/PAPER_C_review_en.html, docs/PAPER_C_review_zh.html
"""

import os
import re
import sys
import base64

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

FIGDIR = "outputs/figures"
FIGMAP = {
    "1": "NEWFig1_inversion.png",
    "1x": "MainFigV_fleet_validation.png",
    "2": "NEWFig2_mechanisms.png",
    "3": "NEWFig3_segmentation.png",
    "4": "NEWFig4_economics_timing.png",
    "5": "NEWFig5_deployment.png",
    "3x": "MainFig3x_temporal_fingerprint.png",
    "3y": "MainFig3y_tandem_decomposition.png",
    "4x": "MainFig4x_degradation_risk.png",
    "4y": "MainFig4y_substitution_timing_geo.png",
}

CSS = """
:root{--ink:#1a1a1a;--mut:#666;--line:#ddd;--accent:#b8360f;--codebg:#f4f4f4}
*{box-sizing:border-box}
body{font-family:-apple-system,'Segoe UI','Microsoft YaHei',Roboto,Helvetica,Arial,sans-serif;
 color:var(--ink);line-height:1.65;max-width:880px;margin:0 auto;padding:48px 28px 120px;
 font-size:16px;background:#fff}
h1{font-size:1.85em;line-height:1.25;margin:0 0 .2em;border-bottom:3px solid var(--accent);
 padding-bottom:.3em}
h2{font-size:1.32em;margin:1.9em 0 .5em;color:var(--accent);border-bottom:1px solid var(--line);
 padding-bottom:.2em}
h3{font-size:1.1em;margin:1.5em 0 .35em}
p{margin:.55em 0}
strong{color:#000}
code{background:var(--codebg);padding:.08em .35em;border-radius:3px;font-size:.88em;
 font-family:'SF Mono',Consolas,Monaco,monospace}
hr{border:none;border-top:1px solid var(--line);margin:2em 0}
ul{margin:.5em 0;padding-left:1.4em}
li{margin:.25em 0}
table{border-collapse:collapse;width:100%;margin:1em 0;font-size:.92em}
th,td{border:1px solid var(--line);padding:6px 9px;text-align:left}
th{background:#faf3f0}
figure{margin:1.6em 0;padding:14px;border:1px solid var(--line);border-radius:8px;
 background:#fafafa}
figure img{width:100%;height:auto;border-radius:4px;cursor:zoom-in;
 box-shadow:0 1px 5px rgba(0,0,0,.12)}
figcaption{font-size:.9em;color:#333;margin-top:10px;line-height:1.5}
.eyebrow{color:var(--mut);font-size:.9em}
.toc{background:#faf7f5;border:1px solid var(--line);border-radius:8px;padding:14px 20px;
 margin:1.5em 0;font-size:.93em}
.toc a{color:var(--accent);text-decoration:none}.toc a:hover{text-decoration:underline}
@media print{body{max-width:100%;padding:0;font-size:11pt}figure{break-inside:avoid}
 h2{break-after:avoid}a{color:inherit}}
"""

JS = """
document.querySelectorAll('figure img').forEach(function(im){
  im.addEventListener('click',function(){
    var w=window.open('');w.document.write('<img src="'+im.src+'" style="width:100%">');});
});
"""


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def inline(s):
    s = esc(s)
    s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
    s = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<em>\1</em>", s)
    s = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', s)
    return s


def img_tag(figid):
    fn = FIGMAP.get(figid)
    if not fn:
        return ""
    path = os.path.join(FIGDIR, fn)
    if not os.path.exists(path):
        return f'<p style="color:red">[missing {fn}]</p>'
    b64 = base64.b64encode(open(path, "rb").read()).decode()
    return f'<img src="data:image/png;base64,{b64}" alt="{fn}">'


def render(md, lang):
    fig_re = re.compile(r"^\*\*(?:Figure|图)\s*(\d+[xy]?)")
    blocks = re.split(r"\n\s*\n", md)
    html, slug_n = [], 0
    for blk in blocks:
        lines = [l for l in blk.split("\n") if l.strip() != ""]
        if not lines:
            continue
        first = lines[0].strip()
        # 跳过独立图片行, HTML 经 FIGMAP 自带 base64 嵌图
        if len(lines) == 1 and (
            re.match(r"^!\[.*\]\(.*\)$", first) or
            re.match(r'^<img\s+[^>]*src="[^"]+"[^>]*>\s*$', first)
        ):
            continue
        # heading
        if first.startswith("#"):
            lvl = len(first) - len(first.lstrip("#"))
            txt = first.lstrip("#").strip()
            slug_n += 1
            anchor = f"s{slug_n}"
            html.append(f'<h{lvl} id="{anchor}">{inline(txt)}</h{lvl}>')
            continue
        # hr
        if set(first) <= set("-") and len(first) >= 3 and len(lines) == 1:
            html.append("<hr>")
            continue
        # table
        if first.startswith("|"):
            rows = [r for r in lines if r.strip().startswith("|")]
            body = [r for r in rows if not re.match(r"^\s*\|[\s:|-]+\|\s*$", r)]
            html.append("<table>")
            for ri, r in enumerate(body):
                cells = [c.strip() for c in r.strip().strip("|").split("|")]
                tag = "th" if ri == 0 else "td"
                html.append("<tr>" + "".join(
                    f"<{tag}>{inline(c)}</{tag}>" for c in cells) + "</tr>")
            html.append("</table>")
            continue
        # list
        if all(re.match(r"^\s*[-*]\s+", l) for l in lines):
            html.append("<ul>")
            for l in lines:
                html.append("<li>" + inline(re.sub(r"^\s*[-*]\s+", "", l)) + "</li>")
            html.append("</ul>")
            continue
        # figure legend block -> embed image + caption
        m = fig_re.match(first)
        if m:
            html.append('<figure>')
            html.append(img_tag(m.group(1)))
            html.append('<figcaption>' + inline(" ".join(l.strip() for l in lines))
                        + '</figcaption>')
            html.append('</figure>')
            continue
        # paragraph
        html.append("<p>" + inline(" ".join(l.strip() for l in lines)) + "</p>")
    title = "PV transition review (EN)" if lang == "en" else "光伏转型评估 (中文)"
    return (f'<!doctype html><html lang="{lang}"><head><meta charset="utf-8">'
            f'<meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>{title}</title><style>{CSS}</style></head><body>'
            + "\n".join(html) + f'<script>{JS}</script></body></html>')


def main():
    jobs = [("docs/PAPER_C_draft.md", "docs/PAPER_C_review_en.html", "en"),
            ("docs/PAPER_C_draft_zh.md", "docs/PAPER_C_review_zh.html", "zh")]
    for src, out, lang in jobs:
        md = open(src, encoding="utf-8").read()
        html = render(md, lang)
        open(out, "w", encoding="utf-8").write(html)
        kb = os.path.getsize(out) / 1024
        print(f"{out}  ({kb:.0f} KB, {html.count('<figure>')} figures embedded)")


if __name__ == "__main__":
    main()
