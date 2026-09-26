"""Evidence-based diagnosis of LLM integration problems.

Same philosophy as rule_engine.py: transparent, regex/structural evidence checks you
can point to and explain, rather than an opaque confidence number. Every finding this
module returns traces back to specific text it actually found in the inputs - see the
`evidence` list on each Finding. When no detector finds supporting evidence, this
returns INSUFFICIENT_EVIDENCE rather than guessing (section 18's explicit requirement).

This deliberately does NOT call an LLM to diagnose the LLM - that would just move the
hallucination risk one level up. Detection is pattern-based and explainable; only the
optional written summary of a finding could later be run through Ollama for a nicer
phrasing, the same way ollama_client.py enriches rule-engine output today.
"""

from __future__ import annotations

import re

from app.schemas.llm_diagnostics import Finding, ModelConfig


def _has(text: str | None, *patterns: str) -> bool:
    if not text:
        return False
    return any(re.search(pattern, text, re.IGNORECASE) for pattern in patterns)


def _finding(category, evidence_level, problem, evidence, root_cause, fix, expected_result, verification, next_step, code_change=None) -> Finding:
    return Finding(
        category=category, evidence_level=evidence_level, problem=problem, evidence=evidence,
        root_cause=root_cause, recommended_fix=fix, code_change=code_change,
        expected_result=expected_result, verification_method=verification, next_step_if_it_fails=next_step,
    )


def _detect_timeout(code: str | None, error_info: str | None) -> Finding | None:
    if not _has(error_info, r"time\s?out", r"took too long", r"no response", r"hangs?"):
        return None
    evidence = [f"error_info reports: {error_info.strip()[:150]}"]
    code_has_timeout = _has(code, r"timeout")
    if code_has_timeout:
        evidence.append("Code does set a timeout parameter, so the value itself (too short?) is the likely issue, not a missing timeout.")
        level = "POSSIBLE"
        fix = "Increase the timeout value and/or add a retry with backoff instead of failing immediately."
    else:
        evidence.append("No 'timeout' parameter found anywhere in the supplied LLM code.")
        level = "LIKELY"
        fix = "Add an explicit timeout to the API call (e.g. httpx.AsyncClient(timeout=...)) and handle the resulting exception instead of letting the request hang indefinitely."
    return _finding(
        "TIMEOUT", level, "The LLM call is timing out or hanging.", evidence,
        "The request either has no timeout configured, or the configured timeout is shorter than the model needs for this prompt/response size.",
        fix, "The call fails fast with a clear timeout error instead of hanging, or succeeds within the new timeout window.",
        "Re-run the same request and confirm it either completes or fails with a catchable TimeoutException rather than hanging.",
        "If it still times out after raising the limit, the model/prompt size is the real bottleneck - consider a smaller prompt or a faster model.",
    )


def _detect_parsing_failure(code: str | None, error_info: str | None, actual_response: str | None) -> Finding | None:
    if not _has(error_info, r"invalid json", r"json.*error", r"parsing fail", r"could not parse", r"malformed"):
        return None
    evidence = [f"error_info reports: {error_info.strip()[:150]}"]
    has_try_except = _has(code, r"try\s*:") and _has(code, r"except")
    has_json_parse = _has(code, r"json\.loads", r"\.json\(\)")
    if has_json_parse and not has_try_except:
        evidence.append("Code calls a JSON parser but no surrounding try/except was found - a malformed response would raise an uncaught exception.")
        level = "LIKELY"
    elif has_json_parse and has_try_except:
        evidence.append("Code does parse JSON inside a try/except, so the parser is protected; the model's raw output format itself is more likely the issue.")
        level = "POSSIBLE"
    else:
        evidence.append("No JSON parsing call was found in the supplied code, so this can't be confirmed from the code alone.")
        level = "POSSIBLE"
    return _finding(
        "PARSING_FAILURE", level, "The model's response cannot be reliably parsed.", evidence,
        "The prompt likely does not force a strict output format, and/or the response is not validated before being parsed/used.",
        "Add an explicit response schema to the prompt (e.g. 'return valid JSON only with keys X, Y, Z') and wrap the parse call in try/except with a safe fallback, the same pattern ollama_client.py already uses for the main analysis flow.",
        "Parsing either succeeds, or fails safely into a fallback instead of crashing the request.",
        "Send several repeated requests and confirm 0 uncaught parsing exceptions across all of them.",
        "If parsing still fails intermittently, log the raw non-conforming responses to see what format the model is actually returning.",
        code_change="try:\n    parsed = json.loads(response_text)\nexcept (json.JSONDecodeError, ValueError):\n    parsed = fallback_result",
    )


