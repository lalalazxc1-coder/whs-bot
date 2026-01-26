import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")

# Админы (все еще нужны для команд типа /add_branch, но можно разрешить всем в группе, если хотите)
admin_ids_str = os.getenv("ADMIN_IDS", "")
ADMIN_IDS = [int(x.strip()) for x in admin_ids_str.split(",") if x.strip().isdigit()]

# ID группы поддержки (обязательно начинается с -100 для супергрупп)
group_id = os.getenv("SUPPORT_GROUP_ID", "")
SUPPORT_GROUP_ID = int(group_id) if group_id.lstrip("-").isdigit() else None

questions_id = os.getenv("QUESTIONS_GROUP_ID", "")
QUESTIONS_GROUP_ID = int(questions_id) if questions_id.lstrip("-").isdigit() else None
