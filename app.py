from __future__ import annotations

import base64
import json
import os
import time
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
TRAILER_NAMES = {"Flach", "Hoch", "Klein"}
VEHICLE_NAMES = ["Sprinter Gr.", "Sprinter Kl.", "VITO", "CITAN", "FORD", "ALHAMBRA"]
TRAILER_LIST = ["Flach", "Hoch", "Klein"]


def load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


load_dotenv(BASE_DIR / ".env")

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "").strip()
GITHUB_REPO = os.getenv("GITHUB_REPO", "").strip()  # owner/repo
GITHUB_BRANCH = os.getenv("GITHUB_BRANCH", "main").strip() or "main"
GITHUB_STATE_PATH = os.getenv("GITHUB_STATE_PATH", "data/plantafel_state.json").strip()
GITHUB_SYNC_ENABLED = os.getenv("AUTO_SYNC_GITHUB", "0").strip() == "1"
GITHUB_COMMIT_PREFIX = os.getenv("GITHUB_COMMIT_PREFIX", "Plantafel Autosave").strip() or "Plantafel Autosave"
SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip().rstrip("/")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()
SUPABASE_ENABLED = os.getenv("SUPABASE_ENABLED", "1").strip() == "1"


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


def normalize_entry_type(entry_type: str | None) -> str:
    if entry_type == "kunde":
        return "baustelle"
    return entry_type or "ungeklaert"


def normalize_auto_text(text: str) -> str:
    cleaned = (text or "").strip()
    if cleaned.lower().startswith("anhaenger "):
        return cleaned[10:].strip()
    return cleaned


def supabase_configured() -> bool:
    return bool(SUPABASE_ENABLED and SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY)


