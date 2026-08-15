"""
core/patch/fixers.py

Phase 2 AST patch transformers.
Handles secure automated remediation.
"""

import ast
import copy
import difflib
import re

from utils.logger import logger

# =========================================================
# BASE TRANSFORMER
# =========================================================

class BaseTransformer(ast.NodeTransformer):

    def __init__(self, vulnerability, source_code=""):

        self.target_line = int(
            vulnerability.get("line", 0)
        )

        self.target_code = (
            vulnerability.get("code", "")
            .strip()
        )

        self.matched = False
        self.source_code = source_code
        self.original_segment = None
        self.original_lineno = None
        self.original_end_lineno = None

    def matches(self, node):

        # 1. Try fuzzy matching first (handles line number shifts)
        if self.fuzzy_match(node):
            self.matched = True
            if self.source_code:
                self.original_segment = ast.get_source_segment(self.source_code, node)
                self.original_lineno = node.lineno
                self.original_end_lineno = getattr(node, "end_lineno", node.lineno)
            return True

        # 2. Fallback to strict line number (only if fuzzy matching is not possible)
        if hasattr(node, "lineno") and node.lineno == self.target_line:
            self.matched = True
            if self.source_code:
                self.original_segment = ast.get_source_segment(self.source_code, node)
                self.original_lineno = node.lineno
                self.original_end_lineno = getattr(node, "end_lineno", node.lineno)
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
# DATABASE ADAPTER DETECTION
# =========================================================

_DB_PLACEHOLDER_MAP = {
    "sqlite3": "?",
    "aiosqlite": "?",
    "pyodbc": "?",
    "psycopg2": "%s",
    "psycopg2.extras": "%s",
    "mysql.connector": "%s",
    "pymysql": "%s",
    "MySQLdb": "%s",
    "asyncpg": "$PLACEHOLDER",
    "cx_Oracle": ":1",
}

def _detect_db_placeholder(tree) -> str:
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name in _DB_PLACEHOLDER_MAP:
                    return _DB_PLACEHOLDER_MAP[alias.name]
        elif isinstance(node, ast.ImportFrom) and node.module and node.module in _DB_PLACEHOLDER_MAP:
            return _DB_PLACEHOLDER_MAP[node.module]
    return "?"


# =========================================================
# COMMAND INJECTION FIX
# =========================================================

class CommandInjectionFix(BaseTransformer):

    _SUBPROCESS_SHELL_FUNCS = ("run", "Popen", "call", "check_call", "check_output")

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

            if not self._is_safe_system_argument(argument):
                # os.system with shell metacharacters / dynamic input cannot be
                # safely rewritten to shlex.split without changing semantics —
                # do NOT report a successful fix (the vulnerability remains).
                self.matched = False
                return node

            self.matched = True

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

        if self._is_subprocess_shell_call(node):
            fixed = self._fix_subprocess_shell(node)
            if fixed is not None:
                self.matched = True
                return fixed
            # Matched a shell=True subprocess call but could not rewrite it —
            # do NOT report a successful fix (the vulnerability remains).
            self.matched = False
            return node

        return node

    def _is_subprocess_shell_call(self, node) -> bool:
        """Return True if ``node`` is a subprocess call with shell=True."""
        if not (
            isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "subprocess"
            and node.func.attr in self._SUBPROCESS_SHELL_FUNCS
        ):
            return False
        shell_kw = next((kw for kw in node.keywords if kw.arg == "shell"), None)
        if shell_kw is None:
            return False
        return (
            isinstance(shell_kw.value, ast.Constant)
            and shell_kw.value.value is True
        )

    def _is_safe_system_argument(self, argument) -> bool:
        """Whether an os.system argument can be safely rewritten via shlex.split.

        Only constant string commands without shell metacharacters preserve
        semantics under shlex.split; anything else can silently change behavior
        (pipes, redirects, env expansion, globs, command substitution), so we
        refuse to patch it rather than produce a misleading "fixed" output.
        """
        if not (
            isinstance(argument, ast.Constant)
            and isinstance(argument.value, str)
        ):
            return False
        shell_metachars = set("|&;<>$`*?~\n(){}")
        return not any(ch in argument.value for ch in shell_metachars)

    def _fix_subprocess_shell(self, node):
        """Rewrite a subprocess call from shell=True to shell=False.

        String-typed commands (constants, f-strings, names) are wrapped in
        ``shlex.split(...)``; list/tuple commands are left as-is. Returns the
        new node, or None if the command argument cannot be made safe.
        """
        # Locate the command argument (positional args[0] or the `args=` keyword).
        cmd_arg = None
        cmd_via_keyword = None
        if node.args:
            cmd_arg = node.args[0]
        else:
            args_kw = next((kw for kw in node.keywords if kw.arg == "args"), None)
            if args_kw is not None:
                cmd_arg = args_kw.value
                cmd_via_keyword = args_kw

        if cmd_arg is None:
            return None

        if isinstance(cmd_arg, (ast.Constant, ast.JoinedStr, ast.Name)):
            split_call = ast.Call(
                func=ast.Attribute(
                    value=ast.Name(id="shlex", ctx=ast.Load()),
                    attr="split",
                    ctx=ast.Load(),
                ),
                args=[cmd_arg],
                keywords=[],
            )
        elif isinstance(cmd_arg, (ast.List, ast.Tuple)):
            split_call = cmd_arg
        else:
            return None

        new_args = list(node.args)
        if not cmd_via_keyword and new_args:
            new_args[0] = split_call

        new_keywords = []
        for kw in node.keywords:
            if kw.arg == "shell":
                continue
            if kw is cmd_via_keyword:
                kw = ast.keyword(arg="args", value=split_call)
            new_keywords.append(kw)

        new_keywords.append(
            ast.keyword(arg="shell", value=ast.Constant(False))
        )

        return ast.copy_location(
            ast.Call(
                func=node.func,
                args=new_args,
                keywords=new_keywords,
            ),
            node,
        )


