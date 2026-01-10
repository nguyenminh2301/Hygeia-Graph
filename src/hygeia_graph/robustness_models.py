"""Data structures for Robustness/Bootstrapping module."""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class BootnetSettings:
    n_boots_np: int = 200
    n_boots_case: int = 200
    n_cores: int = 1
    case_min: float = 0.05
    case_max: float = 0.75
    case_n: int = 10
    cor_level: float = 0.7


@dataclass
class BootnetCS:
    strength: Optional[float]
    expected_influence: Optional[float]


@dataclass
class BootnetMeta:
    status: str  # "success" | "failed"
    analysis_id: str
    settings: Dict[str, Any]
    cs_coefficient: Dict[str, Optional[float]]
    messages: List[Dict[str, Any]]
    outputs: Dict[str, str]
    computed_at: str


@dataclass
class RobustnessResult:
    meta: Dict[str, Any]  # Raw dict form of BootnetMeta
    tables: Dict[str, Any]  # DataFrames
    paths: Dict[str, str]
    process: Dict[str, Any]
