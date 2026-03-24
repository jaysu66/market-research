"""步骤12-15/19：报告生成 + 自查 + 质疑"""

import json
import os
import time
from pathlib import Path

from config import US_STATES, PRODUCTS, INDUSTRY_BENCHMARKS
from model_client import call_task

CACHE_DIR = Path(__file__).parent / "cache"
TEMPLATES_DIR = Path(__file__).parent / "templates"


def load_template(name: str) -> str:
    path = TEMPLATES_DIR / f"{name}.md"
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def generate_reports(state_code: str, product: str = "curtains") -> dict:
    """生成报告A + 报告B + 自查 + 质疑"""
    state_info = US_STATES[state_code]
    state_name = state_info["name"]
    product_cfg = PRODUCTS[product]
    product_name = product_cfg["display_name"]

    cache_dir = CACHE_DIR / f"{state_code}_{product}"

    # 加载数据池
    pool_path = cache_dir / "data_pool.json"
    with open(pool_path, "r", encoding="utf-8") as f:
        data_pool = json.load(f)

    # 精简数据池（避免超长输入）
    data_summary = summarize_data_pool(data_pool)
    benchmarks = json.dumps(INDUSTRY_BENCHMARKS.get(product, {}), ensure_ascii=False, indent=2)

    results = {}

    # === 步骤12: 生成报告A ===
    print(f"[Step 12] Generating Report A ({state_name} {product_name})...")
    template_a = load_template("report_a")
    prompt_a = template_a.format(
        state_name=state_name,
        product_name=product_name,
        data_json=data_summary,
        benchmarks=benchmarks,
    )

    resp_a = call_task("high",
        messages=[{"role": "user", "content": prompt_a}],
        temperature=0.7,
        max_tokens=16384,
        timeout=600,
    )
    report_a = resp_a["content"]
    results["report_a_raw"] = report_a
    results["report_a_usage"] = resp_a.get("usage", {})
    print(f"  Report A: {len(report_a)} chars")

    # === 步骤13: 生成报告B ===
    print(f"[Step 13] Generating Report B ({state_name} {product_name})...")
    template_b = load_template("report_b")
    prompt_b = template_b.format(
        state_name=state_name,
        product_name=product_name,
        data_json=data_summary,
        benchmarks=benchmarks,
    )

    resp_b = call_task("high",
        messages=[{"role": "user", "content": prompt_b}],
        temperature=0.7,
        max_tokens=16384,
        timeout=600,
    )
    report_b = resp_b["content"]
    results["report_b_raw"] = report_b
    results["report_b_usage"] = resp_b.get("usage", {})
    print(f"  Report B: {len(report_b)} chars")

    # === 步骤14: 自查纠错 ===
    print(f"[Step 14] Reviewing reports...")
    template_review = load_template("review")

    # 审查报告A
    review_prompt_a = template_review.format(
        data_json=data_summary,
        report_text=report_a,
    )
    resp_review_a = call_task("mid",
        messages=[{"role": "user", "content": review_prompt_a}],
        temperature=0.3,
        max_tokens=4096,
        timeout=300,
    )
    results["review_a"] = resp_review_a["content"]
    # 自查只输出修改清单，最终报告保留原始版本（人工或后续流程应用修改）
    results["report_a_final"] = report_a
    print(f"  Report A review: {len(results['review_a'])} chars (原文保留: {len(report_a)} chars)")

    # 审查报告B
    review_prompt_b = template_review.format(
        data_json=data_summary,
        report_text=report_b,
    )
    resp_review_b = call_task("mid",
        messages=[{"role": "user", "content": review_prompt_b}],
        temperature=0.3,
        max_tokens=4096,
        timeout=300,
    )
    results["review_b"] = resp_review_b["content"]
    results["report_b_final"] = report_b
    print(f"  Report B review: {len(results['review_b'])} chars (原文保留: {len(report_b)} chars)")

    # === 步骤15: 反向质疑 ===
    print(f"[Step 15] Challenging report B...")
    template_challenge = load_template("challenge")
    challenge_prompt = template_challenge.format(
        state_name=state_name,
        product_name=product_name,
        report_text=results["report_b_final"],
    )
    resp_challenge = call_task("high",
        messages=[{"role": "user", "content": challenge_prompt}],
        temperature=0.7,
        max_tokens=2048,
        timeout=120,
    )
    results["challenges"] = resp_challenge["content"]
    print(f"  Challenges: {len(results['challenges'])} chars")

    # 保存所有结果
    output_path = cache_dir / "reports.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"  [OK] Reports saved: {output_path}")
    return results


