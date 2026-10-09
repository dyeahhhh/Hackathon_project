"""
Simulation engine for the Outbreak of Lies model.

States:
  0 = SUSCEPTIBLE
  1 = SPREADER
  2 = STIFLER
  3 = IMMUNE   (fact-checked, optionally a corrector)
  4 = BLOCKED  (removed from network)
"""
import numpy as np
from scipy.sparse import csr_matrix

from .models import NodeState

# ---------------------------------------------------------------------------
# Numba acceleration (optional). Falls back to pure NumPy if not installed.
# ---------------------------------------------------------------------------
_NUMBA_AVAILABLE = False
try:
    from numba import njit as _numba_njit
    _NUMBA_AVAILABLE = True
except ImportError:
    pass


def _pure_numpy_step(indptr, indices, data, states, beta, gamma, delta, rand_vals, num_nodes):
    """Pure-NumPy fallback for one discrete-time simulation step."""
    new_states = states.copy()
    rand_idx = 0

    for i in range(num_nodes):
        if states[i] != NodeState.SPREADER:
            continue

        start = indptr[i]
        end = indptr[i + 1]
        became_stifler = False

        for j_idx in range(start, end):
            if rand_idx >= len(rand_vals):
                break
            neighbor = indices[j_idx]
            if neighbor >= num_nodes:
                continue

            if states[neighbor] == NodeState.SUSCEPTIBLE:
                weight = float(data[j_idx])
                transmission_prob = beta * weight
                r = rand_vals[rand_idx]
                rand_idx += 1
                if r < transmission_prob:
                    new_states[neighbor] = NodeState.SPREADER
            elif states[neighbor] == NodeState.IMMUNE:
                r = rand_vals[rand_idx]
                rand_idx += 1
                if r < delta:
                    new_states[i] = NodeState.STIFLER
                    became_stifler = True
                    break

        if not became_stifler and new_states[i] != NodeState.STIFLER:
            if rand_idx < len(rand_vals):
                r = rand_vals[rand_idx]
                rand_idx += 1
                if r < gamma:
                    new_states[i] = NodeState.STIFLER

    return new_states, rand_idx


if _NUMBA_AVAILABLE:
    @_numba_njit(cache=True)
    def _simulate_step(indptr, indices, data, states, beta, gamma, delta, rand_vals, num_nodes):
        new_states = states.copy()
        rand_idx = 0
        for i in range(num_nodes):
            if states[i] != 1:
                continue

            start = indptr[i]
            end = indptr[i + 1]
            became_stifler = False

            for j_idx in range(start, end):
                if rand_idx >= len(rand_vals):
                    break
                neighbor = indices[j_idx]
                if neighbor >= num_nodes:
                    continue

                if states[neighbor] == 0:
                    weight = data[j_idx]
                    transmission_prob = beta * weight
                    r = rand_vals[rand_idx]
                    rand_idx += 1
                    if r < transmission_prob:
                        new_states[neighbor] = 1
                elif states[neighbor] == 3:
                    r = rand_vals[rand_idx]
                    rand_idx += 1
                    if r < delta:
                        new_states[i] = 2
                        became_stifler = True
                        break

            if not became_stifler and new_states[i] != 2:
                if rand_idx < len(rand_vals):
                    r = rand_vals[rand_idx]
                    rand_idx += 1
                    if r < gamma:
                        new_states[i] = 2

        return new_states, rand_idx
else:
    _simulate_step = _pure_numpy_step


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def run_simulation(
    adj_matrix: csr_matrix,
    initial_states: np.ndarray,
    beta: float,
    gamma: float,
    delta: float,
    max_steps: int = 100,
    seed: int = 42,
    edge_weights: np.ndarray | None = None,
    credulity: np.ndarray | None = None,
):
    """Run one stochastic simulation and return the full state history."""
    rng = np.random.default_rng(seed)
    num_nodes = adj_matrix.shape[0]
    states = initial_states.copy()
    history = [states.copy()]

    indptr = adj_matrix.indptr
    indices = adj_matrix.indices
    data = adj_matrix.data if edge_weights is None else edge_weights

    if credulity is None:
        credulity = np.ones(num_nodes, dtype=np.float64)
    if edge_weights is None:
        edge_weights = np.ones(adj_matrix.nnz, dtype=np.float64)

    for _ in range(max_steps):
        if not np.any(states == NodeState.SPREADER):
            break

        rand_vals = rng.random(adj_matrix.nnz + num_nodes)
        states, _ = _simulate_step(
            indptr,
            indices,
            data,
            states,
            beta,
            gamma,
            delta,
            rand_vals,
            num_nodes,
        )
        history.append(states.copy())

    return history


def initialize_states(
    num_nodes: int,
    source_nodes: list,
    intervention_nodes: list,
    intervention_type: str = "blocked",
) -> np.ndarray:
    """Build the initial state vector."""
    states = np.full(num_nodes, NodeState.SUSCEPTIBLE, dtype=np.int32)

    for v in intervention_nodes:
        if 0 <= v < num_nodes:
            if intervention_type == "blocked":
                states[v] = NodeState.BLOCKED
            elif intervention_type == "immune":
                states[v] = NodeState.IMMUNE

    for s in source_nodes:
        if 0 <= s < num_nodes:
            if states[s] not in (NodeState.BLOCKED, NodeState.IMMUNE):
                states[s] = NodeState.SPREADER

    return states
