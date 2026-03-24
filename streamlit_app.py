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

# ========== CSS — Dark Tech header + Minimal Crystal body ==========
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Noto+Sans+SC:wght@300;400;500;700&family=JetBrains+Mono:wght@400;500&display=swap');

:root {
    --bg-primary: #fafbfc;
    --bg-card: #ffffff;
    --bg-dark: #0a0f1a;
    --text-primary: #0f172a;
    --text-secondary: #64748b;
    --text-muted: #94a3b8;
    --accent: #2563eb;
    --accent-light: #dbeafe;
    --accent-glow: rgba(37, 99, 235, 0.12);
    --success: #059669;
    --success-light: #d1fae5;
    --border: #e2e8f0;
    --border-light: #f1f5f9;
    --radius: 14px;
    --radius-sm: 8px;
    --shadow-sm: 0 1px 3px rgba(0,0,0,0.04), 0 1px 2px rgba(0,0,0,0.06);
    --shadow-md: 0 4px 16px rgba(0,0,0,0.06), 0 1px 3px rgba(0,0,0,0.04);
    --shadow-lg: 0 10px 40px rgba(0,0,0,0.08);
    --transition: 0.3s cubic-bezier(0.33, 1, 0.68, 1);
}

/* ===== Global Reset ===== */
.stApp {
    font-family: 'Inter', 'Noto Sans SC', -apple-system, sans-serif;
    background: var(--bg-primary) !important;
}

/* Hide Streamlit branding */
#MainMenu, footer, header[data-testid="stHeader"] { visibility: hidden; height: 0; }
.stDeployButton { display: none; }

/* ===== Sidebar ===== */
section[data-testid="stSidebar"] {
    background: var(--bg-card) !important;
    border-right: 1px solid var(--border) !important;
}
section[data-testid="stSidebar"] .stMarkdown h3 {
    font-size: 0.8rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--text-secondary);
    margin-bottom: 1rem;
}

