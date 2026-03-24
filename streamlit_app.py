"""Streamlit Web UI — 市场调研报告生成系统"""

import streamlit as st
import os
import json
import time
from pathlib import Path

st.set_page_config(
    page_title="Market Research System",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# 自定义CSS
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Noto+Sans+SC:wght@300;400;500;700&display=swap');

    .stApp {
        font-family: 'Inter', 'Noto Sans SC', sans-serif;
    }
    .main-header {
        background: linear-gradient(135deg, #0f172a 0%, #1e3a5f 50%, #2563eb 100%);
        padding: 2rem;
        border-radius: 16px;
        color: white;
        margin-bottom: 2rem;
    }
    .main-header h1 {
        font-size: 2rem;
        font-weight: 700;
        margin: 0;
    }
    .main-header p {
        opacity: 0.7;
        margin-top: 0.5rem;
    }
    .stat-box {
        background: white;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 1.2rem;
        text-align: center;
    }
    .stat-box .label {
        font-size: 0.75rem;
        text-transform: uppercase;
        color: #64748b;
        letter-spacing: 0.5px;
    }
    .stat-box .value {
        font-size: 1.8rem;
        font-weight: 700;
        color: #0f172a;
    }
    .step-badge {
        display: inline-block;
        background: #2563eb;
        color: white;
        border-radius: 20px;
        padding: 4px 12px;
        font-size: 0.75rem;
        font-weight: 600;
        margin-right: 8px;
    }
    .step-done {
        background: #059669;
    }
    .step-running {
        background: #d97706;
    }
</style>
""", unsafe_allow_html=True)

# ========== 导入业务模块 ==========
from config import US_STATES, PRODUCTS


def check_api_keys():
    """检查必要的API Key"""
    keys = {}
    missing = []

    # 从 Streamlit Secrets 或环境变量获取
    for key_name in ["OPENROUTER_API_KEY", "SILICONFLOW_API_KEY", "MINIMAX_API_KEY",
                     "FRED_API_KEY", "HUD_API_KEY", "GOOGLE_PLACES_API_KEY"]:
        val = st.secrets.get(key_name, os.environ.get(key_name, ""))
        if val:
            keys[key_name] = val
            os.environ[key_name] = val
        elif key_name in ["OPENROUTER_API_KEY", "SILICONFLOW_API_KEY", "MINIMAX_API_KEY"]:
            missing.append(key_name)

    return keys, missing


def main():
    # Header
    st.markdown("""
    <div class="main-header">
        <h1>📊 Market Research System</h1>
        <p>美国市场调研报告自动生成系统 — 输入品类和州名，自动搜索数据、生成专业报告</p>
    </div>
    """, unsafe_allow_html=True)

    # 检查API Keys
    keys, missing = check_api_keys()

    if missing:
        st.error(f"缺少 API Keys: {', '.join(missing)}")
        st.info("请在 Streamlit Cloud 的 Settings → Secrets 中配置，或在本地设置环境变量。")
        with st.expander("如何配置 Secrets"):
            st.code("""
# 在 Streamlit Cloud Settings → Secrets 中添加：
OPENROUTER_API_KEY = "sk-or-v1-..."
DEEPSEEK_API_KEY = "sk-..."
SILICONFLOW_API_KEY = "sk-..."
FRED_API_KEY = "..."
BLS_API_KEY = "..."
HUD_API_KEY = "..."
            """)
        return

    # ========== 侧边栏 ==========
    with st.sidebar:
        st.header("⚙️ 配置")

        product = st.selectbox(
            "选择品类",
            options=list(PRODUCTS.keys()),
            format_func=lambda x: PRODUCTS[x]["display_name"],
        )

        state_options = {k: f"{v['name']} ({k})" for k, v in US_STATES.items()}
        selected_states = st.multiselect(
            "选择州（可多选）",
            options=list(state_options.keys()),
            format_func=lambda x: state_options[x],
            default=["TX"],
        )

        st.divider()

        # 快捷选择
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🇺🇸 全选50州", use_container_width=True):
                st.session_state["select_all"] = True
                st.rerun()
        with col2:
            if st.button("🔝 Top 10州", use_container_width=True):
                st.session_state["select_top10"] = True
                st.rerun()

        if st.session_state.get("select_all"):
            selected_states = list(US_STATES.keys())
            st.session_state["select_all"] = False

        if st.session_state.get("select_top10"):
            selected_states = ["CA", "TX", "FL", "NY", "PA", "IL", "OH", "GA", "NC", "MI"]
            st.session_state["select_top10"] = False

        st.divider()
        st.caption(f"已选: {len(selected_states)} 个州")
        st.caption(f"预计费用: ${len(selected_states) * 0.043:.2f}")
        st.caption(f"预计时间: {len(selected_states) * 15 // 60}分{len(selected_states) * 15 % 60}秒")

    # ========== 主区域 ==========
    tab1, tab2, tab3 = st.tabs(["🚀 生成报告", "📁 已生成报告", "📊 数据总览"])

    with tab1:
        if not selected_states:
            st.warning("请在左侧选择至少一个州")
            return

        st.subheader(f"即将生成: {len(selected_states)} 份报告")

        # 显示选中的州
        cols = st.columns(min(len(selected_states), 8))
        for i, state in enumerate(selected_states[:8]):
            with cols[i]:
                st.metric(US_STATES[state]["name"], state)
        if len(selected_states) > 8:
            st.caption(f"... 还有 {len(selected_states) - 8} 个州")

        if st.button("🚀 开始生成", type="primary", use_container_width=True):
            run_generation(selected_states, product)

    with tab2:
        show_existing_reports(product)

    with tab3:
        show_data_overview()


def run_generation(states: list, product: str):
    """运行报告生成流程"""
    from precompute import precompute_state
    from searcher import search_all
    from pipeline import run_pipeline
    from generator import generate_reports
    from exporter import export_all

    total = len(states)
    progress = st.progress(0, text="准备中...")
    status = st.empty()

    for idx, state in enumerate(states):
        state_name = US_STATES[state]["name"]
        pct = idx / total

        # Step 1: 预计算
        progress.progress(pct + 0.0 / total, text=f"[{idx+1}/{total}] {state_name} — 拉取API数据...")
        status.info(f"📡 正在获取 {state_name} 的 Census/FRED/BLS/HUD 数据...")
        try:
            precompute_state(state, product)
        except Exception as e:
            st.error(f"❌ {state_name} 预计算失败: {e}")
            continue

        # Step 2: 搜索
        progress.progress(pct + 0.2 / total, text=f"[{idx+1}/{total}] {state_name} — 搜索中...")
        status.info(f"🔍 正在搜索 {state_name} 的市场数据（Sonar 9个query）...")
        try:
            search_all(state, product)
        except Exception as e:
            st.error(f"❌ {state_name} 搜索失败: {e}")
            continue

        # Step 3: 验证管线
        progress.progress(pct + 0.4 / total, text=f"[{idx+1}/{total}] {state_name} — 提取数据...")
        status.info(f"⚙️ 正在提取和验证 {state_name} 的结构化数据...")
        try:
            run_pipeline(state, product)
        except Exception as e:
            st.error(f"❌ {state_name} 管线失败: {e}")
            continue

        # Step 4: 生成报告
        progress.progress(pct + 0.6 / total, text=f"[{idx+1}/{total}] {state_name} — 生成报告...")
        status.info(f"📝 正在生成 {state_name} 的调研报告和商业分析报告...")
        try:
            generate_reports(state, product)
        except Exception as e:
            st.error(f"❌ {state_name} 报告生成失败: {e}")
            continue

        # Step 5: 导出
        progress.progress(pct + 0.9 / total, text=f"[{idx+1}/{total}] {state_name} — 导出文件...")
        status.info(f"📄 正在导出 {state_name} 的 HTML + DOCX 报告...")
        try:
            export_all(state, product)
        except Exception as e:
            st.error(f"❌ {state_name} 导出失败: {e}")
            continue

        st.success(f"✅ {state_name} 完成")

    progress.progress(1.0, text="全部完成!")
    status.success(f"🎉 全部 {total} 个州的报告已生成完毕！")
    st.balloons()


def show_existing_reports(product: str):
    """显示已生成的报告"""
    output_dir = Path(__file__).parent / "output"
    if not output_dir.exists():
        st.info("还没有生成过报告")
        return

    reports = sorted(output_dir.glob(f"*_{product}"))
    if not reports:
        st.info(f"还没有生成过 {PRODUCTS[product]['display_name']} 的报告")
        return

    for report_dir in reports:
        state_code = report_dir.name.split("_")[0]
        state_name = US_STATES.get(state_code, {}).get("name", state_code)

        with st.expander(f"📋 {state_name} ({state_code})", expanded=False):
            col1, col2, col3, col4 = st.columns(4)

            # 下载按钮
            for fname, label, col in [
                ("report_a.docx", "📄 数据报告", col1),
                ("report_b.docx", "📊 商业分析", col2),
                ("report_a.html", "🌐 HTML报告A", col3),
                ("report_b.html", "🌐 HTML报告B", col4),
            ]:
                fpath = report_dir / fname
                if fpath.exists():
                    with col:
                        with open(fpath, "rb") as f:
                            st.download_button(
                                label=label,
                                data=f.read(),
                                file_name=f"{state_code}_{fname}",
                                use_container_width=True,
                            )


def show_data_overview():
    """显示数据总览"""
    cache_dir = Path(__file__).parent / "cache"
    if not cache_dir.exists():
        st.info("还没有缓存数据")
        return

    # 查找所有数据池
    pools = sorted(cache_dir.glob("*/data_pool.json"))
    if not pools:
        st.info("还没有数据池")
        return

    for pool_path in pools:
        state_code = pool_path.parent.name.split("_")[0]
        state_name = US_STATES.get(state_code, {}).get("name", state_code)

        with open(pool_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        with st.expander(f"📊 {state_name} 数据池", expanded=True):
            # 人口数据
            cities = data.get("demographics", {}).get("cities", [])
            if cities:
                st.caption("主要城市人口")
                city_data = []
                for c in cities[:8]:
                    name = c.get("name", "").split(" city,")[0]
                    city_data.append({
                        "城市": name,
                        "人口": f"{c.get('population', 0):,}",
                        "收入中位数": f"${c.get('median_income', 0):,}",
                        "房价中位数": f"${c.get('median_home_value', 0):,}",
                    })
                st.dataframe(city_data, use_container_width=True, hide_index=True)

            # 数据覆盖
            coverage = data.get("data_coverage", [])
            gaps = data.get("data_gaps", [])
            col1, col2 = st.columns(2)
            with col1:
                st.metric("数据覆盖", f"{len(coverage)} 类")
            with col2:
                st.metric("数据缺口", f"{len(gaps)} 类")


if __name__ == "__main__":
    main()
