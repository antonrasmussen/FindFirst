"""Chronicle engine: evolving markdown timeline maintained by LLM."""

from pathlib import Path
from typing import Callable

CHRONICLE_TEMPLATE = """# Alert Chronicle

A living timeline of topics from Google Alerts. Entries are organized by topic and date.

"""


def load_chronicle(path: Path) -> str:
  """Read current Chronicle content, or return empty template if file does not exist."""
  if not path.exists():
    return CHRONICLE_TEMPLATE
  return path.read_text(encoding="utf-8")


def update_chronicle(
    path: Path,
    new_context: str,
    llm_client: Callable[[str, str | None], str],
    *,
    date_str: str | None = None,
) -> str:
  """
  Given today's RAG-retrieved context, call the LLM to produce an updated Chronicle
  that appends/revises sections without losing prior narrative.
  Returns the updated Chronicle content.
  """
  from datetime import datetime

  current = load_chronicle(path)
  date_str = date_str or datetime.utcnow().date().isoformat()

  system = """You maintain an Alert Chronicle: a markdown timeline of topics from Google Alerts.
Your task: update the Chronicle by incorporating the new context below.

Rules:
- Preserve ALL existing content. Do not remove or shorten prior entries.
- Append new date entries under the appropriate topic heading (## Topic Name).
- If a topic does not exist, create a new ## heading for it.
- Each date entry should be a brief bullet or paragraph summarizing the new developments.
- Note any emerging trends or patterns when relevant.
- Keep entries concise (1-3 sentences per date).
- Output the COMPLETE updated Chronicle, not a diff."""

  user = f"""Today's date: {date_str}

New context to incorporate:
---
{new_context}
---

Current Chronicle:
---
{current}
---

Output the complete updated Chronicle:"""

  updated = llm_client(user, system)
  path.parent.mkdir(parents=True, exist_ok=True)
  path.write_text(updated, encoding="utf-8")
  return updated


def create_openai_llm_client(
    api_key: str,
    model: str = "gpt-4o-mini",
) -> Callable[[str, str | None], str]:
  """Create an LLM client that uses OpenAI's chat API."""

  def _call(user: str, system: str | None) -> str:
    from openai import OpenAI

    client = OpenAI(api_key=api_key)
    messages = []
    if system:
      messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": user})
    resp = client.chat.completions.create(model=model, messages=messages)
    return resp.choices[0].message.content or ""

  return _call