# =========================================================
# CODE INJECTION FIX
# =========================================================

class CodeInjectionFix(BaseTransformer):

    def __init__(self, vulnerability, source_code=""):
        super().__init__(vulnerability, source_code)
        self.is_math = False

    def visit_Call(self, node):

        self.generic_visit(node)

        if not self.matches(node):
            return node

        if isinstance(node.func, ast.Name) and node.func.id == "exec":
            if not self._is_literal_expression(node):
                self.matched = False
                return node
            return self._literal_eval_call(node)

        if isinstance(node.func, ast.Name) and node.func.id == "eval":
            if node.keywords:
                self.matched = False
                return node
            if self._is_math_context(node):
                self.is_math = True
                return ast.copy_location(
                    ast.Call(
                        func=ast.Attribute(
                            value=ast.Name(id="_aeval", ctx=ast.Load()),
                            attr="eval",
                            ctx=ast.Load(),
                        ),
                        args=node.args,
                        keywords=[],
                    ),
                    node,
                )
            else:
                return self._literal_eval_call(node)

        return node

    @staticmethod
    def _literal_eval_call(node):
        return ast.copy_location(
            ast.Call(
                func=ast.Attribute(
                    value=ast.Name(id="ast", ctx=ast.Load()),
                    attr="literal_eval",
                    ctx=ast.Load(),
                ),
                args=node.args,
                keywords=[],
            ),
            node,
        )

    @staticmethod
    def _is_literal_expression(node):
        if not node.args or not isinstance(node.args[0], ast.Constant):
            return False
        if not isinstance(node.args[0].value, str):
            return False
        if node.keywords:
            return False
        try:
            ast.literal_eval(node.args[0].value)
        except (ValueError, SyntaxError):
            return False
        return True

    @staticmethod
    def _is_math_context(node):
        if node.args and isinstance(node.args[0], ast.Constant):
            val = str(node.args[0].value)
            if any(op in val for op in ("+", "-", "*", "/", "**", "%")) and not val.strip().startswith(("{", "[", "(")):
                return True
        return False


_SECRET_NAME_PATTERN = re.compile(
    r"(?:^|[_\W])(?:passwd|password|secret|token|apikey|api[_-]?key|"
    r"private[_-]?key|access[_-]?key|client[_-]?secret|auth[_-]?token|"
    r"refresh[_-]?token)(?:$|[_\W])",
    re.IGNORECASE,
)


# =========================================================
# SECRET FIX
# =========================================================

class SecretFix(BaseTransformer):

    def visit_Assign(self, node):

        self.generic_visit(node)

        if not isinstance(node.value, ast.Constant):
            return node

        should_patch = False

        for target in node.targets:
            if isinstance(target, ast.Name):
                variable_name = target.id
                if _SECRET_NAME_PATTERN.search(variable_name):
                    should_patch = True
                    env_var_name = variable_name.upper()
                    break

        if should_patch:
            self.matched = True
            self.original_segment = ast.get_source_segment(self.source_code, node)
            self.original_lineno = node.lineno
            self.original_end_lineno = getattr(node, "end_lineno", node.lineno)
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

    def visit_AnnAssign(self, node):

        self.generic_visit(node)

        if not isinstance(node.value, ast.Constant):
            return node

        if not isinstance(node.target, ast.Name):
            return node

        variable_name = node.target.id.lower()
        secret_keywords = ["password", "secret", "token", "key", "api_key"]

        if any(kw in variable_name for kw in secret_keywords):
            self.matched = True
            self.original_segment = ast.get_source_segment(self.source_code, node)
            self.original_lineno = node.lineno
            self.original_end_lineno = getattr(node, "end_lineno", node.lineno)
            env_var_name = node.target.id.upper()
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
                    func=ast.Name(id="safe_loads", ctx=ast.Load()),
                    args=node.args,
                    keywords=[],
                ),
                node
            )
        return node


