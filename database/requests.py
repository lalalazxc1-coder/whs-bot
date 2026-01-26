from datetime import datetime, timedelta
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from database.models import async_session, User, Branch, Item, InventoryReport, FeedbackTicket, DepartmentContact

async def get_branches():
    async with async_session() as session:
        result = await session.execute(select(Branch))
        return result.scalars().all()

async def get_branch_by_id(branch_id: int):
    async with async_session() as session:
        return await session.get(Branch, branch_id)

async def add_branch(name: str):
    async with async_session() as session:
        branch = Branch(name=name)
        session.add(branch)
        await session.commit()
        return branch

async def get_active_items():
    async with async_session() as session:
        result = await session.execute(select(Item).where(Item.is_active == True))
        return result.scalars().all()

async def add_item(name: str):
    async with async_session() as session:
        item = Item(name=name)
        session.add(item)
        await session.commit()
        return item

async def get_user(telegram_id: int):
    async with async_session() as session:
        # Используем selectinload для подгрузки связанного branch, чтобы не было ошибок Lazy load
        stmt = select(User).where(User.telegram_id == telegram_id).options(selectinload(User.branch))
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

async def add_user(telegram_id: int):
    async with async_session() as session:
        user = await session.get(User, telegram_id)
        if not user:
            user = User(telegram_id=telegram_id)
            session.add(user)
            await session.commit()
        return user

async def update_user_branch(telegram_id: int, branch_id: int):
    async with async_session() as session:
        user = await session.get(User, telegram_id)
        if user:
            user.selected_branch_id = branch_id
            await session.commit()

async def update_user_language(telegram_id: int, language: str):
    async with async_session() as session:
        user = await session.get(User, telegram_id)
        if user:
            user.language = language
            await session.commit()

async def save_report(user_id: int, branch_name: str, report_text: str, user_name: str = None):
    async with async_session() as session:
        report = InventoryReport(
            user_id=user_id, 
            branch_name=branch_name, 
            report_data=report_text,
            user_name=user_name
        )
        session.add(report)
        await session.commit()

async def get_last_reports(limit: int = 5):
    async with async_session() as session:
        result = await session.execute(
            select(InventoryReport).order_by(InventoryReport.timestamp.desc()).limit(limit)
        )
        return result.scalars().all()

# --- Tickets ---
async def create_ticket(user_id: int, user_name: str, branch_name: str, message: str):
    async with async_session() as session:
        ticket = FeedbackTicket(
            user_id=user_id, 
            user_name=user_name, 
            branch_name=branch_name, 
            message=message,
            status="open"
        )
        session.add(ticket)
        await session.commit()
        return ticket.id

async def get_open_tickets():
    async with async_session() as session:
        result = await session.execute(
            select(FeedbackTicket).where(FeedbackTicket.status == "open").order_by(FeedbackTicket.created_at)
        )
        return result.scalars().all()

async def get_ticket(ticket_id: int):
    async with async_session() as session:
        return await session.get(FeedbackTicket, ticket_id)

async def close_ticket(ticket_id: int, reply_text: str = None, responder_id: int = None, responder_name: str = None):
    async with async_session() as session:
        ticket = await session.get(FeedbackTicket, ticket_id)
        if ticket:
            ticket.status = "closed"
            if reply_text:
                ticket.reply_message = reply_text
                ticket.reply_at = datetime.utcnow()
            if responder_id:
                ticket.responder_id = responder_id
            if responder_name:
                ticket.responder_name = responder_name
            await session.commit()
# --- Admin / Panel ---

async def get_all_users():
    async with async_session() as session:
        result = await session.execute(select(User))
        return result.scalars().all()

async def get_users_by_branch(branch_id: int):
    async with async_session() as session:
        result = await session.execute(select(User).where(User.selected_branch_id == branch_id))
        return result.scalars().all()

async def get_reports_by_range(days: int = 7):
    async with async_session() as session:
        query = select(InventoryReport).order_by(InventoryReport.timestamp.desc())
        
        if days and days > 0:
            cutoff = datetime.utcnow() - timedelta(days=days)
            query = query.where(InventoryReport.timestamp >= cutoff)
            
        result = await session.execute(query)
        return result.scalars().all()

async def get_tickets_by_range(days: int = 7):
    async with async_session() as session:
        query = select(FeedbackTicket).order_by(FeedbackTicket.created_at.desc())
        
        if days and days > 0:
            cutoff = datetime.utcnow() - timedelta(days=days)
            query = query.where(FeedbackTicket.created_at >= cutoff)
            
        result = await session.execute(query)
        return result.scalars().all()

# --- Contacts ---
async def get_contacts():
    async with async_session() as session:
        result = await session.execute(select(DepartmentContact))
        return result.scalars().all()

async def add_contact(department: str, info: str):
    async with async_session() as session:
        contact = DepartmentContact(department=department, info=info)
        session.add(contact)
        await session.commit()
        return contact

async def delete_contact(contact_id: int):
    async with async_session() as session:
        contact = await session.get(DepartmentContact, contact_id)
        if contact:
            await session.delete(contact)
            await session.commit()
            return True
        return False
