"""
core/risk/metrics_extractor.py
Static code metrics via AST: function count, cyclomatic complexity, nesting depth.
These feed into risk_engine.calculate_risk() as the 'complexity' factor.
"""

import ast
from utils.logger import logger


class CodeMetrics(ast.NodeVisitor):

    def __init__(self):
        self.function_count       = 0
        self.cyclomatic_complexity = 1   # baseline = 1
        self.max_depth            = 0
        self._current_depth       = 0

    def visit_FunctionDef(self, node):
        self.function_count += 1
        self.generic_visit(node)

    visit_AsyncFunctionDef = visit_FunctionDef

    def _branch(self, node):
        self.cyclomatic_complexity += 1
        self._current_depth += 1
        self.max_depth = max(self.max_depth, self._current_depth)
        self.generic_visit(node)
        self._current_depth -= 1

    visit_If      = _branch
    visit_For     = _branch
    visit_While   = _branch
    visit_ExceptHandler = _branch
    visit_With    = _branch


def extract_metrics(file_path: str) -> dict:
    """
    Parse *file_path* and return:
        {
            "functions":   int,
            "complexity":  int,   # cyclomatic complexity
            "max_depth":   int,   # maximum nesting depth
        }
    Returns zeros on any error so callers never crash.
    """
    try:
        logger.info(f"Extracting metrics from {file_path}", "METRICS")

        with open(file_path, "r", errors="ignore") as f:
            code = f.read()

        tree     = ast.parse(code)
        analyzer = CodeMetrics()
        analyzer.visit(tree)

        metrics = {
            "functions":  analyzer.function_count,
            "complexity": analyzer.cyclomatic_complexity,
            "max_depth":  analyzer.max_depth,
        }
        logger.info(f"Metrics: {metrics}", "METRICS")
        return metrics

    except Exception as e:
        logger.error(f"Metrics extraction failed for {file_path}: {e}", "METRICS")
        return {"functions": 0, "complexity": 0, "max_depth": 0}