/* ===== Hero Banner ===== */
.hero-banner {
    background: linear-gradient(135deg, #0a0f1a 0%, #111827 40%, #1e3a5f 70%, #2563eb 100%);
    padding: 2.5rem 2.5rem 2rem;
    border-radius: var(--radius);
    color: white;
    margin-bottom: 1.5rem;
    position: relative;
    overflow: hidden;
}
.hero-banner::before {
    content: '';
    position: absolute;
    top: -50%; right: -20%;
    width: 60%; height: 200%;
    background: radial-gradient(ellipse, rgba(37,99,235,0.15) 0%, transparent 70%);
    pointer-events: none;
}
.hero-banner::after {
    content: '';
    position: absolute;
    bottom: 0; left: 0; right: 0; height: 1px;
    background: linear-gradient(90deg, transparent, rgba(255,255,255,0.1), transparent);
}
.hero-eyebrow {
    font-size: 0.7rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.15em;
    color: rgba(255,255,255,0.5);
    margin-bottom: 0.5rem;
    font-family: 'JetBrains Mono', monospace;
}
.hero-title {
    font-size: 1.75rem;
    font-weight: 700;
    margin: 0 0 0.5rem 0;
    letter-spacing: -0.02em;
    line-height: 1.2;
}
.hero-sub {
    font-size: 0.88rem;
    color: rgba(255,255,255,0.55);
    margin: 0;
    line-height: 1.5;
}
.hero-badges {
    display: flex;
    gap: 8px;
    margin-top: 1rem;
    flex-wrap: wrap;
}
.hero-badge {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    background: rgba(255,255,255,0.08);
    border: 1px solid rgba(255,255,255,0.1);
    border-radius: 100px;
    padding: 4px 12px;
    font-size: 0.72rem;
    color: rgba(255,255,255,0.7);
    font-family: 'JetBrains Mono', monospace;
    backdrop-filter: blur(8px);
}

/* ===== State Chips ===== */
.chips-container {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    margin-bottom: 1rem;
}
.state-chip {
    display: inline-flex;
    align-items: center;
    background: var(--accent-light);
    color: var(--accent);
    border-radius: 100px;
    padding: 5px 14px;
    font-size: 0.8rem;
    font-weight: 500;
    transition: var(--transition);
    border: 1px solid transparent;
}
.state-chip:hover {
    border-color: var(--accent);
    box-shadow: 0 0 0 3px var(--accent-glow);
}

/* ===== Pipeline Steps (Timeline) ===== */
.pipeline-timeline {
    display: flex;
    align-items: flex-start;
    gap: 0;
    padding: 1rem 0;
    position: relative;
}
.pipeline-step {
    flex: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    text-align: center;
    position: relative;
    z-index: 1;
}
.pipeline-step::before {
    content: '';
    position: absolute;
    top: 16px;
    left: 50%;
    width: 100%;
    height: 2px;
    background: var(--border);
    z-index: -1;
}
.pipeline-step:last-child::before { display: none; }

.step-dot {
    width: 34px; height: 34px;
    border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    font-size: 0.75rem; font-weight: 600;
    margin-bottom: 8px;
    transition: var(--transition);
    position: relative;
}
.step-pending .step-dot {
    background: var(--border-light);
    color: var(--text-muted);
    border: 2px solid var(--border);
}
.step-active .step-dot {
    background: var(--accent);
    color: white;
    border: 2px solid var(--accent);
    box-shadow: 0 0 0 4px var(--accent-glow);
    animation: stepPulse 2s ease-in-out infinite;
}
.step-done .step-dot {
    background: var(--success);
    color: white;
    border: 2px solid var(--success);
}
.step-done::before {
    background: var(--success) !important;
}
.step-active::before {
    background: linear-gradient(90deg, var(--success), var(--accent)) !important;
}
.step-label {
    font-size: 0.72rem;
    font-weight: 500;
    color: var(--text-secondary);
    line-height: 1.3;
}
.step-active .step-label { color: var(--accent); font-weight: 600; }
.step-done .step-label { color: var(--success); }

@keyframes stepPulse {
    0%, 100% { box-shadow: 0 0 0 4px var(--accent-glow); }
    50% { box-shadow: 0 0 0 8px rgba(37, 99, 235, 0.06); }
}

/* ===== Download File Cards ===== */
.dl-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 12px;
    margin: 1rem 0;
}
@media (max-width: 768px) {
    .dl-grid { grid-template-columns: repeat(2, 1fr); }
}
.dl-file-card {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    padding: 1.2rem 1rem;
    text-align: center;
    transition: var(--transition);
    cursor: pointer;
}
.dl-file-card:hover {
    border-color: var(--accent);
    box-shadow: var(--shadow-md);
    transform: translateY(-2px);
}
.dl-file-icon {
    font-size: 1.8rem;
    margin-bottom: 0.4rem;
    display: block;
}
.dl-file-name {
    font-weight: 600;
    font-size: 0.82rem;
    color: var(--text-primary);
    margin-bottom: 0.2rem;
}
.dl-file-meta {
    font-size: 0.7rem;
    color: var(--text-muted);
    font-family: 'JetBrains Mono', monospace;
}

