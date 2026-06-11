# DevDeck Control

Desktop-App zum Konfigurieren des DevDeck (Arduino-Macropad mit 6 Buttons,
6 OLEDs und 3 Encodern). Das Backend ist Python (pywebview + pyserial), die
Oberfläche ein Vue-3-Frontend (Vite + Tailwind + shadcn-vue).

Läuft unter **macOS** und **Windows**.

## Voraussetzungen

| Was | macOS | Windows |
|---|---|---|
| Python | 3.9 oder neuer | 3.9 oder neuer ([python.org](https://www.python.org/downloads/), bei der Installation „Add to PATH" anhaken) |
| Node.js | 18 oder neuer (nur für Entwicklung/Frontend-Build) | 18 oder neuer |
| WebView-Engine | WKWebView (im System enthalten) | [Edge WebView2 Runtime](https://developer.microsoft.com/microsoft-edge/webview2/) — auf Windows 10/11 normalerweise vorinstalliert |
| Serieller Treiber | meist keiner nötig; für Nano-Clones (CH340) ggf. [CH340-Treiber](https://sparks.gogo.co.nz/ch340.html) | original Arduino: keiner; CH340-Clones: CH340-Treiber |

## Einrichtung

Alle Befehle im Ordner `devdeck-control/` ausführen.

### macOS

```bash
# Virtuelle Umgebung anlegen und aktivieren
python3 -m venv .venv
source .venv/bin/activate

# Python-Abhängigkeiten installieren
pip install -r requirements.txt

# Frontend-Abhängigkeiten installieren
cd frontend && npm install && cd ..
```

### Windows (PowerShell)

```powershell
# Virtuelle Umgebung anlegen und aktivieren
py -m venv .venv
.venv\Scripts\Activate.ps1

# Python-Abhängigkeiten installieren
pip install -r requirements.txt

# Frontend-Abhängigkeiten installieren
cd frontend; npm install; cd ..
```

> Falls PowerShell die Aktivierung blockiert („running scripts is disabled"):
> einmalig `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` ausführen,
> oder stattdessen die Eingabeaufforderung (cmd) mit `.venv\Scripts\activate.bat` nutzen.

## Starten

### Entwicklungsmodus (Standard)

Startet automatisch einen Vite-Dev-Server (Hot-Reload) und öffnet das Fenster:

```bash
# macOS
source .venv/bin/activate
python main.py
```

```powershell
# Windows
.venv\Scripts\Activate.ps1
python main.py
```

Node.js/npm muss dafür installiert sein. Ist npm nicht vorhanden, fällt die
App automatisch auf das gebaute Frontend in `frontend/dist` zurück (sofern
vorhanden).

### Produktionsmodus

Frontend einmal bauen, dann ohne Dev-Server starten:

```bash
# macOS
cd frontend && npm run build && cd ..
DEVDECK_DEV=0 python main.py
```

```powershell
# Windows
cd frontend; npm run build; cd ..
$env:DEVDECK_DEV = "0"
python main.py
```

## DevDeck anschließen

Die App sucht im Hintergrund automatisch nach einem Arduino und verbindet
sich selbstständig (erkennt u. a. Arduino-, CH340-, FTDI- und CP210x-Ports).
Der Port lässt sich im Serial-Panel der App auch manuell wählen:

- **macOS:** Ports heißen `/dev/cu.usbmodemXXXX` oder `/dev/cu.usbserial-XXXX`
- **Windows:** Ports heißen `COM3`, `COM4`, …

Beim ersten Anschließen den Kalibrier-Assistenten in der App ausführen —
er ermittelt die Zuordnung von Buttons, OLEDs und Encodern und speichert
sie in `hw_mapping.json`.

## Als eigenständige App paketieren (optional, experimentell)

Mit [PyInstaller](https://pyinstaller.org) lässt sich eine startbare App ohne
Python-Installation bauen. Vorher das Frontend bauen (`npm run build`).

```bash
# macOS (Trennzeichen bei --add-data ist ":")
pip install pyinstaller
pyinstaller --name "DevDeck Control" --windowed \
  --add-data "frontend/dist:frontend/dist" main.py
```

```powershell
# Windows (Trennzeichen bei --add-data ist ";")
pip install pyinstaller
pyinstaller --name "DevDeck Control" --windowed --add-data "frontend/dist;frontend/dist" main.py
```

Das Ergebnis liegt in `dist/DevDeck Control/`. Die paketierte App startet
automatisch im Produktionsmodus und nutzt das mitgelieferte Frontend —
`DEVDECK_DEV` muss nicht gesetzt werden.

## Problemlösungen

- **`pip install` schlägt fehl:** Prüfen, ob die virtuelle Umgebung aktiv ist
  (`(.venv)` am Zeilenanfang) und Python ≥ 3.9 verwendet wird (`python --version`).
- **Fenster bleibt weiß / App startet nicht (Windows):** Edge WebView2 Runtime
  installieren (Link oben, „Evergreen Bootstrapper").
- **`npm wurde nicht gefunden`:** Node.js installieren — oder das Frontend auf
  einem anderen Rechner bauen und den Ordner `frontend/dist` mitnehmen.
- **Kein Port gefunden:** Anderes USB-Kabel probieren (manche Kabel sind nur
  Ladekabel), bei Nano-Clones den CH340-Treiber installieren. Außerdem darf
  der serielle Monitor der Arduino IDE nicht gleichzeitig offen sein — der
  Port kann nur von einem Programm belegt werden.
- **Verbindung da, aber Displays bleiben leer:** Links in der App eine
  Konfiguration als aktiv auswählen; die OLEDs werden erst dann bespielt.

## Projektstruktur

```
devdeck-control/
├── main.py            # Einstiegspunkt (öffnet das pywebview-Fenster)
├── api.py             # JS-Bridge: Configs, Serial, Kalibrierung, Bilder
├── serial_bridge.py   # JSON-Protokoll zum Arduino (Auto-Connect, ACK)
├── db/                # SQLite-Persistenz (configs.db)
├── models/            # Datenmodell (Buttons, Encoder, Configs)
├── utils/             # Kommando-Ausführung, OLED-Bildkonvertierung
├── frontend/          # Vue-3-Frontend (Vite); dist/ = gebaute Version
├── images/            # Konvertierte 128x64-BMPs für die OLEDs
└── hw_mapping.json    # Ergebnis des Kalibrier-Assistenten
```
