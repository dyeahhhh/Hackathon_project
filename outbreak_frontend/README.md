# Outbreak of Lies Frontend

This frontend provides the interactive control panel and visualization layer for the epidemic simulation project.

## Purpose

The interface lets users:

- generate a network
- adjust infection parameters
- simulate rumor spread
- select intervention nodes
- compare baseline and intervention graphs
- benchmark strategy performance in the evaluation dashboard

## Stack

- React
- TypeScript
- Vite
- Axios
- Recharts
- react-force-graph-2d

## Run locally

```powershell
cd D:\Hackathon\outbreak_frontend
npm install
npm run dev -- --host 127.0.0.1 --port 5173
```

Then open:

```text
http://127.0.0.1:5173/
```

## Build for production

```powershell
cd D:\Hackathon\outbreak_frontend
npm run build
```

## Notes

The frontend expects the backend to be running on port 8001. If the app is not connected to the backend, evaluation and simulation requests will fail.
