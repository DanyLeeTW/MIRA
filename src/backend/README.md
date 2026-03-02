# Backend FHIR Integration 🐳📦🔥

A lightweight Python backend that spins up a local **[HAPI FHIR](https://hapifhir.io/)** server in Docker Desktop 🐳 and provides helper utilities to seed the server with Patients, Practitioners, and Organizations derived from MIMIC-IV data.

---

## Directory structure 📂

```text
.
├── README.md                 ⇠ *This file*
├── __init__.py               ⇠ Marks the directory as a Python package
├── fhir_client.py            ⇠ FHIR HTTP client helpers
├── fhir_setup.py             ⇠ Resource-generation helpers (Patient, Practitioner, ...)
├── hapi-fhir-server
│   └── docker-compose.yml    ⇠ One-service stack for HAPI FHIR v7.4.0
└── log.py                    ⇠ Project-wide structured logging
```

> **Tip** Use the compose file at `backend/hapi-fhir-server/docker-compose.yml` from `HospitalAgent/src`.

---

## Quick start ⚙️

### 0  Canonical working directory 📍

Run all commands below from:

```bash
cd /path/to/HospitalAgent/src
```

### 1  Prerequisites 🔑

| Tool           | Version (tested) | Notes                                                  |
| -------------- | ---------------- | ------------------------------------------------------ |
| Python         | 3.12 +           | Use `uv` (recommended) or `pyenv`/`conda`            |
| Docker Desktop | 4.x +            | Must be **running** before you launch any Python code |

Install dependencies (from this directory, where `pyproject.toml` lives):

```bash
uv sync
```

### 2  Note

You must start the Docker service 🐳 `hapi-fhir` before running Python code.
If you start it with `up -d`, it runs in the background (use `docker compose ... logs -f` to view logs).

If starting was not attempted or failed you might see something like this later:
`FileNotFoundError: [Errno 2] No such file or directory: 'docker'`.

### 3  Configure runtime 🔑

No backend API keys are required for the local Docker setup in this module.

Optional `src/config.py` overrides:

```python
MAX_HOSPITAL_SERVER_RETRIES = 3
LOG_LEVEL = "ERROR"
```

### 4  Launch the stack 🚀

```bash
# From HospitalAgent/src
docker compose -f backend/hapi-fhir-server/docker-compose.yml up -d
```

The service exposes **[http://localhost:8080/fhir/](http://localhost:8080/fhir/)** and becomes healthy when `/metadata` returns `200`.
Port binding is local-only (`127.0.0.1:8080:8080`).

### 5  Tests

Use any runtime entrypoint that posts FHIR resources (for example the run notebooks/scripts in `runs/`) and verify requests succeed against `http://localhost:8080/fhir/`.
Run entrypoints from this `src/` directory so imports like `from config import ...` resolve.

---

## Troubleshooting

| Symptom                                     | Cause / Fix                                                                                           |
| ------------------------------------------- | ----------------------------------------------------------------------------------------------------- |
| `Docker is not running`                     | Start Docker Desktop 🐳 manually; on macOS the app auto-launches via `open /Applications/Docker.app`. |
| `Failed to start the FHIR server container` | Another process is using port `8080`; edit the compose file or stop the conflicting service.         |
| `Connection refused` / `HTTP 500/503`       | The server is still booting. Wait for `/metadata` to return `200`.                                   |
| `FileNotFoundError: docker-compose.yml`     | Start compose with the explicit path above from `HospitalAgent/src`.                                |
| `ModuleNotFoundError: No module named 'config'` | Run from `HospitalAgent/src` (or export `PYTHONPATH=src`) before starting Python entrypoints.     |
