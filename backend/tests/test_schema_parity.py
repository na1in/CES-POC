"""
Guards against schema drift: every enum type in db/schema.sql (the SQL derived from the protos) must exist in the
database with exactly the same labels. The database under test is built by `alembic upgrade head`, so a value added to
schema.sql/protos without a migration fails here instead of failing at runtime.

This is what missed 'policy_attached': schema.sql and the proto had it, the migration did not, and the attach-policy
endpoint returned a 500 on every database built from migrations.
"""
import re
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

SCHEMA_SQL = Path(__file__).resolve().parents[2] / "db" / "schema.sql"


def _schema_enums() -> dict[str, list[str]]:
    sql = SCHEMA_SQL.read_text()
    enums = {}
    for name, body in re.findall(r"CREATE TYPE\s+(\w+)\s+AS ENUM\s*\((.*?)\)\s*;", sql, flags=re.S | re.I):
        body = re.sub(r"--[^\n]*", "", body)  # drop trailing comments
        enums[name] = re.findall(r"'([^']+)'", body)
    return enums


async def test_every_schema_enum_matches_the_database(db: AsyncSession):
    expected = _schema_enums()
    assert "audit_action_type" in expected and len(expected) >= 15, "schema.sql enum parsing found too little"

    rows = (await db.execute(text("""
        SELECT t.typname, e.enumlabel
        FROM pg_enum e JOIN pg_type t ON t.oid = e.enumtypid
    """))).all()
    actual: dict[str, set[str]] = {}
    for typname, label in rows:
        actual.setdefault(typname, set()).add(label)

    problems = []
    for name, labels in expected.items():
        if name not in actual:
            problems.append(f"{name}: type missing from the database")
            continue
        missing = set(labels) - actual[name]
        extra = actual[name] - set(labels)
        if missing:
            problems.append(f"{name}: in schema.sql but not in the database (needs a migration): {sorted(missing)}")
        if extra:
            problems.append(f"{name}: in the database but not in schema.sql: {sorted(extra)}")
    assert not problems, "schema.sql and the migrated database disagree:\n  " + "\n  ".join(problems)
