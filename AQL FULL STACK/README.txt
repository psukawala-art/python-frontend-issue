AirScope - India AQI Dashboard (macOS)

START
  Terminal:  cd into this folder, then run:
               chmod +x run.command
               ./run.command
  Finder:    double-click run.command
             (if macOS blocks it: right-click > Open > Open, once)

First run installs packages (internet needed, about a minute).
Your browser opens automatically. Ctrl+C in the Terminal stops it.

FILES
  run.command       the single launcher (backend check + dashboard + browser)
  app.py            dashboard (frontend)
  aqi_backend.py    AQI engine, data fetching, predictor (backend)
  requirements.txt  Python packages
