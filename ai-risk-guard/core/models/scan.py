"""
core/models/scan.py
Strict Pydantic v2 data models for security scans.
"""

from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field

from core.models.vulnerability import Vulnerability


class ScanResult(BaseModel):
    model_config = ConfigDict(
        json_encoders={datetime: lambda v: v.isoformat()}
    )

    success: bool = Field(
        ..., 
        description="Indicates if the scan completed successfully without parsing errors or crashes"
    )
    file_path: str = Field(
        ..., 
        description="The absolute path of the scanned file"
    )
    vulnerabilities: list[Vulnerability] = Field(
        default_factory=list, 
        description="A list of identified vulnerabilities during the scan"
    )
    scan_duration_seconds: float | None = Field(
        None, 
        description="The time taken to perform the scan in seconds"
    )
    scanned_at: datetime = Field(
        default_factory=lambda: datetime.now(tz=UTC), 
        description="UTC Timestamp when the scan took place"
    )
