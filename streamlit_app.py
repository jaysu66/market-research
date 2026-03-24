"""Streamlit Web UI — 市场调研报告生成系统"""

import streamlit as st
import os
import json
import time
from pathlib import Path

st.set_page_config(
    page_title="Market Research · 市场调研",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ========== CSS ==========
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Noto+Sans+SC:wght@300;400;500;700&display=swap');

.stApp { font-family: 'Inter', 'Noto Sans SC', sans-serif; }

/* Header */
.hero {
    background: linear-gradient(135deg, #0f172a 0%, #1e3a5f 50%, #2563eb 100%);
    padding: 2.5rem 2rem;
    border-radius: 16px;
    color: white;
    margin-bottom: 1.5rem;
}
.hero h1 { font-size: 1.8rem; font-weight: 700; margin: 0 0 0.3rem 0; }
.hero p { opacity: 0.75; margin: 0; font-size: 0.9rem; }

/* Cards */
.card {
    background: white;
    border: 1px solid #e2e8f0;
    border-radius: 12px;
    padding: 1.2rem;
    margin-bottom: 0.8rem;
}
.card h4 { margin: 0 0 0.5rem 0; color: #0f172a; }

/* State chips */
.state-chip {
    display: inline-block;
    background: #eff6ff;
    color: #1e40af;
    border-radius: 8px;
    padding: 6px 14px;
    margin: 3px;
    font-size: 0.85rem;
    font-weight: 500;
}

/* Step indicator */
.step-row {
    display: flex;
    align-items: center;
    padding: 8px 0;
    border-bottom: 1px solid #f1f5f9;
}
.step-num {
    width: 28px; height: 28px;
    border-radius: 50%;
    background: #e2e8f0;
    color: #475569;
    display: flex; align-items: center; justify-content: center;
    font-size: 0.75rem; font-weight: 600;
    margin-right: 12px; flex-shrink: 0;
}
.step-active .step-num { background: #2563eb; color: white; }
.step-done .step-num { background: #059669; color: white; }
.step-label { font-size: 0.85rem; color: #334155; }

/* Download cards */
.dl-card {
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 10px;
    padding: 1rem;
    text-align: center;
    transition: all 0.2s;
}
.dl-card:hover { border-color: #2563eb; background: #eff6ff; }
.dl-icon { font-size: 2rem; margin-bottom: 0.3rem; }
.dl-title { font-weight: 600; color: #0f172a; font-size: 0.85rem; }
.dl-sub { color: #64748b; font-size: 0.75rem; }

/* Pipeline info */
.pipeline-info {
    background: #f0fdf4;
    border: 1px solid #bbf7d0;
    border-radius: 10px;
    padding: 1rem;
    font-size: 0.8rem;
    color: #166534;
}
</style>
""", unsafe_allow_html=True)

# ========== 导入 ==========
from config import US_STATES, PRODUCTS


def load_secrets():
    """从Secrets或.env加载API Keys"""
    keys_needed = ["OPENROUTER_API_KEY", "SILICONFLOW_API_KEY", "MINIMAX_API_KEY"]
    missing = []
    for k in keys_needed:
        val = ""
        try:
            val = st.secrets.get(k, "")
        except Exception:
            pass
        if not val:
            val = os.environ.get(k, "")
        if val:
            os.environ[k] = val
        else:
            missing.append(k)
    return missing


def main():
    missing = load_secrets()

    # Hero
    st.markdown("""
    <div class="hero">
        <h1>📊 Market Research System</h1>
        <p>美国窗帘/窗饰市场调研报告自动生成 · 9个官方API + AI搜索 + 智能报告</p>
    </div>
    """, unsafe_allow_html=True)

    if missing:
        st.error(f"⚠️ 缺少 API Keys: {', '.join(missing)}")
        st.info("在 Streamlit Cloud → Settings → Secrets 中配置TOML格式的API密钥。")
        return

    # ========== 侧边栏 ==========
    with st.sidebar:
        st.markdown("### ⚙️ 报告配置")

        product = st.selectbox(
            "📦 品类",
            options=list(PRODUCTS.keys()),
            format_func=lambda x: PRODUCTS[x]["display_name"],
        )

        state_options = {k: f"{v['name']} ({k})" for k, v in US_STATES.items()}
        selected_states = st.multiselect(
            "🗺️ 选择州",
            options=list(state_options.keys()),
            format_func=lambda x: state_options[x],
            default=["TX"],
        )

        st.divider()
        c1, c2 = st.columns(2)
        with c1:
            if st.button("🇺🇸 全选50州", use_container_width=True):
                st.session_state["_sel"] = list(US_STATES.keys())
                st.rerun()
        with c2:
            if st.button("🔝 Top 10", use_container_width=True):
                st.session_state["_sel"] = ["CA", "TX", "FL", "NY", "PA", "IL", "OH", "GA", "NC", "MI"]
                st.rerun()

        if "_sel" in st.session_state:
            selected_states = st.session_state.pop("_sel")

        st.divider()
        n = len(selected_states)
        st.markdown(f"""
        **已选:** {n} 个州
        **预计费用:** ${n * 0.04:.2f}
        **预计时间:** ~{n * 5}分钟
        """)

        st.divider()
        st.markdown("""
        <div class="pipeline-info">
        <b>Pipeline 流程</b><br>
        ① API采集 (Census/FRED/BLS)<br>
        ② 智能搜索 (Sonar×11)<br>
        ③ 数据清洗验证<br>
        ④ AI报告生成 (MiniMax-M2.7)<br>
        ⑤ HTML + Word 导出
        </div>
        """, unsafe_allow_html=True)

    # ========== 主区域 ==========
    tab1, tab2 = st.tabs(["🚀 生成报告", "📁 已生成报告"])

    with tab1:
        render_generate_tab(selected_states, product)

    with tab2:
        render_reports_tab(product)


def render_generate_tab(states, product):
    """生成报告标签页"""
    if not states:
        st.info("👈 请在左侧选择至少一个州")
        return

    # 显示已选州
    chips = "".join([f'<span class="state-chip">{US_STATES[s]["name"]}</span>' for s in states])
    st.markdown(f'<div style="margin-bottom:1rem">{chips}</div>', unsafe_allow_html=True)

    if st.button("🚀 开始生成报告", type="primary", use_container_width=True, key="gen_btn"):
        run_pipeline(states, product)


def run_pipeline(states, product):
    """执行完整pipeline并显示结果"""
    from precompute import precompute_state
    from searcher import search_all
    from pipeline import run_pipeline as run_data_pipeline
    from generator import generate_reports
    from exporter import export_all

    total = len(states)
    completed = []

    for idx, state in enumerate(states):
        state_name = US_STATES[state]["name"]
        st.markdown(f"---")
        st.subheader(f"📍 {state_name} ({state}) — [{idx+1}/{total}]")

        steps = st.columns(5)
        step_labels = ["API采集", "搜索", "数据清洗", "报告生成", "导出"]
        step_status = [st.empty() for _ in range(5)]
        progress = st.progress(0)

        # 每个step的容器
        for i, label in enumerate(step_labels):
            with steps[i]:
                step_status[i] = st.empty()
                step_status[i].markdown(f"⬜ {label}")

        try:
            # Step 1
            step_status[0].markdown(f"🔄 **API采集**")
            progress.progress(0.05)
            precompute_state(state, product)
            step_status[0].markdown(f"✅ API采集")
            progress.progress(0.2)

            # Step 2
            step_status[1].markdown(f"🔄 **搜索**")
            search_all(state, product)
            step_status[1].markdown(f"✅ 搜索")
            progress.progress(0.4)

            # Step 3
            step_status[2].markdown(f"🔄 **数据清洗**")
            run_data_pipeline(state, product)
            step_status[2].markdown(f"✅ 数据清洗")
            progress.progress(0.55)

            # Step 4
            step_status[3].markdown(f"🔄 **报告生成**")
            generate_reports(state, product)
            step_status[3].markdown(f"✅ 报告生成")
            progress.progress(0.85)

            # Step 5
            step_status[4].markdown(f"🔄 **导出**")
            export_all(state, product)
            step_status[4].markdown(f"✅ 导出")
            progress.progress(1.0)

            # 成功 → 立即显示下载按钮
            st.success(f"✅ {state_name} 报告生成完成！")
            show_download_buttons(state, product)
            completed.append(state)

        except Exception as e:
            st.error(f"❌ {state_name} 失败: {e}")
            continue

    if completed:
        st.balloons()
        st.markdown("---")
        st.success(f"🎉 全部完成！共生成 {len(completed)} 份报告")


def show_download_buttons(state_code, product):
    """显示某个州的下载按钮"""
    output_dir = Path(__file__).parent / "output" / f"{state_code}_{product}"
    state_name = US_STATES.get(state_code, {}).get("name", state_code)

    if not output_dir.exists():
        return

    cols = st.columns(4)
    files = [
        ("report_a.docx", "📄 数据调研报告", "Word · 11章完整版"),
        ("report_b.docx", "📊 商业分析报告", "Word · Go/No-Go决策"),
        ("report.html", "🌐 HTML完整报告", "含ECharts交互图表"),
        ("data_pool.json", "💾 原始数据池", "JSON · 全部API数据"),
    ]

    for i, (fname, title, desc) in enumerate(files):
        fpath = output_dir / fname
        if fpath.exists():
            with cols[i]:
                with open(fpath, "rb") as f:
                    data = f.read()
                st.download_button(
                    label=f"{title}",
                    data=data,
                    file_name=f"{state_code}_{fname}",
                    help=desc,
                    use_container_width=True,
                    key=f"dl_{state_code}_{fname}",
                )

    # HTML预览（iframe）
    html_path = output_dir / "report.html"
    if html_path.exists():
        with st.expander(f"👁️ 预览 {state_name} HTML报告", expanded=False):
            html_content = html_path.read_text(encoding="utf-8")
            st.components.v1.html(html_content, height=800, scrolling=True)


def render_reports_tab(product):
    """已生成报告标签页"""
    output_dir = Path(__file__).parent / "output"
    if not output_dir.exists():
        st.info("还没有生成过报告。点击「生成报告」标签开始。")
        return

    reports = sorted(output_dir.glob(f"*_{product}"))
    if not reports:
        st.info(f"还没有 {PRODUCTS[product]['display_name']} 的报告。")
        return

    st.markdown(f"### 已生成 {len(reports)} 份报告")

    for report_dir in reports:
        state_code = report_dir.name.split("_")[0]
        state_name = US_STATES.get(state_code, {}).get("name", state_code)

        with st.expander(f"📋 {state_name} ({state_code})", expanded=len(reports) == 1):
            show_download_buttons(state_code, product)

            # 报告统计
            reports_json = report_dir / "reports_raw.json"
            if not reports_json.exists():
                reports_json = Path(__file__).parent / "cache" / f"{state_code}_{product}" / "reports.json"

            if reports_json.exists():
                with open(reports_json, "r", encoding="utf-8") as f:
                    rdata = json.load(f)
                ra = rdata.get("report_a_final", rdata.get("report_a_raw", ""))
                rb = rdata.get("report_b_final", rdata.get("report_b_raw", ""))
                c1, c2, c3 = st.columns(3)
                c1.metric("报告A字数", f"{len(ra):,}")
                c2.metric("报告B字数", f"{len(rb):,}")
                c3.metric("章节数", f"{len([l for l in ra.split(chr(10)) if l.startswith('## ')])}")


if __name__ == "__main__":
    main()
