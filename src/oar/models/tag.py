"""Tag model — free-form tagging for agents."""

from sqlalchemy import Column, ForeignKey, Integer, String, Table

from oar.models import Base

agent_tags = Table(
    "agent_tags",
    Base.metadata,
    Column("agent_id", ForeignKey("agents.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", ForeignKey("tags.id"), primary_key=True),
)


class Tag(Base):
    __tablename__ = "tags"

    id: int = Column(Integer, primary_key=True, autoincrement=True)  # type: ignore[assignment]
    name: str = Column(String(100), nullable=False, unique=True, index=True)  # type: ignore[assignment]
