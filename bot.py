import telebot
import requests
import time
import threading
import json
import os
import random
import re
from datetime import datetime, timedelta

# ===== НАСТРОЙКИ =====
TOKEN = "8804412117:AAFClU1wzf_qQWymrcmEQ3_pVBCNdxOP1pM"
OWNER_ID = 8558737152
OWNER_USERNAME = "@Thecomingone16"
DB_FILE = "wall_db.json"
MAX_WARNS = 3

bot = telebot.TeleBot(TOKEN)

# ===== БАЗЫ ДАННЫХ =====
staff_data = {}
warns_data = {}
mutes_data = {}
bans_data = {}
chats_data = {}
message_history = {}
daily_stats = {}
user_profiles = {}
vip_data = {}
economy = {}
temp_data = {}
clans_data = {}  # {clan_name: {owner, members, bank, created}}
start_time = datetime.now()

VIP_LEVELS = {
    1: {"name": "VIP", "prefix": "[VIP]", "color": "🟣", "price": 10000},
    2: {"name": "VIP+", "prefix": "[VIP+]", "color": "🟡", "price": 50000},
    3: {"name": "LEGEND+", "prefix": "[LEGEND+]", "color": "🔴", "price": 150000},
}

VIP_COLORS = ["purple", "gold", "red", "blue", "green", "cyan", "pink", "white"]

DENY_PHRASES = [
    "Твой ранг недостаточен для этого действия.",
    "Цель выше или равна тебе по званию — запрос отклонён.",
    "Ты не можешь применять санкции к равному или старшему.",
    "Попытка засчитана, результат — нет.",
    "Только младший по рангу может быть наказан.",
    "Твои полномочия здесь заканчиваются.",
    "Этот человек находится не ниже тебя в иерархии.",
    "Отказано. Требуется ранг строго выше, чем у цели.",
    "Ты не можешь наказать того, кто равен или старше тебя.",
    "Субординация нарушена — действие заблокировано.",
    "Твой ранг не позволяет этого сделать.",
    "Цель защищена своим статусом.",
    "Повысь свой ранг, затем возвращайся.",
    "Недостаточно прав для наказания этой цели.",
    "Иерархия есть иерархия — запрос отменён.",
    "Равный не может наказать равного.",
    "Требуется превосходство по рангу.",
    "Твой уровень доступа не позволяет наказать эту цель.",
    "Действие доступно только против младших по званию.",
    "Статус цели не позволяет применить санкции.",
]

# ===== СОХРАНЕНИЕ И ЗАГРУЗКА =====
def save_all_data():
    clean_mutes = {}
    for uid, chats in mutes_data.items():
        clean_mutes[str(uid)] = {}
        for cid, dt in chats.items():
            clean_mutes[str(uid)][str(cid)] = dt.isoformat() if dt else None
    
    data = {
        "staff_data": staff_data,
        "warns_data": warns_data,
        "mutes_data": clean_mutes,
        "bans_data": bans_data,
        "chats_data": chats_data,
        "daily_stats": daily_stats,
        "user_profiles": user_profiles,
        "vip_data": vip_data,
        "economy": economy,
        "temp_data": temp_data_serializable(),
        "clans_data": clans_data
    }
    
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def temp_data_serializable():
    result = {}
    for uid, data in temp_data.items():
        result[str(uid)] = {}
        for key, value in data.items():
            if "until" in value and value["until"]:
                result[str(uid)][key] = {
                    "level": value["level"],
                    "until": value["until"].isoformat()
                }
            else:
                result[str(uid)][key] = value
    return result

