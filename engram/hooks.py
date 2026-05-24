from sqlalchemy import Integer, desc, func, literal, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from . import models, schemas


def _json_array_contains_column(column, tag: str, dialect: str):
    """SQL expression testing whether a JSON array column contains *tag*."""
    if dialect in ("postgresql", "postgres"):
        return column.contains(tag)

    if dialect == "sqlite":
        je = func.json_each(column).table_valued("value").alias("je")  # noqa: E501
        tag_stmt = select(literal(1, type_=Integer)).select_from(je)
        return tag_stmt.where(je.c.value == tag).exists()

    return column.like(f"%{tag}%")


class MemoryRetrievalHooks:
    """
    Hooks for retrieving memory context at different stages
    of the agent lifecycle.
    """
    def __init__(self, session: AsyncSession):
        self.session = session

    async def session_start_hook(
        self, limit: int = 10
    ) -> schemas.SessionStartContext:
        """Return the N most-recent memory entries at session start."""
        q = (
            select(models.MemoryEntry)
            .order_by(desc(models.MemoryEntry.created_at))
            .limit(limit)
        )
        result = await self.session.execute(q)
        recent_memories = result.scalars().all()

        return schemas.SessionStartContext(
            recent_memories=[
                schemas.MemoryEntryResponse.model_validate(m)
                for m in recent_memories
            ]
        )

    async def per_message_hook(
        self, tags: list[str] | None = None, limit: int = 5
    ) -> schemas.MessageContext:
        """Return context for the current message with tag filtering + fallback."""
        tag_names = list(tags) if isinstance(tags, list) else []

        if tag_names:
            dialect = self.session.get_bind().dialect.name
            expr = [
                _json_array_contains_column(
                    models.MemoryEntry.tags, t, dialect
                )
                for t in tag_names
            ]
            q = (
                select(models.MemoryEntry)
                .where(or_(*expr))
                .order_by(desc(models.MemoryEntry.created_at))
                .limit(limit)
            )
            memories = (await self.session.execute(q)).scalars().all()

            if not memories:
                memories = (
                    await self.session.execute(
                        select(models.MemoryEntry)
                        .order_by(desc(models.MemoryEntry.created_at))
                        .limit(limit)
                    )
                ).scalars().all()
        else:
            memories = (
                await self.session.execute(
                    select(models.MemoryEntry)
                    .order_by(desc(models.MemoryEntry.created_at))
                    .limit(limit)
                )
            ).scalars().all()

        return schemas.MessageContext(
            relevant_memories=[
                schemas.MemoryEntryResponse.model_validate(m) for m in memories
            ]
        )
