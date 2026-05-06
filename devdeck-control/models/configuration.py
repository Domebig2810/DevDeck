from dataclasses import dataclass
from typing import List


@dataclass
class Configuration:
    name: str
    buttons: List[str]
    images: List[str]
    pots: List[float]