class SqlInjectionFix(BaseTransformer):

    def __init__(self, vulnerability, source_code="", placeholder="?"):
        super().__init__(vulnerability, source_code)
        self.placeholder = placeholder

    def visit_Call(self, node):
        self.generic_visit(node)
        if not self.matches(node):
            return node
        
        func_name = self._get_func_name(node.func)
        if (func_name in ("execute", "executemany") or (
            isinstance(node.func, ast.Attribute) and node.func.attr in ("execute", "executemany")
        )) and node.args:
            query_node = node.args[0]

            # Check for f-string (JoinedStr)
            if isinstance(query_node, ast.JoinedStr):
                param_parts = []
                args_list = []

                for part in query_node.values:
                    if isinstance(part, ast.Constant):
                        param_parts.append(part.value)
                    elif isinstance(part, ast.FormattedValue):
                        param_parts.append(self.placeholder)
                        args_list.append(copy.deepcopy(part.value))

                query_template = "".join(param_parts)
                query_template = re.sub(r"['\"]" + re.escape(self.placeholder) + r"['\"]", self.placeholder, query_template)

                query_template, args_list = self._rewrite_like_clause(query_template, args_list)

                new_args = [ast.Constant(value=query_template)]
                if args_list:
                    tuple_node = ast.Tuple(elts=args_list, ctx=ast.Load())
                    new_args.append(tuple_node)

                node.args = new_args
                return node

            # Check for string formatting with format() or % operator
            elif isinstance(query_node, ast.BinOp) and isinstance(query_node.op, ast.Mod):
                query_template = ""
                if isinstance(query_node.left, ast.Constant):
                    query_template = query_node.left.value

                if query_template:
                    query_template = re.sub(r"['\"]%s['\"]", self.placeholder, query_template)
                    if isinstance(query_node.right, ast.Tuple):
                        arg_exprs = list(query_node.right.elts)
                    else:
                        arg_exprs = [query_node.right]
                    query_template, arg_exprs = self._rewrite_like_clause(query_template, arg_exprs)
                    new_args = [ast.Constant(value=query_template)]
                    if arg_exprs:
                        new_args.append(ast.Tuple(elts=arg_exprs, ctx=ast.Load()))

                    node.args = new_args
                    return node

            elif isinstance(query_node, ast.Call) and isinstance(query_node.func, ast.Attribute) and query_node.func.attr == "format":
                if isinstance(query_node.func.value, ast.Constant):
                    query_template = query_node.func.value.value
                    query_template = re.sub(r"['\"]\{\}['\"]", self.placeholder, query_template)
                    query_template = query_template.replace("{}", self.placeholder)

                    arg_exprs = list(query_node.args)
                    query_template, arg_exprs = self._rewrite_like_clause(query_template, arg_exprs)

                    new_args = [ast.Constant(value=query_template)]
                    if arg_exprs:
                        new_args.append(ast.Tuple(elts=arg_exprs, ctx=ast.Load()))

                    node.args = new_args
                    return node

        return node

    def _get_func_name(self, node: ast.AST) -> str:
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            value_name = self._get_func_name(node.value)
            return f"{value_name}.{node.attr}" if value_name else node.attr
        return ""

    def _rewrite_like_clause(self, query_template, args_list):
        """Rewrite ``LIKE '<wildcards>?...'`` into ``LIKE ?`` with a bound wildcard value.

        e.g. ``... LIKE '%?%'`` becomes ``... LIKE ?`` and the matching argument
        is wrapped as ``f"%{arg}%"`` so the ``%`` wildcards move into the bound
        parameter instead of staying in the SQL text.
        """
        like_re = re.compile(
            r"(LIKE\s+['\"])([^'\"]*)" + re.escape(self.placeholder) + r"([^'\"]*)(['\"])",
            flags=re.IGNORECASE,
        )
        matches = list(like_re.finditer(query_template))
        if not matches or not args_list:
            return query_template, args_list
        new_args = list(args_list)
        new_template = query_template
        for match in reversed(matches):
            pre = match.group(2)
            post = match.group(3)
            ph_pos = match.start() + len(match.group(1)) + len(pre)
            arg_idx = query_template.count(self.placeholder, 0, ph_pos)
            if arg_idx >= len(new_args):
                continue
            new_args[arg_idx] = ast.JoinedStr(values=[
                ast.Constant(value=pre),
                ast.FormattedValue(value=copy.deepcopy(new_args[arg_idx]), conversion=-1),
                ast.Constant(value=post),
            ])
            replacement = "LIKE " + self.placeholder
            new_template = new_template[:match.start()] + replacement + new_template[match.end():]
        return new_template, new_args


