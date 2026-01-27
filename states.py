from aiogram.fsm.state import State, StatesGroup

class InventoryState(StatesGroup):
    fill_item = State()

class FeedbackState(StatesGroup):
    write_message = State()

class AdminReplyState(StatesGroup):
    write_reply = State()

class OrderState(StatesGroup):
    choose_item = State()
    enter_qty = State()

class AdminPanelState(StatesGroup):
    broadcast_msg = State()
    select_target = State()
    
    # Contacts
    contact_dept = State()
    contact_info = State()

    # Auto inventory settings
    auto_start_day = State()
    auto_end_day = State()
    
    # Ticket Reply
    ticket_reply_id = State()
    ticket_reply_msg = State()

class AdminBranchState(StatesGroup):
    add_name = State()
    edit_name = State()

class AdminItemState(StatesGroup):
    add_name = State()
    edit_name = State()

class AdminContactState(StatesGroup):
    add_dept = State()
    add_info = State()
    edit_dept = State()
    edit_info = State()

class RegistrationState(StatesGroup):
    select_sector = State()
