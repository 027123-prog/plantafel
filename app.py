from __future__ import annotations

import base64
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from flask import Flask, jsonify, request, send_from_directory


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
STATE_FILE = DATA_DIR / "plantafel_state.json"

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "").strip()
GITHUB_REPO = os.getenv("GITHUB_REPO", "").strip()  # owner/repo
GITHUB_BRANCH = os.getenv("GITHUB_BRANCH", "main").strip() or "main"
GITHUB_STATE_PATH = os.getenv("GITHUB_STATE_PATH", "data/plantafel_state.json").strip()
GITHUB_SYNC_ENABLED = os.getenv("AUTO_SYNC_GITHUB", "0").strip() == "1"
GITHUB_COMMIT_PREFIX = os.getenv("GITHUB_COMMIT_PREFIX", "Plantafel Autosave").strip() or "Plantafel Autosave"


app = Flask(__name__, static_folder=None)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_state() -> dict[str, Any]:
    if not STATE_FILE.exists():
        return {}
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def write_state(state: dict[str, Any]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    temp_path = STATE_FILE.with_suffix(".tmp")
    payload = json.dumps(state, ensure_ascii=False, indent=2)
    temp_path.write_text(payload, encoding="utf-8")
    temp_path.replace(STATE_FILE)


def github_request(method: str, url: str, data: dict[str, Any] | None = None) -> tuple[int, dict[str, Any]]:
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "plantafel-autosave"
    }
    body = None
    if data is not None:
        body = json.dumps(data).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=body, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            raw = resp.read().decode("utf-8")
            parsed = json.loads(raw) if raw else {}
            return resp.status, parsed
    except urllib.error.HTTPError as err:
        raw = err.read().decode("utf-8")
        parsed = {}
        if raw:
            try:
                parsed = json.loads(raw)
            except json.JSONDecodeError:
                parsed = {"message": raw}
        return err.code, parsed
    except OSError as err:
        return 0, {"message": str(err)}


def sync_state_to_github(state: dict[str, Any]) -> dict[str, Any]:
    if not GITHUB_SYNC_ENABLED:
        return {"enabled": False}
    if not GITHUB_TOKEN or not GITHUB_REPO:
        return {"enabled": True, "ok": False, "error": "Missing GITHUB_TOKEN or GITHUB_REPO"}

    encoded_path = urllib.parse.quote(GITHUB_STATE_PATH, safe="/")
    content_api_url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{encoded_path}"
    get_url = f"{content_api_url}?ref={urllib.parse.quote(GITHUB_BRANCH)}"

    status_get, get_payload = github_request("GET", get_url)
    sha = None
    if status_get == 200:
        sha = get_payload.get("sha")
    elif status_get != 404:
        return {
            "enabled": True,
            "ok": False,
            "phase": "read",
            "status": status_get,
            "error": get_payload.get("message", "Failed to read file from GitHub")
        }

    state_document = {
        "savedAtUtc": utc_now_iso(),
        "state": state
    }
    serialized = json.dumps(state_document, ensure_ascii=False, indent=2).encode("utf-8")
    commit_payload: dict[str, Any] = {
        "message": f"{GITHUB_COMMIT_PREFIX} {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "content": base64.b64encode(serialized).decode("ascii"),
        "branch": GITHUB_BRANCH
    }
    if sha:
        commit_payload["sha"] = sha

    status_put, put_payload = github_request("PUT", content_api_url, commit_payload)
    if status_put not in (200, 201):
        return {
            "enabled": True,
            "ok": False,
            "phase": "write",
            "status": status_put,
            "error": put_payload.get("message", "Failed to write file to GitHub")
        }
    return {
        "enabled": True,
        "ok": True,
        "commit": (put_payload.get("commit") or {}).get("sha", "")
    }


@app.get("/")
def index() -> Any:
    return send_from_directory(BASE_DIR, "index.html")


@app.get("/api/state")
def get_state() -> Any:
    return jsonify({
        "ok": True,
        "savedAtUtc": utc_now_iso(),
        "state": read_state()
    })


@app.route("/api/state", methods=["PUT", "POST"])
def put_state() -> Any:
    payload = request.get_json(silent=True) or {}
    state = payload.get("state")
    if not isinstance(state, dict):
        return jsonify({"ok": False, "error": "Payload must contain an object at key 'state'."}), 400

    write_state(state)
    github = sync_state_to_github(state)
    return jsonify({
        "ok": True,
        "savedAtUtc": utc_now_iso(),
        "github": github
    })


if __name__ == "__main__":
    host = os.getenv("HOST", "127.0.0.1").strip() or "127.0.0.1"
    port = int(os.getenv("PORT", "5055"))
    app.run(host=host, port=port, debug=False)
