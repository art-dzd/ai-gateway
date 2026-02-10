"""CLI утилита (создание клиентских API ключей)."""

import argparse
import secrets
import sys
import uuid

import bcrypt
from sqlalchemy.orm import Session

from ai_gateway.db.models import ApiKey
from ai_gateway.infrastructure.db import SessionLocal


def cmd_create_key(args: argparse.Namespace) -> int:
    """Создаёт API ключ и сохраняет bcrypt-хэш секрета в БД (сам ключ печатаем один раз)."""
    key_id = uuid.uuid4().hex
    secret = secrets.token_urlsafe(32)
    plaintext = f"agw_{key_id}.{secret}"
    key_hash = bcrypt.hashpw(secret.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    session: Session = SessionLocal()
    try:
        api_key = ApiKey(
            name=args.name,
            key_id=key_id,
            key_hash=key_hash,
            rpm_limit=args.rpm_limit,
            daily_budget_rub=args.daily_budget_rub,
            monthly_budget_rub=args.monthly_budget_rub,
            is_active=True,
        )
        session.add(api_key)
        session.commit()

        print("API key создан.")
        print(f"ID: {api_key.id}")
        print("Ключ (показываю один раз):")
        print(plaintext)
        return 0
    finally:
        session.close()


def main(argv: list[str] | None = None) -> int:
    """Точка входа CLI."""
    parser = argparse.ArgumentParser(prog="ai-gateway", description="AI Gateway: CLI")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_create = sub.add_parser("create-key", help="Создать клиентский API key")
    p_create.add_argument("--name", required=True, help="Название ключа (для себя)")
    p_create.add_argument(
        "--rpm-limit",
        type=int,
        default=None,
        help="Лимит запросов в минуту (RPM)",
    )
    p_create.add_argument(
        "--daily-budget-rub",
        type=float,
        default=None,
        help="Дневной бюджет (RUB)",
    )
    p_create.add_argument(
        "--monthly-budget-rub",
        type=float,
        default=None,
        help="Месячный бюджет (RUB)",
    )
    p_create.set_defaults(func=cmd_create_key)

    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
