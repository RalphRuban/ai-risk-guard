"""
core/patch/fixers.py

Phase 2 AST patch transformers.
Handles secure automated remediation.
"""

import ast
import difflib

from utils.logger import logger


# =========================================================
# BASE TRANSFORMER
# =========================================================

class BaseTransformer(ast.NodeTransformer):

    def __init__(self, vulnerability):

        self.target_line = int(
            vulnerability.get("line", 0)
        )

        self.target_code = (
            vulnerability.get("code", "")
            .strip()
        )

        self.matched = False

    def matches(self, node):

        if self.matched:
            return False
            
        # 1. Try fuzzy matching first (handles line number shifts)
        if self.fuzzy_match(node):
            self.matched = True
            return True

        # 2. Fallback to strict line number (only if fuzzy matching is not possible)
        if hasattr(node, "lineno"):
            if node.lineno == self.target_line:
                self.matched = True
                return True

        return False

    def fuzzy_match(self, node):
        try:
            source = ast.unparse(node).strip()
            
            # Normalize quotes to make matching robust
            norm_source = source.replace('"', "'")
            norm_target = self.target_code.replace('"', "'")

            if norm_source and (norm_source in norm_target or norm_target in norm_source):
                self.matched = True
                return True
        except Exception:
            pass
        return False


# =========================================================
# COMMAND INJECTION FIX
# =========================================================

class CommandInjectionFix(BaseTransformer):

    def visit_Call(self, node):

        self.generic_visit(node)

        if not self.matches(node):
            return node

        if (
            isinstance(node.func, ast.Attribute)
            and
            isinstance(node.func.value, ast.Name)
            and
            node.func.value.id == "os"
            and
            node.func.attr == "system"
        ):

            argument = (
                node.args[0]
                if node.args
                else ast.Constant(value="")
            )

            return ast.copy_location(

                ast.Call(

                    func=ast.Attribute(
                        value=ast.Name(
                            id="subprocess",
                            ctx=ast.Load(),
                        ),
                        attr="run",
                        ctx=ast.Load(),
                    ),

                    args=[

                        ast.Call(

                            func=ast.Attribute(
                                value=ast.Name(
                                    id="shlex",
                                    ctx=ast.Load(),
                                ),
                                attr="split",
                                ctx=ast.Load(),
                            ),

                            args=[argument],
                            keywords=[],
                        )
                    ],

                    keywords=[

                        ast.keyword(
                            arg="shell",
                            value=ast.Constant(False),
                        ),

                        ast.keyword(
                            arg="check",
                            value=ast.Constant(True),
                        ),
                    ],
                ),

                node
            )

        return node


# =========================================================
# CODE INJECTION FIX
# =========================================================

class CodeInjectionFix(BaseTransformer):

    def visit_Call(self, node):

        self.generic_visit(node)

        if not self.matches(node):
            return node

        if (
            isinstance(node.func, ast.Name)
            and
            node.func.id in ("eval", "exec")
        ):

            return ast.copy_location(

                ast.Call(

                    func=ast.Attribute(
                        value=ast.Name(
                            id="ast",
                            ctx=ast.Load(),
                        ),
                        attr="literal_eval",
                        ctx=ast.Load(),
                    ),

                    args=node.args,
                    keywords=[],
                ),

                node
            )

        return node


# =========================================================
# SECRET FIX
# =========================================================

class SecretFix(BaseTransformer):

    def visit_Assign(self, node):

        self.generic_visit(node)

        if not self.matches(node):
            return node

        if not isinstance(node.value, ast.Constant):
            return node

        should_patch = False
        secret_keywords = ["password", "secret", "token", "key", "api_key"]

        for target in node.targets:
            if isinstance(target, ast.Name):
                variable_name = target.id.lower()
                if any(kw in variable_name for kw in secret_keywords):
                    should_patch = True
                    env_var_name = target.id.upper()
                    break

        if should_patch:
            node.value = ast.Call(
                func=ast.Attribute(
                    value=ast.Name(id="os", ctx=ast.Load()),
                    attr="getenv",
                    ctx=ast.Load(),
                ),
                args=[ast.Constant(value=env_var_name)],
                keywords=[],
            )

        return node


