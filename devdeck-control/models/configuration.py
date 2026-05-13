from dataclasses import dataclass
from typing import List

NUM_BUTTONS = 6
NUM_ENCODERS = 3


@dataclass
class ButtonConfig:
    label: str = ""
    command: str = ""
    image: str = ""
    display_mode: str = "label"  # "label" | "image"


@dataclass
class EncoderConfig:
    step: float = 1.0
    clockwise_command: str = ""  # {step} replaced at runtime
    counter_command: str = ""  # {step} replaced at runtime
    click_command: str = ""


@dataclass
class Configuration:
    name: str
    buttons: List[ButtonConfig]
    encoders: List[EncoderConfig]

    def __post_init__(self):
        migrated_buttons = []
        for b in self.buttons:
            if isinstance(b, dict):
                known = {
                    k: v for k, v in b.items() if k in ButtonConfig.__dataclass_fields__
                }
                migrated_buttons.append(ButtonConfig(**known))
            elif isinstance(b, ButtonConfig):
                migrated_buttons.append(b)
            else:
                migrated_buttons.append(ButtonConfig(label=str(b)))
        self.buttons = migrated_buttons

        migrated_encoders = []
        for e in self.encoders:
            if isinstance(e, dict):
                known = {
                    k: v
                    for k, v in e.items()
                    if k in EncoderConfig.__dataclass_fields__
                }
                migrated_encoders.append(EncoderConfig(**known))
            elif isinstance(e, EncoderConfig):
                migrated_encoders.append(e)
            else:
                migrated_encoders.append(EncoderConfig())
        self.encoders = migrated_encoders
