"""Seed 3 utenti di default nel database."""
import asyncio
import os

from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.models.user import User

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

USERS = [
    {"username": "retail_user", "password": "retail", "role": "retail"},
    {"username": "compliance_user", "password": "compliance_lead", "role": "compliance"},
    {"username": "admin", "password": "admin", "role": "admin"},
]


async def run(database_url: str) -> None:
    engine = create_async_engine(database_url)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with session_factory() as session:
        for u in USERS:
            session.add(
                User(
                    username=u["username"],
                    password_hash=pwd_context.hash(u["password"]),
                    role=u["role"],
                )
            )
        await session.commit()

    print(f"Seeded {len(USERS)} users")
    await engine.dispose()


def main() -> None:
    database_url = os.environ.get(
        "DATABASE_URL",
        "postgresql+asyncpg://finassist:finassist_dev_password@localhost:5433/finassist",
    )
    asyncio.run(run(database_url))


if __name__ == "__main__":
    main()
