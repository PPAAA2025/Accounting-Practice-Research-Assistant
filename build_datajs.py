# -*- coding: utf-8 -*-
"""把 chenyiwei_qa.json 转成 data.js（window.CHENYIWEI_DATA），供 index.html 内嵌加载。"""
import json, os

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "data", "chenyiwei_qa.json")
DST = os.path.join(HERE, "data.js")

with open(SRC, "r", encoding="utf-8") as f:
    data = json.load(f)

items = data.get("items", [])
print(f"转换 {len(items)} 条答疑 -> data.js")

with open(DST, "w", encoding="utf-8") as f:
    f.write("window.CHENYIWEI_DATA = ")
    json.dump(items, f, ensure_ascii=False)
    f.write(";\n")

print(f"完成: {DST} ({os.path.getsize(DST)/1024:.0f} KB)")
