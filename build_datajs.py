# -*- coding: utf-8 -*-
"""生成会计实务检索助手使用的本地 JavaScript 数据文件。"""
import json, os

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "data", "chenyiwei_qa.json")
DST = os.path.join(HERE, "data.js")
REFS_SRC = os.path.join(HERE, "data", "jixue_cuyao_refs.json")
REFS_DST = os.path.join(HERE, "jixue_refs.js")
INDEX = os.path.join(HERE, "index.html")

with open(SRC, "r", encoding="utf-8") as f:
    data = json.load(f)

items = data.get("items", [])
print(f"转换 {len(items)} 条答疑 -> data.js")

with open(DST, "w", encoding="utf-8") as f:
    f.write("window.CHENYIWEI_DATA = ")
    json.dump(items, f, ensure_ascii=False)
    f.write(";\n")

print(f"完成: {DST} ({os.path.getsize(DST)/1024:.0f} KB)")

if os.path.exists(REFS_SRC):
    with open(REFS_SRC, "r", encoding="utf-8") as f:
        refs = json.load(f).get("items", [])
    with open(REFS_DST, "w", encoding="utf-8") as f:
        f.write("window.JIXUE_CUYAO_REFS = ")
        json.dump(refs, f, ensure_ascii=False)
        f.write(";\n")
    print(f"转换 {len(refs)} 条《计学撮要》引用索引 -> jixue_refs.js")

# Keep the page usable via file:// by loading generated local script files.
with open(INDEX, "r", encoding="utf-8") as f:
    html = f.read()
start = html.find("<script>window.CHENYIWEI_DATA = ")
if start >= 0:
    end = html.find("</script>", start)
    if end < 0:
        raise RuntimeError("Cannot find closing data script tag")
    html = html[:start] + '<script src="data.js"></script>\n<script src="jixue_refs.js"></script>' + html[end + len("</script>"):]
    with open(INDEX, "w", encoding="utf-8") as f:
        f.write(html)
