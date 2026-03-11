from pathlib import Path

_PROMPT_DIR = Path(__file__).resolve().parent


def _prompt_path(prompt_name: str) -> Path:
    name = prompt_name.strip()
    if not name:
        raise ValueError("Prompt name cannot be empty.")
    if not name.endswith(".md"):
        name = f"{name}.md"
    return _PROMPT_DIR / name


def load_prompt(prompt_name: str) -> str:
    """Load a prompt file from this package."""
    prompt_path = _prompt_path(prompt_name)
    try:
        return prompt_path.read_text(encoding="utf-8").strip()
    except FileNotFoundError as e:
        raise FileNotFoundError(f"Prompt file {prompt_path} not found.") from e


def update_prompt(prompt_name: str, prompt: str) -> None:
    """Update a prompt file in this package."""
    prompt_path = _prompt_path(prompt_name)
    if not prompt_path.exists():
        raise FileNotFoundError(f"Prompt file {prompt_path} not found.")
    prompt_path.write_text(prompt, encoding="utf-8")
