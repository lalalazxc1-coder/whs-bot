from datetime import datetime, timedelta
from sqlalchemy import select, func
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
        item = Item(name=name, is_active=True)
        session.add(item)
        await session.commit()
        return item

async def get_item(item_id: int):
    async with async_session() as session:
        return await session.get(Item, item_id)

async def rename_item(item_id: int, new_name: str):
    async with async_session() as session:
        item = await session.get(Item, item_id)
        if item:
            item.name = new_name
            await session.commit()
            return True
        return False

async def delete_item(item_id: int):
    """Soft delete"""
    async with async_session() as session:
        item = await session.get(Item, item_id)
        if item:
            item.is_active = False
            await session.commit()
            return True
        return False

async def rename_branch(branch_id: int, new_name: str):
    async with async_session() as session:
        branch = await session.get(Branch, branch_id)
        if branch:
            branch.name = new_name
            await session.commit()
            return True
        return False

async def delete_branch(branch_id: int):
    async with async_session() as session:
        branch = await session.get(Branch, branch_id)
        if branch:
            # TODO: Handle users linked to this branch?
            # For now simply delete.
            await session.delete(branch)
            await session.commit()
            return True
        return False

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



async def get_last_reports(limit: int = 5):
    async with async_session() as session:
        result = await session.execute(
            select(InventoryReport).order_by(InventoryReport.timestamp.desc()).limit(limit)
        )
        return result.scalars().all()

# --- Tickets ---
async def create_ticket(user_id: int, user_name: str, branch_name: str, message: str, ticket_type: str = "problem"):
    async with async_session() as session:
        ticket = FeedbackTicket(
            user_id=user_id, 
            user_name=user_name, 
            branch_name=branch_name, 
            message=message,
            ticket_type=ticket_type,
            status="open"
        )
        session.add(ticket)
        await session.commit()
        return ticket.id

async def get_open_tickets(ticket_type: str = None):
    async with async_session() as session:
        stmt = select(FeedbackTicket).where(FeedbackTicket.status == "open")
        if ticket_type:
            stmt = stmt.where(FeedbackTicket.ticket_type == ticket_type)
        stmt = stmt.order_by(FeedbackTicket.created_at)
        result = await session.execute(stmt)
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
        result = await session.execute(select(User).options(selectinload(User.branch)))
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

async def get_contact(contact_id: int):
    async with async_session() as session:
        return await session.get(DepartmentContact, contact_id)

async def update_contact(contact_id: int, department: str, info: str):
    async with async_session() as session:
        contact = await session.get(DepartmentContact, contact_id)
        if contact:
            contact.department = department
            contact.info = info
            await session.commit()
            return True
        return False

# --- Statistics ---

async def count_users():
    async with async_session() as session:
        result = await session.execute(select(func.count(User.telegram_id)))
        return result.scalar()

async def count_reports(days: int = 0):
    async with async_session() as session:
        result = await session.execute(select(func.count(InventoryReport.id)))
        # Simple count for now, no filtering implemented in this quick add
        # If we need days filtering, we should add simple logic
        stmt = select(func.count(InventoryReport.id))
        if days > 0:
            cutoff = datetime.utcnow() - timedelta(days=days)
            stmt = stmt.where(InventoryReport.timestamp >= cutoff)
        result = await session.execute(stmt)
        return result.scalar()

async def count_tickets(ticket_type: str = None, status: str = None):
    async with async_session() as session:
        stmt = select(func.count(FeedbackTicket.id))
        if ticket_type:
             stmt = stmt.where(FeedbackTicket.ticket_type == ticket_type)
        if status:
             stmt = stmt.where(FeedbackTicket.status == status)
        result = await session.execute(stmt)
        return result.scalar()

async def count_orders():
    async with async_session() as session:
        stmt = select(func.count(FeedbackTicket.id)).where(FeedbackTicket.message.like("[ЗАКАЗ МАТЕРИАЛОВ]%"))
        result = await session.execute(stmt)
        return result.scalar()

async def count_branches():
    async with async_session() as session:
        result = await session.execute(select(func.count(Branch.id)))
        return result.scalar()

async def count_active_items():
    async with async_session() as session:
        result = await session.execute(select(func.count(Item.id)).where(Item.is_active == True))
        return result.scalar()

async def count_contacts():
    async with async_session() as session:
        result = await session.execute(select(func.count(DepartmentContact.id)))
        return result.scalar()

async def get_users_pending_report():
    """Возвращает пользователей, которые не сдали отчет за последние 24 часа"""
    async with async_session() as session:
        cutoff = datetime.utcnow() - timedelta(hours=24)
        # Subquery: ID пользователей, сдавших отчет
        subquery = select(InventoryReport.user_id).where(InventoryReport.timestamp >= cutoff)
        
        # Select users NOT IN subquery
        stmt = select(User).where(User.telegram_id.not_in(subquery))
        result = await session.execute(stmt)
        return result.scalars().all()

# --- Settings & Inventory Control ---

from database.models import GlobalSettings

async def set_setting(key: str, value: str):
    async with async_session() as session:
        setting = await session.get(GlobalSettings, key)
        if not setting:
            setting = GlobalSettings(key=key, value=value)
            session.add(setting)
        else:
            setting.value = value
        await session.commit()

async def get_setting(key: str, default: str = None):
    async with async_session() as session:
        setting = await session.get(GlobalSettings, key)
        return setting.value if setting else default

async def is_inventory_open():
    val = await get_setting("inventory_open", "0")
    return val == "1"

async def update_user_sector(telegram_id: int, sector: str):
    async with async_session() as session:
        user = await session.get(User, telegram_id)
        if user:
            user.sector = sector
            await session.commit()
            
async def save_report(user_id: int, branch_name: str, report_data: str, user_name: str = None, sector: str = "full"):
    async with async_session() as session:
        report = InventoryReport(
            user_id=user_id, 
            branch_name=branch_name, 
            report_data=report_data,
            user_name=user_name,
            sector=sector
        )
        session.add(report)
        await session.commit()
