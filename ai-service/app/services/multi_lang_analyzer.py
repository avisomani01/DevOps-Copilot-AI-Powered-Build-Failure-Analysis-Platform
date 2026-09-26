"""Real syntax-level static analysis for non-Python languages, using tree-sitter.

static_analyzer.py listed 13 SOURCE_TYPES but only ever gave Python real parsing -
everything else fell back to naive bracket-matching. Tree-sitter ships an actual
grammar-based parser per language with built-in error recovery, so this module gives
JAVA, JAVASCRIPT, TYPESCRIPT, GO, RUST, C, CPP, CSHARP, PHP, and RUBY the same kind of
"this line has a real syntax error" detection Python already got from the ast module.

This catches syntax errors (a parser can't make sense of the structure) - it does NOT
catch semantic/runtime issues the way PythonRuntimeIssueFinder does for Python (no
"division by zero" or "undefined variable" checks here). Tree-sitter grammars don't
carry that kind of semantic knowledge, and building it per-language would need a real
type-checker per language, not a parser. Being honest about that limit here rather than
overclaiming it.
"""

from __future__ import annotations

from dataclasses import dataclass
from importlib import import_module

from tree_sitter import Language, Node, Parser

# Maps our SOURCE_TYPES names to the tree-sitter grammar package + attribute that
# exposes the compiled language. Each of these is a real, actively maintained grammar.
_GRAMMAR_MODULES: dict[str, tuple[str, str]] = {
    "JAVA": ("tree_sitter_java", "language"),
    "JAVASCRIPT": ("tree_sitter_javascript", "language"),
    "TYPESCRIPT": ("tree_sitter_typescript", "language_typescript"),
    "GO": ("tree_sitter_go", "language"),
    "RUST": ("tree_sitter_rust", "language"),
    "C": ("tree_sitter_c", "language"),
    "CPP": ("tree_sitter_cpp", "language"),
    "CSHARP": ("tree_sitter_c_sharp", "language"),
    "PHP": ("tree_sitter_php", "language_php"),
    "RUBY": ("tree_sitter_ruby", "language"),
}

_parser_cache: dict[str, Parser] = {}


def supported(source_type: str) -> bool:
    return source_type.upper() in _GRAMMAR_MODULES


def _get_parser(source_type: str) -> Parser | None:
    source = source_type.upper()
    if source in _parser_cache:
        return _parser_cache[source]
    mapping = _GRAMMAR_MODULES.get(source)
    if not mapping:
        return None
    module_name, attribute = mapping
    try:
        module = import_module(module_name)
        language = Language(getattr(module, attribute)())
    except Exception:
        # Grammar package missing or failed to load - caller falls back to bracket
        # matching rather than the request failing outright.
        return None
    parser = Parser(language)
    _parser_cache[source] = parser
    return parser


@dataclass
class SyntaxIssue:
    line: int
    message: str


def _collect_errors(node: Node, issues: list[SyntaxIssue], limit: int = 12) -> None:
    if len(issues) >= limit:
        return
    if node.is_missing:
        issues.append(SyntaxIssue(node.start_point[0] + 1, f"Expected '{node.type}' here but it is missing."))
    elif node.type == "ERROR":
        start_line = node.start_point[0] + 1
        end_line = node.end_point[0] + 1
        text = node.text.decode("utf-8", errors="replace").strip().splitlines()
        snippet = text[0][:60] if text else ""
        if end_line > start_line + 1:
            # Tree-sitter's error recovery sometimes spans many lines when it can't
            # pinpoint the break - report the honest range instead of a falsely
            # precise single line.
            location = f"somewhere between lines {start_line} and {end_line}"
        else:
            location = f"line {start_line}"
        message = f"Syntax error {location}" + (f", near '{snippet}'." if snippet else ".")
        issues.append(SyntaxIssue(start_line, message))
    for child in node.children:
        if len(issues) >= limit:
            return
        _collect_errors(child, issues, limit)


def analyze(content: str, source_type: str) -> list[SyntaxIssue] | None:
    """Returns a list of syntax issues (empty list = parsed cleanly), or None if this
    language has no tree-sitter grammar available and the caller should fall back."""
    parser = _get_parser(source_type)
    if parser is None:
        return None
    tree = parser.parse(content.encode("utf-8", errors="replace"))
    if not tree.root_node.has_error:
        return []
    issues: list[SyntaxIssue] = []
    _collect_errors(tree.root_node, issues)
    # De-duplicate same-line messages and keep them in source order.
    seen: set[tuple[int, str]] = set()
    unique: list[SyntaxIssue] = []
    for issue in issues:
        key = (issue.line, issue.message)
        if key not in seen:
            seen.add(key)
            unique.append(issue)
    return unique
