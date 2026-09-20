import unittest

from app.services.rule_engine import analyze_with_rules
from app.services.static_analyzer import analyze_source_code


class RuleEngineTests(unittest.TestCase):
    def test_detects_java_compilation_failure(self) -> None:
        result = analyze_with_rules("[ERROR] cannot find symbol\n[ERROR] symbol: class OrderService")
        self.assertEqual("JAVA_COMPILATION", result["error_category"])
        self.assertGreaterEqual(result["confidence_score"], 90)

    def test_detects_missing_python_module(self) -> None:
        result = analyze_with_rules("ModuleNotFoundError: No module named 'fastapi'")
        self.assertEqual("PYTHON_MODULE", result["error_category"])
        self.assertTrue(result["extracted_errors"])

    def test_returns_safe_fallback_for_unknown_log(self) -> None:
        result = analyze_with_rules("Build stopped after an unexpected condition")
        self.assertEqual("UNKNOWN", result["error_category"])
        self.assertEqual("RULE_BASED", result["analyzer_type"])

    def test_scores_gradle_context_above_generic_dependency_message(self) -> None:
        result = analyze_with_rules("Could not find com.example:tool:1.0\nSearched in the following locations.")
        self.assertEqual("GRADLE_DEPENDENCY", result["error_category"])

    def test_source_type_breaks_an_ambiguous_dependency_tie(self) -> None:
        result = analyze_with_rules("Could not find com.example:tool:1.0", source_type="GRADLE")
        self.assertEqual("GRADLE_DEPENDENCY", result["error_category"])

    def test_fingerprint_ignores_line_numbers(self) -> None:
        first = analyze_with_rules("error: incompatible types at line 12")
        second = analyze_with_rules("error: incompatible types at line 99")
        self.assertEqual(first["fingerprint"], second["fingerprint"])

    def test_finds_python_syntax_error_in_source_code(self) -> None:
        result = analyze_source_code("def broken(:\n    pass", "PYTHON")
        self.assertEqual("CODE_SYNTAX", result["error_category"])

    def test_reports_clean_source_code_scan(self) -> None:
        result = analyze_source_code("def fibonacci(n):\n    return n", "PYTHON")
        self.assertEqual("CODE_REVIEW", result["error_category"])

    def test_finds_undefined_python_name_without_running_code(self) -> None:
        result = analyze_source_code("def add_one(value):\n    return value + missing_number", "PYTHON")
        self.assertEqual("PYTHON_STATIC_ERROR", result["error_category"])
        self.assertIn("missing_number", result["extracted_errors"][0])

    def test_finds_constant_division_by_zero(self) -> None:
        result = analyze_source_code("result = 10 / 0", "PYTHON")
        self.assertEqual("PYTHON_STATIC_ERROR", result["error_category"])

    def test_finds_recursive_result_without_return(self) -> None:
        result = analyze_source_code(
            "def fibonacci(n):\n    if n < 2:\n        return n\n    else:\n        fibonacci(n - 1) + fibonacci(n - 2)",
            "PYTHON",
        )
        self.assertEqual("PYTHON_STATIC_ERROR", result["error_category"])
        self.assertIn("not returned", result["extracted_errors"][0])

    def test_finds_constant_runtime_errors(self) -> None:
        result = analyze_source_code("value = ['one'][3]\nnumber = int('not-a-number')", "PYTHON")
        self.assertEqual("PYTHON_STATIC_ERROR", result["error_category"])
        self.assertTrue(any("IndexError" in error for error in result["extracted_errors"]))
        self.assertTrue(any("ValueError" in error for error in result["extracted_errors"]))


if __name__ == "__main__":
    unittest.main()
