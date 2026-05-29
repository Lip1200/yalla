#!/usr/bin/env python3
"""Generate the ANON_KEY and SERVICE_ROLE_KEY for the self-hosted
Supabase stack.

Both keys are JWTs signed with the same JWT_SECRET as GoTrue +
PostgREST. The only difference is the `role` claim: `anon` for the
public key (safe to ship in clients), `service_role` for the backend
key (bypasses RLS — keep secret).

Usage:
    uv run python deploy/self-hosted/scripts/gen-jwt.py "$JWT_SECRET"
    uv run python deploy/self-hosted/scripts/gen-jwt.py "$JWT_SECRET" --years 10

Prints two lines to stdout — paste them into .env.
"""

import argparse
import sys
from datetime import datetime, timedelta, timezone

try:
    import jwt  # PyJWT
except ImportError:
    sys.stderr.write(
        "PyJWT not installed. Run: uv add --dev pyjwt   (or pip install pyjwt)\n"
    )
    sys.exit(1)


def make_token(secret: str, role: str, years: int) -> str:
    """Sign a long-lived JWT with the role claim Supabase expects."""
    now = datetime.now(tz=timezone.utc)
    payload = {
        "iss": "supabase",
        "ref": "self-hosted",
        "role": role,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(days=365 * years)).timestamp()),
    }
    return jwt.encode(payload, secret, algorithm="HS256")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("jwt_secret", help="Same value as JWT_SECRET in .env")
    parser.add_argument(
        "--years", type=int, default=10, help="Token lifetime (default 10y)"
    )
    args = parser.parse_args()

    anon = make_token(args.jwt_secret, "anon", args.years)
    service = make_token(args.jwt_secret, "service_role", args.years)

    print(f"ANON_KEY={anon}")
    print(f"SERVICE_ROLE_KEY={service}")


if __name__ == "__main__":
    main()
