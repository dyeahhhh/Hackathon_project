import pytest
import networkx as nx
from fastapi.testclient import TestClient

from api.main import app
from simulation.models import SimulationConfig
from simulation.networks import generate_network
from strategies.baselines import strategy_highest_degree
from strategies.celf import strategy_celf, evaluate_spread

def test_celf_beats_degree_on_trap():
    config = SimulationConfig(
        network_type="trap",
        num_nodes=200, # Smaller network for fast testing
        beta=0.2,
        gamma=0.05,
        delta=0.0,
        seed=42,
        source_nodes=[0], # source is hub 0
        intervention_type="blocked"
    )
    
    G = generate_network(config)
    k = 3
    
    degree_nodes = strategy_highest_degree(G, k + 1)
    degree_nodes = [n for n in degree_nodes if n not in config.source_nodes][:k]
    if len(degree_nodes) < k:
        degree_nodes += [n for n in G.nodes() if n not in degree_nodes and n not in config.source_nodes][:k-len(degree_nodes)]
    
    # We use num_sims=30 for speed in testing
    celf_nodes = strategy_celf(G, k, config, num_sims=30)
    
    adj_matrix = nx.to_scipy_sparse_array(G, format="csr")
    
    # Evaluate with different seed to avoid leakage
    degree_spread = evaluate_spread(
        adj_matrix, 200, config.source_nodes, degree_nodes, config.intervention_type,
        config.beta, config.gamma, config.delta, num_sims=50, seed_offset=5000
    )
    
    celf_spread = evaluate_spread(
        adj_matrix, 200, config.source_nodes, celf_nodes, config.intervention_type,
        config.beta, config.gamma, config.delta, num_sims=50, seed_offset=5000
    )
    
    print(f"CELF nodes: {celf_nodes}, Spread: {celf_spread}")
    print(f"Degree nodes: {degree_nodes}, Spread: {degree_spread}")
    
    assert celf_spread < degree_spread, f"CELF spread {celf_spread} not less than Degree spread {degree_spread}"


def test_evaluate_route_accepts_wrapped_config_and_query_strategies():
    client = TestClient(app)
    config = {
        'network_type': 'campus',
        'num_nodes': 30,
        'beta': 0.2,
        'gamma': 0.08,
        'delta': 0.12,
        'seed': 42,
        'source_nodes': [0],
        'intervention_nodes': [5],
        'intervention_type': 'blocked',
        'max_steps': 20,
    }

    response = client.post(
        '/evaluate',
        json={'config': config, 'k': 3, 'strategies': ['degree', 'celf']},
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert 'results' in payload
    assert 'degree' in payload['results']
    assert 'celf' in payload['results']
