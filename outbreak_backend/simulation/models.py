from enum import IntEnum
from typing import List

from pydantic import BaseModel, Field


class NodeState(IntEnum):
    SUSCEPTIBLE = 0
    SPREADER = 1
    STIFLER = 2
    IMMUNE = 3
    BLOCKED = 4


class SimulationConfig(BaseModel):
    network_type: str = "campus"
    num_nodes: int = 500
    beta: float = 0.18
    gamma: float = 0.06
    delta: float = 0.12
    seed: int = 42
    source_nodes: List[int] = Field(default_factory=list)
    intervention_nodes: List[int] = Field(default_factory=list)
    intervention_type: str = "blocked"  # "blocked" or "immune"
    edge_weight_scale: float = 1.0
    credulity_scale: float = 1.0
    max_steps: int = 50

    model_config = {
        "arbitrary_types_allowed": True,
    }

    @property
    def normalized_intervention_type(self) -> str:
        value = (self.intervention_type or "blocked").lower()
        return value if value in {"blocked", "immune"} else "blocked"
