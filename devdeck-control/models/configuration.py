from dataclasses import dataclass
from typing import List

NUM_BUTTONS = 6
NUM_POTS = 3


@dataclass
class ButtonConfig:
    label: str = ""
    command: str = ""
    image: str = ""
    display_mode: str = "label"  # "label" | "image"


@dataclass
class PotConfig:
    # Rotary value
    range_min: float = 0.0
    range_max: float = 100.0
    command: str = ""        # shell command; {value} replaced with scaled float at runtime

    # Click
    click_command: str = ""  # executed once on pot press


@dataclass
class Configuration:
    name: str
    buttons: List[ButtonConfig]
    pots: List[PotConfig]

    def __post_init__(self):
        migrated_buttons = []
        for b in self.buttons:
            if isinstance(b, dict):
                known = {k: v for k, v in b.items()
                         if k in ButtonConfig.__dataclass_fields__}
                migrated_buttons.append(ButtonConfig(**known))
            elif isinstance(b, ButtonConfig):
                migrated_buttons.append(b)
            else:
                migrated_buttons.append(ButtonConfig(label=str(b)))
        self.buttons = migrated_buttons

        migrated_pots = []
        for p in self.pots:
            if isinstance(p, dict):
                known = {k: v for k, v in p.items()
                         if k in PotConfig.__dataclass_fields__}
                migrated_pots.append(PotConfig(**known))
            elif isinstance(p, PotConfig):
                migrated_pots.append(p)
            else:
                migrated_pots.append(PotConfig())
        self.pots = migrated_pots