from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field, field_serializer

from .output import DataValue, EngineOutput
from .yaml import BaseModelWithYamlSupport


class ValidationMismatch(BaseModel):
    field: str
    expected_type: str
    actual_type: str
    message: str


class SpecValidationResult(BaseModel):
    mismatches: list[ValidationMismatch] = Field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return len(self.mismatches) == 0


class FileValidationResult(BaseModel):
    """Validation result for a single HTML file."""

    file_name: str
    item_count: int
    errors: list[str] = Field(default_factory=list)

    @property
    def passed(self) -> bool:
        return not self.errors


class TrueValidationResult(BaseModel):
    """Aggregate validation result across all files."""

    file_results: list[FileValidationResult] = Field(default_factory=list)

    @property
    def total_files(self) -> int:
        return len(self.file_results)

    @property
    def total_items(self) -> int:
        return sum(result.item_count for result in self.file_results)

    @property
    def failures(self) -> int:
        return sum(1 for result in self.file_results if not result.passed)

    @property
    def passed(self) -> bool:
        return self.failures == 0


class FileExpectedItems(BaseModel):
    """Expected extraction results for a single example file."""

    file: str
    items: dict[str, DataValue]

    @classmethod
    def from_engine_output(cls, file_name: str, output: EngineOutput) -> FileExpectedItems:
        return cls(file=file_name, items=output.data)


class ExpectedResults(BaseModelWithYamlSupport):
    """Expected extraction output used to validate parser correctness.

    Stored as YAML alongside example data files.
    """

    version: int = 1
    data_path: Path | None = None
    files: list[FileExpectedItems]

    @field_serializer("data_path")
    def serialize_data_path(self, value: Path | None) -> str | None:
        """Serialize data_path as a string in YAML."""
        return str(value) if value is not None else None
