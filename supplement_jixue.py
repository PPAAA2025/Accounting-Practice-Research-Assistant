# -*- coding: utf-8 -*-
"""补录引用《计学撮要》的陈版主答疑，并保留可复跑的进度。"""
import json
import os
import sys
import time
import urllib.parse
import urllib.request
import urllib.error

BASE = "https://bbs.auditdog.cn"
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "data", "chenyiwei_qa.json")
REFS_OUT = os.path.join(HERE, "data", "jixue_cuyao_refs.json")
PAGE_SIZE = 20
REQUEST_INTERVAL = 2.1


def http_get(url, retries=6):
    last_error = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=45) as response:
                return json.loads(response.read().decode("utf-8"))
        except Exception as exc:
            last_error = exc
            delay = 15 if isinstance(exc, urllib.error.HTTPError) and exc.code == 429 else min(2 ** attempt, 20)
            if attempt + 1 < retries:
                print(f"  请求失败，{delay}s 后重试: {exc}", flush=True)
                time.sleep(delay)
    raise last_error


def load_data():
    with open(OUT, "r", encoding="utf-8") as source:
        return json.load(source)


def save_data(data):
    data["total"] = len(data.get("items", []))
    data["generated"] = time.strftime("%Y-%m-%d %H:%M:%S")
    tmp = OUT + ".tmp"
    with open(tmp, "w", encoding="utf-8") as target:
        json.dump(data, target, ensure_ascii=False, indent=1)
    os.replace(tmp, OUT)


def collect_candidates():
    results = {}
    page = 1
    while True:
        url = f"{BASE}/api/public/ref-posts?slug=jixue-cuoyao&page={page}"
        payload = http_get(url)
        for row in payload.get("results", []):
            link = row.get("link")
            if link:
                results[link] = row
        print(f"  引用清单第 {page} 页: {len(payload.get('results', []))} 条，累计 {len(results)}", flush=True)
        if not payload.get("hasMore"):
            return results, payload.get("count", len(results))
        page += 1
        time.sleep(REQUEST_INTERVAL)


def save_reference_index(candidates, expected_count, by_link):
    refs = []
    for link, meta in candidates.items():
        item = by_link.get(link)
        refs.append({
            "title": meta.get("title", ""),
            "link": link,
            "latest_time": meta.get("latest_time", ""),
            "reply_count": meta.get("reply_count", 0),
            "has_full_answer": bool(item and item.get("qa_pairs")),
            "tags": item.get("tags", []) if item else [],
        })
    with open(REFS_OUT, "w", encoding="utf-8") as target:
        json.dump({
            "source": f"{BASE}/api/public/ref-posts?slug=jixue-cuoyao",
            "source_name": "《计学撮要》引用反查",
            "source_count": expected_count,
            "candidate_count": len(refs),
            "generated": time.strftime("%Y-%m-%d %H:%M:%S"),
            "items": refs,
        }, target, ensure_ascii=False, indent=1)


def parse_detail(payload, meta):
    pairs = []
    for post in payload.get("posts", []):
        question = post.get("question_text", "").strip()
        comment = post.get("comment_text", "").strip()
        author = post.get("author", "")
        if comment and author.casefold() in ("chenyiwei", "陈奕蔚", "陈版主"):
            pairs.append({
                "q_author": post.get("question_author", ""),
                "q_time": post.get("question_time", ""),
                "question": question,
                "comment": comment,
                "a_author": author,
                "a_time": post.get("comment_time", ""),
            })
    if not pairs:
        return None
    return {
        "title": meta.get("title", ""),
        "link": meta["link"],
        "tags": ["《计学撮要》引用"],
        "reply_count": meta.get("reply_count", 0),
        "qa_pairs": pairs,
    }


def main():
    data = load_data()
    items = data.get("items", [])
    by_link = {item["link"]: item for item in items if item.get("link")}
    candidates, expected_count = collect_candidates()
    for link in candidates.keys() & by_link.keys():
        tags = by_link[link].setdefault("tags", [])
        if "《计学撮要》引用" not in tags:
            tags.append("《计学撮要》引用")
    save_reference_index(candidates, expected_count, by_link)
    missing = [(link, meta) for link, meta in candidates.items() if link not in by_link]
    print(f"引用清单 {expected_count} 帖；已有 {len(candidates) - len(missing)} 帖；待补 {len(missing)} 帖", flush=True)

    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    if limit <= 0:
        print("仅刷新引用索引。传入正整数可补抓指定条数的完整问答。", flush=True)
        data["items"] = items
        data["jixue_cuyao_coverage"] = {
            "source": f"{BASE}/api/public/ref-posts?slug=jixue-cuoyao",
            "source_name": "《计学撮要》引用反查",
            "source_count": expected_count,
            "candidate_count": len(candidates),
            "added_count": 0,
            "failed_count": 0,
            "last_run": time.strftime("%Y-%m-%d %H:%M:%S"),
        }
        save_data(data)
        return
    else:
        missing = missing[:limit]

    added = 0
    failed = []
    for index, (link, meta) in enumerate(missing, 1):
        try:
            endpoint = BASE + "/api/public/detail?link=" + urllib.parse.quote(link, safe="")
            record = parse_detail(http_get(endpoint), meta)
            if record:
                record["id"] = len(items)
                items.append(record)
                by_link[link] = record
                added += 1
            else:
                failed.append({"link": link, "reason": "未返回陈版主答复"})
        except Exception as exc:
            failed.append({"link": link, "reason": str(exc)})

        if index % 20 == 0 or index == len(missing):
            data["items"] = items
            data["jixue_cuyao_coverage"] = {
                "source": f"{BASE}/api/public/ref-posts?slug=jixue-cuoyao",
                "source_name": "《计学撮要》引用反查",
                "source_count": expected_count,
                "candidate_count": len(candidates),
                "added_count": added,
                "failed_count": len(failed),
                "last_run": time.strftime("%Y-%m-%d %H:%M:%S"),
            }
            data["supplement_failures"] = failed
            save_data(data)
            save_reference_index(candidates, expected_count, by_link)
            print(f"  详情 {index}/{len(missing)}；新增 {added}；失败 {len(failed)}；总计 {len(items)}", flush=True)
        time.sleep(REQUEST_INTERVAL)

    data["items"] = items
    data["jixue_cuyao_coverage"] = {
        "source": f"{BASE}/api/public/ref-posts?slug=jixue-cuoyao",
        "source_name": "《计学撮要》引用反查",
        "source_count": expected_count,
        "candidate_count": len(candidates),
        "added_count": added,
        "failed_count": len(failed),
        "last_run": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    data["supplement_failures"] = failed
    save_data(data)
    save_reference_index(candidates, expected_count, by_link)
    print(f"完成：来源候选 {len(candidates)}，本次新增 {added}，失败 {len(failed)}，库内总计 {len(items)}", flush=True)


if __name__ == "__main__":
    main()
