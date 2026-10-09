# Outbreak of Lies

Outbreak of Lies is a full-stack simulation dashboard for studying how misinformation spreads through a network and which intervention strategy is most effective under a limited budget.

This project combines a Python FastAPI backend with a React + Vite frontend to generate social networks, simulate rumor propagation, compare intervention strategies, and evaluate which tactic performs best under repeated runs.

## Project goal

The system models a campus-like social network in which one or more source nodes begin spreading a rumor. The user can:

- generate a network
- set infection and correction parameters
- run a simulation
- choose intervention nodes
- compare baseline vs intervention outcomes
- evaluate multiple strategies such as degree, CELF, random, pagerank, and betweenness

The goal is to identify strategies that reduce infection spread with a small intervention budget while remaining grounded in the graph structure.

## Why this project matters

A simple degree-based strategy is not always best. Some networks contain trap structures where high-degree nodes are not the best intervention targets. The project includes a trap preset and evaluation logic to demonstrate this challenge and compare strategies quantitatively.

## Architecture

### Backend
The backend lives in [outbreak_backend](outbreak_backend) and uses:

- FastAPI for the API layer
- NetworkX for graph generation and metrics
- NumPy / SciPy for simulation support
- Pydantic models for request validation
- pytest for regression testing

### Frontend
The frontend lives in [outbreak_frontend](outbreak_frontend) and uses:

- React + TypeScript
- Vite
- Axios for API calls
- Recharts for charts
- react-force-graph-2d for network visualization

## Key features

- generate campus, BA, WS, and trap network types
- simulate state transitions across a network timeline
- compare no-intervention vs intervention runs
- select interventions using built-in strategy methods
- evaluate multiple strategies in a repeated benchmark loop
- visualize infection curves and leaderboard-style strategy results
- run the app locally with a clean Windows-friendly setup

## App workflow

1. Choose the network type and simulation parameters.
2. Generate a graph.
3. Run the simulation.
4. Select intervention nodes with the chosen strategy.
5. Compare intervention results with the baseline.
6. Run evaluation to benchmark multiple strategies.
7. Review results in the dashboard chart and leaderboard.

## Project structure

```text
Hackathon/
├── README.md
├── outbreak_backend/
│   ├── api/
│   ├── simulation/
│   ├── strategies/
│   ├── tests/
│   ├── requirements.txt
│   ├── run.py
│   └── setup_dirs.py
├── outbreak_frontend/
│   ├── src/
│   ├── package.json
│   ├── vite.config.ts
│   └── README.md
├── .venv/
├── docker-compose.yml
├── Dockerfile
├── restart_app_windows.bat
├── start_app_windows.bat
└── PITCH.md
```

## Backend API

The backend exposes the following routes:

- `GET /health`
- `POST /network/generate`
- `POST /network/upload`
- `POST /simulate`
- `POST /select`
- `POST /evaluate`
- `GET /results/{result_id}`

The evaluation endpoint accepts a simulation config plus strategy names and returns metrics including spread summaries, confidence bands, and per-strategy comparison data.

## Setup

### 1. Create or activate the Python environment

From the workspace root:

```powershell
D:\Hackathon\.venv\Scripts\python.exe --version
```

If the environment does not exist, recreate it:

```powershell
cd D:\Hackathon
py -3.11 -m venv .venv
D:\Hackathon\.venv\Scripts\python.exe -m pip install --upgrade pip
```

Then install backend dependencies:

```powershell
cd D:\Hackathon\outbreak_backend
D:\Hackathon\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

### 2. Install frontend dependencies

```powershell
cd D:\Hackathon\outbreak_frontend
npm install
```

## Run the project

### Start the backend

Use this exact command from the backend folder:

```powershell
cd D:\Hackathon\outbreak_backend
D:\Hackathon\.venv\Scripts\python.exe -m uvicorn api.main:app --host 127.0.0.1 --port 8001 --reload
```

The app listens on:

```text
http://127.0.0.1:8001
```

### Start the frontend

```powershell
cd D:\Hackathon\outbreak_frontend
npm run dev -- --host 127.0.0.1 --port 5173
```

The dashboard is available at:

```text
http://127.0.0.1:5173/
```

## Validation

Run the backend tests:

```powershell
cd D:\Hackathon\outbreak_backend
D:\Hackathon\.venv\Scripts\python.exe -m pytest -q
```

Run the frontend production build:

```powershell
cd D:\Hackathon\outbreak_frontend
npm run build
```

## Troubleshooting

### Port conflicts
If a port is already in use, stop the existing process and rerun the server on a free port.

### Import errors when starting uvicorn
Make sure you run the command from the backend folder, not from the workspace root. The project imports `api.main` and requires the backend directory to be the active working directory.

### Frontend API connection fails
Ensure the frontend is pointing to the same backend port. This project uses port 8001 for the API and port 5173 for the Vite app.

## Demo notes

This project is intentionally designed as a clean hackathon-demo application: it is easy to run locally, demonstrates graph-based intervention planning, and highlights the difference between naive strategy selection and more effective influence-maximization logic.

## Summary

Outbreak of Lies combines simulation, strategy comparison, and interactive visualization into a single polished demo. It is built to help users understand both how misinformation spreads and how small intervention budgets can be used to reduce impact.
