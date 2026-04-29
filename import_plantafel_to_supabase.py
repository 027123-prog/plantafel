from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parent
STATE_FILE = BASE_DIR / "data" / "plantafel_state.json"
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


def env_required(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise SystemExit(f"Missing environment variable: {name}")
    return value


def normalize_auto_text(text: str) -> str:
    cleaned = (text or "").strip()
    if cleaned.lower().startswith("anhaenger "):
        return cleaned[10:].strip()
    return cleaned


class SupabaseRest:
    def __init__(self, url: str, service_role_key: str) -> None:
        self.base_url = url.rstrip("/") + "/rest/v1"
        self.headers = {
            "apikey": service_role_key,
            "Authorization": f"Bearer {service_role_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def request(
        self,
        method: str,
        table: str,
        query: dict[str, str] | None = None,
        data: Any | None = None,
        prefer: str | None = None,
    ) -> Any:
        url = f"{self.base_url}/{table}"
        if query:
            url += "?" + urllib.parse.urlencode(query)
        headers = dict(self.headers)
        if prefer:
            headers["Prefer"] = prefer
        body = None if data is None else json.dumps(data, ensure_ascii=False).encode("utf-8")
        last_error: Exception | None = None
        for attempt in range(1, 4):
            req = urllib.request.Request(url, data=body, method=method, headers=headers)
            try:
                with urllib.request.urlopen(req, timeout=30) as response:
                    raw = response.read().decode("utf-8")
                    return json.loads(raw) if raw else None
            except urllib.error.HTTPError as err:
                raw = err.read().decode("utf-8")
                raise SystemExit(f"Supabase {method} {table} failed: HTTP {err.code}\n{raw}") from err
            except (ConnectionResetError, TimeoutError, urllib.error.URLError) as err:
                last_error = err
                if attempt == 3:
                    break
                time.sleep(attempt * 1.5)
        raise SystemExit(f"Supabase {method} {table} failed after retries: {last_error}") from last_error

    def select_all(self, table: str) -> list[dict[str, Any]]:
        return self.request("GET", table, {"select": "*"}) or []

    def upsert(self, table: str, rows: list[dict[str, Any]], on_conflict: str) -> list[dict[str, Any]]:
        if not rows:
            return []
        return self.request(
            "POST",
            table,
            {"on_conflict": on_conflict},
            rows,
            prefer="resolution=merge-duplicates,return=representation",
        ) or []


def main() -> None:
    load_dotenv(BASE_DIR / ".env")

    supabase = SupabaseRest(
        env_required("SUPABASE_URL"),
        env_required("SUPABASE_SERVICE_ROLE_KEY"),
    )

    state = json.loads(STATE_FILE.read_text(encoding="utf-8-sig"))
    people = state.get("people") or []
    apprentices = set(state.get("apprentices") or [])

    employee_rows = [
        {
            "name": name,
            "display_order": (index + 1) * 10,
            "is_apprentice": name in apprentices,
            "is_active": True,
        }
        for index, name in enumerate(people)
    ]
    supabase.upsert("employees", employee_rows, "name")

    vehicle_rows = [
        {"name": name, "display_order": (index + 1) * 10, "is_active": True}
        for index, name in enumerate(VEHICLE_NAMES)
    ]
    trailer_rows = [
        {"name": name, "display_order": (index + 1) * 10, "is_active": True}
        for index, name in enumerate(TRAILER_LIST)
    ]
    supabase.upsert("vehicles", vehicle_rows, "name")
    supabase.upsert("trailers", trailer_rows, "name")

    employees = {row["name"]: row["id"] for row in supabase.select_all("employees")}
    vehicles = {row["name"]: row["id"] for row in supabase.select_all("vehicles")}
    trailers = {row["name"]: row["id"] for row in supabase.select_all("trailers")}

    school_rows: list[dict[str, Any]] = []
    for person, weekdays in (state.get("schoolPattern") or {}).items():
        employee_id = employees.get(person)
        if not employee_id:
            continue
        for weekday in weekdays:
            school_rows.append({"employee_id": employee_id, "weekday": int(weekday)})
    supabase.upsert("school_patterns", school_rows, "employee_id,weekday")

    entry_rows: list[dict[str, Any]] = []
    for entry in state.get("entries") or []:
        person = entry.get("person")
        employee_id = employees.get(person)
        if not employee_id:
            continue

        entry_type = "baustelle" if entry.get("type") == "kunde" else (entry.get("type") or "ungeklaert")
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

        entry_rows.append(
            {
                "legacy_id": entry.get("id"),
                "employee_id": employee_id,
                "entry_date": entry.get("date"),
                "entry_type": entry_type,
                "label": label,
                "vehicle_id": vehicle_id,
                "trailer_id": trailer_id,
                "is_workshop": bool(entry.get("ws")),
                "source": "json-import",
            }
        )

    imported_entries = supabase.upsert("schedule_entries", entry_rows, "legacy_id")
    print(json.dumps({
        "employees": len(employee_rows),
        "vehicles": len(vehicle_rows),
        "trailers": len(trailer_rows),
        "school_patterns": len(school_rows),
        "schedule_entries": len(imported_entries),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
