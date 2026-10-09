import numpy as np
import networkx as nx
import pytest
from simulation.models import SimulationConfig, NodeState
from simulation.networks import generate_network
from simulation.engine import run_simulation, initialize_states

def test_determinism():
    config = SimulationConfig(num_nodes=50, network_type="ba", seed=42)
    G = generate_network(config)
    adj_matrix = nx.to_scipy_sparse_array(G, format="csr")
    
    initial_states = initialize_states(50, [0], [])
    
    h1 = run_simulation(adj_matrix, initial_states, 0.5, 0.1, 0.0, 10, seed=123)
    h2 = run_simulation(adj_matrix, initial_states, 0.5, 0.1, 0.0, 10, seed=123)
    
    assert len(h1) == len(h2)
    for s1, s2 in zip(h1, h2):
        np.testing.assert_array_equal(s1, s2)

def test_blocked_nodes_do_not_get_infected():
    config = SimulationConfig(num_nodes=10, network_type="ba", seed=42)
    G = generate_network(config)
    adj_matrix = nx.to_scipy_sparse_array(G, format="csr")
    
    initial_states = initialize_states(10, [0], [1, 2, 3], intervention_type="blocked")
    
    history = run_simulation(adj_matrix, initial_states, 1.0, 0.0, 0.0, max_steps=5, seed=42)
    
    for state in history:
        assert state[1] == NodeState.BLOCKED
        assert state[2] == NodeState.BLOCKED
        assert state[3] == NodeState.BLOCKED

def test_immune_corrector():
    G = nx.Graph()
    G.add_nodes_from([0, 1, 2])
    G.add_edges_from([(0, 1), (1, 2)])
    adj_matrix = nx.to_scipy_sparse_array(G, format="csr")
    
    initial_states = initialize_states(3, [0], [1], intervention_type="immune")
    
    history = run_simulation(adj_matrix, initial_states, 1.0, 0.0, 1.0, max_steps=5, seed=42)
    
    final_state = history[-1]
    assert final_state[1] == NodeState.IMMUNE
    assert final_state[0] == NodeState.STIFLER
    assert final_state[2] == NodeState.SUSCEPTIBLE