class PathTraversalFix(BaseTransformer):

    def __init__(self, vulnerability, source_code=""):
        super().__init__(vulnerability, source_code)
        self.wrapped_opens = 0

    def visit_Call(self, node):
        self.generic_visit(node)
        func_name = self._get_func_name(node.func)
        is_open = (
            func_name in ("open", "os.open", "io.open")
            or (isinstance(node.func, ast.Attribute) and node.func.attr == "open")
        )
        if not is_open or not node.args:
            return node
        if self.matches(node):
            self.matched = True
        base_dir = self._extract_base_dir(node.args[0])
        path_arg, base_node = self._strip_base_prefix(node.args[0], base_dir)
        if path_arg is None:
            # A real base directory was detected but its leading prefix could
            # not be stripped safely. Leave the open() call untouched rather
            # than double the directory: safe_path_join(base, base/path)
            # resolves inside base/base, which silently passes the prefix check.
            return node
        node.args[0] = ast.Call(
            func=ast.Name(id="safe_path_join", ctx=ast.Load()),
            args=[base_node, path_arg],
            keywords=[],
        )
        self.wrapped_opens += 1
        return node

    @staticmethod
    def _is_separator_only(value: str) -> bool:
        return bool(value) and all(ch in "/\\." for ch in value)

    @staticmethod
    def _resolve_module_constant(source_code: str, name: str):
        """Return the value of a module-level string constant assigned to *name*."""
        if not source_code:
            return None
        try:
            tree = ast.parse(source_code)
        except SyntaxError:
            return None
        for node in tree.body:
            if isinstance(node, ast.Assign) and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == name:
                        return node.value.value
            elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and node.target.id == name and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                return node.value.value
        return None

    def _extract_base_dir(self, node):
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add) and isinstance(node.left, ast.Constant) and isinstance(node.left.value, str):
            return node.left.value
        if isinstance(node, ast.JoinedStr):
            for part in node.values:
                val = None
                if isinstance(part, ast.Constant) and isinstance(part.value, str):
                    val = part.value
                elif isinstance(part, ast.FormattedValue) and isinstance(part.value, ast.Name):
                    val = self._resolve_module_constant(self.source_code, part.value.id)
                if val is None:
                    continue
                val = val.strip()
                if not val or self._is_separator_only(val):
                    continue
                if val.startswith(("/", "./", "../")) or "/" in val or "\\" in val:
                    return val.rstrip("/\\")
        return "."

    def _get_func_name(self, node: ast.AST) -> str:
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            value_name = self._get_func_name(node.value)
            return f"{value_name}.{node.attr}" if value_name else node.attr
        return ""

    def _strip_base_prefix(self, node, base_dir):
        """Remove a leading copy of ``base_dir`` from the path expression.

        ``safe_path_join(base_dir, path)`` assumes *path* is relative to
        *base_dir*. When the original expression already embeds the base (e.g.
        ``f"{DATA_DIR}/{task_id}.txt"`` with ``DATA_DIR = "./task_attachments"``),
        wrapping it verbatim doubles the directory. This strips the leading base
        so the example becomes ``safe_path_join(DATA_DIR, f"{task_id}.txt")``.

        Returns ``(path_node, base_node)`` where *base_node* is the base as a
        literal constant or, when it came from a module-level variable, the
        variable name itself. Returns ``(None, None)`` when *base_dir* was
        extracted but the prefix could not be stripped safely.
        """
        if base_dir in (None, ".", ""):
            return node, ast.Constant(value=".")

        def _norm(value: str) -> str:
            return value.strip().lstrip("/.\\").rstrip("/\\")

        base = base_dir.rstrip("/\\")

        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
            left = node.left
            if (
                isinstance(left, ast.Constant)
                and isinstance(left.value, str)
                and left.value.rstrip("/\\").endswith(base)
            ):
                return node.right, ast.Constant(value=base_dir)
            return None, None

        if isinstance(node, ast.JoinedStr):
            norm_base = _norm(base)
            if not norm_base:
                return None, None
            values = list(node.values)
            accum = ""
            i = 0
            base_node = ast.Constant(value=base_dir)
            while i < len(values):
                part = values[i]
                if isinstance(part, ast.Constant) and isinstance(part.value, str):
                    text = part.value
                elif isinstance(part, ast.FormattedValue) and isinstance(part.value, ast.Name):
                    resolved = self._resolve_module_constant(
                        self.source_code, part.value.id
                    )
                    if not resolved:
                        break
                    text = resolved
                else:
                    break
                candidate = _norm(accum + text)
                if not norm_base.startswith(candidate):
                    break
                if i == 0 and isinstance(part, ast.FormattedValue) and isinstance(
                    part.value, ast.Name
                ):
                    base_node = part.value
                accum += text
                i += 1
                if _norm(accum) == norm_base:
                    break
            if i == 0 or _norm(accum) != norm_base:
                return None, None
            while i < len(values) and isinstance(values[i], ast.Constant) and self._is_separator_only(
                values[i].value
            ):
                i += 1
            if i >= len(values):
                return None, None
            return ast.JoinedStr(values=values[i:]), base_node

        return None, None