def summarize_data_pool(data_pool: dict) -> str:
    """精简数据池用于模型输入，每个字段带source标签方便模型引用"""
    summary = {}

    # 人口数据 — 每个值旁边都带引用标签
    demos = data_pool.get("demographics", {})
    state_level = demos.get("state_level", [])
    cities = demos.get("cities", [])

    if state_level:
        s = state_level[0] if isinstance(state_level, list) else state_level
        summary["state_demographics"] = {
            "name": s.get("name"),
            "population": f'{s.get("population")} [Census ACS 2023]',
            "median_income": f'${s.get("median_income")} [Census ACS 2023]',
            "median_home_value": f'${s.get("median_home_value")} [Census ACS 2023]',
            "median_rent": f'${s.get("median_rent")} [Census ACS 2023]',
            "housing_units": f'{s.get("housing_units")} [Census ACS 2023]',
        }

    summary["top_cities"] = []
    for c in cities[:10]:
        summary["top_cities"].append({
            "name": c.get("name", "").replace(" city, ", ", ").replace(" town, ", ", "),
            "population": f'{c.get("population")} [Census ACS 2023]',
            "median_income": f'${c.get("median_income")} [Census ACS 2023]',
            "median_home_value": f'${c.get("median_home_value")} [Census ACS 2023]',
        })

    # 经济数据
    eco = data_pool.get("economy", {})
    summary["economy"] = {}
    for k, v in eco.items():
        if isinstance(v, dict) and "value" in v:
            summary["economy"][k] = f'{v["value"]} [FRED {v.get("date", "2024")}]'

    # 工资数据
    wages = data_pool.get("wages", {})
    summary["wages"] = {}
    for k, v in wages.items():
        if isinstance(v, dict) and "value" in v:
            summary["wages"][k] = f'${v["value"]} [BLS OEWS {v.get("year", "2023")}]'

    # 行业统计 (Census CBP)
    cbp = data_pool.get("industry_stats", {})
    if cbp:
        summary["industry_stats"] = {}
        if "state_total" in cbp:
            st = cbp["state_total"]
            summary["industry_stats"]["total_establishments"] = f'{st.get("establishments", "N/A")} [Census CBP 2022]'
            summary["industry_stats"]["total_employees"] = f'{st.get("employees", "N/A")} [Census CBP 2022]'
            summary["industry_stats"]["annual_payroll"] = f'${st.get("annual_payroll", "N/A")}K [Census CBP 2022]'
        if "by_county" in cbp:
            summary["industry_stats"]["by_county"] = []
            for county in cbp["by_county"][:15]:
                summary["industry_stats"]["by_county"].append(
                    f'{county.get("name","")}: {county.get("establishments",0)}家 [Census CBP 2022]'
                )

    # 住房数据 (Census Housing)
    housing = data_pool.get("housing", {})
    if housing:
        summary["housing"] = {}
        for k, v in housing.items():
            if isinstance(v, (int, float, str)):
                summary["housing"][k] = f'{v} [Census Housing 2023]'

    # 迁入人口 (Census Migration)
    migration = data_pool.get("migration", {})
    if migration:
        summary["migration"] = {}
        for k, v in migration.items():
            if isinstance(v, (int, float, str)):
                summary["migration"][k] = f'{v} [Census Migration 2023]'

    # HUD租金
    hud = data_pool.get("fair_market_rent", {})
    if hud:
        summary["fair_market_rent"] = {}
        if isinstance(hud, list):
            for item in hud[:10]:
                area = item.get("area_name", "Unknown")
                summary["fair_market_rent"][area] = f'2BR=${item.get("fmr_2br", "N/A")} [HUD FMR 2024]'
        elif isinstance(hud, dict):
            for k, v in list(hud.items())[:10]:
                summary["fair_market_rent"][k] = f'{v} [HUD FMR 2024]'

    # Google Places商家
    gp = data_pool.get("local_businesses", {})
    if gp:
        businesses = gp if isinstance(gp, list) else gp.get("businesses", [])
        summary["local_businesses"] = []
        for b in (businesses[:10] if isinstance(businesses, list) else []):
            summary["local_businesses"].append({
                "name": b.get("name"),
                "rating": f'{b.get("rating", "N/A")} [Google Places 实时]',
                "reviews": f'{b.get("user_ratings_total", b.get("reviews", "N/A"))}条评论 [Google Places 实时]',
                "city": b.get("city", b.get("vicinity", "")),
            })

    # RentCast租金
    rc = data_pool.get("rentcast", {})
    if rc:
        summary["rentcast"] = {}
        for k, v in rc.items():
            if isinstance(v, (int, float, str)):
                summary["rentcast"][k] = f'{v} [RentCast 实时]'

    # 搜索提取数据 — 标注为Sonar搜索
    search = data_pool.get("search_extracted", {})
    summary["search_data"] = {}
    for cat, items in search.items():
        if items:
            if isinstance(items, list):
                tagged = []
                for item in items:
                    if isinstance(item, dict):
                        item_copy = dict(item)
                        if "source" not in item_copy:
                            item_copy["source"] = "Sonar搜索"
                        tagged.append(item_copy)
                    else:
                        tagged.append(f'{item} [Sonar搜索]')
                summary["search_data"][cat] = tagged
            else:
                summary["search_data"][cat] = items

    # 数据缺口
    summary["data_gaps"] = data_pool.get("data_gaps", [])

    return json.dumps(summary, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python generator.py TX [curtains]")
        sys.exit(1)

    state = sys.argv[1].upper()
    product = sys.argv[2] if len(sys.argv) > 2 else "curtains"

    if state not in US_STATES:
        print(f"[ERROR] Unknown state: {state}")
        sys.exit(1)

    generate_reports(state, product)
