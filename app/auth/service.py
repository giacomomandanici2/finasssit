from datetime import datetime, timedelta, timezone

import jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.schemas import TokenResponse
from app.core.config import settings
from app.models.user import User

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AuthService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def register(
        self,
        username: str,
        password: str,
        role: str,
    ) -> User:
        result = await self.db.execute(select(User).where(User.username == username))
        if result.scalar_one_or_none() is not None:
            raise ValueError(f"Username '{username}' already exists")

        user = User(
            username=username,
            password_hash=pwd_context.hash(password),
            role=role,
        )
        self.db.add(user)
        await self.db.flush()
        await self.db.refresh(user)
        return user

    async def login(self, username: str, password: str) -> TokenResponse:
        result = await self.db.execute(select(User).where(User.username == username))
        user = result.scalar_one_or_none()

        if user is None or not pwd_context.verify(password, user.password_hash):
            raise ValueError("Invalid username or password")

        now = datetime.now(timezone.utc)
        expire = now + timedelta(minutes=settings.jwt_expire_minutes)
        payload = {
            "sub": str(user.id),
            "iat": now,
            "exp": expire,
            "role": user.role,
        }
        token = jwt.encode(
            payload,
            settings.jwt_secret,
            algorithm=settings.jwt_algorithm,
        )

        return TokenResponse(
            access_token=token,
            expires_in=int(settings.jwt_expire_minutes * 60),
            role=user.role,
        )
