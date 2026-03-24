"""端到端主入口 — 输入州名和品类，输出完整报告"""

import os
import sys
import time

from config import US_STATES


def run(state_code: str, product: str = "curtains"):
    """端到端运行"""
    state_name = US_STATES[state_code]["name"]
    print(f"\n{'='*60}")
    print(f"  Market Research: {state_name} / {product}")
    print(f"{'='*60}\n")

    start = time.time()

    # Phase 1A: 预计算
    print("=" * 40)
    print("PHASE 1A: Precompute (Census/FRED/BLS)")
    print("=" * 40)
    from precompute import precompute_state
    precompute_state(state_code, product)

    # Phase 1A: 搜索
    print("\n" + "=" * 40)
    print("PHASE 1A: Search (Sonar)")
    print("=" * 40)
    from searcher import search_all
    search_all(state_code, product)

    # Phase 1A: 验证管线
    print("\n" + "=" * 40)
    print("PHASE 1A: Pipeline (Extract + Gap Check)")
    print("=" * 40)
    from pipeline import run_pipeline
    run_pipeline(state_code, product)

    # Phase 1B: 报告生成
    print("\n" + "=" * 40)
    print("PHASE 1B: Generate Reports")
    print("=" * 40)
    from generator import generate_reports
    generate_reports(state_code, product)

    # Phase 1B: 输出
    print("\n" + "=" * 40)
    print("PHASE 1B: Export (HTML + DOCX)")
    print("=" * 40)
    from exporter import export_all
    export_all(state_code, product)

    elapsed = time.time() - start
    print(f"\n{'='*60}")
    print(f"  DONE in {elapsed:.1f}s")
    print(f"  Output: output/{state_code}_{product}/")
    print(f"{'='*60}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python main.py TX [curtains]")
        print("\nRequired environment variables:")
        print("  OPENROUTER_API_KEY    - Sonar搜索（阶段2）")
        print("  SILICONFLOW_API_KEY   - 低级任务：提取+缺口检查（Qwen3-8B）")
        print("  MINIMAX_API_KEY       - 中/高级任务：自查+写报告+质疑（MiniMax-M2.7）")
        print("\nOptional:")
        print("  FRED_API_KEY          - 经济数据")
        print("  GOOGLE_PLACES_API_KEY - 商家数据")
        print("  HUD_API_KEY           - 住房租金")
        print("\n3类任务模型可覆盖：")
        print("  TASK_LOW_PROVIDER/MODEL   默认 siliconflow / Qwen3-8B")
        print("  TASK_MID_PROVIDER/MODEL   默认 minimax / MiniMax-M2.7")
        print("  TASK_HIGH_PROVIDER/MODEL  默认 minimax / MiniMax-M2.7")
        sys.exit(1)

    state = sys.argv[1].upper()
    product = sys.argv[2] if len(sys.argv) > 2 else "curtains"

    if state not in US_STATES:
        print(f"Unknown state: {state}")
        sys.exit(1)

    # 检查必要的API Key
    from model_client import TASK_LOW, TASK_MID, TASK_HIGH, PROVIDERS
    missing = []
    if not os.environ.get("OPENROUTER_API_KEY"):
        missing.append("OPENROUTER_API_KEY (Sonar搜索)")

    for tier_name, tier_cfg in [("低级", TASK_LOW), ("中级", TASK_MID), ("高级", TASK_HIGH)]:
        provider = tier_cfg["provider"]
        env_key = PROVIDERS[provider]["env_key"]
        if not os.environ.get(env_key):
            missing.append(f"{env_key} ({tier_name}任务: {tier_cfg['model']})")

    if missing:
        print(f"Missing API keys: {', '.join(missing)}")
        sys.exit(1)

    run(state, product)
