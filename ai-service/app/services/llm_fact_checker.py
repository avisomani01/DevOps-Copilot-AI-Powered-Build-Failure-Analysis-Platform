"""Grounding checks for LLM output: catch claims the model made that aren't backed by
the actual source/log text it was given.

ollama_client.py's _validate_response only checks the LLM's reply has the right JSON
shape and field lengths - it never checks whether what the model *said* is actually
supported by the input. This module does that second check. It works by plain text
matching against the exact content the model was shown, so it needs no per-language
parser and works for logs and source code in any language.

What this catches:
  - A line number mentioned in the LLM's explanation that doesn't exist in the source
    it was given (a classic hallucination: "line 214" when the file has 40 lines).
  - A specific quoted identifier, filename, or error-message fragment the model claims
    is present, that never actually appears anywhere in the source/log text supplied.

What this does NOT catch (be honest about the limit):
  - Whether the model's *reasoning* about a real, correctly-cited line is actually
    correct. It only checks the claim is grounded in real text, not that the
    conclusion drawn from that text is right.
"""

from __future__ import annotations

import re

_LINE_REFERENCE = re.compile(r"\bline[s]?\s+(\d+)\b", re.IGNORECASE)
# Backtick-quoted or double-quoted tokens the model cites as if reading them off the
# source - e.g. `some_function`, "ModuleNotFoundError". Short/common words are ignored
# below since flagging those would just be noise, not a real hallucination signal.
_QUOTED_TOKEN = re.compile(r"[`\"]([A-Za-z_][A-Za-z0-9_.]{2,40})[`\"]")
_COMMON_WORDS = {
    "error", "warning", "true", "false", "none", "null", "self", "this", "return",
    "import", "class", "function", "def", "import", "error_category", "unknown",
}


def check_grounding(candidate: dict, source_content: str, log_content: str) -> dict:
    """Returns {"grounded": bool, "warnings": list[str]}. Never raises - a checker
    that can crash the enrichment path would be worse than no checker at all."""
    warnings: list[str] = []
    haystack = f"{source_content}\n{log_content}"
    total_lines = max(len(source_content.splitlines()), 1) if source_content else None

    text_fields = [candidate.get("summary", ""), candidate.get("root_cause", "")]
    text_fields.extend(candidate.get("suggested_fixes") or [])
    combined_text = "\n".join(str(field) for field in text_fields)

    if total_lines is not None:
        for match in _LINE_REFERENCE.finditer(combined_text):
            line_number = int(match.group(1))
            if line_number < 1 or line_number > total_lines:
                warnings.append(
                    f"Claims 'line {line_number}' but the supplied source only has {total_lines} line(s) - "
                    "likely a hallucinated line number."
                )

    for match in _QUOTED_TOKEN.finditer(combined_text):
        token = match.group(1)
        if token.lower() in _COMMON_WORDS or token.isdigit():
            continue
        if token not in haystack:
            warnings.append(f"References '{token}' which does not appear anywhere in the supplied source or log.")

    # De-duplicate while preserving order.
    seen: set[str] = set()
    unique_warnings = [w for w in warnings if not (w in seen or seen.add(w))]
    return {"grounded": len(unique_warnings) == 0, "warnings": unique_warnings[:5]}
