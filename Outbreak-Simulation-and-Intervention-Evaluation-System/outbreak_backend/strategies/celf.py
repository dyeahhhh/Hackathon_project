import heapq
from typing import Iterable, List

import networkx as nx
import numpy as np

from simulation.engine import initialize_states, run_simulation
from simulation.models import NodeState


def evaluate_spread(
    adj_matrix,
    num_nodes,
    source_nodes,
    interventions,
    intervention_type,
    beta,
    gamma,
    delta,
    num_sims=50,
    seed_offset=0,
):
    total_infected = 0
    for i in range(num_sims):
        states = initialize_states(num_nodes, source_nodes, interventions, intervention_type)
        history = run_simulation(adj_matrix, states, beta, gamma, delta, seed=2000 + seed_offset + i)
        final_state = history[-1]
        infected = np.sum((final_state == NodeState.SPREADER) | (final_state == NodeState.STIFLER))
        total_infected += infected
    return total_infected / num_sims


def strategy_celf(G: nx.Graph, k: int, config, num_sims: int = 30, seed_offset: int = 0) -> List[int]:
    if k <= 0:
        return []

    adj_matrix = nx.to_scipy_sparse_array(G, format="csr")
    num_nodes = G.number_of_nodes()
    blocked = set(config.source_nodes)

    degree_ranking = [n for n, _ in sorted(G.degree(), key=lambda x: (-x[1], x[0]))]
    betweenness = nx.betweenness_centrality(G)
    span = [n for n, _ in sorted(betweenness.items(), key=lambda x: (-x[1], x[0]))]
    candidates = []
    seen = set()
    for n in degree_ranking[: max(20, min(num_nodes, k * 12))] + span[: max(20, min(num_nodes, k * 12))]:
        if n not in blocked and n not in seen:
            candidates.append(n)
            seen.add(n)

    if not candidates:
        candidates = [n for n in G.nodes() if n not in blocked]

    base_spread = evaluate_spread(
        adj_matrix,
        num_nodes,
        config.source_nodes,
        [],
        config.intervention_type,
        config.beta,
        config.gamma,
        config.delta,
        num_sims=num_sims,
        seed_offset=seed_offset,
    )

    q: List[tuple[float, int]] = []
    for node in candidates:
        spread = evaluate_spread(
            adj_matrix,
            num_nodes,
            config.source_nodes,
            [node],
            config.intervention_type,
            config.beta,
            config.gamma,
            config.delta,
            num_sims=num_sims,
            seed_offset=seed_offset,
        )
        marginal_gain = base_spread - spread
        heapq.heappush(q, (-marginal_gain, node))

    selected: List[int] = []
    current_spread = base_spread

    for _ in range(k):
        if not q:
            break

        while q:
            neg_mg, node = heapq.heappop(q)
            gain = -neg_mg
            candidate_set = selected + [node]
            spread = evaluate_spread(
                adj_matrix,
                num_nodes,
                config.source_nodes,
                candidate_set,
                config.intervention_type,
                config.beta,
                config.gamma,
                config.delta,
                num_sims=num_sims,
                seed_offset=seed_offset,
            )
            new_gain = current_spread - spread
            if not q or new_gain >= -q[0][0]:
                selected.append(node)
                current_spread = spread
                break
            heapq.heappush(q, (-new_gain, node))

    if len(selected) < k:
        for node in G.nodes():
            if node not in blocked and node not in selected:
                selected.append(node)
                if len(selected) == k:
                    break

    return selected[:k]
