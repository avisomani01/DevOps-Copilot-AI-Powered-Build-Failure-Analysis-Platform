"""Lightweight static checks for source files sent to the log-analysis endpoint."""

import ast
import builtins
import hashlib
import re

from app.services import multi_lang_analyzer


SOURCE_TYPES = {"PYTHON", "JAVA", "JAVASCRIPT", "TYPESCRIPT", "GO", "RUST", "C", "CPP", "CSHARP", "PHP", "RUBY", "SWIFT", "KOTLIN"}


def _result(category: str, confidence: float, summary: str, root_cause: str, errors: list[str], fixes: list[str]) -> dict:
    key = errors[0] if errors else summary
    return {
        "error_category": category,
        "confidence_score": confidence,
        "summary": summary,
        "root_cause": root_cause,
        "extracted_errors": errors,
        "suggested_fixes": fixes,
        "fingerprint": hashlib.sha256(f"{category}:{key.lower()}".encode()).hexdigest(),
        "analyzer_type": "STATIC",
        "llm_enrichment_applied": False,
    }


def _delimiter_error(content: str) -> str | None:
    pairs = {")": "(", "]": "[", "}": "{"}
    opening = set(pairs.values())
    stack: list[tuple[str, int]] = []
    quote: str | None = None
    escaped = False
    for number, character in enumerate(content, start=1):
        if quote:
            if escaped:
                escaped = False
            elif character == "\\":
                escaped = True
            elif character == quote:
                quote = None
            continue
        if character in {"'", '"', "`"}:
            quote = character
        elif character in opening:
            stack.append((character, number))
        elif character in pairs:
            if not stack or stack[-1][0] != pairs[character]:
                return f"Unexpected '{character}' near character {number}."
            stack.pop()
    if quote:
        return f"Unclosed {quote} string literal."
    if stack:
        character, number = stack[-1]
        return f"Unclosed '{character}' opened near character {number}."
    return None


class PythonRuntimeIssueFinder(ast.NodeVisitor):
    """Find high-confidence Python runtime blockers without executing user code."""

    def __init__(self) -> None:
        self.issues: list[str] = []
        self._scopes: list[set[str]] = [set(dir(builtins))]

    @property
    def _known(self) -> set[str]:
        return set().union(*self._scopes)

    @staticmethod
    def _bound_names(nodes: list[ast.stmt]) -> set[str]:
        names: set[str] = set()
        for node in nodes:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                names.add(node.name)
            elif isinstance(node, (ast.Import, ast.ImportFrom)):
                for alias in node.names:
                    names.add(alias.asname or alias.name.split(".")[0])
            elif isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign, ast.For, ast.AsyncFor, ast.With, ast.AsyncWith)):
                targets = node.targets if isinstance(node, ast.Assign) else [node.target] if hasattr(node, "target") else []
                for target in targets:
                    names.update(PythonRuntimeIssueFinder._target_names(target))
        return names

    @staticmethod
    def _target_names(target: ast.AST) -> set[str]:
        if isinstance(target, ast.Name):
            return {target.id}
        if isinstance(target, (ast.Tuple, ast.List)):
            return set().union(*(PythonRuntimeIssueFinder._target_names(item) for item in target.elts))
        return set()

    def visit_Module(self, node: ast.Module) -> None:
        self._scopes[-1].update(self._bound_names(node.body))
        self.generic_visit(node)

    def _visit_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        arguments = {argument.arg for argument in (*node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs)}
        if node.args.vararg:
            arguments.add(node.args.vararg.arg)
        if node.args.kwarg:
            arguments.add(node.args.kwarg.arg)
        self._scopes.append(arguments | self._bound_names(node.body))
        for statement in node.body:
            self.visit(statement)
        self._scopes.pop()
        for expression in (child for child in ast.walk(node) if isinstance(child, ast.Expr)):
            calls_self = any(
                isinstance(call.func, ast.Name) and call.func.id == node.name
                for call in ast.walk(expression.value)
                if isinstance(call, ast.Call)
            )
            if calls_self:
                self.issues.append(
                    f"Line {expression.lineno}: recursive result is calculated but not returned; add 'return'."
                )

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._visit_function(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._visit_function(node)

    def visit_Name(self, node: ast.Name) -> None:
        if isinstance(node.ctx, ast.Load) and node.id not in self._known:
            self.issues.append(f"Line {node.lineno}: '{node.id}' is used but is not defined.")

    def visit_BinOp(self, node: ast.BinOp) -> None:
        if isinstance(node.op, (ast.Div, ast.FloorDiv, ast.Mod)) and isinstance(node.right, ast.Constant) and node.right.value == 0:
            self.issues.append(f"Line {node.lineno}: division or modulo by zero will raise ZeroDivisionError.")
        if isinstance(node.left, ast.Constant) and isinstance(node.right, ast.Constant):
            left, right = node.left.value, node.right.value
            if isinstance(node.op, ast.Add) and type(left) is not type(right) and not ({type(left), type(right)} <= {int, float, complex}):
                self.issues.append(f"Line {node.lineno}: cannot add {type(left).__name__} and {type(right).__name__} values.")
        self.generic_visit(node)

    def visit_Subscript(self, node: ast.Subscript) -> None:
        if isinstance(node.slice, ast.Constant):
            try:
                value = ast.literal_eval(node.value)
                index = node.slice.value
                if isinstance(value, (str, tuple, list)) and isinstance(index, int) and not -len(value) <= index < len(value):
                    self.issues.append(f"Line {node.lineno}: index {index} is outside this literal sequence and will raise IndexError.")
                if isinstance(value, dict) and index not in value:
                    self.issues.append(f"Line {node.lineno}: key {index!r} is absent from this literal dictionary and will raise KeyError.")
            except (ValueError, TypeError, MemoryError):
                pass
        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute) -> None:
        if isinstance(node.value, ast.Constant) and node.value.value is None:
            self.issues.append(f"Line {node.lineno}: accessing '.{node.attr}' on None will raise AttributeError.")
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        if isinstance(node.func, ast.Name) and node.func.id in {"int", "float"} and len(node.args) == 1 and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str):
            try:
                (int if node.func.id == "int" else float)(node.args[0].value)
            except ValueError:
                self.issues.append(f"Line {node.lineno}: {node.func.id}({node.args[0].value!r}) will raise ValueError.")
        if isinstance(node.func, ast.Name) and node.func.id == "len" and len(node.args) == 1 and isinstance(node.args[0], ast.Constant) and not hasattr(node.args[0].value, "__len__"):
            self.issues.append(f"Line {node.lineno}: len() cannot be used with {type(node.args[0].value).__name__} and will raise TypeError.")
        self.generic_visit(node)


