"""
core/config/policy_config.py
Pydantic v2 model for security policy configuration.
"""


from pydantic import BaseModel, Field


class RestrictedFunctionArgConfig(BaseModel):
    function: str = Field(description="Fully qualified function name (e.g. hashlib.new)")
    arg_index: int = Field(0, description="Positional argument index to check")
    forbidden_values: list[str] = Field(description="Argument values that trigger a violation")
    violation_msg: str = Field("", description="Custom violation message")


class MandatoryCallWrapperConfig(BaseModel):
    target: str = Field(description="Function that must have its argument wrapped")
    wrappers: list[str] = Field(description="Acceptable wrapper function names (e.g. validate_url_ssrf)")
    arg_index: int = Field(0, description="Positional argument index to check for wrapping")
    violation_msg: str = Field("", description="Custom violation message")


class ForbiddenAssignmentConfig(BaseModel):
    pattern: str = Field(description="Glob pattern for variable names (e.g. *password*)")
    violation_msg: str = Field("", description="Custom violation message")


class MandatoryQueryParamConfig(BaseModel):
    function: str = Field(description="Method name that needs parameterized queries (e.g. execute)")
    param_arg_index: int = Field(0, description="Positional argument index for query params")
    violation_msg: str = Field("", description="Custom violation message")


class PolicyConfig(BaseModel):
    policy_name: str = Field("Standard Enterprise Security Policy", description="Policy identifier")
    version: str = Field("1.0", description="Policy version")
    description: str = Field("Default security guardrails for Python applications.", description="Policy description")
    forbidden_modules: list[str] = Field(
        default_factory=lambda: ["marshal", "shelve", "telnetlib"],
        description="Modules that are banned from import"
    )
    forbidden_functions: list[str] = Field(
        default_factory=lambda: ["os.system", "os.popen", "eval", "exec", "hashlib.md5", "hashlib.sha1"],
        description="Functions that are banned from use"
    )
    mandatory_sanitizers: dict[str, list[str]] = Field(
        default_factory=lambda: {
            "subprocess.run": ["shell=False"],
            "subprocess.Popen": ["shell=False"],
        },
        description="Required keyword arguments for specific function calls"
    )
    sensitive_paths: list[str] = Field(
        default_factory=lambda: ["auth/", "secrets/", "credentials/", "billing/"],
        description="File path patterns considered sensitive"
    )
    restricted_function_args: list[RestrictedFunctionArgConfig] = Field(
        default_factory=list,
        description="Check function call arguments for forbidden values (e.g. hashlib.new('md5'))"
    )
    mandatory_call_wrappers: list[MandatoryCallWrapperConfig] = Field(
        default_factory=list,
        description="Require wrapper functions around arguments of sensitive calls"
    )
    forbidden_assignments: list[ForbiddenAssignmentConfig] = Field(
        default_factory=list,
        description="Patterns for variable names that must not be assigned string literals"
    )
    mandatory_query_params: list[MandatoryQueryParamConfig] = Field(
        default_factory=list,
        description="Require parameterized queries for database execute calls"
    )
