"""Market Research API — FastAPI backend for jansonhub.shop"""

import json
import os
import time
import traceback
from pathlib import Path
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Load .env
from dotenv import load_dotenv
load_dotenv()

# --- Models ---

class GenerateRequest(BaseModel):
    state_code: str
    product: str = "curtains"

class GenerateResponse(BaseModel):
    task_id: str
    status: str
    message: str

class TaskStatus(BaseModel):
    task_id: str
    status: str  # pending, running, completed, failed
    progress: int  # 0-100
    step: str  # current step description
    started_at: str
    completed_at: str | None = None
    result: dict | None = None
    error: str | None = None

# --- Task store (in-memory, reset on restart) ---
tasks: dict[str, TaskStatus] = {}

# --- Lifespan ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("[API] Market Research API starting...")
    yield
    print("[API] Shutting down...")

# --- App ---
app = FastAPI(
    title="Market Research API",
    description="Generate market research reports for US states",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://jansonhub.shop",
        "https://www.jansonhub.shop",
        "https://market-research-web.vercel.app",
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Pipeline runner (runs in background) ---

def run_pipeline_task(task_id: str, state_code: str, product: str):
    """Run the full pipeline in background"""
    task = tasks[task_id]
    task.status = "running"
    task.step = "Initializing..."

    try:
        from config import US_STATES
        state_name = US_STATES.get(state_code, {}).get("name", state_code)
        cache_dir = Path(__file__).parent / "cache" / f"{state_code}_{product}"
        output_dir = Path(__file__).parent / "output" / f"{state_code}_{product}"
        cache_dir.mkdir(parents=True, exist_ok=True)
        output_dir.mkdir(parents=True, exist_ok=True)

        # Stage 1: API Collection
        task.step = f"Stage 1/5: Collecting API data for {state_name}..."
        task.progress = 5
        from precompute import precompute_state
        api_data = precompute_state(state_code, product)
        with open(cache_dir / "api_data.json", "w", encoding="utf-8") as f:
            json.dump(api_data, f, ensure_ascii=False, indent=2)
        task.progress = 20

        # Stage 2: Search
        task.step = f"Stage 2/5: Running AI search queries..."
        task.progress = 25
        from searcher import search_all
        search_data = search_all(state_code, product)
        with open(cache_dir / "search_raw.json", "w", encoding="utf-8") as f:
            json.dump(search_data, f, ensure_ascii=False, indent=2)
        task.progress = 40

        # Stage 3: Data Pipeline
        task.step = f"Stage 3/5: Cleaning and verifying data..."
        task.progress = 45
        from pipeline import run_pipeline as run_data_pipeline
        data_pool = run_data_pipeline(state_code, product)
        with open(cache_dir / "data_pool.json", "w", encoding="utf-8") as f:
            json.dump(data_pool, f, ensure_ascii=False, indent=2)
        # Copy to output
        with open(output_dir / "data_pool.json", "w", encoding="utf-8") as f:
            json.dump(data_pool, f, ensure_ascii=False, indent=2)
        task.progress = 55

        # Stage 4: Report Generation
        task.step = f"Stage 4/5: Generating reports with AI..."
        task.progress = 60
        from generator import generate_reports
        reports = generate_reports(state_code, product)
        with open(cache_dir / "reports.json", "w", encoding="utf-8") as f:
            json.dump(reports, f, ensure_ascii=False, indent=2)
        with open(output_dir / "reports_raw.json", "w", encoding="utf-8") as f:
            json.dump(reports, f, ensure_ascii=False, indent=2)
        task.progress = 85

        # Stage 5: Export
        task.step = f"Stage 5/5: Generating HTML and Word documents..."
        task.progress = 90
        from exporter import export_html, export_docx
        export_html(state_code, product)
        export_docx(state_code, product)
        task.progress = 95

        # Upload to Supabase
        task.step = "Uploading to cloud storage..."
        try:
            from storage import upload_report
            uploaded = upload_report(state_code, product, output_dir)
        except Exception as e:
            uploaded = {}
            print(f"  [API] Storage upload failed: {e}")

        # Done
        task.status = "completed"
        task.progress = 100
        task.step = "Done!"
        task.completed_at = datetime.now().isoformat()

        # Extract summary for result
        report_a = reports.get("report_a_final", reports.get("report_a_raw", ""))
        report_b = reports.get("report_b_final", reports.get("report_b_raw", ""))
        task.result = {
            "state_code": state_code,
            "state_name": state_name,
            "product": product,
            "report_a_chars": len(report_a),
            "report_b_chars": len(report_b),
            "chapters_a": len([l for l in report_a.split("\n") if l.startswith("## ")]),
            "chapters_b": len([l for l in report_b.split("\n") if l.startswith("## ")]),
            "cloud_files": uploaded,
        }

    except Exception as e:
        task.status = "failed"
        task.step = f"Error: {str(e)[:200]}"
        task.error = traceback.format_exc()
        print(f"  [API] Pipeline failed: {e}")


# --- Endpoints ---

@app.get("/")
async def root():
    return {
        "service": "Market Research API",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
    }

@app.get("/health")
async def health():
    return {"status": "ok", "timestamp": datetime.now().isoformat()}

@app.post("/generate", response_model=GenerateResponse)
async def generate(req: GenerateRequest, background_tasks: BackgroundTasks):
    """Start report generation for a state"""
    from config import US_STATES
    if req.state_code not in US_STATES:
        raise HTTPException(400, f"Invalid state code: {req.state_code}")

    task_id = f"{req.state_code}_{req.product}_{int(time.time())}"

    tasks[task_id] = TaskStatus(
        task_id=task_id,
        status="pending",
        progress=0,
        step="Queued...",
        started_at=datetime.now().isoformat(),
    )

    background_tasks.add_task(run_pipeline_task, task_id, req.state_code, req.product)

    return GenerateResponse(
        task_id=task_id,
        status="pending",
        message=f"Report generation started for {US_STATES[req.state_code]['name']}",
    )

@app.get("/status/{task_id}", response_model=TaskStatus)
async def get_status(task_id: str):
    """Check generation progress"""
    if task_id not in tasks:
        raise HTTPException(404, f"Task not found: {task_id}")
    return tasks[task_id]

@app.get("/reports")
async def list_reports(product: str = "curtains"):
    """List all generated reports from Supabase"""
    try:
        from storage import list_reports as storage_list
        return storage_list(product)
    except Exception:
        return []

@app.get("/reports/{state_code}")
async def get_report(state_code: str, product: str = "curtains"):
    """Get report data for a specific state"""
    cache_dir = Path(__file__).parent / "cache" / f"{state_code}_{product}"
    reports_file = cache_dir / "reports.json"
    if not reports_file.exists():
        raise HTTPException(404, f"No report found for {state_code}")

    with open(reports_file, "r", encoding="utf-8") as f:
        return json.load(f)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
