from alembic import op
import sqlalchemy as sa

# Идентификаторы миграции
revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None

def upgrade():
    # 1) Делаем appointments.name nullable
    op.alter_column(
        "appointments",
        "name",
        existing_type=sa.TEXT(),
        nullable=True
    )

    # 2) Индекс для быстрого поиска конфликтов (дата + сервис)
    op.create_index(
        "ix_appt_date_service",
        "appointments",
        ["date", "service_id"],
        unique=False
    )

    # 3) Сидирование справочника услуг
    op.execute("""
        INSERT INTO services (name, duration_min, price) VALUES
          ('Стрижка', 60, 100000),
          ('Укладка', 45, 80000),
          ('Окрашивание', 120, 250000)
        ON CONFLICT DO NOTHING;
    """)


def downgrade():
    # 1) Возвращаем name в NOT NULL
    op.alter_column(
        "appointments",
        "name",
        existing_type=sa.TEXT(),
        nullable=False
    )

    # 2) Убираем индекс
    op.drop_index("ix_appt_date_service", table_name="appointments")

    # 3) Чистим seeded услуги (по желанию)
    op.execute("""
        DELETE FROM services
        WHERE name IN ('Стрижка', 'Укладка', 'Окрашивание');
    """)
