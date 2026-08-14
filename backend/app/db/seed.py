import asyncio
import os
from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.models.user import User, UserRole
from app.core.security import hash_password


async def seed_admin() -> None:
    admin_email = os.getenv("ADMIN_EMAIL")
    admin_password = os.getenv("ADMIN_PASSWORD")
    if not admin_email or not admin_password:
        return
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.email == admin_email))
        if result.scalar_one_or_none() is None:
            db.add(User(
                email=admin_email,
                username="admin",
                hashed_password=hash_password(admin_password),
                role=UserRole.SUPER_ADMIN,
                is_verified=True,
            ))
            await db.commit()


async def main() -> None:
    await seed_admin()


if __name__ == "__main__":
    asyncio.run(main())
