# --- Imports ---
import docker
from docker.errors import DockerException
from pathlib import Path
import subprocess
import os
from datetime import datetime
from zoneinfo import ZoneInfo
import logging

logger = logging.getLogger(__name__)

# --- Helper Functions ---

def _check_docker_running() -> tuple[bool, docker.DockerClient | None, str]:
    """Checks if the Docker daemon is running and returns client or error."""
    try:
        client = docker.from_env()
        client.ping()
        return True, client, "Docker daemon is running."
    except DockerException as e:
        error_msg = (
            f"Docker connection failed: {e}\n"
            "Please ensure Docker Desktop (or docker daemon) is running."
        )
        return False, None, error_msg
    except Exception as e:
        return False, None, f"Error checking Docker status: {e}"


# --- Tool Functions ---
# These functions are designed to be wrapped with @ai.tool decorator in main.py

def read_file(path: str) -> str:
    """Reads the content of a file at the given path relative to the current working directory.
    
    Args:
        path: The relative path to the file from the current working directory.
    
    Returns:
        The content of the file as a string, or an error message.
    """
    print(f"\n⚒️ Tool: Reading file: {path}")
    try:
        cwd = Path(os.getcwd())
        target_path = (cwd / path).resolve()
        if not target_path.is_relative_to(cwd):
            return "Error: Access denied. Path is outside the current working directory."
        if not target_path.is_file():
            return f"Error: File not found at {path}"
        return target_path.read_text()
    except Exception as e:
        return f"Error reading file: {e}"


def list_files(directory: str) -> str:
    """Lists files in the specified directory relative to the current working directory.
    
    Args:
        directory: The relative path to the directory to list.
    
    Returns:
        A newline-separated list of file names, or an error message.
    """
    print(f"\n⚒️ Tool: Listing files in directory: {directory}")
    try:
        cwd = Path(os.getcwd())
        target_dir = (cwd / directory).resolve()
        if not target_dir.is_relative_to(cwd):
            return "Error: Access denied. Path is outside the current working directory."
        if not target_dir.is_dir():
            return f"Error: Directory not found at {directory}"

        files = [f.name for f in target_dir.iterdir()]
        return "\n".join(files) if files else "No files found."
    except Exception as e:
        return f"Error listing files: {e}"


def edit_file(path: str, content: str) -> str:
    """Writes or overwrites content to a file at the given path relative to the current working directory.
    
    Args:
        path: The relative path to the file to write.
        content: The content to write to the file.
    
    Returns:
        A success message or an error message.
    """
    print(f"\n⚒️ Tool: Editing file: {path}")
    try:
        cwd = Path(os.getcwd())
        target_path = (cwd / path).resolve()
        if not target_path.is_relative_to(cwd):
            return "Error: Access denied. Path is outside the current working directory."

        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_text(content)
        return f"File '{path}' saved successfully."
    except Exception as e:
        return f"Error writing file: {e}"


def execute_bash_command(command: str) -> str:
    """Executes a whitelisted bash command in the current working directory.

    Allowed commands (including arguments):
    - ls ...
    - cat ...
    - git add ...
    - git status ...
    - git commit ...
    - git push ...
    - git branch ...
    - git worktree ...
    - git checkout ...
    - git merge ...
    - git pull ...
    - git fetch ...
    - git reset ...
    - git revert ...
    - grep ...
    - find ...
    - sed ...
    - awk ...
    - sort ...
    - uniq ...
    - wc ...
    - history ...
    - touch

    Args:
        command: The full bash command string to execute.

    Returns:
        The standard output and standard error of the command, or an error message.
    """
    print(f"\n⚒️ Tool: Executing bash command: {command}")

    whitelist = [
        "ls", "cat", "git add", "git status", "git commit", "git push",
        "git branch", "git worktree", "git checkout", "git merge",
        "git pull", "git fetch", "git reset", "git revert",
        "grep", "find", "sed", "awk", "sort", "uniq", "wc", "history", "touch"
    ]

    is_whitelisted = False
    for prefix in whitelist:
        if command.strip().startswith(prefix):
            is_whitelisted = True
            break

    if not is_whitelisted:
        return f"Error: Command '{command}' is not allowed. Only specific commands are permitted."

    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            cwd=os.getcwd(),
            check=False
        )
        if result.stdout:
            print(f"\n▶️ Command Output (stdout):\n{result.stdout.strip()}")
        output = f"--- stdout ---\n{result.stdout}\n--- stderr ---\n{result.stderr}"
        if result.returncode != 0:
            output += f"\n--- Command exited with code: {result.returncode} ---"
        return output.strip()

    except Exception as e:
        return f"Error executing command: {e}"


