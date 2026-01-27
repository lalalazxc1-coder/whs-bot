from datetime import datetime
from typing import List, Optional

from sqlalchemy import BigInteger, ForeignKey, String, Boolean, Text, DateTime, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.ext.asyncio import AsyncAttrs, async_sessionmaker, create_async_engine

# Вынесем Engine сюда, так как он нужен и моделям (для миграций/метадаты) и запросам
DATABASE_URL = "sqlite+aiosqlite:///./warehouse.db"
engine = create_async_engine(DATABASE_URL, echo=False)
async_session = async_sessionmaker(engine, expire_on_commit=False)

class Base(AsyncAttrs, DeclarativeBase):
    pass

class Branch(Base):
    __tablename__ = "branches"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String, unique=True)
    
    users: Mapped[List["User"]] = relationship(back_populates="branch")

class Item(Base):
    __tablename__ = "items"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String, unique=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

class User(Base):
    __tablename__ = "users"

    telegram_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    selected_branch_id: Mapped[Optional[int]] = mapped_column(ForeignKey("branches.id"), nullable=True)
    language: Mapped[str] = mapped_column(String, default="ru")
    sector: Mapped[str] = mapped_column(String, default="full") # oil, ap, full
    
    branch: Mapped[Optional["Branch"]] = relationship(back_populates="users")

class InventoryReport(Base):
    __tablename__ = "inventory_reports"

    id: Mapped[int] = mapped_column(primary_key=True)
    branch_name: Mapped[str] = mapped_column(String)
    user_id: Mapped[int] = mapped_column(BigInteger)
    user_name: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    report_data: Mapped[str] = mapped_column(Text)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    sector: Mapped[str] = mapped_column(String, default="full")

class GlobalSettings(Base):
    __tablename__ = "settings"
    
    key: Mapped[str] = mapped_column(String, primary_key=True)
    value: Mapped[str] = mapped_column(String)

class FeedbackTicket(Base):
    __tablename__ = "tickets"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger)
    user_name: Mapped[str] = mapped_column(String)
    branch_name: Mapped[str] = mapped_column(String)
    message: Mapped[str] = mapped_column(Text) # Текст обращения
    ticket_type: Mapped[str] = mapped_column(String, default="problem") # problem, question
    status: Mapped[str] = mapped_column(String, default="open") # open, closed
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    reply_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    reply_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    responder_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    responder_name: Mapped[Optional[str]] = mapped_column(String, nullable=True)

class DepartmentContact(Base):
    __tablename__ = "department_contacts"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    department: Mapped[str] = mapped_column(String) # IT, Logistics
    info: Mapped[str] = mapped_column(String) # +777 111... - Alex

from sqlalchemy import inspect

def check_and_migrate(connection):
    inspector = inspect(connection)
    
    # 1. Tickets (ticket_type)
    if inspector.has_table("tickets"):
        columns = [c['name'] for c in inspector.get_columns('tickets')]
        if 'ticket_type' not in columns:
            print("Migrating DB: Adding ticket_type column to tickets...")
            connection.execute(text("ALTER TABLE tickets ADD COLUMN ticket_type VARCHAR DEFAULT 'problem'"))

    # 2. Users (sector)
    if inspector.has_table("users"):
        columns = [c['name'] for c in inspector.get_columns('users')]
        if 'sector' not in columns:
            print("Migrating DB: Adding sector column to users...")
            connection.execute(text("ALTER TABLE users ADD COLUMN sector VARCHAR DEFAULT 'full'"))

    # 3. InventoryReports (sector)
    if inspector.has_table("inventory_reports"):
        columns = [c['name'] for c in inspector.get_columns('inventory_reports')]
        if 'sector' not in columns:
            print("Migrating DB: Adding sector column to inventory_reports...")
            connection.execute(text("ALTER TABLE inventory_reports ADD COLUMN sector VARCHAR DEFAULT 'full'"))
            
    # 4. Settings table check (handled by create_all, but good to know)
    if not inspector.has_table("settings"):
        print("Migrating DB: Creating settings table via create_all...")

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.run_sync(check_and_migrate)