def load_all_data():
    global staff_data, warns_data, mutes_data, bans_data, chats_data, daily_stats, user_profiles, vip_data, economy, temp_data, clans_data
    
    if not os.path.exists(DB_FILE):
        return
    
    try:
        with open(DB_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        staff_data = {int(cid): {int(uid): rank for uid, rank in chats.items()} for cid, chats in data.get("staff_data", {}).items()}
        warns_data = {int(uid): {int(cid): warns for cid, warns in chats.items()} for uid, chats in data.get("warns_data", {}).items()}
        bans_data = {int(uid): {int(cid): ban for cid, ban in chats.items()} for uid, chats in data.get("bans_data", {}).items()}
        
        mutes_data = {}
        for uid, chats in data.get("mutes_data", {}).items():
            mutes_data[int(uid)] = {}
            for cid, dt_str in chats.items():
                if dt_str:
                    mutes_data[int(uid)][int(cid)] = datetime.fromisoformat(dt_str)
        
        chats_data = {int(cid): chat for cid, chat in data.get("chats_data", {}).items()}
        daily_stats = {int(cid): stats for cid, stats in data.get("daily_stats", {}).items()}
        user_profiles = data.get("user_profiles", {})
        vip_data = data.get("vip_data", {})
        economy = data.get("economy", {})
        clans_data = data.get("clans_data", {})
        
        temp_data = {}
        for uid, items in data.get("temp_data", {}).items():
            temp_data[int(uid)] = {}
            for key, value in items.items():
                if "until" in value and value["until"]:
                    temp_data[int(uid)][key] = {
                        "level": value["level"],
                        "until": datetime.fromisoformat(value["until"])
                    }
                else:
                    temp_data[int(uid)][key] = value
        
        print("✅ Данные загружены!")
    except Exception as e:
        print(f"❌ Ошибка загрузки: {e}")

def check_temp_expired():
    now = datetime.now()
    for uid in list(temp_data.keys()):
        data = temp_data[uid]
        if "vip" in data and data["vip"].get("until") and data["vip"]["until"] < now:
            vip_data.pop(str(uid), None)
            del temp_data[uid]["vip"]
        if "rank" in data and data["rank"].get("until") and data["rank"]["until"] < now:
            for cid in list(staff_data.keys()):
                staff_data[cid].pop(uid, None)
            del temp_data[uid]["rank"]
        if uid in temp_data and not temp_data[uid]:
            del temp_data[uid]

def auto_save():
    while True:
        time.sleep(30)
        try:
            check_temp_expired()
            save_all_data()
        except Exception as e:
            print(f"❌ Ошибка сохранения: {e}")

# ===== ЭКОНОМИКА =====
def get_balance(user_id):
    uid = str(user_id)
    if uid not in economy:
        economy[uid] = {"balance": 0, "last_work": None, "last_daily": None}
    return economy[uid]

def add_bricks(user_id, amount):
    data = get_balance(user_id)
    data["balance"] += amount
    return data["balance"]

def spend_bricks(user_id, amount):
    data = get_balance(user_id)
    if data["balance"] < amount:
        return False
    data["balance"] -= amount
    return True

# ===== VIP =====
def get_vip(user_id):
    uid = str(user_id)
    return vip_data.get(uid, {"level": 0, "color": "purple"})

def is_vip(user_id):
    return get_vip(user_id)["level"] >= 1

def get_vip_display(user_id, name):
    vip = get_vip(user_id)
    if vip["level"] == 0:
        return name
    level_info = VIP_LEVELS.get(vip["level"], VIP_LEVELS[1])
    return f"{level_info['color']} {level_info['prefix']} {name}"

# ===== ФУНКЦИИ РАНГОВ =====
def get_rank(chat_id, user_id):
    if user_id == OWNER_ID:
        return 4
    try:
        member = bot.get_chat_member(chat_id, user_id)
        if member.status == 'creator':
            return 4
    except:
        pass
    return staff_data.get(chat_id, {}).get(user_id, 0)

def set_rank(chat_id, user_id, rank):
    if chat_id not in staff_data:
        staff_data[chat_id] = {}
    if rank == 0:
        staff_data[chat_id].pop(user_id, None)
    else:
        staff_data[chat_id][user_id] = rank

def has_rank(chat_id, user_id, min_rank):
    return get_rank(chat_id, user_id) >= min_rank

def is_owner_or_creator(chat_id, user_id):
    return get_rank(chat_id, user_id) >= 4

def get_chat_data(chat_id):
    if chat_id not in chats_data:
        chats_data[chat_id] = {
            "rules": "Правила чата ещё не установлены.",
            "welcome": "👋 Добро пожаловать в чат, {name}!",
            "welcome_enabled": True
        }
    return chats_data[chat_id]

def get_profile(user_id):
    uid = str(user_id)
    if uid not in user_profiles:
        user_profiles[uid] = {"nick": "", "bio": ""}
    return user_profiles[uid]

def get_user_name(uid, cid=None):
    """Получить имя пользователя безопасно"""
    profile = get_profile(uid)
    if profile and profile.get('nick'):
        return profile['nick']
    try:
        if cid:
            u = bot.get_chat_member(cid, uid)
            return u.user.first_name
    except:
        pass
    try:
        chat = bot.get_chat(uid)
        return chat.first_name
    except:
        pass
    return f"ID:{uid}"

def count_message(message):
    cid = message.chat.id
    uid = message.from_user.id
    today = datetime.now().strftime("%Y-%m-%d")
    
    if cid not in daily_stats:
        daily_stats[cid] = {}
    if today not in daily_stats[cid]:
        daily_stats[cid][today] = {"messages": 0, "users": {}, "new_users": []}
    
    daily_stats[cid][today]["messages"] += 1
    daily_stats[cid][today]["users"][uid] = daily_stats[cid][today]["users"].get(uid, 0) + 1
    add_bricks(uid, 1)

# ===== ЛС КНОПКИ =====
def get_private_keyboard():
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(
        telebot.types.KeyboardButton("❓ Помощь"),
        telebot.types.KeyboardButton("👤 Кем создан?"),
        telebot.types.KeyboardButton("💎 Купить VIP"),
        telebot.types.KeyboardButton("👤 Мой профиль"),
        telebot.types.KeyboardButton("💰 Баланс"),
    )
    return markup

@bot.message_handler(commands=['start'])
def start(message):
    if message.chat.type == 'private':
        bot.send_message(message.chat.id,
            "🧱 **Wall — Чат-менеджер**\n\n"
            "Добавь меня в группу и выдай права админа!\n\n"
            "Используй кнопки ниже для навигации!",
            parse_mode="Markdown",
            reply_markup=get_private_keyboard())

# ===== КНОПКИ ЛС =====
@bot.message_handler(func=lambda m: m.chat.type == 'private' and m.text == "❓ Помощь")
def private_help(message):
    text = """🧱 **Wall — Команды**

👤 **Для всех:**
/id, /info, /report, /rules, /staff
/translate, /anonym
/nick, /bio, /profile
/top, /meme
/balance, /work, /daily, /pay
/clan, /lyrics, /song, /youtube

🛡️ **Модерация:**
Ранг 1: /mute, /mutetime, /warn, /kick
Ранг 2: + /bantime, /pin, /unpin
Ранг 3: + /ban, /unban
Ранг 4: + /raising, /downgrade, /gg

💬 **RP:** /hug, /kiss, /slap, /pat, /kill, /revive, /hugme, /cry, /laugh, /dance
💎 **VIP:** /viphelp"""
    bot.reply_to(message, text, parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.chat.type == 'private' and m.text == "👤 Кем создан?")
def who_made(message):
    bot.reply_to(message, f"🧱 Wall создан: {OWNER_USERNAME}")

@bot.message_handler(func=lambda m: m.chat.type == 'private' and m.text == "💎 Купить VIP")
def buy_vip_menu(message):
    markup = telebot.types.InlineKeyboardMarkup()
    for level, info in VIP_LEVELS.items():
        markup.add(telebot.types.InlineKeyboardButton(
            f"{info['color']} {info['name']} — {info['price']:,} 🧱",
            callback_data=f"buyvip_{level}"
        ))
    bal = get_balance(message.from_user.id)["balance"]
    bot.send_message(message.chat.id,
        f"💎 **Покупка VIP**\n\nТвой баланс: {bal:,} 🧱\n\nВыбери уровень:",
        parse_mode="Markdown",
        reply_markup=markup)

@bot.callback_query_handler(func=lambda c: c.data.startswith("buyvip_"))
def buy_vip_callback(call):
    user_id = call.from_user.id
    level = int(call.data.split("_")[1])
    info = VIP_LEVELS[level]
    bal = get_balance(user_id)
    
    if not spend_bricks(user_id, info["price"]):
        bot.answer_callback_query(call.id, f"❌ Не хватает кирпичей! Нужно {info['price']:,}, у тебя {bal['balance']:,}")
        return
    
    vip_data[str(user_id)] = {"level": level, "color": "purple"}
    save_all_data()
    bot.answer_callback_query(call.id, f"✅ Куплен {info['name']}!")
    bot.send_message(user_id, f"🎉 Поздравляем! Ты теперь {info['color']} {info['name']}!\nИспользуй /viphelp для списка VIP-команд.")

@bot.message_handler(func=lambda m: m.chat.type == 'private' and m.text == "💰 Баланс")
def balance_cmd_private(message):
    bal = get_balance(message.from_user.id)
    vip = get_vip(message.from_user.id)
    vip_text = f"\n💎 {VIP_LEVELS[vip['level']]['name']}" if vip['level'] > 0 else ""
    bot.reply_to(message, f"💰 Твой баланс: {bal['balance']:,} 🧱{vip_text}")

@bot.message_handler(func=lambda m: m.chat.type == 'private' and m.text == "👤 Мой профиль")
def profile_private(message):
    profile = get_profile(message.from_user.id)
    bal = get_balance(message.from_user.id)
    vip = get_vip(message.from_user.id)
    vip_text = f"{VIP_LEVELS[vip['level']]['color']} {VIP_LEVELS[vip['level']]['name']}" if vip['level'] > 0 else "Нет"
    clan = get_user_clan(message.from_user.id)
    text = f"""👤 **Профиль**
Имя: {profile['nick'] or message.from_user.first_name}
ID: `{message.from_user.id}`
💰 Баланс: {bal['balance']:,} 🧱
💎 VIP: {vip_text}
🏰 Клан: {clan if clan else 'Нет'}
📝 Статус: {profile['bio'] or 'Не установлен'}"""
    bot.reply_to(message, text, parse_mode="Markdown")

# ===== ЭКОНОМИКА КОМАНДЫ =====
@bot.message_handler(commands=['balance', 'bal'])
def balance_cmd(message):
    bal = get_balance(message.from_user.id)
    vip = get_vip(message.from_user.id)
    vip_text = f" | 💎 {VIP_LEVELS[vip['level']]['name']}" if vip['level'] > 0 else ""
    bot.reply_to(message, f"💰 Баланс: {bal['balance']:,} 🧱{vip_text}")

@bot.message_handler(commands=['work'])
def work_cmd(message):
    user_id = message.from_user.id
    bal = get_balance(user_id)
    last = bal.get("last_work")
    
    if last:
        last_time = datetime.fromisoformat(last)
        if datetime.now() - last_time < timedelta(hours=1):
            remaining = timedelta(hours=1) - (datetime.now() - last_time)
            mins = remaining.seconds // 60
            bot.reply_to(message, f"⏳ Устал! Отдохни ещё {mins} мин.")
            return
    
    earnings = random.randint(50, 200)
    if is_vip(user_id):
        earnings *= 2
    
    bal["balance"] += earnings
    bal["last_work"] = datetime.now().isoformat()
    save_all_data()
    
    jobs = ["разгружал кирпичи", "строил стену", "клал фундамент", "таскал цемент", "делал раствор"]
    job = random.choice(jobs)
    bot.reply_to(message, f"💪 Ты {job} и заработал {earnings} 🧱!\nБаланс: {bal['balance']:,} 🧱")

@bot.message_handler(commands=['daily'])
def daily_cmd(message):
    user_id = message.from_user.id
    bal = get_balance(user_id)
    today = datetime.now().strftime("%Y-%m-%d")
    
    if bal.get("last_daily") == today:
        bot.reply_to(message, "❌ Ты уже получал бонус сегодня!")
        return
    
    bonus = random.randint(100, 500)
    if is_vip(user_id):
        bonus *= 2
    
    bal["balance"] += bonus
    bal["last_daily"] = today
    save_all_data()
    bot.reply_to(message, f"🎁 Ежедневный бонус: {bonus} 🧱\nБаланс: {bal['balance']:,} 🧱")

@bot.message_handler(commands=['pay'])
def pay_cmd(message):
    args = message.text.split()
    if len(args) < 3:
        bot.reply_to(message, "❌ /pay [ID] [сумма]")
        return
    try:
        target = int(args[1])
        amount = int(args[2])
    except:
        bot.reply_to(message, "❌ Неверные данные!")
        return
    
    if amount <= 0:
        bot.reply_to(message, "❌ Сумма должна быть положительной!")
        return
    
    if not spend_bricks(message.from_user.id, amount):
        bot.reply_to(message, "❌ Недостаточно кирпичей!")
        return
    
    add_bricks(target, amount)
    save_all_data()
    bot.reply_to(message, f"✅ Переведено {amount} 🧱 пользователю {target}")

# ===== КЛАНЫ =====
def get_user_clan(user_id):
    for name, data in clans_data.items():
        if user_id in data.get("members", []):
            return name
    return None

@bot.message_handler(commands=['clan'])
def clan_cmd(message):
    args = message.text.split(maxsplit=2)
    if len(args) < 2:
        bot.reply_to(message, 
            "🏰 **Кланы — команды:**\n\n"
            "/clan create [имя] — создать клан (5000 🧱)\n"
            "/clan join [имя] — вступить в клан\n"
            "/clan leave — покинуть клан\n"
            "/clan info — информация о своём клане\n"
            "/clan members — участники клана\n"
            "/clan kick [ID] — выгнать (глава)\n"
            "/clan promote [ID] — передать главенство\n"
            "/clan disband — распустить клан (глава)\n"
            "/clan bank — казна клана\n"
            "/clan donate [сумма] — пополнить казну\n"
            "/clan list — список всех кланов\n"
            "/clan top — топ кланов по казне",
            parse_mode="Markdown")
        return
    
    action = args[1].lower()
    user_id = message.from_user.id
    
    if action == "create":
        if len(args) < 3:
            bot.reply_to(message, "❌ /clan create [имя]")
            return
        name = args[2][:30]
        if name in clans_data:
            bot.reply_to(message, "❌ Клан с таким именем уже существует!")
            return
        if get_user_clan(user_id):
            bot.reply_to(message, "❌ Ты уже состоишь в клане!")
            return
        if not spend_bricks(user_id, 5000):
            bot.reply_to(message, "❌ Недостаточно кирпичей! Нужно 5,000 🧱")
            return
        clans_data[name] = {"owner": user_id, "members": [user_id], "bank": 0, "created": datetime.now().isoformat()}
        save_all_data()
        bot.reply_to(message, f"🏰 Клан **{name}** создан! (-5,000 🧱)\nИспользуй /clan help для списка команд.", parse_mode="Markdown")
    
    elif action == "join":
        if len(args) < 3:
            bot.reply_to(message, "❌ /clan join [имя]")
            return
        name = args[2]
        if name not in clans_data:
            bot.reply_to(message, "❌ Клан не найден!")
            return
        if get_user_clan(user_id):
            bot.reply_to(message, "❌ Ты уже состоишь в клане!")
            return
        clans_data[name]["members"].append(user_id)
        save_all_data()
        bot.reply_to(message, f"✅ Ты вступил в клан **{name}**!")
    
    elif action == "leave":
        clan = get_user_clan(user_id)
        if not clan:
            bot.reply_to(message, "❌ Ты не состоишь в клане!")
            return
        if clans_data[clan]["owner"] == user_id:
            bot.reply_to(message, "❌ Глава не может покинуть клан! Используй /clan disband или /clan promote [ID]")
            return
        clans_data[clan]["members"].remove(user_id)
        save_all_data()
        bot.reply_to(message, f"🚪 Ты покинул клан **{clan}**.")
    
    elif action == "info":
        clan = get_user_clan(user_id)
        if not clan:
            bot.reply_to(message, "❌ Ты не состоишь в клане! Используй /clan info [имя] для просмотра любого клана.")
            return
        data = clans_data[clan]
        owner_name = get_user_name(data["owner"])
        text = f"""🏰 **{clan}**
👑 Глава: {owner_name}
👥 Участников: {len(data['members'])}
💰 Казна: {data['bank']:,} 🧱
📅 Создан: {data['created'][:10]}"""
        bot.reply_to(message, text, parse_mode="Markdown")
    
    elif action == "members":
        clan = get_user_clan(user_id)
        if not clan:
            bot.reply_to(message, "❌ Ты не состоишь в клане!")
            return
        data = clans_data[clan]
        text = f"👥 **Участники {clan}:**\n\n"
        for mid in data["members"]:
            name = get_user_name(mid)
            crown = " 👑" if mid == data["owner"] else ""
            text += f"• {name}{crown}\n"
        bot.reply_to(message, text, parse_mode="Markdown")
    
    elif action == "kick":
        if len(args) < 3:
            bot.reply_to(message, "❌ /clan kick [ID]")
            return
        clan = get_user_clan(user_id)
        if not clan:
            bot.reply_to(message, "❌ Ты не состоишь в клане!")
            return
        if clans_data[clan]["owner"] != user_id:
            bot.reply_to(message, "❌ Только глава может кикать!")
            return
        try:
            target = int(args[2])
        except:
            bot.reply_to(message, "❌ Неверный ID!")
            return
        if target not in clans_data[clan]["members"]:
            bot.reply_to(message, "❌ Этот пользователь не в клане!")
            return
        if target == user_id:
            bot.reply_to(message, "❌ Нельзя кикнуть самого себя!")
            return
        clans_data[clan]["members"].remove(target)
        save_all_data()
        bot.reply_to(message, f"👢 {get_user_name(target)} исключён из клана!")
    
    elif action == "promote":
        if len(args) < 3:
            bot.reply_to(message, "❌ /clan promote [ID]")
            return
        clan = get_user_clan(user_id)
        if not clan:
            bot.reply_to(message, "❌ Ты не состоишь в клане!")
            return
        if clans_data[clan]["owner"] != user_id:
            bot.reply_to(message, "❌ Только глава может передавать главенство!")
            return
        try:
            target = int(args[2])
        except:
            bot.reply_to(message, "❌ Неверный ID!")
            return
        if target not in clans_data[clan]["members"]:
            bot.reply_to(message, "❌ Этот пользователь не в клане!")
            return
        clans_data[clan]["owner"] = target
        save_all_data()
        bot.reply_to(message, f"👑 {get_user_name(target)} теперь глава клана **{clan}**!")
    
    elif action == "disband":
        clan = get_user_clan(user_id)
        if not clan:
            bot.reply_to(message, "❌ Ты не состоишь в клане!")
            return
        if clans_data[clan]["owner"] != user_id:
            bot.reply_to(message, "❌ Только глава может распустить клан!")
            return
        del clans_data[clan]
        save_all_data()
        bot.reply_to(message, f"💀 Клан **{clan}** распущен.")
    
    elif action == "bank":
        clan = get_user_clan(user_id)
        if not clan:
            bot.reply_to(message, "❌ Ты не состоишь в клане!")
            return
        bot.reply_to(message, f"💰 Казна клана **{clan}**: {clans_data[clan]['bank']:,} 🧱")
    
    elif action == "donate":
        if len(args) < 3:
            bot.reply_to(message, "❌ /clan donate [сумма]")
            return
        clan = get_user_clan(user_id)
        if not clan:
            bot.reply_to(message, "❌ Ты не состоишь в клане!")
            return
        try:
            amount = int(args[2])
        except:
            bot.reply_to(message, "❌ Число!")
            return
        if amount <= 0:
            bot.reply_to(message, "❌ Сумма должна быть положительной!")
            return
        if not spend_bricks(user_id, amount):
            bot.reply_to(message, "❌ Недостаточно кирпичей!")
            return
        clans_data[clan]["bank"] += amount
        save_all_data()
        bot.reply_to(message, f"✅ {amount:,} 🧱 добавлено в казну клана **{clan}**!")
    
    elif action == "list":
        if not clans_data:
            bot.reply_to(message, "📭 Нет созданных кланов.")
            return
        text = "🏰 **Список кланов:**\n\n"
        for name, data in sorted(clans_data.items(), key=lambda x: len(x[1]["members"]), reverse=True):
            text += f"• **{name}** — {len(data['members'])} чел. | 💰 {data['bank']:,} 🧱\n"
        bot.reply_to(message, text, parse_mode="Markdown")
    
    elif action == "top":
        if not clans_data:
            bot.reply_to(message, "📭 Нет созданных кланов.")
            return
        sorted_clans = sorted(clans_data.items(), key=lambda x: x[1]["bank"], reverse=True)[:10]
        text = "🏆 **Топ кланов по казне:**\n\n"
        for i, (name, data) in enumerate(sorted_clans, 1):
            text += f"{i}. **{name}** — {data['bank']:,} 🧱 ({len(data['members'])} чел.)\n"
        bot.reply_to(message, text, parse_mode="Markdown")

# ===== ПОИСК МУЗЫКИ =====
@bot.message_handler(commands=['lyrics'])
def lyrics_cmd(message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        bot.reply_to(message, "❌ /lyrics [название песни]")
        return
    try:
        url = f"https://api.lyrics.ovh/v1/{args[1]}"
        response = requests.get(url).json()
        if "lyrics" in response:
            lyrics = response["lyrics"][:4000]
            bot.reply_to(message, f"🎵 **{args[1]}**\n\n{lyrics}", parse_mode="Markdown")
        else:
            bot.reply_to(message, "❌ Текст не найден!")
    except:
        bot.reply_to(message, "❌ Не удалось найти текст песни.")

@bot.message_handler(commands=['song'])
def song_cmd(message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        bot.reply_to(message, "❌ /song [название]")
        return
    try:
        url = f"http://ws.audioscrobbler.com/2.0/?method=track.search&track={args[1]}&api_key=1d3e5c5e5c5e5c5e5c5e5c5e5c5e5c5e&format=json"
        response = requests.get(url).json()
        tracks = response.get("results", {}).get("trackmatches", {}).get("track", [])
        if tracks:
            t = tracks[0]
            text = f"""🎵 **{t['name']}**
👤 Исполнитель: {t['artist']}
🔗 [Слушать на Last.fm]({t['url']})"""
            bot.reply_to(message, text, parse_mode="Markdown")
        else:
            bot.reply_to(message, "❌ Трек не найден!")
    except:
        bot.reply_to(message, "❌ Не удалось найти трек.")

@bot.message_handler(commands=['youtube'])
def youtube_cmd(message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        bot.reply_to(message, "❌ /youtube [запрос]")
        return
    query = args[1].replace(" ", "+")
    bot.reply_to(message, f"🔍 [Поиск на YouTube: {args[1]}](https://www.youtube.com/results?search_query={query})", parse_mode="Markdown", disable_web_page_preview=False)

# ===== ВЫДАЧА ОТ ВЛАДЕЛЬЦА =====
@bot.message_handler(commands=['gift'])
def gift_cmd(message):
    if message.from_user.id != OWNER_ID:
        bot.reply_to(message, "❌ Только владелец бота!")
        return
    
    args = message.text.split()
    if len(args) < 3:
        bot.reply_to(message, 
            "❌ /gift [ID] [что] [кол-во] [время]\n\n"
            "📋 **Что можно выдать:**\n"
            "• vip [1-3] [время] — VIP на время\n"
            "• bricks [сумма] — кирпичи\n"
            "• rank [1-3] [время] — ранг на время\n"
            "• unwarn — снять варны\n"
            "• reset — сбросить игрока\n\n"
            "⏰ Время: 1h, 1d, 7d, 30d, perm")
        return
    
    try:
        target_id = int(args[1])
        action = args[2].lower()
    except:
        bot.reply_to(message, "❌ Неверный ID!")
        return
    
    if action == "vip":
        if len(args) < 4:
            bot.reply_to(message, "❌ /gift [ID] vip [1-3] [время]")
            return
        level = int(args[3])
        if level < 1 or level > 3:
            bot.reply_to(message, "❌ Уровень VIP: 1, 2 или 3!")
            return
        time_str = args[4] if len(args) > 4 else "perm"
        until = None
        if time_str != "perm":
            match = re.match(r'(\d+)(h|d)', time_str)
            if match:
                num = int(match.group(1))
                until = datetime.now() + timedelta(hours=num) if match.group(2) == 'h' else datetime.now() + timedelta(days=num)
            else:
                bot.reply_to(message, "❌ Неверный формат времени!")
                return
        vip_data[str(target_id)] = {"level": level, "color": "purple"}
        if until:
            if str(target_id) not in temp_data:
                temp_data[str(target_id)] = {}
            temp_data[str(target_id)]["vip"] = {"level": level, "until": until}
        save_all_data()
        info = VIP_LEVELS[level]
        time_display = f"на {time_str}" if until else "навсегда"
        bot.reply_to(message, f"✅ {info['color']} {info['name']} выдан {target_id} {time_display}!")
    
    elif action == "bricks":
        if len(args) < 4:
            bot.reply_to(message, "❌ /gift [ID] bricks [сумма]")
            return
        amount = int(args[3])
        add_bricks(target_id, amount)
        save_all_data()
        bot.reply_to(message, f"✅ {amount:,} 🧱 выдано {target_id}!")
    
    elif action == "rank":
        if len(args) < 4:
            bot.reply_to(message, "❌ /gift [ID] rank [1-3] [время]")
            return
        rank_level = int(args[3])
        if rank_level < 1 or rank_level > 3:
            bot.reply_to(message, "❌ Ранг: 1-Модератор, 2-Мл.владелец, 3-Пом.владельца")
            return
        time_str = args[4] if len(args) > 4 else "perm"
        until = None
        if time_str != "perm":
            match = re.match(r'(\d+)(h|d)', time_str)
            if match:
                num = int(match.group(1))
                until = datetime.now() + timedelta(hours=num) if match.group(2) == 'h' else datetime.now() + timedelta(days=num)
        for cid in chats_data.keys():
            set_rank(int(cid), target_id, rank_level)
        if until:
            if str(target_id) not in temp_data:
                temp_data[str(target_id)] = {}
            temp_data[str(target_id)]["rank"] = {"level": rank_level, "until": until}
        save_all_data()
        rank_names = {1: "Модератор", 2: "Младший владелец", 3: "Помощник владельца"}
        time_display = f"на {time_str}" if until else "навсегда"
        bot.reply_to(message, f"✅ Ранг {rank_level} ({rank_names[rank_level]}) выдан {target_id} {time_display}!")
    
    elif action == "unwarn":
        if str(target_id) in warns_data:
            warns_data[str(target_id)] = {}
            save_all_data()
            bot.reply_to(message, f"✅ Все варны сняты с {target_id}!")
        else:
            bot.reply_to(message, f"❌ У {target_id} нет варнов!")
    
    elif action == "reset":
        uid = str(target_id)
        economy.pop(uid, None)
        vip_data.pop(uid, None)
        warns_data.pop(uid, None)
        mutes_data.pop(uid, None)
        bans_data.pop(uid, None)
        user_profiles.pop(uid, None)
        temp_data.pop(target_id, None)
        for cid in staff_data:
            staff_data[cid].pop(target_id, None)
        save_all_data()
        bot.reply_to(message, f"💀 Игрок {target_id} полностью сброшен!")

# ===== VIP-КОМАНДЫ =====
@bot.message_handler(commands=['viphelp'])
def vip_help(message):
    if not is_vip(message.from_user.id):
        bot.reply_to(message, "❌ Только для VIP!")
        return
    text = """💎 **VIP-команды**
⭐ VIP: /flex, /vipcolor, /spotlight, /loud, /ghost, /magic, /slow
🌟 VIP+: /announce, /rainbow, /reverse, /secret, /countdown
💎 LEGEND+: /say, /poll, /echo, /bomb, /weather"""
    bot.reply_to(message, text)

@bot.message_handler(commands=['flex'])
def flex_cmd(message):
    if not is_vip(message.from_user.id):
        bot.reply_to(message, "❌ Только для VIP!")
        return
    vip = get_vip(message.from_user.id)
    info = VIP_LEVELS[vip["level"]]
    bot.send_message(message.chat.id,
        f"💎 {info['prefix']} **{message.from_user.first_name}** показывает свой статус!\nУровень: {info['color']} {info['name']}\n💰 Баланс: {get_balance(message.from_user.id)['balance']:,} 🧱",
        parse_mode="Markdown")

@bot.message_handler(commands=['vipcolor'])
def vipcolor_cmd(message):
    if not is_vip(message.from_user.id):
        bot.reply_to(message, "❌ Только для VIP!")
        return
    args = message.text.split()
    if len(args) < 2:
        bot.reply_to(message, f"❌ /vipcolor [цвет]\nДоступно: {', '.join(VIP_COLORS)}")
        return
    color = args[1].lower()
    if color not in VIP_COLORS:
        bot.reply_to(message, f"❌ Недоступный цвет! Доступно: {', '.join(VIP_COLORS)}")
        return
    vip_data[str(message.from_user.id)]["color"] = color
    save_all_data()
    bot.reply_to(message, f"✅ Цвет изменён на {color}!")

@bot.message_handler(commands=['spotlight'])
def spotlight_cmd(message):
    if not is_vip(message.from_user.id):
        bot.reply_to(message, "❌ Только для VIP!")
        return
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        bot.reply_to(message, "❌ /spotlight [текст]")
        return
    bot.send_message(message.chat.id, f"🔦 **В центре внимания:**\n\n✨ {args[1]} ✨", parse_mode="Markdown")

@bot.message_handler(commands=['loud'])
def loud_cmd(message):
    if not is_vip(message.from_user.id):
        bot.reply_to(message, "❌ Только для VIP!")
        return
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        bot.reply_to(message, "❌ /loud [текст]")
        return
    bot.send_message(message.chat.id, f"📢 {args[1].upper()} 📢")

@bot.message_handler(commands=['ghost'])
def ghost_cmd(message):
    if not is_vip(message.from_user.id):
        bot.reply_to(message, "❌ Только для VIP!")
        return
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        bot.reply_to(message, "❌ /ghost [текст]")
        return
    try:
        bot.delete_message(message.chat.id, message.message_id)
    except:
        pass
    bot.send_message(message.chat.id, f"👻 **Призрак шепчет:** {args[1]}", parse_mode="Markdown")

@bot.message_handler(commands=['magic'])
def magic_cmd(message):
    if not is_vip(message.from_user.id):
        bot.reply_to(message, "❌ Только для VIP!")
        return
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        bot.reply_to(message, "❌ /magic [текст]")
        return
    emojis = ["✨", "🌟", "💫", "⭐", "🔮", "💎", "🎩", "🪄"]
    text = ' '.join(f"{char} {random.choice(emojis)}" for char in args[1])
    bot.send_message(message.chat.id, f"🎩 {text}")

@bot.message_handler(commands=['slow'])
def slow_cmd(message):
    if not is_vip(message.from_user.id):
        bot.reply_to(message, "❌ Только для VIP!")
        return
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        bot.reply_to(message, "❌ /slow [текст]")
        return
    for char in args[1]:
        bot.send_message(message.chat.id, char)
        time.sleep(0.3)

@bot.message_handler(commands=['announce'])
def announce_cmd(message):
    if get_vip(message.from_user.id)["level"] < 2:
        bot.reply_to(message, "❌ Только для VIP+!")
        return
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        bot.reply_to(message, "❌ /announce [текст]")
        return
    msg = bot.send_message(message.chat.id, f"📢 **ОБЪЯВЛЕНИЕ**\n\n{args[1]}", parse_mode="Markdown")
    try:
        bot.pin_chat_message(message.chat.id, msg.message_id)
    except:
        pass

@bot.message_handler(commands=['rainbow'])
def rainbow_cmd(message):
    if get_vip(message.from_user.id)["level"] < 2:
        bot.reply_to(message, "❌ Только для VIP+!")
        return
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        bot.reply_to(message, "❌ /rainbow [текст]")
        return
    colors = ["🔴", "🟠", "🟡", "🟢", "🔵", "🟣"]
    text = ' '.join(f"{colors[i % len(colors)]} {char}" for i, char in enumerate(args[1]))
    bot.send_message(message.chat.id, text)

@bot.message_handler(commands=['reverse'])
def reverse_cmd(message):
    if get_vip(message.from_user.id)["level"] < 2:
        bot.reply_to(message, "❌ Только для VIP+!")
        return
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        bot.reply_to(message, "❌ /reverse [текст]")
        return
    bot.send_message(message.chat.id, args[1][::-1])

@bot.message_handler(commands=['secret'])
def secret_cmd(message):
    if get_vip(message.from_user.id)["level"] < 2:
        bot.reply_to(message, "❌ Только для VIP+!")
        return
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        bot.reply_to(message, "❌ /secret [текст]")
        return
    bot.send_message(message.chat.id, f"🔒 Секретное сообщение: ||{args[1]}||", parse_mode="Markdown")

@bot.message_handler(commands=['countdown'])
def countdown_cmd(message):
    if get_vip(message.from_user.id)["level"] < 2:
        bot.reply_to(message, "❌ Только для VIP+!")
        return
    args = message.text.split()
    if len(args) < 2:
        bot.reply_to(message, "❌ /countdown [секунды]")
        return
    try:
        secs = min(int(args[1]), 10)
    except:
        bot.reply_to(message, "❌ Число!")
        return
    msg = bot.send_message(message.chat.id, f"⏳ {secs}...")
    for i in range(secs-1, 0, -1):
        time.sleep(1)
        try:
            bot.edit_message_text(f"⏳ {i}...", message.chat.id, msg.message_id)
        except:
            pass
    bot.edit_message_text("🚀 ПУСК!", message.chat.id, msg.message_id)

@bot.message_handler(commands=['say'])
def say_cmd(message):
    if get_vip(message.from_user.id)["level"] < 3:
        bot.reply_to(message, "❌ Только для LEGEND+!")
        return
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        bot.reply_to(message, "❌ /say [текст]")
        return
    try:
        bot.delete_message(message.chat.id, message.message_id)
    except:
        pass
    bot.send_message(message.chat.id, args[1])

@bot.message_handler(commands=['echo'])
def echo_cmd(message):
    if get_vip(message.from_user.id)["level"] < 3:
        bot.reply_to(message, "❌ Только для LEGEND+!")
        return
    args = message.text.split(maxsplit=2)
    if len(args) < 3:
        bot.reply_to(message, "❌ /echo [число] [текст]")
        return
    try:
        count = min(int(args[1]), 5)
    except:
        bot.reply_to(message, "❌ Число!")
        return
    for _ in range(count):
        bot.send_message(message.chat.id, args[2])
        time.sleep(0.5)

@bot.message_handler(commands=['bomb'])
def bomb_cmd(message):
    if get_vip(message.from_user.id)["level"] < 3:
        bot.reply_to(message, "❌ Только для LEGEND+!")
        return
    args = message.text.split()
    secs = min(int(args[1]) if len(args) > 1 else 5, 10)
    msg = bot.send_message(message.chat.id, f"💣 Бомба активирована! {secs}...")
    for i in range(secs-1, 0, -1):
        time.sleep(1)
        try:
            bot.edit_message_text(f"💣 {i}... {'💥' if i <= 3 else ''}", message.chat.id, msg.message_id)
        except:
            pass
    bot.edit_message_text("💥 БУМ! Все в порядке, это просто шутка 😄", message.chat.id, msg.message_id)

@bot.message_handler(commands=['weather'])
def weather_cmd(message):
    if get_vip(message.from_user.id)["level"] < 3:
        bot.reply_to(message, "❌ Только для LEGEND+!")
        return
    weathers = ["☀️ Солнечно", "🌧 Дождь", "⛈ Гроза", "❄️ Снег", "🌪 Ураган", "🌈 Радуга", "🌙 Ночь"]
    bot.send_message(message.chat.id, f"🌤 Погода в чате: **{random.choice(weathers)}**", parse_mode="Markdown")

# ===== ОТПРАВКА СООБЩЕНИЙ В ЛС =====
@bot.message_handler(commands=['msg'])
def msg_cmd(message):
    if message.from_user.id != OWNER_ID:
        bot.reply_to(message, "❌ Только владелец бота!")
        return
    args = message.text.split(maxsplit=2)
    if len(args) < 3:
        bot.reply_to(message, "❌ /msg [юзернейм или ID] [сообщение]")
        return
    target = args[1]
    text = args[2]
    target_id = None
    if target.startswith("@"):
        target = target[1:]
    else:
        try:
            target_id = int(target)
        except:
            bot.reply_to(message, "❌ Неверный юзернейм или ID!")
            return
    try:
        if target_id:
            bot.send_message(target_id, f"📨 **Сообщение от администрации:**\n\n{text}", parse_mode="Markdown")
        else:
            bot.send_message(f"@{target}", f"📨 **Сообщение от администрации:**\n\n{text}", parse_mode="Markdown")
        bot.reply_to(message, f"✅ Сообщение отправлено: {target}")
    except Exception as e:
        bot.reply_to(message, f"❌ Не удалось отправить!\nОшибка: {e}")

@bot.message_handler(commands=['dmall'])
def dmall_cmd(message):
    if message.from_user.id != OWNER_ID:
        bot.reply_to(message, "❌ Только владелец бота!")
        return
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        bot.reply_to(message, "❌ /dmall [сообщение]")
        return
    text = args[1]
    sent = 0
    failed = 0
    bot.reply_to(message, "⏳ Начинаю рассылку...")
    for uid in list(economy.keys()):
        try:
            bot.send_message(int(uid), f"📢 **Массовое уведомление:**\n\n{text}", parse_mode="Markdown")
            sent += 1
            time.sleep(0.05)
        except:
            failed += 1
    bot.reply_to(message, f"✅ Рассылка завершена!\nОтправлено: {sent}\nНе удалось: {failed}")

# ===== КОМАНДЫ ДЛЯ ВСЕХ =====
@bot.message_handler(commands=['help'])
def help_cmd(message):
    text = """🧱 **Wall — Команды**

👤 **Для всех:**
/id, /info, /report, /rules, /staff
/translate, /anonym
/nick, /bio, /profile
/top, /meme
/balance, /work, /daily, /pay
/clan, /lyrics, /song, /youtube

🛡️ **Модерация:**
Ранг 1: /mute, /mutetime, /warn, /kick
Ранг 2: + /bantime, /pin, /unpin
Ранг 3: + /ban, /unban
Ранг 4: + /raising, /downgrade, /gg

💬 **RP:** /hug, /kiss, /slap, /pat, /kill, /revive, /hugme, /cry, /laugh, /dance
💎 **VIP:** /viphelp"""
    bot.reply_to(message, text, parse_mode="Markdown")

@bot.message_handler(commands=['id'])
def id_cmd(message):
    if message.reply_to_message:
        u = message.reply_to_message.from_user
        bot.reply_to(message, f"🆔 {u.first_name}: `{u.id}`", parse_mode="Markdown")
    else:
        bot.reply_to(message, f"🆔 Твой ID: `{message.from_user.id}`\nЧат: `{message.chat.id}`", parse_mode="Markdown")

@bot.message_handler(commands=['info'])
def info_cmd(message):
    u = message.reply_to_message.from_user if message.reply_to_message else message.from_user
    cid = message.chat.id
    uid = u.id
    profile = get_profile(uid)
    vip = get_vip(uid)
    try:
        member = bot.get_chat_member(cid, uid)
        status = member.status
    except:
        status = "неизвестно"
    warns = warns_data.get(uid, {}).get(cid, [])
    mute_info = mutes_data.get(uid, {}).get(cid)
    muted = f"Да (до {mute_info.strftime('%H:%M')})" if mute_info else "Нет"
    banned = bans_data.get(uid, {}).get(cid, False)
    rank = get_rank(cid, uid)
    rank_names = {0: "Участник", 1: "Модератор", 2: "Мл. владелец", 3: "Пом. владельца", 4: "Владелец"}
    vip_text = f"{VIP_LEVELS[vip['level']]['color']} {VIP_LEVELS[vip['level']]['name']}" if vip['level'] > 0 else "Нет"
    bal = get_balance(uid)
    clan = get_user_clan(uid)
    text = f"""📊 **Информация**
👤 {get_vip_display(uid, profile['nick'] or u.first_name)}
🆔 `{uid}`
📝 {profile['bio'] or 'Нет статуса'}
💰 Баланс: {bal['balance']:,} 🧱
💎 VIP: {vip_text}
🏰 Клан: {clan if clan else 'Нет'}
👑 Статус: {status}
🎖 Ранг: {rank_names[rank]} ({rank})
⚠️ Варны: {len(warns)}/3
🔇 Мут: {muted}
🚫 Бан: {'Да' if banned else 'Нет'}"""
    bot.reply_to(message, text, parse_mode="Markdown")

@bot.message_handler(commands=['rules'])
def rules_cmd(message):
    cd = get_chat_data(message.chat.id)
    bot.reply_to(message, f"📜 **Правила:**\n\n{cd['rules']}", parse_mode="Markdown")

@bot.message_handler(commands=['report'])
def report_cmd(message):
    if not message.reply_to_message:
        bot.reply_to(message, "❌ Ответьте на сообщение!")
        return
    args = message.text.split(maxsplit=1)
    reason = args[1] if len(args) > 1 else "Не указана"
    reported = message.reply_to_message.from_user
    for adm in bot.get_chat_administrators(message.chat.id):
        try:
            bot.send_message(adm.user.id, f"🚨 Репорт от {message.from_user.first_name}\nНа: {reported.first_name}\nПричина: {reason}")
        except:
            pass
    bot.reply_to(message, "✅ Жалоба отправлена!")

@bot.message_handler(commands=['staff'])
def staff_list(message):
    cid = message.chat.id
    staff = staff_data.get(cid, {})
    if not staff:
        bot.reply_to(message, "📭 Нет персонала.")
        return
    rn = {1: "Модератор", 2: "Мл. владелец", 3: "Пом. владельца"}
    text = "🛡️ **Персонал:**\n\n"
    for uid, rank in sorted(staff.items(), key=lambda x: x[1], reverse=True):
        name = get_user_name(uid, cid)
        text += f"• {get_vip_display(uid, name)} — {rn[rank]} (ранг {rank})\n"
    bot.reply_to(message, text, parse_mode="Markdown")

# ===== ПРОФИЛЬ =====
@bot.message_handler(commands=['nick'])
def nick_cmd(message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        bot.reply_to(message, "❌ /nick [новое имя]")
        return
    profile = get_profile(message.from_user.id)
    profile['nick'] = args[1]
    save_all_data()
    bot.reply_to(message, f"✅ Ник изменён на: {args[1]}")

@bot.message_handler(commands=['bio'])
def bio_cmd(message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        bot.reply_to(message, "❌ /bio [статус]")
        return
    profile = get_profile(message.from_user.id)
    profile['bio'] = args[1]
    save_all_data()
    bot.reply_to(message, f"✅ Статус обновлён: {args[1]}")

@bot.message_handler(commands=['profile'])
def profile_cmd(message):
    u = message.reply_to_message.from_user if message.reply_to_message else message.from_user
    profile = get_profile(u.id)
    bal = get_balance(u.id)
    vip = get_vip(u.id)
    vip_text = f"{VIP_LEVELS[vip['level']]['color']} {VIP_LEVELS[vip['level']]['name']}" if vip['level'] > 0 else "Нет"
    clan = get_user_clan(u.id)
    text = f"""👤 **Профиль**
Имя: {get_vip_display(u.id, profile['nick'] or u.first_name)}
ID: `{u.id}`
💰 Баланс: {bal['balance']:,} 🧱
💎 VIP: {vip_text}
🏰 Клан: {clan if clan else 'Нет'}
📝 Статус: {profile['bio'] or 'Не установлен'}"""
    bot.reply_to(message, text, parse_mode="Markdown")

# ===== ТОП =====
@bot.message_handler(commands=['top'])
def top_cmd(message):
    cid = message.chat.id
    today = datetime.now().strftime("%Y-%m-%d")
    stats = daily_stats.get(cid, {}).get(today, {})
    
    text = "🏆 **Топ-10 богачей**\n\n"
    rich = sorted(economy.items(), key=lambda x: x[1].get("balance", 0), reverse=True)[:10]
    
    for i, (uid, data) in enumerate(rich, 1):
        name = get_user_name(int(uid), cid)
        vip_display = get_vip_display(int(uid), name)
        text += f"{i}. {vip_display} — {data.get('balance', 0):,} 🧱\n"
    
    text += "\n📊 **Топ активных:**\n"
    if stats and stats.get("users"):
        top_users = sorted(stats["users"].items(), key=lambda x: x[1], reverse=True)[:5]
        for i, (uid, count) in enumerate(top_users, 1):
            name = get_user_name(uid, cid)
            text += f"{i}. {name} — {count} сообщ.\n"
    else:
        text += "Нет данных за сегодня.\n"
    
    bot.reply_to(message, text, parse_mode="Markdown")

# ===== ПЕРЕВОДЧИК =====
@bot.message_handler(commands=['translate'])
def translate_cmd(message):
    args = message.text.split(maxsplit=1)
    if not message.reply_to_message and len(args) < 2:
        bot.reply_to(message, "❌ Ответьте на сообщение или напишите текст!\nПример: /translate Hello world")
        return
    if message.reply_to_message:
        text = message.reply_to_message.text
        if not text:
            bot.reply_to(message, "❌ В сообщении нет текста!")
            return
    else:
        text = args[1]
    try:
        url = f"https://api.mymemory.translated.net/get?q={text}&langpair=auto|ru"
        response = requests.get(url).json()
        translated = response['responseData']['translatedText']
        original_lang = response['responseData']['detectedLanguage'].upper()
        bot.reply_to(message, f"🌐 **Перевод**\n\n📥 {original_lang}: {text}\n📤 RU: {translated}", parse_mode="Markdown")
    except:
        bot.reply_to(message, "❌ Не удалось перевести.")

# ===== АНОНИМНОЕ СООБЩЕНИЕ =====
@bot.message_handler(commands=['anonym'])
def anonym_cmd(message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        bot.reply_to(message, "❌ /anonym [текст]")
        return
    try:
        bot.delete_message(message.chat.id, message.message_id)
    except:
        pass
    bot.send_message(message.chat.id, f"🕵️ **Аноним:**\n\n{args[1]}", parse_mode="Markdown")

# ===== МЕМ =====
@bot.message_handler(commands=['meme'])
def meme_cmd(message):
    try:
        response = requests.get("https://meme-api.com/gimme")
        data = response.json()
        bot.send_photo(message.chat.id, data['url'], caption=f"😄 {data['title']}")
    except:
        bot.reply_to(message, "❌ Не удалось загрузить мем.")

# ===== PIN / UNPIN =====
@bot.message_handler(commands=['pin'])
def pin_cmd(message):
    if not has_rank(message.chat.id, message.from_user.id, 2):
        bot.reply_to(message, "❌ Нужен ранг 2+!")
        return
    if not message.reply_to_message:
        bot.reply_to(message, "❌ Ответьте на сообщение!")
        return
    try:
        bot.pin_chat_message(message.chat.id, message.reply_to_message.message_id)
        bot.reply_to(message, "📌 Закреплено!")
    except:
        bot.reply_to(message, "❌ Не удалось!")

@bot.message_handler(commands=['unpin'])
def unpin_cmd(message):
    if not has_rank(message.chat.id, message.from_user.id, 2):
        bot.reply_to(message, "❌ Нужен ранг 2+!")
        return
    try:
        bot.unpin_chat_message(message.chat.id)
        bot.reply_to(message, "📌 Откреплено!")
    except:
        bot.reply_to(message, "❌ Не удалось!")

# ===== BANLIST / MUTELIST =====
@bot.message_handler(commands=['banlist'])
def banlist_cmd(message):
    if not has_rank(message.chat.id, message.from_user.id, 2):
        bot.reply_to(message, "❌ Нужен ранг 2+!")
        return
    cid = message.chat.id
    banned = [uid for uid, chats in bans_data.items() if cid in chats and chats[cid]]
    if not banned:
        bot.reply_to(message, "📭 Нет забаненных.")
        return
    text = "🚫 **Забаненные:**\n\n"
    for uid in banned[:20]:
        name = get_user_name(int(uid), cid)
        text += f"• {name} (`{uid}`)\n"
    bot.reply_to(message, text, parse_mode="Markdown")

@bot.message_handler(commands=['mutelist'])
def mutelist_cmd(message):
    if not has_rank(message.chat.id, message.from_user.id, 2):
        bot.reply_to(message, "❌ Нужен ранг 2+!")
        return
    cid = message.chat.id
    muted = [uid for uid, chats in mutes_data.items() if cid in chats and chats[cid] and datetime.now() < chats[cid]]
    if not muted:
        bot.reply_to(message, "📭 Нет замученных.")
        return
    text = "🔇 **Замученные:**\n\n"
    for uid in muted[:20]:
        name = get_user_name(uid, cid)
        until = mutes_data[uid][cid]
        remaining = until - datetime.now()
        mins = remaining.seconds // 60
        text += f"• {name} — ещё {mins} мин.\n"
    bot.reply_to(message, text, parse_mode="Markdown")

# ===== RP-КОМАНДЫ =====
@bot.message_handler(commands=['hug'])
def hug_cmd(message):
    if not message.reply_to_message:
        bot.reply_to(message, "❌ Ответьте на сообщение!")
        return
    u1 = message.from_user.first_name
    u2 = message.reply_to_message.from_user.first_name
    bot.send_message(message.chat.id, f"🤗 {u1} крепко обнимает {u2}!")

@bot.message_handler(commands=['kiss'])
def kiss_cmd(message):
    if not message.reply_to_message:
        bot.reply_to(message, "❌ Ответьте на сообщение!")
        return
    u1 = message.from_user.first_name
    u2 = message.reply_to_message.from_user.first_name
    bot.send_message(message.chat.id, f"💋 {u1} целует {u2}!")

@bot.message_handler(commands=['slap'])
def slap_cmd(message):
    if not message.reply_to_message:
        bot.reply_to(message, "❌ Ответьте на сообщение!")
        return
    u1 = message.from_user.first_name
    u2 = message.reply_to_message.from_user.first_name
    bot.send_message(message.chat.id, f"👋 {u1} даёт звонкую пощёчину {u2}!")

@bot.message_handler(commands=['pat'])
def pat_cmd(message):
    if not message.reply_to_message:
        bot.reply_to(message, "❌ Ответьте на сообщение!")
        return
    u1 = message.from_user.first_name
    u2 = message.reply_to_message.from_user.first_name
    bot.send_message(message.chat.id, f"🤚 {u1} нежно гладит {u2} по голове!")

@bot.message_handler(commands=['kill'])
def kill_cmd(message):
    if not message.reply_to_message:
        bot.reply_to(message, "❌ Ответьте на сообщение!")
        return
    u1 = message.from_user.first_name
    u2 = message.reply_to_message.from_user.first_name
    ways = [f"🔪 {u1} жестоко убивает {u2}!", f"💀 {u1} отправляет {u2} в нокаут!", f"⚰️ {u2} был уничтожен {u1}!", f"🪦 {u1} вырыл могилу для {u2}!"]
    bot.send_message(message.chat.id, random.choice(ways))

@bot.message_handler(commands=['revive'])
def revive_cmd(message):
    if not message.reply_to_message:
        bot.reply_to(message, "❌ Ответьте на сообщение!")
        return
    u1 = message.from_user.first_name
    u2 = message.reply_to_message.from_user.first_name
    bot.send_message(message.chat.id, f"💖 {u1} воскрешает {u2}!")

@bot.message_handler(commands=['hugme'])
def hugme_cmd(message):
    u = message.from_user.first_name
    bot.send_message(message.chat.id, f"🤗 {u} обнимает себя... Это грустно и мило одновременно.")

@bot.message_handler(commands=['cry'])
def cry_cmd(message):
    u = message.from_user.first_name
    bot.send_message(message.chat.id, f"😢 {u} плачет... Кто-то обнимет?")

@bot.message_handler(commands=['laugh'])
def laugh_cmd(message):
    u = message.from_user.first_name
    laughs = [f"😂 {u} смеётся до слёз!", f"🤣 {u} умирает со смеху!", f"😆 {u} хихикает как школьник!"]
    bot.send_message(message.chat.id, random.choice(laughs))

@bot.message_handler(commands=['dance'])
def dance_cmd(message):
    u = message.from_user.first_name
    bot.send_message(message.chat.id, f"💃 {u} зажигает на танцполе! 🕺")

# ===== ПОВЫШЕНИЕ/ПОНИЖЕНИЕ =====
@bot.message_handler(commands=['raising'])
def raising_cmd(message):
    if not is_owner_or_creator(message.chat.id, message.from_user.id):
        bot.reply_to(message, "❌ Только владелец!")
        return
    if not message.reply_to_message:
        bot.reply_to(message, "❌ Ответьте на сообщение!")
        return
    u = message.reply_to_message.from_user
    cid = message.chat.id
    cr = get_rank(cid, u.id)
    if cr >= 3:
        bot.reply_to(message, f"❌ {u.first_name} уже макс. ранг!")
        return
    nr = cr + 1
    set_rank(cid, u.id, nr)
    save_all_data()
    rn = {1: "Модератор", 2: "Мл. владелец", 3: "Пом. владельца"}
    bot.reply_to(message, f"⬆️ {u.first_name} → ранг {nr} ({rn[nr]})")

@bot.message_handler(commands=['downgrade'])
def downgrade_cmd(message):
    if not is_owner_or_creator(message.chat.id, message.from_user.id):
        bot.reply_to(message, "❌ Только владелец!")
        return
    if not message.reply_to_message:
        bot.reply_to(message, "❌ Ответьте на сообщение!")
        return
    u = message.reply_to_message.from_user
    cid = message.chat.id
    cr = get_rank(cid, u.id)
    if cr <= 1:
        bot.reply_to(message, f"❌ Нельзя понизить (ранг {cr}). Используйте /gg")
        return
    nr = cr - 1
    set_rank(cid, u.id, nr)
    save_all_data()
    rn = {1: "Модератор", 2: "Мл. владелец", 3: "Пом. владельца"}
    bot.reply_to(message, f"⬇️ {u.first_name} → ранг {nr} ({rn.get(nr, 'Участник')})")

@bot.message_handler(commands=['gg'])
def gg_cmd(message):
    if not is_owner_or_creator(message.chat.id, message.from_user.id):
        bot.reply_to(message, "❌ Только владелец!")
        return
    if not message.reply_to_message:
        bot.reply_to(message, "❌ Ответьте на сообщение!")
        return
    u = message.reply_to_message.from_user
    cid = message.chat.id
    if get_rank(cid, u.id) == 0:
        bot.reply_to(message, f"❌ {u.first_name} и так без ранга!")
        return
    set_rank(cid, u.id, 0)
    save_all_data()
    bot.reply_to(message, f"💀 {u.first_name} лишён ранга!")

# ===== МОДЕРАЦИЯ =====
@bot.message_handler(commands=['warn'])
def warn_cmd(message):
    if not has_rank(message.chat.id, message.from_user.id, 1):
        bot.reply_to(message, "❌ Нет прав!")
        return
    if not message.reply_to_message:
        bot.reply_to(message, "❌ Ответьте на сообщение!")
        return
    u = message.reply_to_message.from_user
    cid = message.chat.id
    warner_rank = get_rank(cid, message.from_user.id)
    target_rank = get_rank(cid, u.id)
    if target_rank >= warner_rank:
        bot.reply_to(message, f"❌ {random.choice(DENY_PHRASES)} (Твой ранг: {warner_rank}, цель: {target_rank})")
        return
    args = message.text.split(maxsplit=1)
    reason = args[1] if len(args) > 1 else "Нарушение"
    if u.id not in warns_data:
        warns_data[u.id] = {}
    if cid not in warns_data[u.id]:
        warns_data[u.id][cid] = []
    warns_data[u.id][cid].append({"reason": reason, "time": datetime.now().isoformat(), "by": message.from_user.id})
    wc = len(warns_data[u.id][cid])
    if wc >= MAX_WARNS:
        cr = get_rank(cid, u.id)
        if cr > 0:
            set_rank(cid, u.id, cr - 1)
            warns_data[u.id][cid] = []
            save_all_data()
            rn = {0: "Участник", 1: "Модератор", 2: "Мл. владелец", 3: "Пом. владельца"}
            bot.reply_to(message, f"🚨 {u.first_name} 3/3!\n⬇️ Ранг → {cr-1} ({rn[cr-1]})")
        else:
            try:
                bot.restrict_chat_member(cid, u.id, until_date=datetime.now() + timedelta(hours=1))
                warns_data[u.id][cid] = []
                save_all_data()
                bot.reply_to(message, f"🚨 {u.first_name} 3/3!\n🔇 Мут 1 час (нет ранга)")
            except:
                bot.reply_to(message, f"⚠️ 3/3! Нужен мут, но нет прав!")
    else:
        save_all_data()
        bot.reply_to(message, f"⚠️ {u.first_name} — {wc}/{MAX_WARNS}\nПричина: {reason}")

@bot.message_handler(commands=['mute'])
def mute_cmd(message):
    if not has_rank(message.chat.id, message.from_user.id, 1):
        bot.reply_to(message, "❌ Нет прав!")
        return
    if not message.reply_to_message:
        bot.reply_to(message, "❌ Ответьте на сообщение!")
        return
    u = message.reply_to_message.from_user
    cid = message.chat.id
    warner_rank = get_rank(cid, message.from_user.id)
    target_rank = get_rank(cid, u.id)
    if target_rank >= warner_rank:
        bot.reply_to(message, f"❌ {random.choice(DENY_PHRASES)} (Твой ранг: {warner_rank}, цель: {target_rank})")
        return
    try:
        bot.restrict_chat_member(cid, u.id, until_date=datetime.now() + timedelta(days=3650))
        if u.id not in mutes_data:
            mutes_data[u.id] = {}
        mutes_data[u.id][cid] = datetime.now() + timedelta(days=3650)
        save_all_data()
        bot.reply_to(message, f"🔇 {u.first_name} замучен навсегда!")
    except:
        bot.reply_to(message, "❌ Не удалось!")

@bot.message_handler(commands=['mutetime'])
def mutetime_cmd(message):
    if not has_rank(message.chat.id, message.from_user.id, 1):
        bot.reply_to(message, "❌ Нет прав!")
        return
    if not message.reply_to_message:
        bot.reply_to(message, "❌ Ответьте на сообщение!")
        return
    u = message.reply_to_message.from_user
    cid = message.chat.id
    warner_rank = get_rank(cid, message.from_user.id)
    target_rank = get_rank(cid, u.id)
    if target_rank >= warner_rank:
        bot.reply_to(message, f"❌ {random.choice(DENY_PHRASES)} (Твой ранг: {warner_rank}, цель: {target_rank})")
        return
    args = message.text.split()
    if len(args) < 2:
        bot.reply_to(message, "❌ /mutetime [минуты]")
        return
    try:
        mins = int(args[1])
    except:
        bot.reply_to(message, "❌ Число!")
        return
    try:
        bot.restrict_chat_member(cid, u.id, until_date=datetime.now() + timedelta(minutes=mins))
        if u.id not in mutes_data:
            mutes_data[u.id] = {}
        mutes_data[u.id][cid] = datetime.now() + timedelta(minutes=mins)
        save_all_data()
        bot.reply_to(message, f"🔇 {u.first_name} замучен на {mins} мин!")
    except:
        bot.reply_to(message, "❌ Не удалось!")

@bot.message_handler(commands=['unmute'])
def unmute_cmd(message):
    if not has_rank(message.chat.id, message.from_user.id, 1):
        bot.reply_to(message, "❌ Нет прав!")
        return
    if not message.reply_to_message:
        bot.reply_to(message, "❌ Ответьте на сообщение!")
        return
    u = message.reply_to_message.from_user
    cid = message.chat.id
    try:
        bot.restrict_chat_member(cid, u.id, can_send_messages=True)
        if u.id in mutes_data:
            mutes_data[u.id].pop(cid, None)
        save_all_data()
        bot.reply_to(message, f"🔊 {u.first_name} размучен!")
    except:
        bot.reply_to(message, "❌ Не удалось!")

@bot.message_handler(commands=['bantime'])
def bantime_cmd(message):
    if not has_rank(message.chat.id, message.from_user.id, 2):
        bot.reply_to(message, "❌ Нужен ранг 2!")
        return
    if not message.reply_to_message:
        bot.reply_to(message, "❌ Ответьте на сообщение!")
        return
    u = message.reply_to_message.from_user
    cid = message.chat.id
    warner_rank = get_rank(cid, message.from_user.id)
    target_rank = get_rank(cid, u.id)
    if target_rank >= warner_rank:
        bot.reply_to(message, f"❌ {random.choice(DENY_PHRASES)} (Твой ранг: {warner_rank}, цель: {target_rank})")
        return
    args = message.text.split()
    if len(args) < 2:
        bot.reply_to(message, "❌ /bantime [минуты]")
        return
    try:
        mins = int(args[1])
    except:
        bot.reply_to(message, "❌ Число!")
        return
    try:
        bot.ban_chat_member(cid, u.id, until_date=datetime.now() + timedelta(minutes=mins))
        save_all_data()
        bot.reply_to(message, f"🚫 {u.first_name} забанен на {mins} мин!")
    except:
        bot.reply_to(message, "❌ Не удалось!")

@bot.message_handler(commands=['ban'])
def ban_cmd(message):
    if not has_rank(message.chat.id, message.from_user.id, 3):
        bot.reply_to(message, "❌ Нужен ранг 3!")
        return
    if not message.reply_to_message:
        bot.reply_to(message, "❌ Ответьте на сообщение!")
        return
    u = message.reply_to_message.from_user
    cid = message.chat.id
    warner_rank = get_rank(cid, message.from_user.id)
    target_rank = get_rank(cid, u.id)
    if target_rank >= warner_rank:
        bot.reply_to(message, f"❌ {random.choice(DENY_PHRASES)} (Твой ранг: {warner_rank}, цель: {target_rank})")
        return
    args = message.text.split(maxsplit=1)
    reason = args[1] if len(args) > 1 else "Нарушение"
    try:
        bot.ban_chat_member(cid, u.id)
        if u.id not in bans_data:
            bans_data[u.id] = {}
        bans_data[u.id][cid] = True
        save_all_data()
        bot.reply_to(message, f"🚫 {u.first_name} забанен!\nПричина: {reason}")
    except:
        bot.reply_to(message, "❌ Не удалось!")

@bot.message_handler(commands=['kick'])
def kick_cmd(message):
    if not has_rank(message.chat.id, message.from_user.id, 1):
        bot.reply_to(message, "❌ Нет прав!")
        return
    if not message.reply_to_message:
        bot.reply_to(message, "❌ Ответьте на сообщение!")
        return
    u = message.reply_to_message.from_user
    cid = message.chat.id
    warner_rank = get_rank(cid, message.from_user.id)
    target_rank = get_rank(cid, u.id)
    if target_rank >= warner_rank:
        bot.reply_to(message, f"❌ {random.choice(DENY_PHRASES)} (Твой ранг: {warner_rank}, цель: {target_rank})")
        return
    try:
        bot.ban_chat_member(cid, u.id)
        bot.unban_chat_member(cid, u.id)
        bot.reply_to(message, f"👢 {u.first_name} кикнут!")
    except:
        bot.reply_to(message, "❌ Не удалось!")

@bot.message_handler(commands=['unban'])
def unban_cmd(message):
    if not has_rank(message.chat.id, message.from_user.id, 3):
        bot.reply_to(message, "❌ Нужен ранг 3!")
        return
    args = message.text.split()
    if len(args) < 2:
        bot.reply_to(message, "❌ /unban [ID]")
        return
    try:
        uid = int(args[1])
        bot.unban_chat_member(message.chat.id, uid)
        if uid in bans_data:
            bans_data[uid].pop(message.chat.id, None)
        save_all_data()
        bot.reply_to(message, f"✅ {uid} разбанен!")
    except:
        bot.reply_to(message, "❌ Ошибка!")

# ===== НАСТРОЙКИ ЧАТА =====
@bot.message_handler(commands=['setrules'])
def setrules_cmd(message):
    if not is_owner_or_creator(message.chat.id, message.from_user.id):
        bot.reply_to(message, "❌ Только владелец!")
        return
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        bot.reply_to(message, "❌ /setrules [текст]")
        return
    get_chat_data(message.chat.id)['rules'] = args[1]
    save_all_data()
    bot.reply_to(message, "✅ Правила обновлены!")

@bot.message_handler(commands=['setwelcome'])
def setwelcome_cmd(message):
    if not is_owner_or_creator(message.chat.id, message.from_user.id):
        bot.reply_to(message, "❌ Только владелец!")
        return
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        bot.reply_to(message, "❌ /setwelcome [текст]")
        return
    get_chat_data(message.chat.id)['welcome'] = args[1]
    save_all_data()
    bot.reply_to(message, "✅ Приветствие обновлено!")

@bot.message_handler(commands=['welcome_on'])
def welcome_on(message):
    if not is_owner_or_creator(message.chat.id, message.from_user.id):
        bot.reply_to(message, "❌ Только владелец!")
        return
    get_chat_data(message.chat.id)['welcome_enabled'] = True
    save_all_data()
    bot.reply_to(message, "✅ Приветствие включено!")

@bot.message_handler(commands=['welcome_off'])
def welcome_off(message):
    if not is_owner_or_creator(message.chat.id, message.from_user.id):
        bot.reply_to(message, "❌ Только владелец!")
        return
    get_chat_data(message.chat.id)['welcome_enabled'] = False
    save_all_data()
    bot.reply_to(message, "✅ Приветствие выключено!")

# ===== ПРИВЕТСТВИЕ =====
@bot.message_handler(content_types=['new_chat_members'])
def welcome_new(message):
    cd = get_chat_data(message.chat.id)
    if not cd['welcome_enabled']:
        return
    for nm in message.new_chat_members:
        bot.send_message(message.chat.id, cd['welcome'].replace('{name}', nm.first_name))

# ===== АНТИСПАМ =====
@bot.message_handler(func=lambda m: True)
def auto_mod(message):
    uid = message.from_user.id
    cid = message.chat.id
    if message.chat.type == 'private':
        return
    count_message(message)
    if uid in mutes_data and cid in mutes_data.get(uid, {}):
        if datetime.now() < mutes_data[uid][cid]:
            try:
                bot.delete_message(cid, message.message_id)
            except:
                pass
            return
    if uid not in message_history:
        message_history[uid] = []
    message_history[uid].append({"text": message.text, "time": datetime.now()})
    if len(message_history[uid]) > 10:
        message_history[uid] = message_history[uid][-10:]
    recent = [m for m in message_history[uid] if (datetime.now() - m['time']).seconds < 5]
    if len(recent) >= 5:
        try:
            bot.delete_message(cid, message.message_id)
            if has_rank(cid, bot.get_me().id, 1):
                bot.restrict_chat_member(cid, uid, until_date=datetime.now() + timedelta(minutes=1))
        except:
            pass

# ===== ГЛОБАЛЬНЫЕ =====
@bot.message_handler(commands=['gban'])
def gban_cmd(message):
    if message.from_user.id != OWNER_ID:
        bot.reply_to(message, "❌ Только владелец бота!")
        return
    if not message.reply_to_message:
        bot.reply_to(message, "❌ Ответьте на сообщение!")
        return
    bot.reply_to(message, f"🌍 {message.reply_to_message.from_user.first_name} глобально забанен!")

@bot.message_handler(commands=['broadcast'])
def broadcast_cmd(message):
    if message.from_user.id != OWNER_ID:
        bot.reply_to(message, "❌ Только владелец бота!")
        return
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        bot.reply_to(message, "❌ /broadcast [текст]")
        return
    sent = 0
    for cid in list(chats_data.keys()):
        try:
            bot.send_message(cid, f"📢 {args[1]}")
            sent += 1
        except:
            pass
    bot.reply_to(message, f"✅ Отправлено в {sent} чатов!")

@bot.message_handler(commands=['uptime'])
def uptime_cmd(message):
    delta = datetime.now() - start_time
    days = delta.days
    hours = delta.seconds // 3600
    minutes = (delta.seconds % 3600) // 60
    bot.reply_to(message, f"⏱ **Аптайм:** {days} дн. {hours} ч. {minutes} мин.", parse_mode="Markdown")

# ===== АВТО-ОТЧЁТ =====
def auto_daily_report():
    while True:
        now = datetime.now()
        target = now.replace(hour=23, minute=55, second=0, microsecond=0)
        if now > target:
            target += timedelta(days=1)
        time.sleep((target - now).total_seconds())
        today = datetime.now().strftime("%Y-%m-%d")
        for cid in list(chats_data.keys()):
            stats = daily_stats.get(cid, {}).get(today, {})
            if stats and stats["messages"] > 10:
                total_msgs = stats["messages"]
                total_users = len(stats["users"])
                top_users = sorted(stats["users"].items(), key=lambda x: x[1], reverse=True)[:5]
                text = f"📰 **Итоги дня** ({today})\n💬 {total_msgs} сообщ. | 👥 {total_users} акт.\n🏆 Топ: "
                for i, (uid, _) in enumerate(top_users):
                    name = get_user_name(uid, cid)
                    text += f"{i+1}. {name} "
                try:
                    bot.send_message(cid, text, parse_mode="Markdown")
                except:
                    pass

# ===== ЗАПУСК =====
print("🧱 Wall запущен!")
load_all_data()
threading.Thread(target=auto_daily_report, daemon=True).start()
threading.Thread(target=auto_save, daemon=True).start()
bot.infinity_polling()