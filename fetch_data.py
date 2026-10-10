# -*- coding: utf-8 -*-
"""抓取陈版主(chenyiwei)会计视野论坛答疑，蒸馏成结构化 JSON。
数据源: bbs.auditdog.cn 公开 API (匿名, 30 req/min)。
"""
import json, time, urllib.parse, urllib.request, sys, os

BASE = "https://bbs.auditdog.cn"
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "data", "chenyiwei_qa.json")

# 核心财务/会计专题关键词（扩充版，覆盖细分专题）
KEYWORDS = [
    # 收入准则
    "收入确认", "总额法", "净额法", "可变对价", "合同资产", "合同负债",
    "履约义务", "时段法", "时点法", "合同变更", "重大融资成分",
    "非现金对价", "应付客户对价", "售后回购", "销售退回", "质保",
    "销售返利", "委托代销", "委托加工", "分期收款",
    # 合并与长投
    "合并报表", "长期股权投资", "同一控制", "非同一控制", "商誉",
    "商誉减值", "权益法", "成本法", "联营企业", "合营企业",
    "少数股东", "控制权", "反向购买", "或有对价", "一揽子交易",
    "分步交易", "结构化主体",
    # 金融工具
    "金融工具", "预期信用损失", "金融资产转移", "公允价值", "套期会计",
    "永续债", "可转债", "优先股", "认股权证", "明股实债", "资产证券化",
    # 租赁与股份支付
    "租赁", "使用权资产", "转租赁", "租赁变更", "售后租回",
    "股份支付", "限制性股票", "股票期权", "员工持股计划", "现金结算股份支付",
    # 企业合并与特殊业务
    "企业合并", "PPP", "BOT", "借款费用", "投资性房地产",
    # 资产与负债
    "资产减值", "固定资产", "存货", "研发费用", "无形资产",
    "长期待摊费用", "或有事项", "预计负债", "债务重组",
    "非货币性资产交换", "政府补助", "权益性交易", "关联方",
    # 所得税与报表
    "递延所得税", "所得税费用", "现金流量表", "外币折算",
    "每股收益", "分部报告", "会计政策变更", "会计估计变更", "前期差错",
    "资产负债表日后事项", "非经常性损益", "追溯调整",
    # 职工薪酬与其他
    "职工薪酬", "辞退福利", "设定受益计划", "增值税", "进项税额",
    "视同销售", "留抵退税", "安全生产费", "生物资产",
]

def http_get(url, retries=3):
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < retries - 1:
                time.sleep(15)  # 限流，等待后重试
                continue
            raise
        except Exception:
            if attempt < retries - 1:
                time.sleep(5)
                continue
            raise

def search(q):
    u = BASE + "/api/public/search?q=" + urllib.parse.quote(q)
    return http_get(u)

def detail(link):
    u = BASE + "/api/public/detail?link=" + urllib.parse.quote(link, safe="")
    return http_get(u)

def main():
    links = {}
    # 第一阶段：搜索，收集候选
    print("=== 阶段1: 关键词搜索 ===", flush=True)
    for i, kw in enumerate(KEYWORDS):
        try:
            d = search(kw)
            for r in d.get("results", []):
                l = r.get("link")
                if l and l not in links:
                    links[l] = {
                        "title": r.get("title", ""),
                        "tags": r.get("tags", []),
                        "preview": r.get("preview", ""),
                        "match_type": r.get("match_type", ""),
                        "reply_count": r.get("reply_count", 0),
                    }
            print(f"  [{i+1}/{len(KEYWORDS)}] {kw}: +{len(d.get('results',[]))} (累计 {len(links)})", flush=True)
        except Exception as e:
            print(f"  [{i+1}/{len(KEYWORDS)}] {kw}: ERROR {e}", flush=True)
        time.sleep(2.2)  # 限流 30/min

    print(f"\n共收集候选 {len(links)} 条，开始拉取详情...", flush=True)

    # 第二阶段：拉取完整问答
    qa_list = []
    failed = []
    for idx, (link, meta) in enumerate(links.items()):
        try:
            d = detail(link)
            posts = d.get("posts", [])
            # 提取陈版主的回复
            qa_pairs = []
            for p in posts:
                qt = p.get("question_text", "").strip()
                ct = p.get("comment_text", "").strip()
                if ct:  # 有回复才算有效
                    qa_pairs.append({
                        "q_author": p.get("question_author", ""),
                        "q_time": p.get("question_time", ""),
                        "question": qt,
                        "comment": ct,
                        "a_author": p.get("author", "陈版主"),
                        "a_time": p.get("comment_time", ""),
                    })
            if qa_pairs:
                qa_list.append({
                    "id": idx,
                    "title": meta["title"],
                    "link": link,
                    "tags": meta["tags"],
                    "reply_count": meta["reply_count"],
                    "qa_pairs": qa_pairs,
                })
            else:
                failed.append(link)
            if (idx + 1) % 20 == 0:
                print(f"  详情 {idx+1}/{len(links)} 完成，有效 {len(qa_list)}", flush=True)
        except Exception as e:
            failed.append(link)
            print(f"  detail ERROR {link}: {e}", flush=True)
        time.sleep(2.0)

    result = {
        "source": "中国会计视野论坛 陈奕蔚(chenyiwei)版主答疑",
        "source_api": BASE,
        "generated": time.strftime("%Y-%m-%d %H:%M:%S"),
        "total": len(qa_list),
        "failed": len(failed),
        "items": qa_list,
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=1)
    print(f"\n=== 完成 === 有效 {len(qa_list)} 条，失败 {len(failed)} 条")
    print(f"输出: {OUT}")

if __name__ == "__main__":
    main()
