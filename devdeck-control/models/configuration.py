from dataclasses import dataclass
from typing import List


@dataclass
class ButtonConfig:
    label: str = ""
    command: str = ""
    image: str = ""
    display_mode: str = "label"  # "label" | "image"


@dataclass
class Configuration:
    name: str
    buttons: List[ButtonConfig]
    images: List[str]  # kept for legacy JSON compatibility
    pots: List[float]

    def __post_init__(self):
        migrated = []
        for b in self.buttons:
            if isinstance(b, dict):
                known = {
                    k: v for k, v in b.items() if k in ButtonConfig.__dataclass_fields__
                }
                migrated.append(ButtonConfig(**known))
            elif isinstance(b, ButtonConfig):
                migrated.append(b)
            else:
                migrated.append(ButtonConfig(label=str(b)))
        self.buttons = migrated
