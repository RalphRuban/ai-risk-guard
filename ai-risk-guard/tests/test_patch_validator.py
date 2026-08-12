"""
tests/test_patch_validator.py
Tests for the deterministic patch validation engine.
All methods are pure functions — no mocking required.
"""

from core.validator.patch_validator import PatchValidator


class TestPatchValidator:
    def setup_method(self):
        self.validator = PatchValidator()

    def test_validate_ast_valid_code(self):
        result = self.validator.validate_ast("x = 1")
        assert result["success"] is True

    def test_validate_ast_syntax_error(self):
        result = self.validator.validate_ast("def foo(")
        assert result["success"] is False

    def test_validate_imports_dangerous(self):
        result = self.validator.validate_imports("import socket")
        assert result["success"] is False

    def test_validate_imports_safe(self):
        result = self.validator.validate_imports("import os")
        assert result["success"] is True

    def test_validate_imports_from_dangerous(self):
        result = self.validator.validate_imports("from socket import *")
        assert result["success"] is False

    def test_validate_patterns_eval(self):
        result = self.validator.validate_patterns("eval(x)")
        assert result["success"] is False

    def test_validate_patterns_literal_eval_safe(self):
        result = self.validator.validate_patterns("ast.literal_eval(x)")
        assert result["success"] is True

    def test_validate_patterns_os_system(self):
        result = self.validator.validate_patterns('os.system("ls")')
        assert result["success"] is False

    def test_validate_all_short_circuits_on_first_failure(self):
        result = self.validator.validate_all('import socket\neval(x)')
        assert result["success"] is False
        assert result["stage"] == "validate_imports"

    def test_validate_all_passes_clean_code(self):
        result = self.validator.validate_all("x = 1")
        assert result["success"] is True
        assert len(result["results"]) == 4

    def test_validate_names_rejects_undefined_reference(self):
        result = self.validator.validate_names("shlex.split(cmd)")
        assert result["success"] is False
        assert "shlex" in result["undefined_names"]

    def test_validate_names_accepts_imported_and_builtin_names(self):
        code = "import shlex\ndef f(cmd):\n    return shlex.split(cmd)\nprint(len('x'))"
        result = self.validator.validate_all(code)
        assert result["success"] is True
