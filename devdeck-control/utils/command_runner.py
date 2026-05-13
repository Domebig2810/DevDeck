import shlex
import subprocess
import sys
from typing import Optional, Tuple


def run_command(command: str, step: Optional[float] = None) -> Tuple[bool, str]:
    """
    Execute a shell command, optionally replacing ``{step}`` with the encoder step value.

    Parameters
    ----------
    command:
        Shell command string. May contain ``{step}`` which will be replaced
        by the formatted step float before execution.
    step:
        Step value to substitute. Pass ``None`` for commands that don't use it.

    Returns
    -------
    (success, message)
    """
    command = command.strip()
    if not command:
        return False, "No command specified."

    if step is not None:
        formatted = str(int(step)) if step == int(step) else f"{step:.2f}"
        command = command.replace("{step}", formatted)

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
                return False, stderr.decode(errors="replace").strip() or f"Exit code {proc.returncode}"
        except subprocess.TimeoutExpired:
            pass  # still running → fine

        return True, f"Started: {command}"

    except FileNotFoundError:
        return False, f"Command not found: {command.split()[0]}"
    except Exception as e:
        return False, str(e)