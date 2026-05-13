import shlex
import subprocess
import sys
from typing import Optional, Tuple


def run_command(command: str, value: Optional[float] = None) -> Tuple[bool, str]:
    """
    Execute a shell command, optionally replacing ``{value}`` with a number.

    Parameters
    ----------
    command:
        Shell command string. May contain ``{value}`` which will be replaced
        by the (already scaled) float before execution.
    value:
        Pre-scaled value to substitute into the command. Pass ``None`` for
        button commands that don't use a value.

    Returns
    -------
    (success, message)
    """
    command = command.strip()
    if not command:
        return False, "No command specified."

    if value is not None:
        # Format as integer if the result is a whole number, else 2 decimals
        formatted = str(int(value)) if value == int(value) else f"{value:.2f}"
        command = command.replace("{value}", formatted)

    try:
        if sys.platform == "win32":
            proc = subprocess.Popen(
                command,
                shell=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
            )
        else:
            proc = subprocess.Popen(
                shlex.split(command),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
            )

        try:
            _, stderr = proc.communicate(timeout=1)
            if proc.returncode not in (0, None):
                return False, stderr.decode(
                    errors="replace"
                ).strip() or f"Exit code {proc.returncode}"
        except subprocess.TimeoutExpired:
            pass  # still running → that's fine

        return True, f"Started: {command}"

    except FileNotFoundError:
        return False, f"Command not found: {command.split()[0]}"
    except Exception as e:
        return False, str(e)


def scale_value(
    raw: int, range_min: float, range_max: float, hw_min: int = 0, hw_max: int = 1023
) -> float:  # type: ignore[return]
    """
    Linearly scale a raw hardware value (default 0–1023) into
    [range_min, range_max].
    """
    if hw_max == hw_min:
        return range_min
    t = (raw - hw_min) / (hw_max - hw_min)
    t = max(0.0, min(1.0, t))
    return range_min + t * (range_max - range_min)
