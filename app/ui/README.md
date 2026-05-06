# UI (Phase 4)

Minimal interface: welcome, three example factual questions, visible disclaimer **“Facts-only. No investment advice.”**, message + single source link + footer.

See `docs/phase-wise-architecture.md` §7 and `docs/edge-cases-phase-4.md`.

## Run

1) Start backend (in one terminal):

```powershell
$env:PORT="8787"
.\.venv\Scripts\python.exe -m app.api
```

2) Start UI static server (in another terminal):

```powershell
powershell -ExecutionPolicy Bypass -File scripts/run_ui.ps1
```

Then open `http://127.0.0.1:5173/`.
