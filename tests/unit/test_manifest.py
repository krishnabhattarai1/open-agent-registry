"""Unit tests for the agent card manifest schema."""

import pytest
from pydantic import ValidationError

from oar.schemas.manifest import AgentManifest


VALID_MANIFEST = {
    "oar": "1.0",
    "name": "code-reviewer",
    "description": "Reviews PRs for bugs",
    "version": "0.1.0",
    "publisher": "acme-corp",
    "capabilities": [
        {"code": "code.review", "input_types": ["text/plain"], "output_types": ["application/json"]}
    ],
    "endpoints": [
        {"protocol": "a2a", "url": "https://agent.example.com/.well-known/agent.json"}
    ],
}


def test_valid_manifest():
    m = AgentManifest.model_validate(VALID_MANIFEST)
    assert m.name == "code-reviewer"
    assert len(m.capabilities) == 1
    assert m.capabilities[0].code == "code.review"


def test_invalid_capability_code():
    bad = {**VALID_MANIFEST, "capabilities": [{"code": "not.a.real.code"}]}
    with pytest.raises(ValidationError) as exc:
        AgentManifest.model_validate(bad)
    assert "Unknown capability code" in str(exc.value)


def test_invalid_version():
    bad = {**VALID_MANIFEST, "version": "not-semver"}
    with pytest.raises(ValidationError):
        AgentManifest.model_validate(bad)


def test_unsupported_oar_version():
    bad = {**VALID_MANIFEST, "oar": "2.0"}
    with pytest.raises(ValidationError) as exc:
        AgentManifest.model_validate(bad)
    assert "Unsupported manifest version" in str(exc.value)


def test_optional_fields():
    minimal = {
        "oar": "1.0",
        "name": "minimal-agent",
        "description": "A minimal agent",
        "version": "1.0.0",
        "publisher": "test-pub",
    }
    m = AgentManifest.model_validate(minimal)
    assert m.tags == []
    assert m.capabilities == []
    assert m.endpoints == []
    assert m.status == "active"
