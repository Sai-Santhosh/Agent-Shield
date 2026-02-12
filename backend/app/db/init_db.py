"""Initialize database schema."""
import asyncio
import logging

from app.db.models import Base
from app.db.session import engine

logger = logging.getLogger(__name__)


async def init_db() -> None:
    """Create all tables."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database schema initialized")


if __name__ == "__main__":
    asyncio.run(init_db())