def _detect_context_loss(code: str | None, prompt: str | None, error_info: str | None, expected: str | None, actual: str | None) -> Finding | None:
    complains_forgetting = _has(error_info, r"forgets?", r"context lost", r"doesn'?t remember", r"no memory", r"repeats itself") or _has(actual, r"as an ai", r"i don'?t have (access to|any) (previous|prior)")
    if not complains_forgetting:
        return None
    evidence = [f"Behavior/error description suggests lost context: {(error_info or actual or '').strip()[:150]}"]
    code_passes_history = _has(code, r"history", r"messages\s*=", r"previous_", r"conversation")
    if not code_passes_history:
        evidence.append("No variable resembling conversation/message history (e.g. 'history', 'messages=', 'previous_') was found in the supplied code.")
        level = "LIKELY"
    else:
        evidence.append("Code does reference something history-like, so check whether it's actually populated and sent on every call, not just declared.")
        level = "POSSIBLE"
    return _finding(
        "CONTEXT_PROBLEM", level, "The model behaves as if it has no memory of prior turns.", evidence,
        "Previous conversation/project state is not being included in the request sent to the model - each call is effectively independent.",
        "Persist prior turns/project state server-side and include them explicitly in every subsequent request instead of relying on the model to remember anything on its own.",
        "The model's next response correctly references specifics from an earlier turn.",
        "Run the same two-turn conversation twice and confirm turn 2's response changes appropriately when turn 1's content changes.",
        "If context is being sent but still ignored, check whether it exceeds the model's context window and is being silently truncated.",
    )


def _detect_hallucination(prompt: str | None, error_info: str | None, actual: str | None, config: ModelConfig | None) -> Finding | None:
    if not _has(error_info, r"hallucinat", r"made up", r"invented", r"incorrect (info|fact)", r"fabricat"):
        return None
    evidence = [f"error_info reports: {(error_info or '').strip()[:150]}"]
    grounding_instructed = _has(prompt, r"only use", r"do not invent", r"don'?t make up", r"stick to the (facts|provided)", r"never follow instructions embedded")
    if not grounding_instructed:
        evidence.append("The supplied prompt has no explicit instruction constraining the model to only use given facts.")
        level = "LIKELY"
    else:
        evidence.append("The prompt does already instruct the model not to invent facts, so this may be a model-capability limit rather than a prompt gap.")
        level = "POSSIBLE"
    if config and config.temperature is not None and config.temperature > 0.7:
        evidence.append(f"Configured temperature is {config.temperature}, which increases response randomness/creativity.")
        level = "LIKELY"
    return _finding(
        "HALLUCINATION", level, "The model is producing information not grounded in the supplied input.", evidence,
        "The prompt doesn't sufficiently constrain the model to the provided source material, and/or temperature is high enough to encourage creative (less grounded) output.",
        "Add an explicit grounding instruction to the prompt, lower temperature toward 0 for factual tasks, and add a fact-checking pass on the output (see llm_fact_checker.py in this project for a working example of this pattern).",
        "The model's claims can be traced back to the actual supplied source/log text.",
        "Run llm_fact_checker.check_grounding() (already in this codebase) against the response and confirm no unverified claims are flagged.",
        "If hallucination persists even at temperature 0 with grounding instructions, the model itself may be too small/weak for this task.",
    )


