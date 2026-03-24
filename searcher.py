"""步骤5/10：Sonar搜索 — 定向搜索+通用搜索"""

import json
import os
import time
import re
from pathlib import Path

from config import US_STATES, PRODUCTS, TRUSTED_SOURCES, BLOCKED_PATTERNS
from model_client import call_sonar

CACHE_DIR = Path(__file__).parent / "cache"


def build_queries(state_code: str, product: str = "curtains") -> list[dict]:
    """根据配置生成搜索query列表"""
    state_info = US_STATES[state_code]
    state_name = state_info["name"]
    cities = state_info["cities"]
    product_cfg = PRODUCTS[product]

    city = cities[0] if cities else state_name
    city2 = cities[1] if len(cities) > 1 else city

    queries = []
    for category, templates in product_cfg["search_queries"].items():
        for tmpl in templates:
            q = tmpl.format(
                city=city,
                city2=city2,
                state=state_name,
                en_name=product_cfg["en_name"],
                angi_term=product_cfg["angi_term"],
            )
            queries.append({"category": category, "query": q})

    # 补充：商家列表搜索（替代Yelp/Foursquare）
    for c in cities[:2]:
        queries.append({
            "category": "businesses",
            "query": f'"{product_cfg["en_name"]}" stores in {c}, {state_name} reviews ratings',
        })

    return queries


def search_all(state_code: str, product: str = "curtains") -> dict:
    """执行所有搜索query"""
    queries = build_queries(state_code, product)
    state_name = US_STATES[state_code]["name"]

    results = {"state": state_code, "product": product, "searches": []}

    print(f"Searching {state_name} ({product}): {len(queries)} queries")

    for i, q in enumerate(queries):
        print(f"  [{i+1}/{len(queries)}] {q['category']}: {q['query'][:60]}...")
        try:
            resp = call_sonar(q["query"])
            result = {
                "category": q["category"],
                "query": q["query"],
                "response": resp["content"],
                "usage": resp.get("usage", {}),
                "trust_filtered": filter_by_trust(resp["content"]),
            }
            results["searches"].append(result)
        except Exception as e:
            results["searches"].append({
                "category": q["category"],
                "query": q["query"],
                "error": str(e),
            })
        time.sleep(0.5)  # 避免限流

    # 保存原始搜索结果
    output_dir = CACHE_DIR / f"{state_code}_{product}"
    output_dir.mkdir(exist_ok=True)
    output_path = output_dir / "search_raw.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    ok = sum(1 for s in results["searches"] if "error" not in s)
    print(f"  [OK] {ok}/{len(queries)} searches succeeded -> {output_path}")
    return results


def filter_by_trust(text: str) -> dict:
    """对搜索结果做可信度标注"""
    # 提取URL
    urls = re.findall(r'https?://[^\s\)]+', text)

    trusted = []
    blocked = []
    medium = []

    all_trusted = []
    for tier_sources in TRUSTED_SOURCES.values():
        all_trusted.extend(tier_sources)

    for url in urls:
        domain = re.sub(r'^https?://(www\.)?', '', url).split('/')[0]

        is_blocked = any(re.match(p, domain) for p in BLOCKED_PATTERNS)
        if is_blocked:
            blocked.append(url)
            continue

        is_trusted = any(domain.endswith(t) for t in all_trusted)
        if is_trusted:
            trusted.append(url)
        else:
            medium.append(url)

    return {
        "trusted": trusted,
        "blocked": blocked,
        "medium": medium,
    }


def search_supplement(state_code: str, product: str, gap_queries: list[str]) -> list[dict]:
    """步骤10：补搜"""
    results = []
    for q in gap_queries:
        print(f"  [supplement] {q[:60]}...")
        try:
            resp = call_sonar(q)
            results.append({
                "query": q,
                "response": resp["content"],
                "usage": resp.get("usage", {}),
            })
        except Exception as e:
            results.append({"query": q, "error": str(e)})
        time.sleep(0.5)
    return results


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python searcher.py TX [curtains]")
        sys.exit(1)

    state = sys.argv[1].upper()
    product = sys.argv[2] if len(sys.argv) > 2 else "curtains"

    if state not in US_STATES:
        print(f"[ERROR] Unknown state: {state}")
        sys.exit(1)

    if not os.environ.get("OPENROUTER_API_KEY"):
        print("[ERROR] Set OPENROUTER_API_KEY")
        sys.exit(1)

    search_all(state, product)
