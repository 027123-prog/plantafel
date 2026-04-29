from __future__ import annotations

import json

from import_plantafel_to_supabase import BASE_DIR, SupabaseRest, env_required, load_dotenv


def main() -> None:
    load_dotenv(BASE_DIR / ".env")
    supabase = SupabaseRest(
        env_required("SUPABASE_URL"),
        env_required("SUPABASE_SERVICE_ROLE_KEY"),
    )
    counts = {}
    for table in ("employees", "vehicles", "trailers", "school_patterns", "schedule_entries"):
        rows = supabase.request("GET", table, {"select": "id"})
        counts[table] = len(rows or [])
    print(json.dumps(counts, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
