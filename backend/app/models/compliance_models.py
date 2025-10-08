# Pydantic models for compliance data
from pydantic import BaseModel, Field,RootModel
from typing import List, Optional, Union
from dataclasses import dataclass, field


@dataclass
class RegistryCheck:
    """Individual registry value to check"""

    value_name: str
    expected_value: Union[str, int]
    description: str = ""


@dataclass
class ComplianceRule:
    """Represents a compliance rule for Windows system"""

    name: str
    description: str
    check_type: str
    check_path: str
    registry_key: Optional[str] = None
    registry_checks: List[RegistryCheck] = field(default_factory=list)
    expected_value: str = ""


@dataclass
class CheckResult:
    """Represents the result of a compliance check"""

    rule_name: str
    description: str
    check_type: str
    compliant: bool
    details: List[dict]
    error: Optional[str] = None


class RegistryCheck(BaseModel):
    value_name: str = Field(..., description="Name of the registry value")
    expected_value: str = Field(..., description="Expected value for compliance")


class ComplianceRuleForLLM(BaseModel):
    name: str = Field(..., description="Rule name derived from context")
    description: str = Field(
        ..., description="Short description of what this registry rule enforces"
    )
    check_type: str = Field("registry", description="Always 'registry' for these rules")
    registry_key: str = Field(
        ..., description="Registry path (e.g., HKLM\\Software\\...)"
    )
    registry_checks: List[RegistryCheck] = Field(
        ..., description="List of registry values and expected settings"
    )


class ComplianceRuleList(RootModel[List[ComplianceRuleForLLM]]):
    pass
