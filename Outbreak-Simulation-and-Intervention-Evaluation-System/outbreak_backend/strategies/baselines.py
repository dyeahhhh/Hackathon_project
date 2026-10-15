import random
from typing import List

import networkx as nx
import numpy as np


def strategy_random(G: nx.Graph, k: int, seed: int = 42) -> List[int]:
    rng = random.Random(seed)
    nodes = list(G.nodes())
    rng.shuffle(nodes)
    return nodes[:k]


def strategy_highest_degree(G: nx.Graph, k: int) -> List[int]:
    return [n for n, _ in sorted(G.degree(), key=lambda item: (-item[1], item[0]))[:k]]


def strategy_highest_betweenness(G: nx.Graph, k: int) -> List[int]:
    scores = nx.betweenness_centrality(G)
    return [n for n, _ in sorted(scores.items(), key=lambda item: (-item[1], item[0]))[:k]]


def strategy_highest_pagerank(G: nx.Graph, k: int) -> List[int]:
    scores = nx.pagerank(G)
    return [n for n, _ in sorted(scores.items(), key=lambda item: (-item[1], item[0]))[:k]]


def strategy_k_core(G: nx.Graph, k: int) -> List[int]:
    core = nx.core_number(G)
    deg = dict(G.degree())
    ranked = sorted(G.nodes(), key=lambda n: (core[n], deg[n], n), reverse=True)
    return ranked[:k]


def strategy_closeness(G: nx.Graph, k: int) -> List[int]:
    scores = nx.closeness_centrality(G)
    return [n for n, _ in sorted(scores.items(), key=lambda item: (-item[1], item[0]))[:k]]
