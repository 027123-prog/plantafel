# Projektdokumentation Plantafel

## 2026-04-24: Tagesstuecke einzeln verschieben und Anhaenger ersetzen

Ausloeser:

- Mehrtaegige Eintraege werden bewusst tageweise als einzelne Stuecke dargestellt.
- Beim nachtraeglichen Verschieben eines einzelnen Stuecks durfte bisher nicht der komplette zusammenhaengende Zeitraum mitwandern.
- Wenn fuer einen Tag bereits ein Anhaenger hinterlegt ist und ein anderer Anhaenger gewaehlt wird, soll der neue Anhaenger den alten ersetzen.

Umsetzung:

- Drag/Drop verschiebt jetzt nur noch das konkret angefasste Tagesstueck.
- Die vorhandene Logik zum Erweitern oder Verkuerzen ueber die seitlichen Ziehgriffe bleibt getrennt davon erhalten.
- Beim Hinzufuegen oder Bearbeiten eines Anhaengers werden vorhandene Anhaenger in derselben Person/Tag-Zelle ersetzt.
- Die Maximalregel fuer Fahrzeuge/Anhaenger pro Tag bleibt bestehen.

Relevante Dateien:

- `plantafel.html`
- `index.html`

Naechster Test:

- Mehrtaegigen Eintrag anlegen, ein mittleres Tagesstueck per Drag/Drop verschieben und pruefen, dass nur dieses eine Stueck wandert.
- In einer Zelle erst `Flach`, danach `Hoch` oder `Klein` waehlen und pruefen, dass nur ein Anhaenger sichtbar bleibt.

## 2026-04-29: Zielrichtung Betriebsapp statt GitHub als Datenspeicher

Ausloeser:

- Die Plantafel soll perspektivisch Teil einer groesseren Betriebsapp werden.
- Geplant sind spaeter unter anderem Stundenzettel, Materialzettel und Austausch zwischen mehreren Nutzern.
- Deshalb soll nicht nur die schnellste Loesung fuer die Plantafel gewaehlt werden, sondern eine tragfaehige Architektur.

Entscheidung:

- GitHub bleibt fuer Code, Versionierung, Deployment und optional lesbare Backups sinnvoll.
- Betriebsdaten sollen perspektivisch nicht in GitHub-Commits geschrieben werden.
- Fuer die produktive App ist eine echte Datenbank mit Authentifizierung, Rollen, Dateispeicher und spaeterer Echtzeit-Synchronisierung sinnvoller.
- Als naheliegender Zielweg wurde Supabase/Postgres festgehalten, weil es Datenbank, Auth, Storage, Realtime und serverseitige Funktionen in einem System buendelt.

Naechste Schritte:

- Plantafel-Datenmodell in Tabellen ueberfuehren: Mitarbeiter, Eintraege, Fahrzeuge/Anhaenger, Schulmuster.
- Supabase-Projekt anlegen und Zugriff nur ueber Rollen/Rechte regeln.
- Bestehende JSON-Speicherung als Uebergang behalten, bis Import/Export stabil ist.
- Danach Stundenzettel und Materialzettel als eigene Module auf derselben Grundlage planen.

## 2026-04-29: Supabase-Projekt angelegt

Ausloeser:

- Nils hat Supabase ueber seinen GitHub-Account gestartet.
- Das Projekt soll fuer die spaetere Betriebsapp genutzt werden.
- Sobald moeglich soll Codex Pflege, Import und Aenderungen ueber APIs oder lokale Skripte uebernehmen, statt dauerhaft per Hand-Klicks im Dashboard zu arbeiten.

Festgehaltene Projektdaten:

- Supabase Project ID: `tocayvbnygkkhwvhhgow`
- Supabase URL: `https://tocayvbnygkkhwvhhgow.supabase.co`
- Public/Publishable Key wurde bereitgestellt und ist fuer Browser-Nutzung vorgesehen.

Wichtige Sicherheitsregel:

- Geheime Supabase-Schluessel, insbesondere Service-Role-Key und Datenbankpasswort, werden nicht in den Chat, nicht in HTML-Dateien und nicht in GitHub geschrieben.
- Sie gehoeren nur in lokale `.env`-Dateien oder sichere Secret-Speicher.

Naechste Schritte:

- Initiales Datenbankschema aus `supabase_schema_001.sql` im Supabase SQL Editor ausfuehren.
- Danach lokale `.env` vorbereiten.
- Import-Skript fuer `data/plantafel_state.json` nach Supabase erstellen.

## 2026-04-29: Plantafel-Daten nach Supabase importiert

Ausloeser:

- Nach erfolgreichem Schema-Lauf sollten die vorhandenen lokalen Plantafel-Daten in Supabase uebertragen werden.
- Ziel war, ab jetzt API- und Skriptarbeit statt manueller Dashboard-Pflege zu nutzen.

Umsetzung:

- `.env` lokal angelegt und Supabase-Zugangsdaten dort gespeichert.
- `import_plantafel_to_supabase.py` erstellt und ueber die Supabase REST-API ausgefuehrt.
- Das Skript arbeitet idempotent mit Upserts, damit es wiederholt laufen kann.
- UTF-8-BOM in der bestehenden JSON-Datei wird beim Import toleriert.
- Retry-Logik fuer einzelne API-/Netzwerkabbrueche wurde ergaenzt.
- `check_supabase_counts.py` erstellt, um Tabellenstaende per API zu pruefen.

