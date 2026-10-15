import logging
from typing import Any, Dict, List, Optional

import networkx as nx
from fastapi import Body, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from simulation.engine import initialize_states, run_simulation
from simulation.evaluation import run_evaluation_suite
from simulation.models import NodeState, SimulationConfig
from simulation.networks import generate_network, network_summary

app = FastAPI(title="Outbreak of Lies API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logger = logging.getLogger(__name__)
RESULT_STORE: Dict[str, Dict[str, object]] = {}


class NetworkUploadRequest(BaseModel):
    edges: List[List[int | float]] = Field(default_factory=list)
    nodes: Optional[List[int]] = None


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.post("/network/generate")
def api_generate_network(config: SimulationConfig):
    G = generate_network(config)
    summary = network_summary(G)
    nodes = [{"id": node, "group": 1} for node in G.nodes()]
    links = [{"source": u, "target": v, "weight": G[u][v].get("weight", 1.0)} for u, v in G.edges()]
    return {"nodes": nodes, "links": links, "summary": summary}


@app.post("/network/upload")
def api_upload_network(payload: NetworkUploadRequest):
    G = nx.Graph()
    if payload.nodes:
        G.add_nodes_from(payload.nodes)
    for edge in payload.edges:
        if len(edge) == 2:
            u, v = edge
            weight = 1.0
        else:
            u, v, weight = edge
        G.add_edge(int(u), int(v), weight=float(weight))
    if G.number_of_nodes() == 0:
        raise HTTPException(status_code=400, detail="Empty graph upload")
    return {"nodes": [{"id": n, "group": 1} for n in G.nodes()], "links": [{"source": u, "target": v, "weight": G[u][v].get("weight", 1.0)} for u, v in G.edges()], "summary": network_summary(G)}


@app.post("/simulate")
def api_simulate(config: SimulationConfig):
    G = generate_network(config)
    adj_matrix = nx.to_scipy_sparse_array(G, format="csr")
    states = initialize_states(config.num_nodes, config.source_nodes, config.intervention_nodes, config.intervention_type)
    history = run_simulation(
        adj_matrix,
        states,
        config.beta,
        config.gamma,
        config.delta,
        max_steps=config.max_steps,
        seed=config.seed,
    )
    timeline = [step.tolist() for step in history]
    return {"timeline": timeline, "final_state": history[-1].tolist() if history else []}


@app.post("/select")
def api_select(config: SimulationConfig, k: int = 5, strategy: str = "celf"):
    G = generate_network(config)
    from strategies.baselines import (
        strategy_closeness,
        strategy_highest_betweenness,
        strategy_highest_degree,
        strategy_highest_pagerank,
        strategy_k_core,
        strategy_random,
    )
    from strategies.celf import strategy_celf

    strategy_name = (strategy or "celf").lower()
    if strategy_name == "random":
        selected = strategy_random(G, k, seed=config.seed)
    elif strategy_name == "degree":
        selected = strategy_highest_degree(G, k)
    elif strategy_name == "betweenness":
        selected = strategy_highest_betweenness(G, k)
    elif strategy_name == "pagerank":
        selected = strategy_highest_pagerank(G, k)
    elif strategy_name == "k_core":
        selected = strategy_k_core(G, k)
    elif strategy_name == "closeness":
        selected = strategy_closeness(G, k)
    else:
        selected = strategy_celf(G, k, config, num_sims=25)

    if not selected:
        selected = strategy_highest_degree(G, k)
    return {"selected": selected, "strategy": strategy_name}


def _coerce_int(value: Any, default: int) -> int:
    if value is None:
        return default
    if hasattr(value, "default"):
        value = value.default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _normalize_strategy_names(values: Any) -> List[str]:
    if values is None:
        return []
    if isinstance(values, str):
        values = [values]
    elif not isinstance(values, (list, tuple, set)):
        values = [values]

    normalized: List[str] = []
    seen: set[str] = set()
    for value in values:
        if value is None:
            continue
        for item in str(value).split(","):
            name = item.strip().lower()
            if name and name not in seen:
                normalized.append(name)
                seen.add(name)
    return normalized


@app.post("/evaluate")
def api_evaluate(
    body: Any = Body(default=None),
    k: int = Query(default=5),
    strategies: List[str] | None = Query(default=None),
    num_sims: int | None = Query(default=None),
):
    logger.info("Evaluation request received: k=%s strategies=%s num_sims=%s body_type=%s", k, strategies, num_sims, type(body).__name__)
    try:
        k = _coerce_int(k, 5)
        num_sims = _coerce_int(num_sims, 50)

        if isinstance(body, dict):
            config_payload = body.get("config", body)
            if not isinstance(config_payload, dict):
                raise HTTPException(status_code=400, detail="Invalid evaluation config payload")
            config = SimulationConfig.model_validate(config_payload)
            if body.get("k") is not None:
                k = _coerce_int(body["k"], k)
            if body.get("num_sims") is not None:
                num_sims = _coerce_int(body["num_sims"], num_sims)
            strategy_input = body.get("strategies")
        elif isinstance(body, SimulationConfig):
            config = body
            strategy_input = None
        else:
            config = SimulationConfig()
            strategy_input = None

        strategy_list = _normalize_strategy_names(strategies if strategies is not None else strategy_input)
        if not strategy_list:
            strategy_list = ["degree", "celf"]

        safe_num_sims = max(1, int(num_sims))
        results = run_evaluation_suite(config, k, strategies=strategy_list, num_sims=safe_num_sims)
        result_id = f"eval-{len(RESULT_STORE) + 1}"
        RESULT_STORE[result_id] = results
        return {"result_id": result_id, "results": results}
    except Exception as exc:
        logger.exception("Evaluation failed for config=%s k=%s strategies=%s num_sims=%s", getattr(body, 'get', lambda *_: body) if isinstance(body, dict) else body, k, strategies, num_sims)
        if isinstance(exc, HTTPException):
            raise
        raise HTTPException(status_code=500, detail=f"Evaluation failed: {exc}") from exc


@app.get("/results/{result_id}")
def api_results(result_id: str):
    if result_id not in RESULT_STORE:
        raise HTTPException(status_code=404, detail="Result not found")
    return RESULT_STORE[result_id]