/* ===== Sidebar Pipeline Card ===== */
.pipe-card {
    background: linear-gradient(135deg, #f0f9ff 0%, #f8fafc 100%);
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    padding: 1rem;
    font-size: 0.78rem;
}
.pipe-card-title {
    font-weight: 700;
    font-size: 0.7rem;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: var(--accent);
    margin-bottom: 0.6rem;
}
.pipe-step-row {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 4px 0;
    color: var(--text-secondary);
    font-size: 0.78rem;
}
.pipe-step-num {
    width: 20px; height: 20px;
    border-radius: 50%;
    background: var(--accent-light);
    color: var(--accent);
    display: flex; align-items: center; justify-content: center;
    font-size: 0.6rem; font-weight: 700;
    flex-shrink: 0;
}

/* ===== Sidebar Stats ===== */
.stat-grid {
    display: grid;
    grid-template-columns: 1fr 1fr 1fr;
    gap: 8px;
    margin: 0.5rem 0;
}
.stat-card {
    background: var(--bg-primary);
    border: 1px solid var(--border-light);
    border-radius: var(--radius-sm);
    padding: 10px 8px;
    text-align: center;
}
.stat-value {
    font-size: 1.1rem;
    font-weight: 700;
    color: var(--text-primary);
    font-family: 'JetBrains Mono', monospace;
}
.stat-label {
    font-size: 0.65rem;
    color: var(--text-muted);
    margin-top: 2px;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}

/* ===== Report History Card ===== */
.history-card {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 1.2rem;
    margin-bottom: 10px;
    transition: var(--transition);
}
.history-card:hover {
    box-shadow: var(--shadow-md);
    border-color: var(--accent);
}
.history-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 0.8rem;
}
.history-state {
    font-weight: 600;
    font-size: 0.95rem;
    color: var(--text-primary);
}
.history-time {
    font-size: 0.72rem;
    color: var(--text-muted);
    font-family: 'JetBrains Mono', monospace;
}
.history-files {
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
}
.history-file-btn {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    background: var(--bg-primary);
    border: 1px solid var(--border);
    border-radius: 6px;
    padding: 5px 12px;
    font-size: 0.75rem;
    color: var(--text-secondary);
    text-decoration: none;
    transition: var(--transition);
}
.history-file-btn:hover {
    background: var(--accent-light);
    color: var(--accent);
    border-color: var(--accent);
}

/* ===== Empty State ===== */
.empty-state {
    text-align: center;
    padding: 3rem 2rem;
    color: var(--text-muted);
}
.empty-icon { font-size: 3rem; margin-bottom: 0.8rem; opacity: 0.4; }
.empty-title { font-weight: 600; font-size: 1rem; color: var(--text-secondary); margin-bottom: 0.3rem; }
.empty-sub { font-size: 0.85rem; }

/* ===== Streamlit Widget Overrides ===== */
.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, var(--accent), #1d4ed8) !important;
    border: none !important;
    border-radius: var(--radius-sm) !important;
    font-weight: 600 !important;
    letter-spacing: 0.02em;
    transition: var(--transition) !important;
    box-shadow: 0 2px 8px rgba(37, 99, 235, 0.25) !important;
}
.stButton > button[kind="primary"]:hover {
    box-shadow: 0 4px 16px rgba(37, 99, 235, 0.35) !important;
    transform: translateY(-1px);
}
.stButton > button[kind="primary"]:active {
    transform: translateY(0);
}

.stDownloadButton > button {
    border-radius: var(--radius-sm) !important;
    border: 1px solid var(--border) !important;
    background: var(--bg-card) !important;
    transition: var(--transition) !important;
    font-weight: 500 !important;
}
.stDownloadButton > button:hover {
    border-color: var(--accent) !important;
    color: var(--accent) !important;
    box-shadow: var(--shadow-sm) !important;
}

