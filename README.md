# Multiagent for Rare

Hospital-oriented rare disease multi-agent workspace with a Python backend and a React frontend.

## Run

1. Create and activate a virtual environment if you want one, or use the included local `.venv`.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Start the app on `127.0.0.1`:

```bash
python -m uvicorn server:app --host 127.0.0.1 --port 8501 --reload
```

4. Open:

```text
http://127.0.0.1:8501
```

Or, if you are using the local `.venv` created in this folder:

```bash
./run_local.sh
```

## What This Demo Includes

- React-based product UI with a professional workspace shell
- Python API layer for profile, settings, intake parsing, history, and diagnosis flows
- Persistent doctor profile and system settings
- Configurable agent roles, provider definitions, and orchestration topology
- Modern bottom composer with attachments, clipboard paste, advanced mode, and diagnostics drawer
- Diagnostic and treatment style outputs with coding, cost estimates, references, and convergence rounds
- Local session history stored on disk

## Design Docs

- [Rare Disease Multi-Agent Framework Design](docs/agent-framework-design.md)

## Notes

- The legacy Streamlit app remains in the repository, but the main local entrypoint now serves the React frontend from `server.py`.
- This is still a demo workflow for prototyping and presentation.
- It does not call real external medical APIs by default.
- Clinical outputs are simulation-oriented and should be reviewed by qualified clinicians before any real-world use.