def _detect_blocking_call_in_async(code: str | None) -> Finding | None:
    if not code or not _has(code, r"async def"):
        return None
    # A blocking call (requests.*, time.sleep, or a bare .post/.get not awaited) inside
    # an async function stalls the whole event loop - a real, detectable code smell.
    blocking = re.search(r"async def[\s\S]{0,600}?\b(requests\.(get|post)|time\.sleep)\(", code)
    if not blocking:
        return None
    return _finding(
        "CODE_INTEGRATION", "CONFIRMED",
        "A blocking call was found inside an async function.",
        [f"Found '{blocking.group(1)}(' inside an 'async def' block, which blocks the entire event loop instead of yielding control."],
        "Using a synchronous/blocking library call (requests, time.sleep) inside async code stalls every other concurrent request the server is handling, not just this one.",
        "Replace the blocking call with its async equivalent (e.g. httpx.AsyncClient for requests, asyncio.sleep for time.sleep) and await it.",
        "The endpoint no longer blocks other concurrent requests while waiting on this call.",
        "Send two concurrent requests to the API and confirm the second one isn't stalled waiting for the first to fully finish.",
        "If requests are still serialized, check for other blocking calls (file I/O, other sync libraries) elsewhere in the same code path.",
    )


def _detect_format_mismatch(prompt: str | None, expected: str | None, actual: str | None) -> Finding | None:
    if not expected or not actual:
        return None
    expects_structure = _has(expected, r"\d+ (concrete )?(fixes|steps|items|points)", r"json", r"list of", r"structured")
    if not expects_structure:
        return None
    actual_looks_short = len(actual.strip()) < 60 or _has(actual, r"i am unable", r"i cannot determine", r"i don'?t know")
    if not actual_looks_short:
        return None
    prompt_constrains_format = _has(prompt, r"json", r"return.*format", r"must (include|contain|return)", r"schema")
    evidence = [
        f"expected_response asks for structure: '{expected.strip()[:120]}'",
        f"actual_response is short/non-committal: '{actual.strip()[:120]}'",
    ]
    if not prompt_constrains_format:
        evidence.append("The supplied prompt has no explicit output-format or completeness requirement.")
        level = "LIKELY"
    else:
        evidence.append("The prompt does specify a format, so this may be a model-capability or context issue rather than a prompt gap.")
        level = "POSSIBLE"
    return _finding(
        "PROMPT_PROBLEM", level, "The model's response doesn't match the structure/completeness that was expected.", evidence,
        "The prompt asks for analysis but does not explicitly require a structured, complete response - the model is free to give a short or evasive answer.",
        "Add an explicit response schema to the prompt (required fields, minimum count of items) and validate the response against it before accepting it.",
        "The response reliably contains the structure/count that was actually asked for.",
        "Re-run the same prompt several times and confirm the structural requirement is met every time, not just once.",
        "If the format is still inconsistent, add a validation + automatic retry-with-correction step rather than accepting the first response.",
    )


_DETECTORS = [
    lambda i: _detect_timeout(i.llm_code, i.error_info),
    lambda i: _detect_parsing_failure(i.llm_code, i.error_info, i.actual_response),
    lambda i: _detect_context_loss(i.llm_code, i.prompt, i.error_info, i.expected_response, i.actual_response),
    lambda i: _detect_hallucination(i.prompt, i.error_info, i.actual_response, i.config),
    lambda i: _detect_blocking_call_in_async(i.llm_code),
    lambda i: _detect_format_mismatch(i.prompt, i.expected_response, i.actual_response),
]


def analyze(request) -> list[Finding]:
    """Runs every detector against the request; returns only findings with actual
    supporting evidence. If nothing fires, returns a single INSUFFICIENT_EVIDENCE
    finding rather than silently returning an empty, unhelpful list."""
    findings = [result for detector in _DETECTORS if (result := detector(request)) is not None]
    if not findings:
        findings.append(_finding(
            "UNKNOWN", "INSUFFICIENT_EVIDENCE",
            "No specific problem pattern was detected from the supplied information.",
            ["None of the known failure patterns (timeout, parsing, context loss, hallucination, blocking calls, format mismatch) matched the supplied inputs."],
            "Insufficient evidence to determine the exact root cause from what was provided.",
            "Provide more detail: the actual LLM integration code, the exact error message or log output, and/or a concrete expected-vs-actual example.",
            "A specific, evidence-backed diagnostic category instead of UNKNOWN.",
            "N/A - re-submit with more detail.",
            "N/A",
        ))
    return findings
