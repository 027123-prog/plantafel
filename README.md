# Plantafel mit Supabase-Speicher

Diese Plantafel laeuft im Browser und speichert den aktuellen Stand ueber eine kleine Flask-API.
Die API liest und schreibt den Plantafel-Stand in Supabase/Postgres. Die lokale JSON-Datei bleibt als Backup/Fallback erhalten.
Optional kann die API bei jeder Speicherung zusaetzlich nach GitHub schreiben.

Repository:

```text
https://github.com/027123-prog/plantafel
```

## Start lokal

```powershell
cd "C:\Users\Nils Wienstroer\Documents\Codex\Projekte\aktiv\Plantafel"
python -m pip install -r requirements.txt
python app.py
```

Danach im Browser oeffnen:

```text
http://127.0.0.1:5055
```

## Supabase aktivieren

Die echten Supabase-Zugangsdaten gehoeren in `.env` und duerfen nicht nach GitHub.

```powershell
SUPABASE_ENABLED=1
SUPABASE_URL=https://tocayvbnygkkhwvhhgow.supabase.co
SUPABASE_PROJECT_ID=tocayvbnygkkhwvhhgow
SUPABASE_PUBLISHABLE_KEY=...
SUPABASE_SERVICE_ROLE_KEY=...
python app.py
```

Wichtig: `SUPABASE_SERVICE_ROLE_KEY` ist geheim und darf nie in `index.html`, Commits oder Screenshots stehen.

## GitHub-Sync optional aktivieren

Fuer Schreibzugriff nach GitHub braucht die API einen GitHub Personal Access Token mit `Contents: Read and write`.
Der Token darf nie in `index.html`, in Commits oder in GitHub Pages gespeichert werden.

PowerShell-Beispiel:

```powershell
$env:AUTO_SYNC_GITHUB="1"
$env:GITHUB_TOKEN="DEIN_TOKEN"
$env:GITHUB_REPO="027123-prog/plantafel"
$env:GITHUB_BRANCH="main"
$env:GITHUB_STATE_PATH="data/plantafel_state.json"
python app.py
```

Dann schreibt die API den Stand in:

```text
data/plantafel_state.json
```

## Smartphone und mehrere Nutzer

Fuer Zugriff per Smartphone oder von mehreren Browsern muss `app.py` auf einem erreichbaren Server laufen.
GitHub Pages allein reicht nicht aus, weil geheime Server-Schluessel sonst im Browser sichtbar waeren.

Weitere Hinweise stehen in `DEPLOYMENT.md`.