# =========================================================
# DESERIALIZATION FIX
# =========================================================

class DeserializationFix(BaseTransformer):

    def visit_Call(self, node):

        self.generic_visit(node)

        if not self.matches(node):
            return node

        # Handle pickle.loads or marshal.loads
        if (
            isinstance(node.func, ast.Attribute)
            and
            isinstance(node.func.value, ast.Name)
            and
            node.func.value.id in ("pickle", "marshal")
            and
            node.func.attr == "loads"
        ):

            return ast.copy_location(
                ast.Call(
                    func=ast.Attribute(
                        value=ast.Name(id="json", ctx=ast.Load()),
                        attr="loads",
                        ctx=ast.Load(),
                    ),
                    args=node.args,
                    keywords=[],
                ),
                node
            )

        return node


class ModuleRemover(ast.NodeTransformer):
    """Removes forbidden module imports from the AST."""
    def __init__(self, forbidden_modules):
        self.forbidden_modules = forbidden_modules
        self.removed_any = False

    def visit_Import(self, node):
        node.names = [n for n in node.names if n.name not in self.forbidden_modules]
        if not node.names:
            self.removed_any = True
            return None
        return node

    def visit_ImportFrom(self, node):
        if node.module in self.forbidden_modules:
            self.removed_any = True
            return None
        return node


# =========================================================
# IMPORT INJECTION
# =========================================================

def inject_imports(tree, modules):

    existing_imports = set()

    for node in tree.body:

        if isinstance(node, ast.Import):

            for imported in node.names:
                existing_imports.add(
                    imported.name
                )

    new_imports = [

        ast.Import(
            names=[ast.alias(name=module)]
        )

        for module in modules

        if module not in existing_imports
    ]

    tree.body = new_imports + tree.body

    return tree


# =========================================================
# PATCH ENGINE
# =========================================================

from core.policy.policy_engine import PolicyEngine

def apply_patch_to_content(
    code,
    vulnerability
):

    try:
        policy_engine = PolicyEngine()
        tree = ast.parse(code)
        
        # 0. Strip forbidden modules (Governance)
        forbidden = policy_engine.policy.get("forbidden_modules", [])
        stripper = ModuleRemover(forbidden)
        tree = stripper.visit(tree)

        vulnerability_type = vulnerability.get(
            "type"
        )

        if vulnerability_type == "COMMAND_INJECTION":

            transformer = CommandInjectionFix(
                vulnerability
            )

            required_imports = [
                "subprocess",
                "shlex",
            ]

        elif vulnerability_type == "CODE_INJECTION":

            transformer = CodeInjectionFix(
                vulnerability
            )

            required_imports = [
                "ast"
            ]

        elif vulnerability_type == "HARDCODED_SECRET":

            transformer = SecretFix(
                vulnerability
            )

            required_imports = [
                "os"
            ]

        elif vulnerability_type == "INSECURE_DESERIALIZATION":

            transformer = DeserializationFix(
                vulnerability
            )

            required_imports = [
                "json"
            ]

        else:

            return {
                "patched_code": code,
                "diff": "",
                "ast_success": False,
            }

        transformed_tree = transformer.visit(
            tree
        )

        if not transformer.matched:

            return {
                "patched_code": code,
                "diff": "",
                "ast_success": False,
            }

        transformed_tree = inject_imports(
            transformed_tree,
            required_imports
        )

        ast.fix_missing_locations(
            transformed_tree
        )

        patched_code = ast.unparse(
            transformed_tree
        )

        diff = "".join(

            difflib.unified_diff(

                code.splitlines(
                    keepends=True
                ),

                patched_code.splitlines(
                    keepends=True
                ),

                fromfile="before.py",
                tofile="after.py",
            )
        )

        return {
            "patched_code": patched_code,
            "diff": diff,
            "ast_success": True,
        }

    except Exception as error:

        logger.error(
            f"Patch engine failed: {error}",
            "PATCH"
        )

        return {
            "patched_code": code,
            "diff": "",
            "ast_success": False,
            "error": str(error),
        }