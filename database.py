from __future__ import annotations
import datetime as dt
from typing import Optional

from sqlalchemy import String, Text, DateTime, func, select
from sqlalchemy.dialects.postgresql import BIGINT
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from config import DATABASE_URL

# --- SQLAlchemy base ---
class Base(DeclarativeBase):
    pass

class AppointmentStatus:
    PENDING = "Ожидание"
    CONFIRMED = "Подтверждено"
    CANCELLED = "Отменено"

class Appointment(Base):
    __tablename__ = "appointments"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BIGINT, index=True)
    name: Mapped[str] = mapped_column(Text)
    service: Mapped[str] = mapped_column(Text)
    date: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), index=True)
    status: Mapped[str] = mapped_column(String(32), index=True, default=AppointmentStatus.PENDING)
    event_id: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


# --- Engine / Session ---
engine = create_async_engine(DATABASE_URL, echo=False, pool_pre_ping=True)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)

async def init_db() -> None:
    """Проверка соединения и (временно) создание таблиц.
    В проде таблицы создаём Alembic-миграциями; здесь можно оставить на первый запуск.
    """
    async with engine.begin() as conn:
        # ВРЕМЕННО: создать таблицы, пока не включили Alembic
        await conn.run_sync(Base.metadata.create_all)
    print("✅ База данных (PostgreSQL) инициализирована!")

# --- CRUD (async) ---

async def add_appointment(
    user_id: int, name: str, service: str, date: dt.datetime, status: str = AppointmentStatus.PENDING
) -> int:
    """Добавляет запись. Возвращает ID."""
    appt = Appointment(user_id=user_id, name=name, service=service, date=date, status=status)
    async with AsyncSessionLocal() as session:
        session.add(appt)
        await session.commit()
        await session.refresh(appt)
        return appt.id

# ✅ Возвращаем именно ORM-объекты Appointment
async def get_appointments() -> list[Appointment]:
    async with AsyncSessionLocal() as session:
        res = await session.execute(select(Appointment).order_by(Appointment.date.asc()))
        return list(res.scalars())



async def get_appointment_by_id(appointment_id: int) -> Optional[Appointment]:
    async with AsyncSessionLocal() as session:
        res = await session.execute(select(Appointment).where(Appointment.id == appointment_id))
        return res.scalar_one_or_none()

async def update_appointment_status(appointment_id: int, new_status: str) -> bool:
    async with AsyncSessionLocal() as session:
        appt = await session.get(Appointment, appointment_id)
        if not appt:
            print(f"⚠️ Запись ID {appointment_id} не найдена!")
            return False
        appt.status = new_status
        await session.commit()
        return True

async def update_appointment(appointment_id: int, new_date: dt.datetime) -> bool:
    async with AsyncSessionLocal() as session:
        appt = await session.get(Appointment, appointment_id)
        if not appt:
            print(f"❌ Запись ID {appointment_id} не найдена!")
            return False
        appt.date = new_date
        await session.commit()
        return True

async def update_appointment_event_id(appointment_id: int, event_id: str) -> bool:
    async with AsyncSessionLocal() as session:
        appt = await session.get(Appointment, appointment_id)
        if not appt:
            print(f"⚠️ Запись ID {appointment_id} не найдена в БД!")
            return False
        if appt.event_id:
            print(f"⚠️ У записи уже есть event_id={appt.event_id}, обновление не требуется.")
            return False
        appt.event_id = event_id
        await session.commit()
        return True

async def delete_appointment(appointment_id: int) -> bool:
    async with AsyncSessionLocal() as session:
        appt = await session.get(Appointment, appointment_id)
        if not appt:
            print(f"⚠️ Запись ID {appointment_id} не найдена!")
            return False
        await session.delete(appt)
        await session.commit()
        return True