class SsrfFix(BaseTransformer):

    def visit_Call(self, node):
        self.generic_visit(node)
        if not self.matches(node):
            return node
        
        func_name = self._get_func_name(node.func)
        if func_name in (
            "requests.get", "requests.post", "requests.put", "requests.delete",
            "requests.patch", "requests.head", "requests.options", "requests.request",
            "urllib.request.urlopen", "urlopen",
            "httpx.get", "httpx.post", "httpx.put", "httpx.delete",
            "httpx.patch", "httpx.head", "httpx.options", "httpx.request",
            "httpx.Client.get", "httpx.Client.post", "httpx.Client.request",
            "httpx.AsyncClient.get", "httpx.AsyncClient.post", "httpx.AsyncClient.request",
        ) and node.args:
            url_node = node.args[0]
            node.args[0] = ast.Call(
                func=ast.Name(id="validate_url_ssrf", ctx=ast.Load()),
                args=[url_node],
                keywords=[]
            )
            return node
        return node

    def _get_func_name(self, node: ast.AST) -> str:
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            value_name = self._get_func_name(node.value)
            return f"{value_name}.{node.attr}" if value_name else node.attr
        return ""


class WeakCryptographyFix(BaseTransformer):

    def visit_Call(self, node):
        self.generic_visit(node)
        if not self.matches(node):
            return node
        
        func_name = self._get_func_name(node.func)
        
        if func_name in ("hashlib.md5", "hashlib.sha1"):
            node.func = ast.Attribute(
                value=ast.Name(id="hashlib", ctx=ast.Load()),
                attr="sha256",
                ctx=ast.Load()
            )
            return node
        elif func_name in ("md5", "sha1"):
            node.func = ast.Name(id="sha256", ctx=ast.Load())
            return node
            
        elif func_name in ("hashlib.new", "new"):
            if node.args:
                first_arg = node.args[0]
                if isinstance(first_arg, ast.Constant) and str(first_arg.value).lower() in ("md5", "sha1"):
                    node.args[0] = ast.Constant(value="sha256")
                    return node
                    
        return node

    def _get_func_name(self, node: ast.AST) -> str:
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            value_name = self._get_func_name(node.value)
            return f"{value_name}.{node.attr}" if value_name else node.attr
        return ""


# =========================================================
# HELPER INJECTION UTILITY — insert after last import
# =========================================================

def _find_insertion_point(tree):
    insert_idx = 0
    for i, node in enumerate(tree.body):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            insert_idx = i + 1
    return insert_idx


# =========================================================
# SURGICAL SPLICING (minimal diffs)
# =========================================================

_INJECTED_TOP_LEVEL_NAMES = frozenset({
    "validate_url_ssrf", "_is_private_ip", "_PRIVATE_RANGES",
    "safe_path_join", "_aeval", "RestrictedUnpickler", "safe_loads",
})


