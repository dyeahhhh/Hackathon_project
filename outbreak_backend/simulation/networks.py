import networkx as nx
import numpy as np


def _assign_edge_weights(G: nx.Graph, seed: int) -> nx.Graph:
    rng = np.random.default_rng(seed)
    for u, v in G.edges():
        G[u][v]["weight"] = float(np.clip(rng.uniform(0.35, 1.2), 0.1, 1.5))
    return G


def generate_network(config):
    seed = int(config.seed)
    np.random.seed(seed)
    n = max(10, int(config.num_nodes))

    if config.network_type == "ba":
        G = nx.barabasi_albert_graph(n, 4, seed=seed)
    elif config.network_type == "ws":
        G = nx.watts_strogatz_graph(n, k=6, p=0.14, seed=seed)
    elif config.network_type == "campus":
        groups = [n // 4, n // 4, n // 4, n - 3 * (n // 4)]
        if len(groups) != 4:
            groups = [max(4, n // 4), max(4, n // 4), max(4, n // 4), max(4, n - 3 * (n // 4))]
        probs = [
            [0.09, 0.008, 0.006, 0.004],
            [0.008, 0.09, 0.006, 0.004],
            [0.006, 0.006, 0.1, 0.01],
            [0.004, 0.004, 0.01, 0.08],
        ]
        G = nx.stochastic_block_model(groups, probs, seed=seed)
    elif config.network_type == "trap":
        cluster_a = max(12, int(n * 0.38))
        cluster_b = max(10, int(n * 0.28))
        cluster_c = n - cluster_a - cluster_b

        sizes = [cluster_a, cluster_b, cluster_c]
        probs = [
            [0.18, 0.002, 0.001],
            [0.002, 0.12, 0.01],
            [0.001, 0.01, 0.09],
        ]
        G = nx.stochastic_block_model(sizes, probs, seed=seed)

        dense_hub_nodes = list(range(min(8, cluster_a)))
        for hub in dense_hub_nodes:
            for v in range(cluster_a, min(cluster_a + 10, n)):
                if hub != v and np.random.rand() < 0.4:
                    G.add_edge(hub, v)

        bridge_1 = cluster_a - 1
        bridge_2 = cluster_a - 2
        bridge_3 = cluster_a + cluster_b - 1
        G.add_edge(bridge_1, cluster_a)
        G.add_edge(bridge_2, cluster_a + cluster_b)
        G.add_edge(bridge_3, cluster_a + cluster_b + 1)
        G.add_edge(0, bridge_1)
        G.add_edge(1, bridge_2)
        G.add_edge(2, bridge_3)

        # Create a small external bridge cluster to make degree-based selection fail
        bridge_cluster = [cluster_a + cluster_b + cluster_c - 1, cluster_a + cluster_b + cluster_c - 2]
        if len(bridge_cluster) >= 2:
            G.add_edge(bridge_cluster[0], bridge_cluster[1])
            G.add_edge(bridge_cluster[0], max(0, cluster_a - 1))
            G.add_edge(bridge_cluster[1], max(0, cluster_a - 2))
    else:
        G = nx.fast_gnp_random_graph(n, 0.02, seed=seed)

    if not G.is_directed():
        G = G.copy()
    G = _assign_edge_weights(G, seed)
    return G


def network_summary(G: nx.Graph):
    communities = list(nx.community.greedy_modularity_communities(G)) if G.number_of_nodes() > 0 else []
    density = nx.density(G)
    clustering = nx.average_clustering(G)
    return {
        "num_nodes": G.number_of_nodes(),
        "num_edges": G.number_of_edges(),
        "density": density,
        "average_clustering": clustering,
        "communities": len(communities),
        "largest_community_size": max((len(c) for c in communities), default=0),
    }
