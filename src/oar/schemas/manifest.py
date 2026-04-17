"""Agent card manifest schema — validated on CLI and API ingest.

This is the YAML format agent developers maintain in their repos.
"""

from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

from oar.taxonomy import validate_codes

STATUS = Literal["active", "deprecated", "archived"]
PROTOCOL = Literal["a2a", "mcp", "acp", "rest", "grpc"]
AUTH_TYPE = Literal["bearer", "api_key", "oauth2", "none"]


class ManifestCapability(BaseModel):
    code: str = Field(..., description="Taxonomy code e.g. code.review")
    input_types: list[str] | None = None
    output_types: list[str] | None = None

    @model_validator(mode="after")
    def validate_code(self) -> "ManifestCapability":
        invalid = validate_codes([self.code])
        if invalid:
            raise ValueError(f"Unknown capability code: {self.code!r}. Run `oar taxonomy` for valid codes.")
        return self


class ManifestAuth(BaseModel):
    type: AUTH_TYPE
    config: dict[str, Any] | None = None


class ManifestEndpoint(BaseModel):
    protocol: PROTOCOL
    url: str
    auth: ManifestAuth | None = None


class AgentManifest(BaseModel):
    """The agent-card.yaml format."""

    oar: str = Field(..., description="Manifest format version, e.g. '1.0'")
    name: str = Field(..., max_length=255)
    description: str
    version: str = Field(..., pattern=r"^\d+\.\d+\.\d+.*$")
    publisher: str = Field(..., description="Publisher slug")
    homepage: str | None = None
    repository: str | None = None
    license: str | None = None
    status: STATUS = "active"
    tags: list[str] = []
    capabilities: list[ManifestCapability] = []
    endpoints: list[ManifestEndpoint] = []

    @model_validator(mode="after")
    def validate_oar_version(self) -> "AgentManifest":
        if not self.oar.startswith("1"):
            raise ValueError(f"Unsupported manifest version: {self.oar!r}. Only 1.x supported.")
        return self