def _splice_statement(code, transformer, new_segment):
    """Replace the statement containing the matched span with ``new_segment``."""
    if not new_segment or not transformer.original_segment or not transformer.original_lineno:
        return None
    try:
        orig_tree = ast.parse(code)
    except SyntaxError:
        return None

    # Find the enclosing statement that contains the matched node span.
    _STATEMENT_NODES = (ast.Assign, ast.AnnAssign, ast.AugAssign, ast.Expr, ast.Return,
                        ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.If,
                        ast.For, ast.While, ast.With, ast.Try, ast.Import, ast.ImportFrom)
    target = None
    for node in ast.walk(orig_tree):
        if not isinstance(node, _STATEMENT_NODES) or not hasattr(node, "lineno"):
            continue
        end = getattr(node, "end_lineno", node.lineno)
        if node.lineno <= transformer.original_lineno <= end and (target is None or (node.lineno >= target.lineno and end <= target.end_lineno)):
            target = node
    if target is None:
        return None

    lines = code.splitlines(keepends=True)
    start_idx = target.lineno - 1
    end_idx = getattr(target, "end_lineno", target.lineno)
    if start_idx < 0 or start_idx >= len(lines) or end_idx < start_idx or end_idx > len(lines):
        return None
    old_block = "".join(lines[start_idx:end_idx])
    if transformer.original_segment.strip() not in old_block:
        return None
    indent = re.match(r"^(\s*)", lines[start_idx]).group(1)
    seg_lines = new_segment.splitlines(keepends=True)
    base_indent = ""
    for nl in seg_lines:
        if nl.strip():
            base_indent = re.match(r"^(\s*)", nl).group(1)
            break
    new_lines = []
    for nl in seg_lines:
        if nl.strip():
            rel = re.match(r"^(\s*)", nl).group(1)
            new_lines.append(indent + rel[len(base_indent):] + nl.lstrip(" \t"))
        else:
            new_lines.append(nl)
    if new_lines and new_lines[-1] and not new_lines[-1].endswith(("\n", "\r")):
        new_lines[-1] += "\n"
    lines[start_idx:end_idx] = new_lines
    return "".join(lines)


def _insert_helper_after_imports(code, helper_src):
    """Insert a helper block after the last top-level import in ``code``."""
    lines = code.splitlines(keepends=True)
    last_import = -1
    for i, line in enumerate(lines):
        if re.match(r"^(import |from )", line):
            last_import = i
    block = "\n" + helper_src.strip() + "\n\n"
    lines.insert(last_import + 1, block)
    return "".join(lines)


def _insert_missing_imports(code, required_modules):
    """Insert any of ``required_modules`` not already imported, at the top."""
    if not required_modules:
        return code
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return code
    existing = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for n in node.names:
                existing.add(n.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom) and node.module:
            existing.add(node.module.split(".")[0])
    missing = [m for m in required_modules if m not in existing]
    if not missing:
        return code
    lines = code.splitlines(keepends=True)
    insert_at = 0
    if tree.body:
        first = tree.body[0]
        if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant) and isinstance(first.value.value, str):
            insert_at = getattr(first, "end_lineno", 1)
        else:
            insert_at = max(0, getattr(first, "lineno", 1) - 1)
    block = "".join(f"import {m}\n" for m in missing)
    lines.insert(insert_at, block)
    return "".join(lines)


def _splice_patched_code(code, transformer, new_segment, helper_src, all_required):
    """Build a minimal patch by splicing only the changed statement span.

    Returns None when splicing is not possible, in which case the caller
    falls back to a whole-module AST unparse.
    """
    spliced = _splice_statement(code, transformer, new_segment)
    if spliced is None:
        return None
    if helper_src:
        spliced = _insert_helper_after_imports(spliced, helper_src)
    spliced = _insert_missing_imports(spliced, all_required)
    try:
        ast.parse(spliced)
    except SyntaxError:
        return None
    return spliced


# =========================================================
# SAFE PATH JOIN HELPER
# =========================================================

_SAFE_PATH_JOIN_SRC = r"""
import os

def safe_path_join(base_dir, user_path):
    base = os.path.realpath(base_dir)
    full = os.path.realpath(os.path.join(base, user_path))
    if not full.startswith(base + os.sep) and full != base:
        raise ValueError("Path traversal detected")
    return os.path.normpath(os.path.join(base_dir, user_path))
"""

def inject_safe_path_join(tree):
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == "safe_path_join":
            return tree
    helper_tree = ast.parse(_SAFE_PATH_JOIN_SRC)
    insert_idx = _find_insertion_point(tree)
    tree.body[insert_idx:insert_idx] = helper_tree.body
    return tree


# =========================================================
# ASTEVAL HELPER (safe math evaluation)
# =========================================================

_ASTEVAL_SRC = r"""
from asteval import Interpreter
_aeval = Interpreter(minimal=True)
"""

def inject_asteval(tree):
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(t, ast.Name) and t.id == "_aeval" for t in node.targets
        ):
            return tree
    helper_tree = ast.parse(_ASTEVAL_SRC)
    insert_idx = _find_insertion_point(tree)
    tree.body[insert_idx:insert_idx] = helper_tree.body
    return tree


# =========================================================
# RESTRICTED UNPICKLER (safe deserialization)
# =========================================================