def run_in_sandbox(command: str, image: str = "python:3.12-slim", memory_limit: str = "512m") -> str:
    """Executes a command inside a sandboxed Docker container.

    The sandbox's cwd is the directory where the agent is run from.
    The project directory is mounted at /app.
    Network access is disabled for security.
    Resource limits (CPU, memory) are applied.

    Args:
        command: The command string to execute inside the container's /app directory.
        image: The Docker image to use. Defaults to 'python:3.12-slim'.
        memory_limit: Memory limit for the container. Defaults to '512m'.

    Returns:
        The combined stdout/stderr from the container, or an error message.
    """
    print(f"\n⚒️ Tool: Running in sandbox (Image: {image}): {command}")

    is_running, client, message = _check_docker_running()
    if not is_running:
        return f"Error: Cannot run sandbox. {message}"

    try:
        print(f"\n⏳ Starting Docker container (image: {image})...")
        container_output = client.containers.run(
            image=image,
            command=f"sh -c '{command}'",
            working_dir="/app",
            volumes={os.getcwd(): {'bind': '/app', 'mode': 'rw'}},
            remove=True,         # Remove container after execution
            network_mode='none', # Disable network access
            mem_limit=memory_limit,
            detach=False,        # Run in foreground
            stdout=True,         # Capture stdout
            stderr=True          # Capture stderr
        )
        output_str = container_output.decode('utf-8').strip()
        print(f"\n▶️ Sandbox Output:\n{output_str}")
        return f"--- Container Output ---\n{output_str}"

    except DockerException as e:
        error_msg = f"Docker error during sandbox execution: {e}"
        print(f"\n❌ {error_msg}")
        if "not found" in str(e).lower() or "no such image" in str(e).lower():
            error_msg += f"\nPlease ensure the image '{image}' exists locally or can be pulled."
        return f"Error: {error_msg}"
    except Exception as e:
        error_msg = f"Unexpected error during sandbox execution: {e}"
        print(f"\n❌ {error_msg}")
        return f"Error: {error_msg}"


def get_current_date_and_time(timezone: str = "America/Los_Angeles") -> str:
    """Returns the current date and time as ISO 8601 string in the specified timezone.

    Args:
        timezone: The timezone string (e.g., 'America/Los_Angeles', 'UTC').
                  Defaults to 'America/Los_Angeles' (PST) if invalid.

    Returns:
        The current date and time as an ISO 8601 string.
    """
    print(f"\n⚒️ Tool: Getting current date and time for timezone: {timezone}")
    try:
        tz = ZoneInfo(timezone)
    except Exception:
        print(f"Warning: Invalid timezone '{timezone}'. Using default: America/Los_Angeles")
        tz = ZoneInfo('America/Los_Angeles')
    now = datetime.now(tz)
    return now.isoformat()


def web_search(query: str, num_results: int = 10) -> str:
    """Search the web for information using a search engine.

    Note: This is a placeholder. In production, integrate with a search API
    like SerpAPI, Tavily, or similar.

    Args:
        query: The search query.
        num_results: The number of results to return.

    Returns:
        Search results as a formatted string.
    """
    print(f"\n⚒️ Tool: Web search for: {query}")
    # Placeholder - integrate with actual search API
    return f"Web search is not yet implemented. Query: '{query}', num_results: {num_results}"


def open_url(url: str) -> str:
    """Fetch and return the content of a URL.

    Note: This is a placeholder. In production, use requests or httpx.

    Args:
        url: The URL to fetch.

    Returns:
        The content of the URL or an error message.
    """
    print(f"\n⚒️ Tool: Opening URL: {url}")
    try:
        import requests
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        # Truncate if too long
        content = response.text
        if len(content) > 10000:
            content = content[:10000] + "\n... [truncated]"
        return content
    except Exception as e:
        return f"Error fetching URL: {e}"


# --- Tool Registry ---
# List of all available tool functions for registration with AI SDK
AVAILABLE_TOOLS = [
    read_file,
    list_files,
    edit_file,
    execute_bash_command,
    run_in_sandbox,
    get_current_date_and_time,
    web_search,
    open_url,
]