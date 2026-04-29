# Plantafel Deployment

Die Plantafel besteht aus einer Webseite (`index.html`) und einer kleinen Flask-API (`app.py`).
Die API haelt geheime Schluessel serverseitig und liest/schreibt den Plantafel-Stand in Supabase/Postgres.
GitHub-Sync ist nur noch optional fuer Backups oder Versionsspuren.

## Wichtige Regel

Geheime Schluessel duerfen nie in `index.html`, in GitHub Pages oder in Commits stehen.
Das gilt besonders fuer `SUPABASE_SERVICE_ROLE_KEY` und `GITHUB_TOKEN`.
Sie gehoeren nur als Umgebungsvariablen auf den Server oder Hoster.

## Lokaler Start

```powershell
cd "C:\Users\Nils Wienstroer\Documents\Codex\Projekte\aktiv\Plantafel"
python -m pip install -r requirements.txt

$env:AUTO_SYNC_GITHUB="1"
$env:GITHUB_REPO="027123-prog/plantafel"
$env:GITHUB_BRANCH="main"
$env:GITHUB_STATE_PATH="data/plantafel_state.json"
$env:GITHUB_TOKEN="DEIN_TOKEN"
$env:SUPABASE_ENABLED="1"
$env:SUPABASE_URL="https://tocayvbnygkkhwvhhgow.supabase.co"
$env:SUPABASE_PROJECT_ID="tocayvbnygkkhwvhhgow"
$env:SUPABASE_SERVICE_ROLE_KEY="DEIN_SUPABASE_SERVICE_ROLE_KEY"

python app.py
```

Danach im Browser oeffnen:

```text
http://127.0.0.1:5055
```

## Hosting

Fuer Smartphone- und Browser-Zugriff durch mehrere Nutzer braucht die App einen erreichbaren Server,
zum Beispiel Render, Railway, PythonAnywhere oder einen eigenen kleinen Server.

## Render

Fuer den aktuellen Stand ist Render als wartungsarmer Webservice vorgesehen.
Die Datei `render.yaml` beschreibt den Service:

```text
Name: plantafel
Runtime: Python
Plan: Free fuer den ersten Test, spaeter Starter fuer dauerhaften Betrieb ohne Einschlafen
Region: Frankfurt
Build Command: pip install -r requirements.txt
Start Command: gunicorn app:app --bind 0.0.0.0:$PORT
Health Check: /api/state
```

Geheime Werte werden nicht in `render.yaml` gespeichert.
Render fragt bei `sync: false` nach dem Wert oder der Wert wird manuell im Dashboard unter Environment gesetzt.

Beim Hoster diese Umgebungsvariablen setzen:

```text
SUPABASE_ENABLED=1
SUPABASE_URL=https://tocayvbnygkkhwvhhgow.supabase.co
SUPABASE_PROJECT_ID=tocayvbnygkkhwvhhgow
SUPABASE_SERVICE_ROLE_KEY=<als Secret setzen>
AUTO_SYNC_GITHUB=1
GITHUB_REPO=027123-prog/plantafel
GITHUB_BRANCH=main
GITHUB_STATE_PATH=data/plantafel_state.json
GITHUB_COMMIT_PREFIX=Plantafel Autosave
HOST=0.0.0.0
PORT=<vom Hoster vorgegeben oder 5055>
GITHUB_TOKEN=<als Secret setzen>
```

Startbefehl je nach Hoster:

```text
python app.py
```

oder mit Gunicorn auf Linux-Hostern:

```text
gunicorn app:app
```

## GitHub Pages

GitHub Pages allein reicht fuer diese App nicht aus, weil Pages keine sicheren Schreibzugriffe mit geheimen Server-Schluesseln
ausfuehren kann. Die Webseite kann aber ueber den Flask-Server ausgeliefert werden.
