# Multiagent for Rare

Hospital-oriented Streamlit demo for a configurable rare disease multi-agent system.

## Run

1. Create and activate a virtual environment if you want one, or use the included local `.venv`.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Start the app on `127.0.0.1`:

```bash
streamlit run app.py --server.address 127.0.0.1 --server.port 8501
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

- Premium landing and control-room style Streamlit UI
- First-use profile setup and persistent user settings
- Configurable agent roles, role specs, API providers, quick-paste API keys, and symmetric/asymmetric topologies
- Multimodal intake for text, images, PDFs, and structured clinical fields
- Convergence diagnostics showing how agents align toward a consistent recommendation
- Diagnostic and treatment style outputs with demo coding blocks, surgical grade, cost estimates, and references
- Local history of previous queries

## Notes

- This is a demo workflow for prototyping and presentation.
- It does not call real external medical APIs by default.
- Clinical outputs are simulation-oriented and should be reviewed by qualified clinicians before any real-world use.
