"""
Create the initial admin user.

The README documented default credentials but nothing in the repository
created them, so a fresh install had no way to sign in.

    python -m scripts.seed_admin
    python -m scripts.seed_admin --username ops --password 's3cret'
"""

import argparse
import os
import secrets
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.database import Base, SessionLocal, engine  # noqa: E402
from app.core.security import get_password_hash  # noqa: E402
from app.models import *  # noqa: F401,F403,E402 - register mappers
from app.models.user import User  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--username", default=os.getenv("ADMIN_USERNAME", "admin"))
    parser.add_argument("--email", default=os.getenv("ADMIN_EMAIL", "admin@woenv.local"))
    parser.add_argument("--full-name", default="Administrator")
    parser.add_argument(
        "--password",
        default=os.getenv("ADMIN_PASSWORD"),
        help="Defaults to ADMIN_PASSWORD, or a generated one printed once.",
    )
    parser.add_argument("--reset-password", action="store_true",
                        help="Reset the password if the user already exists.")
    args = parser.parse_args()

    Base.metadata.create_all(bind=engine)

    generated = False
    password = args.password
    if not password:
        password = secrets.token_urlsafe(12)
        generated = True

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == args.username).first()
        if user:
            if not args.reset_password:
                print(f"User {args.username!r} already exists. "
                      f"Pass --reset-password to change its password.")
                return 0
            user.hashed_password = get_password_hash(password)
            user.role = "admin"
            user.is_active = True
            db.commit()
            print(f"Password reset for {args.username!r}.")
        else:
            db.add(User(
                username=args.username,
                email=args.email,
                full_name=args.full_name,
                role="admin",
                is_active=True,
                hashed_password=get_password_hash(password),
            ))
            db.commit()
            print(f"Created admin user {args.username!r}.")

        if generated:
            print(f"\n  Generated password: {password}\n"
                  f"  Store it now - it is not shown again.\n")
    finally:
        db.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