def analyze_source_code(content: str, source_type: str) -> dict | None:
    source = source_type.upper()
    if source not in SOURCE_TYPES:
        return None
    if source == "PYTHON":
        try:
            tree = ast.parse(content)
        except SyntaxError as error:
            line = error.lineno or "unknown"
            detail = error.msg or "Invalid Python syntax"
            return _result("CODE_SYNTAX", 98, "Python syntax error found.", f"Line {line}: {detail}.", [f"Line {line}: {detail}"], ["Fix the syntax at the reported line.", "Check brackets, quotes, indentation, and colons near that line."])
        finder = PythonRuntimeIssueFinder()
        finder.visit(tree)
        if finder.issues:
            issues = list(dict.fromkeys(finder.issues))[:12]
            return _result("PYTHON_STATIC_ERROR", 92, "Potential Python runtime error found.", "The static scan found code that will fail or produce an incorrect result when that path runs.", issues, ["Define the missing name, import it, or correct the spelling.", "Return values produced by recursive calculations instead of discarding them.", "Correct the reported literal operation, index, key, or conversion before running the program."])
    if multi_lang_analyzer.supported(source):
        issues = multi_lang_analyzer.analyze(content, source)
        if issues is not None:
            if not issues:
                return _result("CODE_REVIEW", 85, f"{source.replace('_', ' ').title()} source parsed with no syntax errors.", "No syntax issue was found by the grammar-based parser. Runtime, type, dependency, and framework errors still require build output or a language-specific compiler.", [], ["Run the language compiler, linter, or test suite for deeper checks.", "Upload any resulting error output for root-cause analysis."])
            formatted = [issue.message[0].upper() + issue.message[1:] for issue in issues]
            return _result("CODE_SYNTAX", 95, f"{source.replace('_', ' ').title()} syntax error found.", formatted[0], formatted, ["Fix the syntax at the reported line(s).", "Check brackets, quotes, semicolons, and matching keywords near that line."])
    delimiter_error = _delimiter_error(content)
    if delimiter_error:
        return _result("CODE_SYNTAX", 90, "A structural syntax issue was found.", delimiter_error, [delimiter_error], ["Match every opening bracket, parenthesis, and brace.", "Close the unterminated string or remove the unexpected delimiter."])
    return _result("CODE_REVIEW", 85, f"{source.replace('_', ' ').title()} source scan completed.", "No syntax issue was found by the built-in static checks. Runtime, type, dependency, and framework errors still require build output or a language-specific compiler.", [], ["Run the language compiler, linter, or test suite for deeper checks.", "Upload any resulting error output for root-cause analysis."])
