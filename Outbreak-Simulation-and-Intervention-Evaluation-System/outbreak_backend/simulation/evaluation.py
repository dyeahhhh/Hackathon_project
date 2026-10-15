import logging
import time
from typing import Any, Dict, List

import networkx as nx
import numpy as np
from scipy.stats import wilcoxon

from simulation.engine import initialize_states, run_simulation
from simulation.models import NodeState, SimulationConfig
from simulation.networks import generate_network
from strategies.baselines import (
    strategy_closeness,
    strategy_highest_betweenness,
    strategy_highest_degree,
    strategy_highest_pagerank,
    strategy_k_core,
    strategy_random,
)
from strategies.celf import strategy_celf

logger = logging.getLogger(__name__)

STRATEGY_MAP = {
    "random": strategy_random,
    "degree": strategy_highest_degree,
    "betweenness": strategy_highest_betweenness,
    "pagerank": strategy_highest_pagerank,
    "k_core": strategy_k_core,
    "closeness": strategy_closeness,
    "celf": strategy_celf,
}


def evaluate_strategy(
    G: nx.Graph,
    strategy_name: str,
    k: int,
    config: SimulationConfig,
    num_sims: int = 200,
    seed_offset: int = 0,
) -> Dict[str, Any]:
    start = time.time()

    if strategy_name == "none":
        selected_nodes = []
    elif strategy_name == "random":
        selected_nodes = strategy_random(G, k, seed=config.seed + seed_offset)
    elif strategy_name == "celf":
        selected_nodes = strategy_celf(G, k, config, num_sims=min(num_sims, 30), seed_offset=seed_offset)
    else:
        func = STRATEGY_MAP.get(strategy_name)
        if func is None:
            selected_nodes = []
        else:
            selected_nodes = func(G, k)

    selected_nodes = [n for n in selected_nodes if n not in config.source_nodes][:k]
    if len(selected_nodes) < k:
        for n in G.nodes():
            if n not in config.source_nodes and n not in selected_nodes:
                selected_nodes.append(n)
            if len(selected_nodes) == k:
                break

    selection_time = time.time() - start
    adj_matrix = nx.to_scipy_sparse_array(G, format="csr")
    num_nodes = G.number_of_nodes()

    spread_values = []
    peak_spreaders = []
    curve_matrix: List[List[int]] = []
    for i in range(num_sims):
        states = initialize_states(num_nodes, config.source_nodes, selected_nodes, config.intervention_type)
        history = run_simulation(
            adj_matrix,
            states,
            config.beta,
            config.gamma,
            config.delta,
            max_steps=config.max_steps,
            seed=10_000 + seed_offset + i,
        )
        infected_by_step = [
            int(np.sum((step == NodeState.SPREADER) | (step == NodeState.STIFLER)))
            for step in history
        ]
        curve_matrix.append(infected_by_step)

        final_state = history[-1]
        infected = int(np.sum((final_state == NodeState.SPREADER) | (final_state == NodeState.STIFLER)))
        spread_values.append(infected)
        peak_spreaders.append(max(np.sum(step == NodeState.SPREADER) for step in history))

    if not curve_matrix:
        curve_mean = np.zeros(0, dtype=float)
        curve_lower = np.zeros(0, dtype=float)
        curve_upper = np.zeros(0, dtype=float)
        curve_array = np.zeros((0, 0), dtype=float)
    else:
        max_len = max(len(row) for row in curve_matrix)
        padded_curve = []
        for row in curve_matrix:
            if len(row) < max_len:
                pad_value = row[-1] if row else 0
                row = row + [pad_value] * (max_len - len(row))
            padded_curve.append(row)
        curve_array = np.asarray(padded_curve, dtype=float)
        curve_mean = curve_array.mean(axis=0)
    curve_std = curve_array.std(axis=0, ddof=1 if curve_array.shape[0] > 1 else 0)
    ci_multiplier = 1.96
    curve_sem = curve_std / np.sqrt(curve_array.shape[0]) if curve_array.shape[0] > 0 else np.zeros_like(curve_mean)
    curve_lower = curve_mean - ci_multiplier * curve_sem
    curve_upper = curve_mean + ci_multiplier * curve_sem

    return {
        "strategy": strategy_name,
        "nodes": selected_nodes,
        "spreads": spread_values,
        "mean_spread": float(np.mean(spread_values)),
        "std_spread": float(np.std(spread_values)),
        "median_spread": float(np.median(spread_values)),
        "peak_spreaders_mean": float(np.mean(peak_spreaders)),
        "selection_time_sec": selection_time,
        "curve_mean": curve_mean.tolist(),
        "curve_lower": curve_lower.tolist(),
        "curve_upper": curve_upper.tolist(),
        "timeline_steps": list(range(len(curve_mean))),
    }


def run_evaluation_suite(
    config: SimulationConfig,
    k: int,
    strategies: List[str] = ["degree", "celf"],
    num_sims: int = 200,
) -> Dict[str, Dict[str, Any]]:
    G = generate_network(config)
    results: Dict[str, Dict[str, Any]] = {}
    safe_num_sims = max(1, int(num_sims))

    baseline = evaluate_strategy(G, "none", 0, config, num_sims=safe_num_sims)
    results["none"] = baseline

    for strat in strategies:
        strat_name = (strat or "").strip().lower()
        if not strat_name:
            continue
        if strat_name not in STRATEGY_MAP and strat_name != "none":
            logger.warning("Skipping unsupported strategy in evaluation: %s", strat_name)
            continue
        res = evaluate_strategy(G, strat_name, k, config, num_sims=safe_num_sims)
        reductions = np.array(baseline["spreads"], dtype=float) - np.array(res["spreads"], dtype=float)
        res["mean_reduction"] = float(np.mean(reductions))
        res["reduction_pct"] = float((res["mean_reduction"] / max(baseline["mean_spread"], 1e-9)) * 100.0)
        try:
            if np.allclose(baseline["spreads"], res["spreads"]):
                p_value = 1.0
            else:
                _, p_value = wilcoxon(baseline["spreads"], res["spreads"], zero_method="wilcox", alternative="two-sided")
        except ValueError:
            p_value = 1.0
        res["p_value_vs_none"] = float(p_value)
        results[strat_name] = res

    return results
