from pydantic import BaseModel, Field


class ValidationMismatch(BaseModel):
    field: str
    expected_type: str
    actual_type: str
    message: str


class ValidationResult(BaseModel):
    mismatches: list[ValidationMismatch] = Field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return len(self.mismatches) == 0