Importierter Stand:

- Mitarbeiter: 19
- Fahrzeuge: 6
- Anhaenger: 3
- Schulmuster: 7
- Plantafel-Eintraege: 114

Relevante Dateien:

- `.env` lokal, nicht fuer GitHub
- `.env.example`
- `supabase_schema_001.sql`
- `import_plantafel_to_supabase.py`
- `check_supabase_counts.py`
- `data/plantafel_state.json`

Naechste Schritte:

- Plantafel-App erst lesend an Supabase anbinden.
- Danach Speichern in Supabase aktivieren.
- Lokale JSON-Speicherung zunaechst als Backup behalten, bis Supabase stabil genutzt wird.

## 2026-04-29: Plantafel-API auf Supabase als Hauptspeicher umgestellt

Ausloeser:

- Nils hat entschieden, direkt "all in" auf die spaetere Betriebsapp-Richtung zu gehen.
- Die Plantafel wird noch nicht produktiv genutzt, deshalb kann Supabase sofort als Hauptspeicher eingefuehrt werden.

Umsetzung:

- `app.py` laedt `.env` lokal und nutzt `SUPABASE_URL` sowie `SUPABASE_SERVICE_ROLE_KEY` serverseitig.
- `GET /api/state` liest den Plantafel-Stand jetzt aus Supabase.
- `PUT/POST /api/state` schreibt zuerst eine lokale JSON-Sicherung und ersetzt danach den Stand in Supabase.
- Mitarbeiter, Fahrzeuge und Anhaenger werden per Upsert gepflegt.
- Schulmuster und Plantafel-Eintraege werden beim Speichern aus dem Browser-State neu aufgebaut.
- Lokale JSON bleibt Backup/Fallback, GitHub-Sync bleibt optional.

Gepruefter Stand:

- API-Lesen aus Supabase: erfolgreich, 19 Personen und 114 Eintraege.
- API-Schreiben nach Supabase: erfolgreich, 19 Mitarbeiter, 7 Schulmuster, 114 Eintraege.
- Kontrollzaehlung per API: 19 Mitarbeiter, 6 Fahrzeuge, 3 Anhaenger, 7 Schulmuster, 114 Eintraege.

Relevante Dateien:

- `app.py`
- `.env.example`
- `README.md`
- `DEPLOYMENT.md`
- `check_supabase_counts.py`

Naechste Schritte:

- Plantafel lokal im Browser testen.
- Danach Benutzer/Login und Rollen fuer die Betriebsapp planen.
- Anschliessend Stundenzettel und Materialzettel als Module auf derselben Supabase-Grundlage entwerfen.

## 2026-04-29: Testaenderung und Dublettenbereinigung

Ausloeser:

- Nils hat in der laufenden Plantafel doppelte Urlaube bei Ludger geloescht.
- Bei Jannek wurde am Donnerstag `krank` eingetragen.
- Beim Pruefen zeigte sich, dass durch den Uebergang von lokalem Browserstand zu Supabase identische Eintraege teilweise doppelt gespeichert waren.

Umsetzung:

- Backend-Funktion `dedupe_state_entries` in `app.py` ergaenzt.
- Beim Speichern ueber `/api/state` werden identische Eintraege nach Person, Datum, Typ, Text, Werkstatt-Flag und Anhaenger-Flag entfernt.
- Aktueller Supabase-Stand einmalig bereinigt.

Gepruefter Stand:

- Vor Bereinigung: 280 Plantafel-Eintraege.
- Nach Bereinigung: 200 Plantafel-Eintraege.
- Ludger aktuelle Woche: je ein Urlaub pro Tag von 2026-04-27 bis 2026-05-01.
- Jannek aktuelle Woche: Donnerstag, 2026-04-30, `krank`.

## 2026-04-29: Render-Hosting vorbereitet

Ausloeser:

- Die Plantafel soll nicht dauerhaft vom lokalen PC unter `127.0.0.1` laufen.
- Nils sucht eine wartungsarme Hosting-Loesung, die Codex moeglichst weit ueber Konfiguration, GitHub und APIs bedienen kann.
- Budgetziel: unter 30 EUR/Monat, Geld darf aber monatlich kosten.

Entscheidung:

- Render Starter Web Service als naechster Hosting-Schritt.
- Supabase bleibt Datenbank.
- GitHub bleibt Code-Quelle und triggert Render-Deploys.

Umsetzung:

- `render.yaml` angelegt.
- Python-Webservice `plantafel` definiert.
- Region `frankfurt`, Plan `starter`, Start via `gunicorn app:app --bind 0.0.0.0:$PORT`.
- `SUPABASE_SERVICE_ROLE_KEY` und `GITHUB_TOKEN` sind als `sync: false` markiert und werden nicht ins Repo geschrieben.
- `DEPLOYMENT.md` um Render-Hinweise erweitert.

Naechste Schritte:

- Aenderungen nach Freigabe committen und zu GitHub pushen.
- In Render Blueprint/Webservice aus dem GitHub-Repo erstellen oder vorhandenen Git-Link nutzen.
- Secret `SUPABASE_SERVICE_ROLE_KEY` im Render Dashboard setzen.
- Nach Deployment `/api/state` auf der Render-URL pruefen.
