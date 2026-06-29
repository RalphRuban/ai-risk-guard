
import pytest
from core.validator.security_rescan import SecurityRescanner

def test_security_rescan_clean_code():
    rescanner = SecurityRescanner()
    code = 'print("Hello World")'
    result = rescanner.rescan_code(code)
    assert result["success"] is True
    assert len(result["remaining_vulnerabilities"]) == 0

def test_security_rescan_vulnerable_code():
    rescanner = SecurityRescanner()
    code = 'import os\nos.system("ls")'
    result = rescanner.rescan_code(code)
    assert result["success"] is False
    assert len(result["remaining_vulnerabilities"]) > 0
    assert result["remaining_vulnerabilities"][0]["type"] == "COMMAND_INJECTION"
