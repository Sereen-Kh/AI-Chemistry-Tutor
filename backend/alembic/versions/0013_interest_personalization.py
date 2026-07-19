"""Seed canonical interests and make user-interest selections unique.

Revision ID: 0013_interest_personalization
Revises: 0012_curriculum_entity_mappings
Create Date: 2026-07-16
"""

from __future__ import annotations

from collections.abc import Iterable

from alembic import op
import sqlalchemy as sa

revision = "0013_interest_personalization"
down_revision = "0012_curriculum_entity_mappings"
branch_labels = None
depends_on = None

INTERESTS = (
    {"key": "daily_life", "name_ar": "الحياة اليومية", "name_en": "Daily life", "icon": "house", "display_order": 10},
    {"key": "laboratory", "name_ar": "المختبر", "name_en": "Laboratory", "icon": "flask-conical", "display_order": 20},
    {"key": "nature", "name_ar": "الطبيعة", "name_en": "Nature", "icon": "leaf", "display_order": 30},
    {"key": "football", "name_ar": "كرة القدم", "name_en": "Football", "icon": "trophy", "display_order": 40},
    {"key": "cars", "name_ar": "السيارات", "name_en": "Cars", "icon": "car", "display_order": 50},
    {"key": "cooking", "name_ar": "الطبخ", "name_en": "Cooking", "icon": "cooking-pot", "display_order": 60},
    {"key": "gaming", "name_ar": "الألعاب", "name_en": "Gaming", "icon": "gamepad-2", "display_order": 70},
)


def _keys(value: object) -> list[str]:
    if not isinstance(value, Iterable) or isinstance(value, (str, bytes, dict)):
        return []
    return list(dict.fromkeys(str(item) for item in value if item))


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("interest_categories") or not inspector.has_table("user_interests"):
        return

    categories = sa.table(
        "interest_categories",
        sa.column("id", sa.Integer),
        sa.column("key", sa.String),
        sa.column("name_ar", sa.String),
        sa.column("name_en", sa.String),
        sa.column("icon", sa.String),
        sa.column("display_order", sa.Integer),
    )
    user_interests = sa.table(
        "user_interests",
        sa.column("id", sa.Integer),
        sa.column("user_id", sa.Integer),
        sa.column("interest_id", sa.Integer),
    )

    existing_keys = set(bind.execute(sa.select(categories.c.key)).scalars())
    missing = [payload for payload in INTERESTS if payload["key"] not in existing_keys]
    if missing:
        op.bulk_insert(categories, missing)

    category_ids = dict(bind.execute(sa.select(categories.c.key, categories.c.id)).all())
    existing_pairs = set(
        bind.execute(sa.select(user_interests.c.user_id, user_interests.c.interest_id)).all()
    )

    users = sa.table(
        "users",
        sa.column("id", sa.Integer),
        sa.column("student_interests", sa.JSON),
    )
    profile_by_user: dict[int, list[str]] = {}
    if inspector.has_table("student_profiles"):
        profiles = sa.table(
            "student_profiles",
            sa.column("user_id", sa.Integer),
            sa.column("student_interests", sa.JSON),
        )
        profile_by_user = {
            row.user_id: _keys(row.student_interests)
            for row in bind.execute(sa.select(profiles.c.user_id, profiles.c.student_interests))
        }

    new_rows: list[dict[str, int]] = []
    for row in bind.execute(sa.select(users.c.id, users.c.student_interests)):
        selected_keys = profile_by_user.get(row.id) or _keys(row.student_interests)
        for key in selected_keys:
            interest_id = category_ids.get(key)
            pair = (row.id, interest_id)
            if interest_id is not None and pair not in existing_pairs:
                existing_pairs.add(pair)
                new_rows.append({"user_id": row.id, "interest_id": interest_id})
    if new_rows:
        op.bulk_insert(user_interests, new_rows)

    bind.execute(
        sa.text(
            """
            DELETE FROM user_interests
            WHERE id NOT IN (
                SELECT MIN(id)
                FROM user_interests
                GROUP BY user_id, interest_id
            )
            """
        )
    )
    with op.batch_alter_table("user_interests") as batch_op:
        batch_op.create_unique_constraint(
            "uq_user_interests_user_interest",
            ["user_id", "interest_id"],
        )


def downgrade() -> None:
    bind = op.get_bind()
    if not sa.inspect(bind).has_table("user_interests"):
        return
    with op.batch_alter_table("user_interests") as batch_op:
        batch_op.drop_constraint("uq_user_interests_user_interest", type_="unique")
