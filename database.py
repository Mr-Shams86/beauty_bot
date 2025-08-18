# database.py
from __future__ import annotations
import datetime as dt
from decimal import Decimal
from typing import Optional, List

from sqlalchemy import (
    String, Text, DateTime, Numeric, func, select, ForeignKey, Integer, and_
)
from sqlalchemy.dialects.postgresql import BIGINT
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from config import DATABASE_URL

# ---------- Base ----------
class Base(DeclarativeBase):
    pass


# ---------- Dictionaries ----------
class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BIGINT, primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BIGINT, unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Service(Base):
    __tablename__ = "services"

    id: Mapped[int] = mapped_column(BIGINT, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    duration_min: Mapped[int] = mapped_column(Integer, nullable=False)
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)


# ---------- Appointments ----------
class AppointmentStatus:
    PENDING = "Ожидание"
    CONFIRMED = "Подтверждено"
    CANCELLED = "Отменено"


class Appointment(Base):
    __tablename__ = "appointments"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # !!! По текущей схеме: telegram_id пользователя, не FK на users.id
    user_id: Mapped[int] = mapped_column(BIGINT, index=True)

    # В БД поле name ЕСТЬ — оставляем для совместимости с текущими хендлерами
    name: Mapped[str] = mapped_column(Text, nullable=False)

    service_id: Mapped[Optional[int]] = mapped_column(BIGINT, ForeignKey("services.id"), index=True)
    duration_min: Mapped[Optional[int]] = mapped_column(Integer)

    # чтобы удобно получать название услуги
    service: Mapped[Optional[Service]] = relationship(lazy="joined")

    date: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), index=True)
    status: Mapped[str] = mapped_column(String(32), index=True, default=AppointmentStatus.PENDING)
    event_id: Mapped[Optional[str]] = mapped_column(Text)

    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


# ---------- Engine / Session ----------
# ВАЖНО: DATABASE_URL должен быть async-видом:
# postgresql+asyncpg://user:pass@postgres:5432/beautybot
engine = create_async_engine(DATABASE_URL, echo=False, pool_pre_ping=True)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


# ---------- Users CRUD ----------
async def upsert_user(telegram_id: int, name: str, phone: Optional[str] = None) -> User:
    async with AsyncSessionLocal() as s:
        res = await s.execute(select(User).where(User.telegram_id == telegram_id))
        user = res.scalar_one_or_none()
        if user:
            changed = False
            if name and user.name != name:
                user.name = name; changed = True
            if phone and user.phone != phone:
                user.phone = phone; changed = True
            if changed:
                await s.commit()
                await s.refresh(user)
            return user

        user = User(telegram_id=telegram_id, name=name or f"user_{telegram_id}", phone=phone)
        s.add(user)
        await s.commit()
        await s.refresh(user)
        return user


# ---------- Services CRUD ----------
async def get_service_by_id(service_id: int) -> Optional[Service]:
    async with AsyncSessionLocal() as s:
        res = await s.execute(select(Service).where(Service.id == service_id))
        return res.scalar_one_or_none()

async def get_service_by_name(name: str, *, partial: bool = False) -> Optional[Service]:
    async with AsyncSessionLocal() as s:
        cond = Service.name.ilike(f"%{name}%") if partial else Service.name.ilike(name)
        res = await s.execute(select(Service).where(cond))
        return res.scalar_one_or_none()

async def list_services() -> List[Service]:
    async with AsyncSessionLocal() as s:
        res = await s.execute(select(Service).order_by(Service.name.asc()))
        return list(res.scalars())


# ---------- Appointments CRUD ----------
async def add_appointment(user_id: int, service_id: int, date: dt.datetime, *, name: str) -> int:
    """
    user_id — telegram_id пользователя (историческое поле).
    name — отображаемое имя клиента (пока храним в appointments для совместимости).
    """
    async with AsyncSessionLocal() as s:
        svc = (await s.execute(select(Service).where(Service.id == service_id))).scalar_one_or_none()
        if not svc:
            raise ValueError("Service not found")

        appt = Appointment(
            user_id=user_id,
            name=name,
            service_id=svc.id,
            duration_min=svc.duration_min,
            date=date,
            status=AppointmentStatus.PENDING,
        )
        s.add(appt)
        await s.commit()
        await s.refresh(appt)
        return appt.id


async def get_appointments() -> List[Appointment]:
    async with AsyncSessionLocal() as s:
        res = await s.execute(select(Appointment).order_by(Appointment.date.asc()))
        return list(res.scalars())


async def get_future_appointments_by_user(
    telegram_id: int, now: Optional[dt.datetime] = None
) -> List[Appointment]:
    now = now or dt.datetime.now(dt.timezone.utc)
    async with AsyncSessionLocal() as s:
        res = await s.execute(
            select(Appointment)
            .where(Appointment.user_id == telegram_id, Appointment.date >= now)
            .order_by(Appointment.date.asc())
        )
        return list(res.scalars())


async def get_appointment_by_id(appointment_id: int) -> Optional[Appointment]:
    async with AsyncSessionLocal() as s:
        res = await s.execute(select(Appointment).where(Appointment.id == appointment_id))
        return res.scalar_one_or_none()


async def update_appointment_status(appointment_id: int, new_status: str) -> bool:
    async with AsyncSessionLocal() as s:
        appt = await s.get(Appointment, appointment_id)
        if not appt:
            return False
        appt.status = new_status
        await s.commit()
        return True


async def update_appointment(appointment_id: int, new_date: dt.datetime) -> bool:
    async with AsyncSessionLocal() as s:
        appt = await s.get(Appointment, appointment_id)
        if not appt:
            return False
        appt.date = new_date
        await s.commit()
        return True


async def update_appointment_event_id(appointment_id: int, event_id: str) -> bool:
    async with AsyncSessionLocal() as s:
        appt = await s.get(Appointment, appointment_id)
        if not appt or appt.event_id:
            return False
        appt.event_id = event_id
        await s.commit()
        return True


async def delete_appointment(appointment_id: int) -> bool:
    async with AsyncSessionLocal() as s:
        appt = await s.get(Appointment, appointment_id)
        if not appt:
            return False
        await s.delete(appt)
        await s.commit()
        return True


# ---------- Валидация слотов ----------
async def has_time_conflict(start: dt.datetime, duration_min: int) -> bool:
    """
    Проверка пересечения со СУЩЕСТВУЮЩИМИ (не отменёнными) слотами.
    Делаем предварительный SQL-фильтр по окну времени, а точную проверку — в Python.
    Это безопасно и просто, пока объём записей небольшой.
    """
    end = start + dt.timedelta(minutes=duration_min)
    window_before = dt.timedelta(hours=6)   # достаточно, чтобы сузить выборку
    window_after  = dt.timedelta(hours=6)

    async with AsyncSessionLocal() as s:
        q = (
            select(Appointment)
            .where(
                Appointment.status != AppointmentStatus.CANCELLED,
                Appointment.date >= (start - window_before),
                Appointment.date <= (end + window_after),
            )
            .order_by(Appointment.date.asc())
        )
        res = await s.execute(q)
        for a in res.scalars():
            a_end = a.date + dt.timedelta(minutes=(a.duration_min or 60))
            # пересечение интервалов [start, end) и [a.date, a_end)
            if (start < a_end) and (a.date < end):
                return True
        return False


# ---------- Локальная инициализация (только для первого запуска/локалки) ----------
async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("✅ База данных (PostgreSQL) инициализирована!")
