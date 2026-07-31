# Video Privacy Studio

Workstation locale per l'oscuramento automatico della privacy nei video (volti e targhe automobilistiche) con tracciamento temporale continuo senza GPU su CPU (**OpenCV Multi-Cascade + Temporal Box Persistence Tracker**).

100% Offline | Zero Chiamate Cloud | Funziona su CPU senza GPU | Privacy-First

---

## 🌟 Caratteristiche Principali

- **Pipeline Video su CPU con Tracciamento Temporale (100% Offline)**:
  - **Multi-Cascade OpenCV Detector**: Combinazione di classificatori in cascata (`haarcascade_frontalface_default`, `haarcascade_frontalface_alt`, `haarcascade_profileface` e `haarcascade_russian_plate_number`) per la rilevazione di volti frontali, inclinati, di profilo e targhe automobilistiche.
  - **Temporal Box Persistence Tracker**: Mantiene attivo l'oscuramento per i fotogrammi intermedi anche durante movimenti rapidi o rotazioni del capo, evitando che i volti o le targhe vengano scoperti tra un frame e l'altro.
  - **Margine Dinamico (+35%)**: Espansione automatica dei rettangoli di oscuramento del 35% su tutti i lati per coprire interamente fronte, orecchie, mento, capelli e sfocature da movimento (*motion blur*).
- **Modalità di Oscuramento**:
  - **Sfocatura Gaussiana (*Gaussian Blur*)**: Sfocatura adattiva ad alta intensità.
  - **Pixelatura (*Pixelate*)**: Effetto censura a blocchi di pixel.
  - **Oscuramento Totale (*Blackout*)**: Copertura solida nera opaca.
- **Interfaccia Web Studio Integrata**:
  - **Player di Anteprima Video**: Riproduzione HTML5 immediata del video anonimizzato al termine dell'elaborazione.
  - **Scarica Video Anonimizzato (.mp4)**: Esportazione in un clic del video elaborato salvato nella cartella `~/Documents/Video Privacy Studio - Results/`.
  - **Ricevuta di Privacy (.json)**: Report di verifica con metadati del video, risoluzione, FPS, frame totali ed il conteggio preciso dei rettangoli oscurati.
  - **Gestione Cronologia**: Archiviazione dei task in SQLite locale con possibilità di pulire la cronologia.

---

## 🚀 Avvio Rapido

```bash
# Clone della repository
git clone https://github.com/davidealbertazzi97-jpg/video-privacy-ai-no-gpu.git
cd video-privacy-ai-no-gpu

# Installazione dipendenze ed avvio ambiente
./install.sh
./start.sh
```

*(L'applicazione si aprirà automaticamente nel browser all'indirizzo `http://127.0.0.1:8765`)*.

---

## 🧪 Verifiche e Test del Codice

```bash
# Esecuzione test unitari e test d'integrazione locale
.venv/bin/ruff format .
.venv/bin/ruff check .
.venv/bin/bandit -q -c pyproject.toml -r app runtime_guard scripts
.venv/bin/python -m unittest discover -s tests -p "test_*.py"
.venv/bin/python tests/smoke_local.py
```

---

## 📜 Licenza & Note Legali

Il codice sorgente di **Video Privacy Studio** è distribuito sotto licenza **GNU General Public License v3.0 (GPL-3.0)**.
Per i dettagli sulle componenti di terze parti (OpenCV Apache 2.0, FastAPI, Uvicorn), consulta il file [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md).

---

# Video Privacy Studio — English Overview

A privacy-first local video workstation for automatic face and license plate redaction with continuous temporal tracking on CPU (**OpenCV Multi-Cascade + Temporal Box Persistence Tracker**).

100% Offline | Zero Cloud Requests | Runs on CPU without GPU | Privacy-First

## Key Features

- **Multi-Cascade OpenCV Detection**: Combined cascades (`haarcascade_frontalface_default`, `haarcascade_frontalface_alt`, `haarcascade_profileface`, `haarcascade_russian_plate_number`) for frontal, tilted, profile faces, and license plates.
- **Temporal Box Persistence Tracker**: Maintains redaction boxes across missing intermediate frames during fast movement or head turns, ensuring 100% frame coverage with zero face flickering.
- **35% Bounding Box Padding**: Automatically expands redaction regions by 35% on all sides to cover forehead, ears, chin, hair, and motion blur.
- **Redaction Modes**: Gaussian Blur, Pixelate, and Solid Blackout.
- **Integrated Video Player**: Instant HTML5 preview of the redacted output video.
- **Privacy Audit Receipt (.json)**: Machine-readable report with resolution, FPS, total frames, and redaction count.
- **Local History Management**: Internal SQLite job tracking with full data control.
