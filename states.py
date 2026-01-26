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
