# Plantafel Deployment

Die Plantafel besteht aus einer Webseite (`index.html`) und einer kleinen Flask-API (`app.py`).
Die API haelt den GitHub-Token geheim und schreibt den Plantafel-Stand nach GitHub.

## Wichtige Regel

Der GitHub-Token darf nie in `index.html`, in GitHub Pages oder in Commits stehen.
Er gehoert nur als Umgebungsvariable auf den Server oder Hoster.

## Lokaler Start

```powershell
cd "C:\Users\Nils Wienstroer\Documents\Codex\Projekte\aktiv\Plantafel"
python -m pip install -r requirements.txt

$env:AUTO_SYNC_GITHUB="1"
$env:GITHUB_REPO="027123-prog/plantafel"
$env:GITHUB_BRANCH="main"
$env:GITHUB_STATE_PATH="data/plantafel_state.json"
$env:GITHUB_TOKEN="DEIN_TOKEN"

python app.py
```

Danach im Browser oeffnen:

```text
http://127.0.0.1:5055
```

## Hosting

Fuer Smartphone- und Browser-Zugriff durch mehrere Nutzer braucht die App einen erreichbaren Server,
zum Beispiel Render, Railway, PythonAnywhere oder einen eigenen kleinen Server.

Beim Hoster diese Umgebungsvariablen setzen:

```text
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

GitHub Pages allein reicht fuer diese App nicht aus, weil Pages keine sicheren Schreibzugriffe mit geheimem Token
ausfuehren kann. Die Webseite kann aber ueber den Flask-Server ausgeliefert werden.
