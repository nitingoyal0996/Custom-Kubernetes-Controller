# define types for local.py
from dataclasses import dataclass, MISSING
from typing import Any


@dataclass(init=True, frozen=True)
class Params():
    a: float
    b: float
    Kp: float
    Ki: float
    node_name: str
    data_path: str
    polling_interval: int = 15

    def __getattr__(self, name: str) -> Any:
        cli_name = f"--{name}".replace("_", "-")
        raise RuntimeError(f"Require argument {cli_name} not set")
