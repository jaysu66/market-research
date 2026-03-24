"""步骤6-9/11：验证管线 — 过滤+提取+口径标注+缺口检查"""

import json
import os
import time
from pathlib import Path

from config import US_STATES, PRODUCTS, INDUSTRY_BENCHMARKS
from model_client import call_task

CACHE_DIR = Path(__file__).parent / "cache"


EXTRACT_PROMPT = """You are a data extraction specialist. Extract structured data from the following search result text.

Search category: {category}
Search query: {query}

Text:
{text}

Extract all relevant data points and return a JSON object. Include:
- prices (with low/high/unit/scope like "labor only" or "materials+labor")
- business names and ratings
- statistics and percentages
- trends and preferences
- rent/cost data

For each data point, preserve the original source if mentioned.
Return ONLY valid JSON, no explanation. If no relevant data found, return {{"no_data": true}}.
"""

GAP_CHECK_PROMPT = """You are a data completeness checker for a market research report about {product} retail stores in {state}.

The report needs data for these categories:
1. Demographics (population, income, housing) - from Census API
2. Economy (GDP, unemployment, building permits) - from FRED API
3. Local businesses (store names, count, locations)
4. Installation pricing (cost per window/sqft)
5. Commercial rent (retail rent per sqft)
6. Consumer trends and preferences
7. Supply chain / manufacturers
8. Promotions and sales strategies
9. Competition landscape (brands, market share)

Here is the current data pool:
{data_pool}

Check which categories have sufficient data and which are missing or weak.
For missing/weak categories, suggest 1-2 specific search queries to fill the gap.

Return JSON:
{{
  "covered": ["category1", "category2", ...],
  "gaps": [
    {{"category": "...", "reason": "...", "suggested_query": "..."}}
  ]
}}
"""


def run_pipeline(state_code: str, product: str = "curtains") -> dict:
    """运行完整验证管线"""
    state_name = US_STATES[state_code]["name"]
    cache_dir = CACHE_DIR / f"{state_code}_{product}"

    # 加载API数据
    api_path = cache_dir / "api_data.json"
    api_data = {}
    if api_path.exists():
        with open(api_path, "r", encoding="utf-8") as f:
            api_data = json.load(f)

    # 加载搜索结果
    search_path = cache_dir / "search_raw.json"
    search_data = {}
    if search_path.exists():
        with open(search_path, "r", encoding="utf-8") as f:
            search_data = json.load(f)

    # 步骤6: 可信度过滤（已在searcher.py中完成trust_filtered标注）
    print(f"[Step 6] Trust filtering...")
    searches = search_data.get("searches", [])
    valid_searches = [s for s in searches if "error" not in s]
    print(f"  {len(valid_searches)}/{len(searches)} valid searches")

    # 步骤7: 智能提取
    print(f"[Step 7] Extracting structured data...")
    extracted = []
    for s in valid_searches:
        try:
            result = extract_data(s["category"], s["query"], s["response"])
            extracted.append({
                "category": s["category"],
                "data": result,
            })
        except Exception as e:
            print(f"  Warning: extraction failed for {s['category']}: {e}")
            extracted.append({
                "category": s["category"],
                "data": {"extraction_error": str(e)},
            })

    # 步骤8: 合并数据池
    print(f"[Step 8] Merging data pool...")
    data_pool = {
        "state": state_code,
        "state_name": state_name,
        "product": product,
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "demographics": api_data.get("demographics", {}),
        "economy": api_data.get("economy", {}),
        "wages": api_data.get("wages", {}),
        "local_businesses": api_data.get("local_businesses", {}),
        "search_extracted": {
            "pricing": [],
            "rent": [],
            "trends": [],
            "supply": [],
            "promotion": [],
            "competition": [],
            "businesses": [],
        },
        "industry_benchmarks": INDUSTRY_BENCHMARKS.get(product, {}),
        "data_gaps": [],
    }

    # 按类别归类提取数据
    for item in extracted:
        cat = item["category"]
        if cat in data_pool["search_extracted"]:
            data_pool["search_extracted"][cat].append(item["data"])

    # 步骤9: 缺口检查
    print(f"[Step 9] Checking data gaps...")
    gaps = check_gaps(state_name, product, data_pool)
    data_pool["data_gaps"] = gaps.get("gaps", [])
    data_pool["data_coverage"] = gaps.get("covered", [])

    # 保存数据池
    pool_path = cache_dir / "data_pool.json"
    with open(pool_path, "w", encoding="utf-8") as f:
        json.dump(data_pool, f, ensure_ascii=False, indent=2)

    print(f"  [OK] Data pool saved: {pool_path}")
    print(f"  Covered: {len(data_pool['data_coverage'])} categories")
    print(f"  Gaps: {len(data_pool['data_gaps'])} categories")

    return data_pool


def extract_data(category: str, query: str, text: str) -> dict:
    """步骤7: 用低级任务模型从搜索结果提取结构化数据"""
    prompt = EXTRACT_PROMPT.format(category=category, query=query, text=text[:3000])

    resp = call_task("low",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
        max_tokens=2048,
    )

    content = resp["content"].strip()
    # 尝试从markdown代码块中提取JSON
    if "```json" in content:
        content = content.split("```json")[1].split("```")[0].strip()
    elif "```" in content:
        content = content.split("```")[1].split("```")[0].strip()

    try:
        return json.loads(content)
    except json.JSONDecodeError:
        return {"raw_extraction": content}


def check_gaps(state_name: str, product: str, data_pool: dict) -> dict:
    """步骤9: 检查数据缺口"""
    # 简化数据池摘要（避免超长输入）
    summary = {
        "demographics": {
            "has_state_level": bool(data_pool.get("demographics", {}).get("state_level")),
            "city_count": len(data_pool.get("demographics", {}).get("cities", [])),
        },
        "economy": {
            k: bool(v.get("value")) if isinstance(v, dict) else False
            for k, v in data_pool.get("economy", {}).items()
            if isinstance(v, dict)
        },
        "wages": {
            k: bool(v.get("value")) if isinstance(v, dict) else False
            for k, v in data_pool.get("wages", {}).items()
            if isinstance(v, dict)
        },
        "businesses_by_city": {
            city: len(biz) for city, biz in data_pool.get("local_businesses", {}).items()
        },
        "search_extracted": {
            cat: len(items) for cat, items in data_pool.get("search_extracted", {}).items()
        },
    }

    prompt = GAP_CHECK_PROMPT.format(
        product=PRODUCTS.get(product, {}).get("display_name", product),
        state=state_name,
        data_pool=json.dumps(summary, ensure_ascii=False, indent=2),
    )

    resp = call_task("low",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
        max_tokens=1024,
    )

    content = resp["content"].strip()
    if "```json" in content:
        content = content.split("```json")[1].split("```")[0].strip()
    elif "```" in content:
        content = content.split("```")[1].split("```")[0].strip()

    try:
        return json.loads(content)
    except json.JSONDecodeError:
        return {"covered": [], "gaps": [{"category": "unknown", "reason": "gap check failed"}]}


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python pipeline.py TX [curtains]")
        sys.exit(1)

    state = sys.argv[1].upper()
    product = sys.argv[2] if len(sys.argv) > 2 else "curtains"

    if state not in US_STATES:
        print(f"[ERROR] Unknown state: {state}")
        sys.exit(1)

    run_pipeline(state, product)