def supabase_request(
    method: str,
    table: str,
    query: dict[str, str] | None = None,
    data: Any | None = None,
    prefer: str | None = None
) -> Any:
    if not supabase_configured():
        raise RuntimeError("Supabase is not configured")

    url = f"{SUPABASE_URL}/rest/v1/{table}"
    if query:
        url += "?" + urllib.parse.urlencode(query)
    headers = {
        "apikey": SUPABASE_SERVICE_ROLE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_ROLE_KEY}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    if prefer:
        headers["Prefer"] = prefer

    body = None if data is None else json.dumps(data, ensure_ascii=False).encode("utf-8")
    last_error: Exception | None = None
    for attempt in range(1, 4):
        req = urllib.request.Request(url, data=body, method=method, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                raw = resp.read().decode("utf-8")
                return json.loads(raw) if raw else None
        except urllib.error.HTTPError as err:
            raw = err.read().decode("utf-8")
            message = raw
            if raw:
                try:
                    message = json.loads(raw).get("message", raw)
                except json.JSONDecodeError:
                    pass
            raise RuntimeError(f"Supabase {method} {table} failed: HTTP {err.code} {message}") from err
        except (ConnectionResetError, TimeoutError, urllib.error.URLError, OSError) as err:
            last_error = err
            if attempt == 3:
                break
            time.sleep(attempt * 1.5)
    raise RuntimeError(f"Supabase {method} {table} failed after retries: {last_error}") from last_error


def supabase_select_all(table: str, select: str = "*", order: str | None = None) -> list[dict[str, Any]]:
    query = {"select": select}
    if order:
        query["order"] = order
    return supabase_request("GET", table, query) or []


def supabase_upsert(table: str, rows: list[dict[str, Any]], on_conflict: str) -> list[dict[str, Any]]:
    if not rows:
        return []
    return supabase_request(
        "POST",
        table,
        {"on_conflict": on_conflict},
        rows,
        prefer="resolution=merge-duplicates,return=representation"
    ) or []


def supabase_delete_all(table: str) -> None:
    supabase_request(
        "DELETE",
        table,
        {"id": "not.is.null"},
        prefer="return=minimal"
    )


def seed_supabase_catalogs(state: dict[str, Any]) -> dict[str, dict[str, str]]:
    people = state.get("people") if isinstance(state.get("people"), list) else []
    apprentices = set(state.get("apprentices") if isinstance(state.get("apprentices"), list) else [])
    employee_rows = [
        {
            "name": str(name),
            "display_order": (index + 1) * 10,
            "is_apprentice": name in apprentices,
            "is_active": True
        }
        for index, name in enumerate(people)
    ]
    vehicle_rows = [
        {"name": name, "display_order": (index + 1) * 10, "is_active": True}
        for index, name in enumerate(VEHICLE_NAMES)
    ]
    trailer_rows = [
        {"name": name, "display_order": (index + 1) * 10, "is_active": True}
        for index, name in enumerate(TRAILER_LIST)
    ]

    supabase_upsert("employees", employee_rows, "name")
    supabase_upsert("vehicles", vehicle_rows, "name")
    supabase_upsert("trailers", trailer_rows, "name")

    return {
        "employees": {row["name"]: row["id"] for row in supabase_select_all("employees")},
        "vehicles": {row["name"]: row["id"] for row in supabase_select_all("vehicles")},
        "trailers": {row["name"]: row["id"] for row in supabase_select_all("trailers")}
    }


def read_state_from_supabase() -> dict[str, Any]:
    employees = supabase_select_all("employees", order="display_order.asc,name.asc")
    vehicles = supabase_select_all("vehicles")
    trailers = supabase_select_all("trailers")
    school_patterns = supabase_select_all("school_patterns")
    entries = supabase_select_all("schedule_entries", order="entry_date.asc,created_at.asc")

    employee_by_id = {row["id"]: row for row in employees}
    vehicle_by_id = {row["id"]: row for row in vehicles}
    trailer_by_id = {row["id"]: row for row in trailers}

    state = {
        "people": [row["name"] for row in employees if row.get("is_active", True)],
        "apprentices": [row["name"] for row in employees if row.get("is_apprentice") and row.get("is_active", True)],
        "schoolPattern": {},
        "entries": []
    }

    for row in employees:
        if row.get("is_apprentice") and row.get("is_active", True):
            state["schoolPattern"][row["name"]] = []
    for row in school_patterns:
        employee = employee_by_id.get(row.get("employee_id"))
        if not employee:
            continue
        name = employee["name"]
        state["schoolPattern"].setdefault(name, []).append(int(row["weekday"]))
    for days in state["schoolPattern"].values():
        days.sort()

    for row in entries:
        employee = employee_by_id.get(row.get("employee_id"))
        if not employee:
            continue
        entry_type = normalize_entry_type(row.get("entry_type"))
        label = row.get("label") or ""
        trailer = False
        if entry_type == "auto":
            if row.get("trailer_id"):
                trailer_row = trailer_by_id.get(row["trailer_id"])
                label = (trailer_row or {}).get("name") or label
                trailer = True
            elif row.get("vehicle_id"):
                vehicle_row = vehicle_by_id.get(row["vehicle_id"])
                label = (vehicle_row or {}).get("name") or label

        state["entries"].append({
            "id": row.get("legacy_id") or row["id"],
            "person": employee["name"],
            "date": row["entry_date"],
            "type": entry_type,
            "text": label,
            "ws": bool(row.get("is_workshop")),
            "trailer": trailer
        })

    return state


def write_state_to_supabase(state: dict[str, Any]) -> dict[str, Any]:
    state = dedupe_state_entries(state)
    maps = seed_supabase_catalogs(state)
    employees = maps["employees"]
    vehicles = maps["vehicles"]
    trailers = maps["trailers"]

    school_rows: list[dict[str, Any]] = []
    school_pattern = state.get("schoolPattern") if isinstance(state.get("schoolPattern"), dict) else {}
    for person, weekdays in school_pattern.items():
        employee_id = employees.get(person)
        if not employee_id or not isinstance(weekdays, list):
            continue
        for weekday in weekdays:
            school_rows.append({"employee_id": employee_id, "weekday": int(weekday)})

    entry_rows: list[dict[str, Any]] = []
    entries = state.get("entries") if isinstance(state.get("entries"), list) else []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        person = entry.get("person")
        employee_id = employees.get(person)
        if not employee_id:
            continue
        entry_type = normalize_entry_type(entry.get("type"))
        label = entry.get("text") or ""
        vehicle_id = None
        trailer_id = None

        if entry_type == "auto":
            auto_text = normalize_auto_text(label)
            is_trailer = bool(entry.get("trailer")) or auto_text in TRAILER_NAMES
            if is_trailer:
                trailer_id = trailers.get(auto_text)
            else:
                vehicle_id = vehicles.get(auto_text)
            label = auto_text

        entry_rows.append({
            "legacy_id": entry.get("id"),
            "employee_id": employee_id,
            "entry_date": entry.get("date"),
            "entry_type": entry_type,
            "label": label,
            "vehicle_id": vehicle_id,
            "trailer_id": trailer_id,
            "is_workshop": bool(entry.get("ws")),
            "source": "plantafel-api"
        })

    supabase_delete_all("school_patterns")
    supabase_delete_all("schedule_entries")
    supabase_upsert("school_patterns", school_rows, "employee_id,weekday")
    inserted_entries = supabase_upsert("schedule_entries", entry_rows, "legacy_id")
    return {
        "enabled": True,
        "ok": True,
        "employees": len(employees),
        "school_patterns": len(school_rows),
        "schedule_entries": len(inserted_entries)
    }


def dedupe_state_entries(state: dict[str, Any]) -> dict[str, Any]:
    entries = state.get("entries")
    if not isinstance(entries, list):
        return state

    seen: set[tuple[Any, ...]] = set()
    deduped: list[dict[str, Any]] = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        entry_type = normalize_entry_type(entry.get("type"))
        text = normalize_auto_text(entry.get("text") or "") if entry_type == "auto" else (entry.get("text") or "")
        signature = (
            entry.get("person"),
            entry.get("date"),
            entry_type,
            text,
            bool(entry.get("ws")),
            bool(entry.get("trailer")) or (entry_type == "auto" and text in TRAILER_NAMES),
        )
        if signature in seen:
            continue
        seen.add(signature)
        deduped.append(entry)

    if len(deduped) != len(entries):
        state = dict(state)
        state["entries"] = deduped
    return state


def read_current_state() -> tuple[dict[str, Any], dict[str, Any]]:
    if supabase_configured():
        try:
            state = read_state_from_supabase()
            return state, {"enabled": True, "ok": True, "source": "supabase"}
        except RuntimeError as err:
            return read_state(), {"enabled": True, "ok": False, "source": "local-fallback", "error": str(err)}
    return read_state(), {"enabled": False, "source": "local"}


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
    state, storage = read_current_state()
    return jsonify({
        "ok": True,
        "savedAtUtc": utc_now_iso(),
        "storage": storage,
        "state": state
    })


@app.route("/api/state", methods=["PUT", "POST"])
def put_state() -> Any:
    payload = request.get_json(silent=True) or {}
    state = payload.get("state")
    if not isinstance(state, dict):
        return jsonify({"ok": False, "error": "Payload must contain an object at key 'state'."}), 400

    state = dedupe_state_entries(state)
    write_state(state)
    supabase: dict[str, Any]
    if supabase_configured():
        try:
            supabase = write_state_to_supabase(state)
        except RuntimeError as err:
            return jsonify({
                "ok": False,
                "savedAtUtc": utc_now_iso(),
                "error": str(err),
                "supabase": {"enabled": True, "ok": False},
                "localBackup": True
            }), 502
    else:
        supabase = {"enabled": False}

    github = sync_state_to_github(state)
    return jsonify({
        "ok": True,
        "savedAtUtc": utc_now_iso(),
        "supabase": supabase,
        "github": github
    })


if __name__ == "__main__":
    host = os.getenv("HOST", "127.0.0.1").strip() or "127.0.0.1"
    port = int(os.getenv("PORT", "5055"))
    app.run(host=host, port=port, debug=False)
