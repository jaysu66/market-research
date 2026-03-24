"""Supabase Storage — 报告持久化存储"""

import httpx
import json
import os
from pathlib import Path
from datetime import datetime

# Supabase配置
SUPABASE_URL = "https://bbfyfkjcvhpqmjticmsy.supabase.co"
SUPABASE_BUCKET = "market-reports"

def _get_key():
    """获取Supabase service_role key"""
    import streamlit as st
    try:
        return st.secrets.get("SUPABASE_KEY", os.environ.get("SUPABASE_KEY", ""))
    except Exception:
        return os.environ.get("SUPABASE_KEY", "")


def upload_report(state_code: str, product: str, output_dir: Path) -> dict:
    """上传报告文件到Supabase Storage

    路径格式: {product}/{state_code}/{timestamp}/{filename}
    """
    key = _get_key()
    if not key:
        print("  [Storage] No SUPABASE_KEY, skipping upload")
        return {}

    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    base_path = f"{product}/{state_code}/{timestamp}"

    files_to_upload = [
        "report.html",
        "report_a.docx",
        "report_b.docx",
        "data_pool.json",
        "reports_raw.json",
    ]

    uploaded = {}
    headers = {
        "Authorization": f"Bearer {key}",
        "apikey": key,
    }

    for fname in files_to_upload:
        fpath = output_dir / fname
        if not fpath.exists():
            continue

        remote_path = f"{base_path}/{fname}"

        # 根据文件类型设置content-type
        ct = "application/octet-stream"
        if fname.endswith(".html"):
            ct = "text/html; charset=utf-8"
        elif fname.endswith(".json"):
            ct = "application/json"
        elif fname.endswith(".docx"):
            ct = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

        try:
            with open(fpath, "rb") as f:
                data = f.read()

            url = f"{SUPABASE_URL}/storage/v1/object/{SUPABASE_BUCKET}/{remote_path}"
            resp = httpx.post(
                url,
                content=data,
                headers={**headers, "Content-Type": ct},
                timeout=30,
            )

            if resp.status_code in (200, 201):
                public_url = f"{SUPABASE_URL}/storage/v1/object/public/{SUPABASE_BUCKET}/{remote_path}"
                uploaded[fname] = public_url
                print(f"  [Storage] Uploaded {fname} → {public_url}")
            else:
                print(f"  [Storage] Failed {fname}: {resp.status_code} {resp.text[:100]}")
        except Exception as e:
            print(f"  [Storage] Error uploading {fname}: {e}")

    # 保存索引
    if uploaded:
        save_index(state_code, product, timestamp, uploaded, key)

    return uploaded


def save_index(state_code: str, product: str, timestamp: str, files: dict, key: str):
    """更新报告索引文件（用于历史记录）"""
    index_path = f"{product}/index.json"
    headers = {
        "Authorization": f"Bearer {key}",
        "apikey": key,
    }

    # 尝试读取现有索引
    index = []
    try:
        url = f"{SUPABASE_URL}/storage/v1/object/public/{SUPABASE_BUCKET}/{index_path}"
        resp = httpx.get(url, timeout=10)
        if resp.status_code == 200:
            index = resp.json()
    except Exception:
        pass

    # 添加新记录
    from config import US_STATES
    state_name = US_STATES.get(state_code, {}).get("name", state_code)

    index.append({
        "state_code": state_code,
        "state_name": state_name,
        "product": product,
        "timestamp": timestamp,
        "created_at": datetime.now().isoformat(),
        "files": files,
    })

    # 上传更新后的索引（upsert）
    try:
        url = f"{SUPABASE_URL}/storage/v1/object/{SUPABASE_BUCKET}/{index_path}"
        # 先尝试update
        resp = httpx.put(
            url,
            content=json.dumps(index, ensure_ascii=False, indent=2).encode("utf-8"),
            headers={**headers, "Content-Type": "application/json"},
            timeout=10,
        )
        if resp.status_code not in (200, 201):
            # 如果update失败，尝试create
            resp = httpx.post(
                url,
                content=json.dumps(index, ensure_ascii=False, indent=2).encode("utf-8"),
                headers={**headers, "Content-Type": "application/json"},
                timeout=10,
            )
        print(f"  [Storage] Index updated: {len(index)} reports")
    except Exception as e:
        print(f"  [Storage] Index update failed: {e}")


def list_reports(product: str = "curtains") -> list:
    """从Supabase读取报告历史"""
    index_path = f"{product}/index.json"
    try:
        url = f"{SUPABASE_URL}/storage/v1/object/public/{SUPABASE_BUCKET}/{index_path}"
        resp = httpx.get(url, timeout=10)
        if resp.status_code == 200:
            return resp.json()
    except Exception:
        pass
    return []