_RESTRICTED_UNPICKLER_SRC = r"""
import pickle

class RestrictedUnpickler(pickle.Unpickler):
    SAFE_CLASSES = {
        ("builtins", "dict"), ("builtins", "list"), ("builtins", "tuple"),
        ("builtins", "str"), ("builtins", "int"), ("builtins", "float"),
        ("builtins", "bool"), ("builtins", "NoneType"),
        ("datetime", "datetime"), ("datetime", "date"), ("datetime", "time"),
        ("decimal", "Decimal"), ("collections", "OrderedDict"),
    }

    def find_class(self, module, name):
        if (module, name) not in self.SAFE_CLASSES:
            raise pickle.UnpicklingError(
                f"Deserialization of {module}.{name} is not allowed"
            )
        return super().find_class(module, name)

def safe_loads(data):
    if isinstance(data, str):
        import json
        try:
            return json.loads(data)
        except (json.JSONDecodeError, ValueError):
            pass
    return RestrictedUnpickler(data).load()
"""

def inject_restricted_unpickler(tree):
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == "RestrictedUnpickler":
            return tree
    helper_tree = ast.parse(_RESTRICTED_UNPICKLER_SRC)
    insert_idx = _find_insertion_point(tree)
    tree.body[insert_idx:insert_idx] = helper_tree.body
    return tree


_SSRF_VALIDATOR_SRC = r"""
import ipaddress

_PRIVATE_RANGES = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("100.64.0.0/10"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("0.0.0.0/8"),
    ipaddress.ip_network("fc00::/7"),
    ipaddress.ip_network("fe80::/10"),
    ipaddress.ip_network("::1"),
]


def _is_private_ip(host: str) -> bool:
    try:
        addr = ipaddress.ip_address(host)
        for network in _PRIVATE_RANGES:
            if addr in network:
                return True
        return (
            addr.is_private
            or addr.is_loopback
            or addr.is_link_local
            or addr.is_reserved
            or addr.is_multicast
            or addr.is_unspecified
        )
    except ValueError:
        return False


def validate_url_ssrf(url):
    from urllib.parse import urlparse
    parsed = urlparse(url)
    if parsed.scheme not in ('http', 'https'):
        raise ValueError('Invalid URL scheme')
    hostname = parsed.hostname or parsed.netloc.split(':')[0]
    if hostname in ('localhost', '127.0.0.1', '::1') or _is_private_ip(hostname):
        raise ValueError('Access to internal URL forbidden')
    return url
"""


def inject_ssrf_validator(tree):
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == "validate_url_ssrf":
            return tree
    helper_tree = ast.parse(_SSRF_VALIDATOR_SRC)
    insert_idx = _find_insertion_point(tree)
    tree.body[insert_idx:insert_idx] = helper_tree.body
    return tree



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

        elif isinstance(node, ast.ImportFrom) and node.module:
            existing_imports.add(
                node.module
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
# IMPORT CALL REMOVER
# =========================================================

class ImportCallRemover(ast.NodeTransformer):
    """
    Replaces __import__('module') calls with standard Name references.
    Records the modules that need import statements.
    """
    def __init__(self):
        self.modules_to_import = []

    def visit_Call(self, node):
        self.generic_visit(node)
        if isinstance(node.func, ast.Name) and node.func.id == '__import__' and node.args and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str):
            module_name = node.args[0].value
            self.modules_to_import.append(module_name)
            return ast.copy_location(
                ast.Name(id=module_name, ctx=ast.Load()),
                node
            )
        return node


# =========================================================
# PATCH ENGINE
# =========================================================

from core.policy.policy_engine import PolicyEngine