.stProgress > div > div {
    background: linear-gradient(90deg, var(--accent), #60a5fa) !important;
    border-radius: 100px;
    transition: width 0.5s cubic-bezier(0.33, 1, 0.68, 1);
}

div[data-testid="stExpander"] {
    border: 1px solid var(--border) !important;
    border-radius: var(--radius-sm) !important;
    overflow: hidden;
}

/* Tabs */
.stTabs [data-baseweb="tab-list"] {
    gap: 0;
    border-bottom: 2px solid var(--border-light);
}
.stTabs [data-baseweb="tab"] {
    font-weight: 500 !important;
    font-size: 0.88rem !important;
    padding: 0.7rem 1.5rem !important;
    border-radius: 0 !important;
}
.stTabs [aria-selected="true"] {
    border-bottom: 2px solid var(--accent) !important;
    color: var(--accent) !important;
}

/* Success/Info boxes */
div[data-testid="stAlert"] {
    border-radius: var(--radius-sm) !important;
    border: none !important;
}
</style>
""", unsafe_allow_html=True)

# ========== Imports ==========
from config import US_STATES, PRODUCTS


def load_secrets():
    """Load API Keys from Secrets or .env"""
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

    # ===== Hero Banner =====
    st.markdown("""
    <div class="hero-banner">
        <div class="hero-eyebrow">Market Research System v3</div>
        <h1 class="hero-title">美国窗帘市场调研报告</h1>
        <p class="hero-sub">9个官方API采集 + AI智能搜索 + 数据验证 + 自动生成双报告</p>
        <div class="hero-badges">
            <span class="hero-badge">Census ACS</span>
            <span class="hero-badge">FRED</span>
            <span class="hero-badge">BLS</span>
            <span class="hero-badge">Google Places</span>
            <span class="hero-badge">Sonar Search</span>
            <span class="hero-badge">MiniMax M2.7</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    if missing:
        st.error(f"Missing API Keys: {', '.join(missing)}")
        st.info("Go to Streamlit Cloud Settings > Secrets to configure.")
        return

    # ===== Sidebar =====
    with st.sidebar:
        st.markdown("### Configuration")

        product = st.selectbox(
            "Product Category",
            options=list(PRODUCTS.keys()),
            format_func=lambda x: PRODUCTS[x]["display_name"],
        )

        state_options = {k: f"{v['name']} ({k})" for k, v in US_STATES.items()}
        selected_states = st.multiselect(
            "Select States",
            options=list(state_options.keys()),
            format_func=lambda x: state_options[x],
            default=["TX"],
        )

        st.divider()
        c1, c2 = st.columns(2)
        with c1:
            if st.button("All 50", use_container_width=True):
                st.session_state["_sel"] = list(US_STATES.keys())
                st.rerun()
        with c2:
            if st.button("Top 10", use_container_width=True):
                st.session_state["_sel"] = ["CA", "TX", "FL", "NY", "PA", "IL", "OH", "GA", "NC", "MI"]
                st.rerun()

        if "_sel" in st.session_state:
            selected_states = st.session_state.pop("_sel")

        st.divider()
        n = len(selected_states)
        st.markdown(f"""
        <div class="stat-grid">
            <div class="stat-card">
                <div class="stat-value">{n}</div>
                <div class="stat-label">States</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">${n * 0.04:.2f}</div>
                <div class="stat-label">Cost</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">~{n * 5}m</div>
                <div class="stat-label">Time</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.divider()
        steps_html = "".join([
            f'<div class="pipe-step-row"><span class="pipe-step-num">{i+1}</span>{label}</div>'
            for i, label in enumerate([
                "API Data Collection",
                "AI Search (Sonar x11)",
                "Data Cleaning & Validation",
                "Report Generation (MiniMax)",
                "HTML + Word Export",
            ])
        ])
        st.markdown(f"""
        <div class="pipe-card">
            <div class="pipe-card-title">Pipeline</div>
            {steps_html}
        </div>
        """, unsafe_allow_html=True)

    # ===== Main Area =====
    tab1, tab2 = st.tabs(["Generate", "History"])

    with tab1:
        render_generate_tab(selected_states, product)

    with tab2:
        render_reports_tab(product)


def render_generate_tab(states, product):
    """Generate reports tab"""
    if not states:
        st.markdown("""
        <div class="empty-state">
            <div class="empty-icon">🗺️</div>
            <div class="empty-title">Select states to begin</div>
            <div class="empty-sub">Choose one or more states from the sidebar</div>
        </div>
        """, unsafe_allow_html=True)
        return

    chips = "".join([f'<span class="state-chip">{US_STATES[s]["name"]}</span>' for s in states])
    st.markdown(f'<div class="chips-container">{chips}</div>', unsafe_allow_html=True)

    if st.button("Generate Reports", type="primary", use_container_width=True, key="gen_btn"):
        run_pipeline(states, product)


def render_pipeline_steps(step_labels, current_step, done_steps):
    """Render the timeline-style pipeline steps"""
    steps_html = ""
    for i, label in enumerate(step_labels):
        if i in done_steps:
            cls = "step-done"
            icon = "✓"
        elif i == current_step:
            cls = "step-active"
            icon = str(i + 1)
        else:
            cls = "step-pending"
            icon = str(i + 1)
        steps_html += f"""
        <div class="pipeline-step {cls}">
            <div class="step-dot">{icon}</div>
            <div class="step-label">{label}</div>
        </div>
        """
    return f'<div class="pipeline-timeline">{steps_html}</div>'


def run_pipeline(states, product):
    """Execute full pipeline with visual feedback"""
    from precompute import precompute_state
    from searcher import search_all
    from pipeline import run_pipeline as run_data_pipeline
    from generator import generate_reports
    from exporter import export_all

    total = len(states)
    completed = []
    step_labels = ["API Collection", "Search", "Data Cleaning", "Report Gen", "Export"]

    for idx, state in enumerate(states):
        state_name = US_STATES[state]["name"]
        st.markdown("---")
        st.markdown(f"#### {state_name} ({state}) — {idx+1}/{total}")

        timeline_container = st.empty()
        progress = st.progress(0)
        status_text = st.empty()

        done_steps = set()

        try:
            # Step 0: API Collection
            timeline_container.markdown(render_pipeline_steps(step_labels, 0, done_steps), unsafe_allow_html=True)
            status_text.caption("Collecting data from Census, FRED, BLS, HUD, Google Places...")
            progress.progress(0.05)
            precompute_state(state, product)
            done_steps.add(0)
            progress.progress(0.2)

            # Step 1: Search
            timeline_container.markdown(render_pipeline_steps(step_labels, 1, done_steps), unsafe_allow_html=True)
            status_text.caption("Running 11 Sonar search queries...")
            search_all(state, product)
            done_steps.add(1)
            progress.progress(0.4)

            # Step 2: Data Cleaning
            timeline_container.markdown(render_pipeline_steps(step_labels, 2, done_steps), unsafe_allow_html=True)
            status_text.caption("Filtering, extracting, merging data pool...")
            run_data_pipeline(state, product)
            done_steps.add(2)
            progress.progress(0.55)

            # Step 3: Report Generation
            timeline_container.markdown(render_pipeline_steps(step_labels, 3, done_steps), unsafe_allow_html=True)
            status_text.caption("MiniMax M2.7 generating Report A (11 chapters) + Report B (6 chapters)...")
            generate_reports(state, product)
            done_steps.add(3)
            progress.progress(0.85)

            # Step 4: Export
            timeline_container.markdown(render_pipeline_steps(step_labels, 4, done_steps), unsafe_allow_html=True)
            status_text.caption("Generating HTML with ECharts + Word documents...")
            export_all(state, product)
            done_steps.add(4)
            progress.progress(1.0)

            # All done
            timeline_container.markdown(render_pipeline_steps(step_labels, -1, done_steps), unsafe_allow_html=True)
            status_text.empty()

            st.success(f"{state_name} report generated successfully!")
            show_download_buttons(state, product, prefix="gen_")

            # Upload to Supabase
            try:
                from storage import upload_report
                out_dir = Path(__file__).parent / "output" / f"{state}_{product}"
                uploaded = upload_report(state, product, out_dir)
                if uploaded:
                    st.caption(f"Synced to cloud ({len(uploaded)} files)")
            except Exception:
                pass

            completed.append(state)

        except Exception as e:
            st.error(f"{state_name} failed: {e}")
            continue

    if completed:
        st.balloons()
        st.markdown("---")
        st.success(f"All done! {len(completed)} report(s) generated.")


def show_download_buttons(state_code, product, prefix=""):
    """Download buttons for a state's reports"""
    output_dir = Path(__file__).parent / "output" / f"{state_code}_{product}"
    state_name = US_STATES.get(state_code, {}).get("name", state_code)

    if not output_dir.exists():
        return

    cols = st.columns(4)
    files = [
        ("report_a.docx", "Data Report", "Word 11-chapter", "📄"),
        ("report_b.docx", "Business Analysis", "Word Go/No-Go", "📊"),
        ("report.html", "HTML Report", "ECharts interactive", "🌐"),
        ("data_pool.json", "Data Pool", "JSON raw data", "💾"),
    ]

    for i, (fname, title, desc, icon) in enumerate(files):
        fpath = output_dir / fname
        if fpath.exists():
            with cols[i]:
                with open(fpath, "rb") as f:
                    data = f.read()
                size_kb = len(data) / 1024
                size_str = f"{size_kb:.0f}KB" if size_kb < 1024 else f"{size_kb/1024:.1f}MB"
                st.download_button(
                    label=f"{icon} {title} ({size_str})",
                    data=data,
                    file_name=f"{state_code}_{fname}",
                    help=desc,
                    use_container_width=True,
                    key=f"{prefix}dl_{state_code}_{fname}",
                )

    # HTML preview
    html_path = output_dir / "report.html"
    if html_path.exists():
        try:
            with st.expander(f"Preview {state_name} HTML Report", expanded=False):
                html_content = html_path.read_text(encoding="utf-8")
                st.components.v1.html(html_content, height=800)
        except Exception:
            pass


def render_reports_tab(product):
    """Report history tab"""
    from storage import list_reports, SUPABASE_URL, SUPABASE_BUCKET

    cloud_reports = list_reports(product)
    output_dir = Path(__file__).parent / "output"
    local_reports = sorted(output_dir.glob(f"*_{product}")) if output_dir.exists() else []

    if not cloud_reports and not local_reports:
        st.markdown("""
        <div class="empty-state">
            <div class="empty-icon">📂</div>
            <div class="empty-title">No reports yet</div>
            <div class="empty-sub">Generate your first report from the Generate tab</div>
        </div>
        """, unsafe_allow_html=True)
        return

    # Cloud history
    if cloud_reports:
        st.markdown(f"**Cloud History** — {len(cloud_reports)} report(s)")
        for i, report in enumerate(reversed(cloud_reports)):
            state_name = report.get("state_name", report.get("state_code", "?"))
            state_code = report.get("state_code", "?")
            created = report.get("created_at", "")[:16].replace("T", " ")
            files = report.get("files", {})

            file_btns = ""
            for fname, url in files.items():
                label = {
                    "report.html": "HTML",
                    "report_a.docx": "Data Report",
                    "report_b.docx": "Analysis",
                    "data_pool.json": "Data Pool",
                    "reports_raw.json": "Raw",
                }.get(fname, fname)
                file_btns += f'<a href="{url}" target="_blank" class="history-file-btn">{label}</a>'

            st.markdown(f"""
            <div class="history-card">
                <div class="history-header">
                    <span class="history-state">{state_name} ({state_code})</span>
                    <span class="history-time">{created}</span>
                </div>
                <div class="history-files">{file_btns}</div>
            </div>
            """, unsafe_allow_html=True)

    # Local (current session)
    if local_reports:
        st.markdown(f"**This Session** — {len(local_reports)} report(s)")
        for report_dir in local_reports:
            state_code = report_dir.name.split("_")[0]
            state_name = US_STATES.get(state_code, {}).get("name", state_code)
            with st.expander(f"{state_name} ({state_code})", expanded=len(local_reports) == 1):
                show_download_buttons(state_code, product, prefix="hist_")


if __name__ == "__main__":
    main()
