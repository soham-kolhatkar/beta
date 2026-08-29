"""Idempotent dev-only seed script.

Phase 1 scope: just enough `users` rows to exercise login end-to-end.
Phase 2 will extend this same script with the full academic graph
(institutions, academic years, branches, divisions, subjects, classes,
enrollments) per docs/PLAN.md.

Usage: uv run python scripts/seed.py
"""

import asyncio

from app.core.database import AsyncSessionLocal
from app.core.security import hash_password
from app.models.user import User, UserRole
from app.repositories import user_repository

# Dev-only known passwords. Never use this pattern in production — real
# account creation belongs to an admin-driven process (docs/PRODUCT.md §4).
SEED_USERS = [
    {
        "email": "student@example.com",
        "password": "password123",
        "name": "Aarav Sharma",
        "role": UserRole.STUDENT,
    },
    {
        "email": "faculty@example.com",
        "password": "password123",
        "name": "Professor XYZ",
        "role": UserRole.FACULTY,
    },
    {
        "email": "admin@example.com",
        "password": "password123",
        "name": "Admin User",
        "role": UserRole.ADMIN,
    },
]


async def seed() -> None:
    async with AsyncSessionLocal() as db:
        for entry in SEED_USERS:
            existing = await user_repository.get_by_email(db, entry["email"])
            password_hash = hash_password(entry["password"])

            if existing is None:
                db.add(
                    User(
                        email=entry["email"].strip().lower(),
                        password_hash=password_hash,
                        name=entry["name"],
                        role=entry["role"],
                        is_active=True,
                    )
                )
                print(f"created {entry['email']} ({entry['role'].value})")
            else:
                existing.password_hash = password_hash
                existing.name = entry["name"]
                existing.role = entry["role"]
                existing.is_active = True
                print(f"updated {entry['email']} ({entry['role'].value})")

        await db.commit()


if __name__ == "__main__":
    asyncio.run(seed())