# Vulnerability types that have a deterministic AST fixer in apply_patch_to_content().
# Types not listed here are detected but intentionally left unpatched (informational).
SUPPORTED_FIXER_TYPES: frozenset[str] = frozenset({
    "COMMAND_INJECTION",
    "CODE_INJECTION",
    "HARDCODED_SECRET",
    "INSECURE_DESERIALIZATION",
    "SQL_INJECTION",
    "PATH_TRAVERSAL",
    "SSRF",
    "WEAK_CRYPTOGRAPHY",
})


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

        # 0.5. Replace __import__() calls with standard imports
        import_remover = ImportCallRemover()
        tree = import_remover.visit(tree)

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

            required_imports = ["ast"]

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

            required_imports = []

        elif vulnerability_type == "SQL_INJECTION":

            placeholder = _detect_db_placeholder(tree)
            transformer = SqlInjectionFix(
                vulnerability,
                placeholder=placeholder,
            )

            required_imports = []

        elif vulnerability_type == "PATH_TRAVERSAL":

            transformer = PathTraversalFix(
                vulnerability
            )

            required_imports = [
                "os"
            ]

        elif vulnerability_type == "SSRF":

            transformer = SsrfFix(
                vulnerability
            )

            required_imports = []

        elif vulnerability_type == "WEAK_CRYPTOGRAPHY":

            transformer = WeakCryptographyFix(
                vulnerability
            )

            required_imports = [
                "hashlib"
            ]

        else:

            return {
                "patched_code": code,
                "diff": "",
                "ast_success": False,
            }

        # Give transformer access to original source so matches() can record
        # the exact statement span for surgical splicing.
        transformer.source_code = code

        transformed_tree = transformer.visit(
            tree
        )

        if vulnerability_type == "SSRF" and transformer.matched:
            transformed_tree = inject_ssrf_validator(transformed_tree)

        if vulnerability_type == "CODE_INJECTION" and transformer.matched and transformer.is_math:
            transformed_tree = inject_asteval(transformed_tree)
            existing = {n.names[0].name for n in ast.walk(transformed_tree) if isinstance(n, ast.Import)}
            if "asteval" not in existing:
                required_imports.append("asteval")

        if vulnerability_type == "INSECURE_DESERIALIZATION" and transformer.matched:
            transformed_tree = inject_restricted_unpickler(transformed_tree)

        if vulnerability_type == "PATH_TRAVERSAL" and transformer.matched:
            transformed_tree = inject_safe_path_join(transformed_tree)

        if not transformer.matched:

            return {
                "patched_code": code,
                "diff": "",
                "ast_success": False,
            }

        # Merge imports from __import__() replacement with vulnerability-specific ones
        all_required = list(required_imports)
        for mod in import_remover.modules_to_import:
            if mod not in all_required:
                all_required.append(mod)

        # Helper block needed by certain fixers (kept for the unparse fallback).
        helper_src = None
        if vulnerability_type == "SSRF":
            helper_src = _SSRF_VALIDATOR_SRC
        elif vulnerability_type == "PATH_TRAVERSAL":
            helper_src = _SAFE_PATH_JOIN_SRC
        elif vulnerability_type == "CODE_INJECTION" and getattr(transformer, "is_math", False):
            helper_src = _ASTEVAL_SRC
        elif vulnerability_type == "INSECURE_DESERIALIZATION":
            helper_src = _RESTRICTED_UNPICKLER_SRC

        transformed_tree = inject_imports(
            transformed_tree,
            all_required
        )

        ast.fix_missing_locations(
            transformed_tree
        )

        patched_code = ast.unparse(
            transformed_tree
        )

        # --- Minimal patch via surgical splicing (fall back to full unparse) ---
        # Surgical splicing replaces only the matched statement span, so it is
        # skipped when the transformer changed multiple statements (e.g. all
        # open() calls wrapped by the PATH_TRAVERSAL fixer).
        surgically_patched = None
        if getattr(transformer, "wrapped_opens", 0) <= 1:
            anchor_line = transformer.original_lineno or transformer.target_line
            new_segment = _find_transformed_segment(
                transformed_tree,
                anchor_line,
                skip_names=_INJECTED_TOP_LEVEL_NAMES,
            )
            surgically_patched = _splice_patched_code(
                code,
                transformer,
                new_segment,
                helper_src,
                all_required,
            )
        base_code = surgically_patched if surgically_patched is not None else patched_code

        diff = "".join(
            difflib.unified_diff(
                code.splitlines(keepends=True),
                base_code.splitlines(keepends=True),
                fromfile="before.py",
                tofile="after.py",
            )
        )

        return {
            "patched_code": base_code,
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
            "error": "Patch fixer failed — internal error",
        }


def _find_transformed_segment(tree, anchor_line, skip_names=frozenset()):
    """Walk the AST tree and find a statement-level node containing anchor_line."""
    _STATEMENT_NODES = (ast.Assign, ast.AnnAssign, ast.AugAssign, ast.Expr, ast.Return,
                        ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.If,
                        ast.For, ast.While, ast.With, ast.Try, ast.Import, ast.ImportFrom)

    class Finder(ast.NodeVisitor):
        def __init__(self):
            self.found = None

        def _is_injected(self, node):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                return node.name in skip_names
            if isinstance(node, ast.Assign):
                return any(isinstance(t, ast.Name) and t.id in skip_names for t in node.targets)
            return bool(isinstance(node, (ast.Import, ast.ImportFrom)))

        def visit(self, node):
            if self._is_injected(node):
                return
            self.generic_visit(node)
            if self.found is not None:
                return
            if isinstance(node, _STATEMENT_NODES) and hasattr(node, 'lineno'):
                end = getattr(node, 'end_lineno', node.lineno)
                if node.lineno <= anchor_line <= end:
                    self.found = node
    finder = Finder()
    finder.visit(tree)
    return ast.unparse(finder.found) if finder.found else None