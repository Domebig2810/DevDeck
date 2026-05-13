import subprocess
import shlex
import sys


def run_command(command: str) -> tuple[bool, str]:
    """
    Execute a shell command and return (success, message).
    Returns immediately – does NOT block the UI.
    """
    command = command.strip()
    if not command:
        return False, "No command specified."

    try:
        if sys.platform == "win32":
            # On Windows use shell=True so paths with spaces and
            # built-in commands (e.g. 'start chrome') work out of the box.
            proc = subprocess.Popen(
                command,
                shell=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
            )
        else:
            # On macOS / Linux split into a proper argv list.
            proc = subprocess.Popen(
                shlex.split(command),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
            )

        # Give it up to 1 s to fail immediately (e.g. file-not-found).
        try:
            _, stderr = proc.communicate(timeout=1)
            if proc.returncode not in (0, None):
                return False, stderr.decode(errors="replace").strip() or f"Exit code {proc.returncode}"
        except subprocess.TimeoutExpired:
            # Still running after 1 s → that's fine, app is launching.
            pass

        return True, f"Started: {command}"

    except FileNotFoundError:
        return False, f"Command not found: {command.split()[0]}"
    except Exception as e:
        return False, str(e)