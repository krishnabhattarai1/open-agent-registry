"""SQLAlchemy models."""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


from oar.models.publisher import Publisher  # noqa: E402, F401
from oar.models.agent import Agent, AgentVersion, Capability, AgentEndpoint  # noqa: E402, F401
from oar.models.tag import Tag, agent_tags  # noqa: E402, F401
from oar.models.api_key import ApiKey, ApiKeyUsageLog  # noqa: E402, F401
