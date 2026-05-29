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
clans_data = {}
captcha_data = {}
steal_times = {}
boss_data = {}
start_time = datetime.now()

# Настройки владельца
owner_settings = {
    "casino_odds": 0.5,
    "steal_chance": 0.5,
    "work_min": 10,
    "work_max": 30,
    "daily_bonus_min": 50,
    "daily_bonus_max": 250,
}

VIP_LEVELS = {
    1: {"name": "VIP", "prefix": "[VIP]", "color": "🟣", "price": 3000},
    2: {"name": "VIP+", "prefix": "[VIP+]", "color": "🟡", "price": 15000},
    3: {"name": "LEGEND+", "prefix": "[LEGEND+]", "color": "🔴", "price": 50000},
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
        "clans_data": clans_data,
        "captcha_data": captcha_data,
        "owner_settings": owner_settings
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
    global staff_data, warns_data, mutes_data, bans_data, chats_data, daily_stats, user_profiles, vip_data, economy, temp_data, clans_data, captcha_data, owner_settings
    
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
        captcha_data = {int(cid): users for cid, users in data.get("captcha_data", {}).items()}
        owner_settings = data.get("owner_settings", {
            "casino_odds": 0.5, "steal_chance": 0.5,
            "work_min": 10, "work_max": 30,
            "daily_bonus_min": 50, "daily_bonus_max": 250
        })
        
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
    
    # Автоматически добавляем пользователя в базу при любом сообщении
    get_balance(uid)
    
    if cid not in daily_stats:
        daily_stats[cid] = {}
    if today not in daily_stats[cid]:
        daily_stats[cid][today] = {"messages": 0, "users": {}, "new_users": []}
    
    daily_stats[cid][today]["messages"] += 1
    daily_stats[cid][today]["users"][uid] = daily_stats[cid][today]["users"].get(uid, 0) + 1
    add_bricks(uid, 1)

# ===== КЛАНЫ =====
def get_user_clan(user_id):
    for name, data in clans_data.items():
        if user_id in data.get("members", []):
            return name
    return None

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

# ===== START С КАПЧЕЙ =====
@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    
    # Проверяем капчу
    for cid, users in list(captcha_data.items()):
        if user_id in users:
            try:
                bot.restrict_chat_member(
                    cid, user_id,
                    can_send_messages=True, can_send_photos=True, can_send_videos=True,
                    can_send_voices=True, can_send_audios=True, can_send_documents=True,
                    can_send_stickers=True, can_send_animations=True, can_send_games=True,
                    can_send_polls=True
                )
                captcha_data[cid].remove(user_id)
                if not captcha_data[cid]:
                    del captcha_data[cid]
                bot.send_message(user_id, "✅ Капча пройдена! Можешь общаться в чате.")
                save_all_data()
            except:
                pass
    
    # Сохраняем пользователя в базу
    get_balance(user_id)
    save_all_data()
    
    if message.chat.type == 'private':
        bot.send_message(message.chat.id,
            "🧱 **Wall — Чат-менеджер**\n\n"
            "Добавь меня в группу и выдай права админа!\n\n"
            "Используй кнопки ниже для навигации!",
            parse_mode="Markdown",
            reply_markup=get_private_keyboard())

# ===== ОБРАБОТЧИК ВСЕХ ЛС СООБЩЕНИЙ =====
@bot.message_handler(func=lambda m: m.chat.type == 'private')
def private_handler(message):
    """Сохраняет пользователя при любом сообщении в ЛС"""
    get_balance(message.from_user.id)
    save_all_data()
    
    # Авто-ответ только на неизвестные команды
    known_buttons = ["❓ Помощь", "👤 Кем создан?", "💎 Купить VIP", "👤 Мой профиль", "💰 Баланс"]
    if message.text and message.text not in known_buttons and not message.text.startswith('/'):
        bot.reply_to(message, 
            "👋 Привет! Используй кнопки ниже или напиши /help",
            reply_markup=get_private_keyboard())

# ===== КНОПКИ ЛС =====
@bot.message_handler(func=lambda m: m.chat.type == 'private' and m.text == "❓ Помощь")
def private_help(message):
    text = """🧱 **Wall — Команды**
👤 **Для всех:** /id, /info, /report, /rules, /staff, /translate, /anonym, /nick, /bio, /profile, /top, /meme, /balance, /work, /daily, /pay, /casino, /clan, /lyrics, /song, /youtube, /botlink
🛡️ **Модерация:** Ранг 1: /mute, /mutetime, /warn, /kick. Ранг 2: + /bantime, /pin, /unpin. Ранг 3: + /ban, /unban. Ранг 4: + /raising, /downgrade, /gg
💬 **RP:** /hug, /kiss, /slap, /pat, /kill, /revive, /hugme, /cry, /laugh, /dance, /poke, /tickle, /highfive, /wink, /blush, /facepalm, /shrug, /angry, /bored, /confused, /hungry, /sleep, /wakeup, /yawn, /think
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
        parse_mode="Markdown", reply_markup=markup)

@bot.callback_query_handler(func=lambda c: c.data.startswith("buyvip_"))
def buy_vip_callback(call):
    user_id = call.from_user.id
    level = int(call.data.split("_")[1])
    info = VIP_LEVELS[level]
    bal = get_balance(user_id)
    if not spend_bricks(user_id, info["price"]):
        bot.answer_callback_query(call.id, f"❌ Не хватает! Нужно {info['price']:,}, у тебя {bal['balance']:,}")
        return
    vip_data[str(user_id)] = {"level": level, "color": "purple"}
    save_all_data()
    bot.answer_callback_query(call.id, f"✅ Куплен {info['name']}!")
    bot.send_message(user_id, f"🎉 Ты теперь {info['color']} {info['name']}!\n/viphelp — список команд.")

@bot.message_handler(func=lambda m: m.chat.type == 'private' and m.text == "💰 Баланс")
def balance_cmd_private(message):
    bal = get_balance(message.from_user.id)
    vip = get_vip(message.from_user.id)
    vip_text = f"\n💎 {VIP_LEVELS[vip['level']]['name']}" if vip['level'] > 0 else ""
    bot.reply_to(message, f"💰 Баланс: {bal['balance']:,} 🧱{vip_text}")

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

# ===== ЭКОНОМИКА =====
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
    earnings = random.randint(owner_settings["work_min"], owner_settings["work_max"])
    if is_vip(user_id):
        earnings = int(earnings * 1.5)
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
    bonus = random.randint(owner_settings["daily_bonus_min"], owner_settings["daily_bonus_max"])
    if is_vip(user_id):
        bonus = int(bonus * 1.5)
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

# ===== ПРОФИЛЬ =====
@bot.message_handler(commands=['profile'])
def profile_cmd(message):
    if message.reply_to_message:
        u = message.reply_to_message.from_user
    else:
        u = message.from_user
    uid = u.id
    cid = message.chat.id
    profile = get_profile(uid)
    vip = get_vip(uid)
    clan = get_user_clan(uid)
    rank = get_rank(cid, uid)
    total_msgs = 0
    for chat_id, days in daily_stats.items():
        for day, data in days.items():
            total_msgs += data.get("users", {}).get(uid, 0)
    reg_date = "Неизвестно"
    if str(uid) in economy:
        eco = economy[str(uid)]
        dates = []
        if eco.get("last_work"): dates.append(eco["last_work"][:10])
        if eco.get("last_daily"): dates.append(eco["last_daily"])
        if dates: reg_date = sorted(dates)[0]
    vip_text = f"{VIP_LEVELS[vip['level']]['color']} {VIP_LEVELS[vip['level']]['name']}" if vip['level'] > 0 else "Нет"
    rank_names = {0: "Участник", 1: "Модератор", 2: "Мл. владелец", 3: "Пом. владельца", 4: "Владелец"}
    text = f"""📇 **Профиль игрока**
━━━━━━━━━━━━━━━━
👤 Имя: {profile['nick'] or u.first_name}
🆔 ID: `{uid}`
💎 VIP: {vip_text}
🏰 Клан: {clan if clan else 'Нет'}
🎖 Ранг в чате: {rank_names[rank]}
📅 В боте с: {reg_date}
💬 Сообщений: {total_msgs}
━━━━━━━━━━━━━━━━"""
    bot.reply_to(message, text, parse_mode="Markdown")

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

# ===== КЛАНЫ =====
@bot.message_handler(commands=['clan'])
def clan_cmd(message):
    args = message.text.split(maxsplit=2)
    if len(args) < 2:
        bot.reply_to(message, 
            "🏰 **Кланы:**\n/clan create [имя] (2000 🧱)\n/clan join [имя]\n/clan leave\n/clan info\n/clan members\n/clan kick [ID]\n/clan promote [ID]\n/clan disband\n/clan bank\n/clan donate [сумма]\n/clan list\n/clan top",
            parse_mode="Markdown")
        return
    action = args[1].lower()
    user_id = message.from_user.id
    if action == "create":
        if len(args) < 3: bot.reply_to(message, "❌ /clan create [имя]"); return
        name = args[2][:30]
        if name in clans_data: bot.reply_to(message, "❌ Клан уже существует!"); return
        if get_user_clan(user_id): bot.reply_to(message, "❌ Ты уже в клане!"); return
        if not spend_bricks(user_id, 2000): bot.reply_to(message, "❌ Нужно 2,000 🧱!"); return
        clans_data[name] = {"owner": user_id, "members": [user_id], "bank": 0, "created": datetime.now().isoformat()}
        save_all_data()
        bot.reply_to(message, f"🏰 Клан **{name}** создан! (-2,000 🧱)", parse_mode="Markdown")
    elif action == "join":
        if len(args) < 3: bot.reply_to(message, "❌ /clan join [имя]"); return
        name = args[2]
        if name not in clans_data: bot.reply_to(message, "❌ Клан не найден!"); return
        if get_user_clan(user_id): bot.reply_to(message, "❌ Ты уже в клане!"); return
        clans_data[name]["members"].append(user_id)
        save_all_data()
        bot.reply_to(message, f"✅ Ты вступил в клан **{name}**!")
    elif action == "leave":
        clan = get_user_clan(user_id)
        if not clan: bot.reply_to(message, "❌ Ты не в клане!"); return
        if clans_data[clan]["owner"] == user_id: bot.reply_to(message, "❌ Глава не может покинуть клан!"); return
        clans_data[clan]["members"].remove(user_id)
        save_all_data()
        bot.reply_to(message, f"🚪 Ты покинул клан **{clan}**.")
    elif action == "info":
        clan = get_user_clan(user_id)
        if not clan: bot.reply_to(message, "❌ Ты не в клане!"); return
        data = clans_data[clan]
        text = f"""🏰 **{clan}**\n👑 Глава: {get_user_name(data['owner'])}\n👥 Участников: {len(data['members'])}\n💰 Казна: {data['bank']:,} 🧱\n📅 Создан: {data['created'][:10]}"""
        bot.reply_to(message, text, parse_mode="Markdown")
    elif action == "members":
        clan = get_user_clan(user_id)
        if not clan: bot.reply_to(message, "❌ Ты не в клане!"); return
        data = clans_data[clan]
        text = f"👥 **{clan}:**\n\n"
        for mid in data["members"]:
            crown = " 👑" if mid == data["owner"] else ""
            text += f"• {get_user_name(mid)}{crown}\n"
        bot.reply_to(message, text, parse_mode="Markdown")
    elif action == "kick":
        if len(args) < 3: bot.reply_to(message, "❌ /clan kick [ID]"); return
        clan = get_user_clan(user_id)
        if not clan or clans_data[clan]["owner"] != user_id: bot.reply_to(message, "❌ Только глава!"); return
        try: target = int(args[2])
        except: bot.reply_to(message, "❌ Неверный ID!"); return
        if target not in clans_data[clan]["members"]: bot.reply_to(message, "❌ Не в клане!"); return
        clans_data[clan]["members"].remove(target)
        save_all_data()
        bot.reply_to(message, f"👢 {get_user_name(target)} исключён!")
    elif action == "promote":
        if len(args) < 3: bot.reply_to(message, "❌ /clan promote [ID]"); return
        clan = get_user_clan(user_id)
        if not clan or clans_data[clan]["owner"] != user_id: bot.reply_to(message, "❌ Только глава!"); return
        try: target = int(args[2])
        except: bot.reply_to(message, "❌ Неверный ID!"); return
        if target not in clans_data[clan]["members"]: bot.reply_to(message, "❌ Не в клане!"); return
        clans_data[clan]["owner"] = target
        save_all_data()
        bot.reply_to(message, f"👑 {get_user_name(target)} теперь глава!")
    elif action == "disband":
        clan = get_user_clan(user_id)
        if not clan or clans_data[clan]["owner"] != user_id: bot.reply_to(message, "❌ Только глава!"); return
        del clans_data[clan]
        save_all_data()
        bot.reply_to(message, f"💀 Клан **{clan}** распущен.")
    elif action == "bank":
        clan = get_user_clan(user_id)
        if not clan: bot.reply_to(message, "❌ Ты не в клане!"); return
        bot.reply_to(message, f"💰 Казна клана **{clan}**: {clans_data[clan]['bank']:,} 🧱")
    elif action == "donate":
        if len(args) < 3: bot.reply_to(message, "❌ /clan donate [сумма]"); return
        clan = get_user_clan(user_id)
        if not clan: bot.reply_to(message, "❌ Ты не в клане!"); return
        try: amount = int(args[2])
        except: bot.reply_to(message, "❌ Число!"); return
        if amount <= 0: bot.reply_to(message, "❌ Сумма > 0!"); return
        if not spend_bricks(user_id, amount): bot.reply_to(message, "❌ Недостаточно!"); return
        clans_data[clan]["bank"] += amount
        save_all_data()
        bot.reply_to(message, f"✅ {amount:,} 🧱 в казну **{clan}**!")
    elif action == "list":
        if not clans_data: bot.reply_to(message, "📭 Нет кланов."); return
        text = "🏰 **Список кланов:**\n\n"
        for name, data in sorted(clans_data.items(), key=lambda x: len(x[1]["members"]), reverse=True):
            text += f"• **{name}** — {len(data['members'])} чел. | 💰 {data['bank']:,} 🧱\n"
        bot.reply_to(message, text, parse_mode="Markdown")
    elif action == "top":
        if not clans_data: bot.reply_to(message, "📭 Нет кланов."); return
        sorted_clans = sorted(clans_data.items(), key=lambda x: x[1]["bank"], reverse=True)[:10]
        text = "🏆 **Топ кланов:**\n\n"
        for i, (name, data) in enumerate(sorted_clans, 1):
            text += f"{i}. **{name}** — {data['bank']:,} 🧱 ({len(data['members'])} чел.)\n"
        bot.reply_to(message, text, parse_mode="Markdown")

# ===== МУЗЫКА =====
@bot.message_handler(commands=['lyrics'])
def lyrics_cmd(message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2: bot.reply_to(message, "❌ /lyrics [песня]"); return
    try:
        url = f"https://api.lyrics.ovh/v1/{args[1]}"
        response = requests.get(url).json()
        if "lyrics" in response:
            bot.reply_to(message, f"🎵 **{args[1]}**\n\n{response['lyrics'][:4000]}", parse_mode="Markdown")
        else: bot.reply_to(message, "❌ Текст не найден!")
    except: bot.reply_to(message, "❌ Ошибка!")

@bot.message_handler(commands=['song'])
def song_cmd(message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2: bot.reply_to(message, "❌ /song [название]"); return
    try:
        url = f"http://ws.audioscrobbler.com/2.0/?method=track.search&track={args[1]}&api_key=1d3e5c5e5c5e5c5e5c5e5c5e5c5e5c5e&format=json"
        response = requests.get(url).json()
        tracks = response.get("results", {}).get("trackmatches", {}).get("track", [])
        if tracks:
            t = tracks[0]
            bot.reply_to(message, f"🎵 **{t['name']}**\n👤 {t['artist']}\n🔗 [Last.fm]({t['url']})", parse_mode="Markdown")
        else: bot.reply_to(message, "❌ Не найдено!")
    except: bot.reply_to(message, "❌ Ошибка!")

@bot.message_handler(commands=['youtube'])
def youtube_cmd(message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2: bot.reply_to(message, "❌ /youtube [запрос]"); return
    query = args[1].replace(" ", "+")
    bot.reply_to(message, f"🔍 [YouTube: {args[1]}](https://www.youtube.com/results?search_query={query})", parse_mode="Markdown", disable_web_page_preview=False)

# ===== ВЫДАЧА ОТ ВЛАДЕЛЬЦА =====
@bot.message_handler(commands=['gift'])
def gift_cmd(message):
    if message.from_user.id != OWNER_ID:
        bot.reply_to(message, "❌ Только владелец!")
        return
    args = message.text.split()
    if len(args) < 3:
        bot.reply_to(message, "❌ /gift [ID] [что] [кол-во] [время]\n📋 vip [1-3], bricks [сумма], rank [1-3], unwarn, reset\n⏰ 1h, 1d, 7d, 30d, perm")
        return
    try:
        target_id = int(args[1])
        action = args[2].lower()
    except:
        bot.reply_to(message, "❌ Неверный ID!"); return
    
    if action == "vip":
        if len(args) < 4: bot.reply_to(message, "❌ /gift [ID] vip [1-3] [время]"); return
        level = int(args[3])
        if level < 1 or level > 3: bot.reply_to(message, "❌ Уровень 1-3!"); return
        time_str = args[4] if len(args) > 4 else "perm"
        until = None
        if time_str != "perm":
            match = re.match(r'(\d+)(h|d)', time_str)
            if match: until = datetime.now() + timedelta(hours=int(match.group(1))) if match.group(2) == 'h' else datetime.now() + timedelta(days=int(match.group(1)))
            else: bot.reply_to(message, "❌ Формат: 1h, 1d, 7d"); return
        vip_data[str(target_id)] = {"level": level, "color": "purple"}
        if until:
            if str(target_id) not in temp_data: temp_data[str(target_id)] = {}
            temp_data[str(target_id)]["vip"] = {"level": level, "until": until}
        save_all_data()
        bot.reply_to(message, f"✅ {VIP_LEVELS[level]['color']} {VIP_LEVELS[level]['name']} выдан {target_id}!")
    elif action == "bricks":
        if len(args) < 4: bot.reply_to(message, "❌ /gift [ID] bricks [сумма]"); return
        add_bricks(target_id, int(args[3]))
        save_all_data()
        bot.reply_to(message, f"✅ {int(args[3]):,} 🧱 выдано {target_id}!")
    elif action == "rank":
        if len(args) < 4: bot.reply_to(message, "❌ /gift [ID] rank [1-3] [время]"); return
        rank_level = int(args[3])
        time_str = args[4] if len(args) > 4 else "perm"
        until = None
        if time_str != "perm":
            match = re.match(r'(\d+)(h|d)', time_str)
            if match: until = datetime.now() + timedelta(hours=int(match.group(1))) if match.group(2) == 'h' else datetime.now() + timedelta(days=int(match.group(1)))
        for cid in chats_data.keys(): set_rank(int(cid), target_id, rank_level)
        if until:
            if str(target_id) not in temp_data: temp_data[str(target_id)] = {}
            temp_data[str(target_id)]["rank"] = {"level": rank_level, "until": until}
        save_all_data()
        rn = {1: "Модератор", 2: "Мл. владелец", 3: "Пом. владельца"}
        bot.reply_to(message, f"✅ Ранг {rn[rank_level]} выдан {target_id}!")
    elif action == "unwarn":
        if str(target_id) in warns_data: warns_data[str(target_id)] = {}; save_all_data(); bot.reply_to(message, f"✅ Варны сняты с {target_id}!")
        else: bot.reply_to(message, f"❌ У {target_id} нет варнов!")
    elif action == "reset":
        uid = str(target_id)
        for d in [economy, vip_data, warns_data, mutes_data, bans_data, user_profiles, temp_data]:
            d.pop(uid, None) if uid in d else None
        for cid in staff_data: staff_data[cid].pop(target_id, None)
        save_all_data()
        bot.reply_to(message, f"💀 {target_id} сброшен!")

# ===== ПАНЕЛЬ ВЛАДЕЛЬЦА =====
@bot.message_handler(commands=['owner'])
def owner_panel(message):
    if message.from_user.id != OWNER_ID:
        bot.reply_to(message, "❌ Только владелец!")
        return
    text = f"""👑 **Панель владельца**

⚙️ **Настройки:**
/setboss [HP] — создать босса
/killboss — убить босса
/setcasinoodds [0.1-0.9] — шанс казино (сейчас: {owner_settings['casino_odds']})
/setstealchance [0.1-0.9] — шанс кражи (сейчас: {owner_settings['steal_chance']})
/setworkmin [сумма] — мин. работа (сейчас: {owner_settings['work_min']})
/setworkmax [сумма] — макс. работа (сейчас: {owner_settings['work_max']})
/setdailybonusmin [сумма] — мин. бонус (сейчас: {owner_settings['daily_bonus_min']})
/setdailybonusmax [сумма] — макс. бонус (сейчас: {owner_settings['daily_bonus_max']})

🎮 **Действия:**
/gift — выдать что угодно
/msg — сообщение в ЛС
/dmall — рассылка всем в ЛС
/broadcast — рассылка в чаты
/gban — глобальный бан"""
    bot.reply_to(message, text, parse_mode="Markdown")

@bot.message_handler(commands=['setboss'])
def setboss_cmd(message):
    if message.from_user.id != OWNER_ID: return
    args = message.text.split()
    if len(args) < 2: bot.reply_to(message, "❌ /setboss [HP]"); return
    try: hp = int(args[1])
    except: bot.reply_to(message, "❌ Число!"); return
    cid = message.chat.id
    boss_data[cid] = {"hp": hp, "max_hp": hp, "players": [OWNER_ID], "active": True, "started": True, "damage_dealt": {}}
    bot.reply_to(message, f"🐉 Босс создан! HP: {hp}")

@bot.message_handler(commands=['killboss'])
def killboss_cmd(message):
    if message.from_user.id != OWNER_ID: return
    cid = message.chat.id
    if cid in boss_data: del boss_data[cid]; bot.reply_to(message, "💀 Босс уничтожен.")
    else: bot.reply_to(message, "❌ Нет активного босса!")

@bot.message_handler(commands=['setcasinoodds'])
def setcasinoodds_cmd(message):
    if message.from_user.id != OWNER_ID: return
    args = message.text.split()
    if len(args) < 2: bot.reply_to(message, f"❌ /setcasinoodds [0.1-0.9] (сейчас: {owner_settings['casino_odds']})"); return
    try: val = float(args[1])
    except: bot.reply_to(message, "❌ Число!"); return
    if val < 0.1 or val > 0.9: bot.reply_to(message, "❌ От 0.1 до 0.9!"); return
    owner_settings["casino_odds"] = val
    save_all_data()
    bot.reply_to(message, f"✅ Шанс казино: {val}")

@bot.message_handler(commands=['setstealchance'])
def setstealchance_cmd(message):
    if message.from_user.id != OWNER_ID: return
    args = message.text.split()
    if len(args) < 2: bot.reply_to(message, f"❌ /setstealchance [0.1-0.9] (сейчас: {owner_settings['steal_chance']})"); return
    try: val = float(args[1])
    except: bot.reply_to(message, "❌ Число!"); return
    if val < 0.1 or val > 0.9: bot.reply_to(message, "❌ От 0.1 до 0.9!"); return
    owner_settings["steal_chance"] = val
    save_all_data()
    bot.reply_to(message, f"✅ Шанс кражи: {val}")

@bot.message_handler(commands=['setworkmin'])
def setworkmin_cmd(message):
    if message.from_user.id != OWNER_ID: return
    args = message.text.split()
    if len(args) < 2: bot.reply_to(message, f"❌ /setworkmin [сумма] (сейчас: {owner_settings['work_min']})"); return
    try: val = int(args[1])
    except: bot.reply_to(message, "❌ Число!"); return
    owner_settings["work_min"] = val
    save_all_data()
    bot.reply_to(message, f"✅ Мин. работа: {val} 🧱")

@bot.message_handler(commands=['setworkmax'])
def setworkmax_cmd(message):
    if message.from_user.id != OWNER_ID: return
    args = message.text.split()
    if len(args) < 2: bot.reply_to(message, f"❌ /setworkmax [сумма] (сейчас: {owner_settings['work_max']})"); return
    try: val = int(args[1])
    except: bot.reply_to(message, "❌ Число!"); return
    owner_settings["work_max"] = val
    save_all_data()
    bot.reply_to(message, f"✅ Макс. работа: {val} 🧱")

@bot.message_handler(commands=['setdailybonusmin'])
def setdailybonusmin_cmd(message):
    if message.from_user.id != OWNER_ID: return
    args = message.text.split()
    if len(args) < 2: bot.reply_to(message, f"❌ /setdailybonusmin [сумма] (сейчас: {owner_settings['daily_bonus_min']})"); return
    try: val = int(args[1])
    except: bot.reply_to(message, "❌ Число!"); return
    owner_settings["daily_bonus_min"] = val
    save_all_data()
    bot.reply_to(message, f"✅ Мин. бонус: {val} 🧱")

@bot.message_handler(commands=['setdailybonusmax'])
def setdailybonusmax_cmd(message):
    if message.from_user.id != OWNER_ID: return
    args = message.text.split()
    if len(args) < 2: bot.reply_to(message, f"❌ /setdailybonusmax [сумма] (сейчас: {owner_settings['daily_bonus_max']})"); return
    try: val = int(args[1])
    except: bot.reply_to(message, "❌ Число!"); return
    owner_settings["daily_bonus_max"] = val
    save_all_data()
    bot.reply_to(message, f"✅ Макс. бонус: {val} 🧱")

# ===== КАЗИНО =====
@bot.message_handler(commands=['casino'])
def casino_cmd(message):
    args = message.text.split()
    if len(args) < 2: bot.reply_to(message, "❌ /casino [ставка]"); return
    try: bet = int(args[1])
    except: bot.reply_to(message, "❌ Число!"); return
    if bet < 10: bot.reply_to(message, "❌ Минимум 10 🧱!"); return
    user_id = message.from_user.id
    if not spend_bricks(user_id, bet): bot.reply_to(message, "❌ Недостаточно!"); return
    
    if random.random() < owner_settings["casino_odds"]:
        win = bet * 2
        add_bricks(user_id, win)
        save_all_data()
        bot.reply_to(message, f"🎰 Выигрыш! +{win} 🧱\nБаланс: {get_balance(user_id)['balance']:,} 🧱")
    else:
        save_all_data()
        bot.reply_to(message, f"🎰 Проигрыш! -{bet} 🧱\nБаланс: {get_balance(user_id)['balance']:,} 🧱")

# ===== КРАЖА (VIP 2+) =====
@bot.message_handler(commands=['steal'])
def steal_cmd(message):
    if get_vip(message.from_user.id)["level"] < 2:
        bot.reply_to(message, "❌ Только для VIP+!")
        return
    user_id = message.from_user.id
    last_steal = steal_times.get(user_id)
    if last_steal:
        elapsed = datetime.now() - last_steal
        if elapsed < timedelta(minutes=10):
            remaining = timedelta(minutes=10) - elapsed
            bot.reply_to(message, f"⏳ Жди {remaining.seconds // 60} мин. {remaining.seconds % 60} сек.")
            return
    if not message.reply_to_message: bot.reply_to(message, "❌ Ответь на сообщение жертвы!"); return
    victim = message.reply_to_message.from_user
    if victim.id == user_id: bot.reply_to(message, "❌ Нельзя украсть у себя!"); return
    victim_bal = get_balance(victim.id)
    if victim_bal["balance"] < 10: bot.reply_to(message, "❌ У жертвы меньше 10 🧱!"); return
    amount = random.randint(10, min(100, victim_bal["balance"]))
    
    if random.random() < owner_settings["steal_chance"]:
        victim_bal["balance"] -= amount
        add_bricks(user_id, amount)
        steal_times[user_id] = datetime.now()
        save_all_data()
        bot.reply_to(message, f"🦹 Ты украл {amount} 🧱 у {victim.first_name}!\nБаланс: {get_balance(user_id)['balance']:,} 🧱")
    else:
        penalty = random.randint(5, 20)
        if get_balance(user_id)["balance"] >= penalty:
            spend_bricks(user_id, penalty)
            add_bricks(victim.id, penalty)
            steal_times[user_id] = datetime.now()
            save_all_data()
            bot.reply_to(message, f"🚨 Провал! Штраф {penalty} 🧱 → {victim.first_name}.")
        else:
            bot.reply_to(message, f"🚨 Провал! Но нет денег на штраф. Повезло...")

# ===== БОСС (VIP 3+) =====
@bot.message_handler(commands=['boss'])
def boss_cmd(message):
    if get_vip(message.from_user.id)["level"] < 3:
        bot.reply_to(message, "❌ Только для LEGEND+!")
        return
    cid = message.chat.id
    user_id = message.from_user.id
    if cid in boss_data and boss_data[cid].get("active"):
        bot.reply_to(message, "⚔️ Босс уже активен! /joinboss")
        return
    hp = random.choice([2500, 3000])
    boss_data[cid] = {"hp": hp, "max_hp": hp, "players": [user_id], "active": True, "started": False, "damage_dealt": {}}
    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(telebot.types.InlineKeyboardButton("⚔️ Присоединиться!", callback_data="joinboss"))
    markup.add(telebot.types.InlineKeyboardButton("👊 Атаковать!", callback_data="attackboss"))
    bot.send_message(cid, f"🐉 **БОСС!**\n❤️ HP: {hp}/{hp}\n👥 1/4\nНужно 4 чел.!", parse_mode="Markdown", reply_markup=markup)

@bot.callback_query_handler(func=lambda c: c.data == "joinboss")
def join_boss(call):
    cid = call.message.chat.id
    user_id = call.from_user.id
    if cid not in boss_data or not boss_data[cid].get("active"): bot.answer_callback_query(call.id, "❌ Нет босса!"); return
    boss = boss_data[cid]
    if user_id in boss["players"]: bot.answer_callback_query(call.id, "❌ Ты уже в битве!"); return
    if boss["started"]: bot.answer_callback_query(call.id, "❌ Битва началась!"); return
    boss["players"].append(user_id)
    if len(boss["players"]) >= 4:
        boss["started"] = True
        markup = telebot.types.InlineKeyboardMarkup()
        markup.add(telebot.types.InlineKeyboardButton("👊 Атаковать!", callback_data="attackboss"))
        names = ", ".join(get_user_name(p, cid) for p in boss["players"])
        bot.edit_message_text(f"🐉 **БОСС!**\n❤️ HP: {boss['hp']}/{boss['max_hp']}\n👥 {names}\nАтакуйте!", parse_mode="Markdown", chat_id=cid, message_id=call.message.message_id, reply_markup=markup)
        bot.answer_callback_query(call.id, "⚔️ Битва началась!")
    else:
        names = ", ".join(get_user_name(p, cid) for p in boss["players"])
        markup = telebot.types.InlineKeyboardMarkup()
        markup.add(telebot.types.InlineKeyboardButton("⚔️ Присоединиться!", callback_data="joinboss"))
        markup.add(telebot.types.InlineKeyboardButton("👊 Атаковать!", callback_data="attackboss"))
        bot.edit_message_text(f"🐉 **БОСС!**\n❤️ HP: {boss['hp']}/{boss['max_hp']}\n👥 {len(boss['players'])}/4\n{names}\nНужно ещё {4-len(boss['players'])}", parse_mode="Markdown", chat_id=cid, message_id=call.message.message_id, reply_markup=markup)
        bot.answer_callback_query(call.id, f"✅ {len(boss['players'])}/4")

@bot.callback_query_handler(func=lambda c: c.data == "attackboss")
def attack_boss(call):
    cid = call.message.chat.id
    user_id = call.from_user.id
    if cid not in boss_data or not boss_data[cid].get("active"): bot.answer_callback_query(call.id, "❌ Нет босса!"); return
    boss = boss_data[cid]
    if user_id not in boss["players"]: bot.answer_callback_query(call.id, "❌ Не в битве!"); return
    if not boss["started"]: bot.answer_callback_query(call.id, "⏳ Ждём игроков!"); return
    damage = random.randint(50, 200)
    boss["hp"] -= damage
    boss["damage_dealt"][user_id] = boss["damage_dealt"].get(user_id, 0) + damage
    
    if boss["hp"] <= 0:
        boss["hp"] = 0; boss["active"] = False
        reward = random.randint(100, 500) // len(boss["players"])
        for pid in boss["players"]: add_bricks(pid, reward)
        top = sorted(boss["damage_dealt"].items(), key=lambda x: x[1], reverse=True)
        mvp_name = get_user_name(top[0][0], cid) if top else "Никто"
        text = f"🎉 **БОСС ПОВЕРЖЕН!**\n💰 Награда: {reward} 🧱\n🏆 MVP: {mvp_name}\n📊 Урон:\n"
        for pid, dmg in top: text += f"• {get_user_name(pid, cid)}: {dmg}\n"
        del boss_data[cid]
        save_all_data()
        bot.edit_message_text(text, parse_mode="Markdown", chat_id=cid, message_id=call.message.message_id)
        bot.answer_callback_query(call.id, f"💥 {damage} урона! Победа!")
    else:
        markup = telebot.types.InlineKeyboardMarkup()
        markup.add(telebot.types.InlineKeyboardButton("👊 Атаковать!", callback_data="attackboss"))
        names = ", ".join(get_user_name(p, cid) for p in boss["players"])
        bot.edit_message_text(f"🐉 **БОСС!**\n❤️ HP: {boss['hp']}/{boss['max_hp']}\n👥 {names}\nАтакуйте!", parse_mode="Markdown", chat_id=cid, message_id=call.message.message_id, reply_markup=markup)
        bot.answer_callback_query(call.id, f"👊 {damage} урона! HP: {boss['hp']}")

# ===== VIP-КОМАНДЫ =====
@bot.message_handler(commands=['viphelp'])
def vip_help(message):
    if not is_vip(message.from_user.id): bot.reply_to(message, "❌ Только VIP!"); return
    bot.reply_to(message, "💎 VIP: /flex, /vipcolor, /spotlight, /loud, /ghost, /magic, /slow\n🌟 VIP+: + /announce, /rainbow, /reverse, /secret, /countdown, /steal\n💎 LEGEND+: + /say, /echo, /bomb, /weather, /boss")

@bot.message_handler(commands=['flex'])
def flex_cmd(message):
    if not is_vip(message.from_user.id): return
    vip = get_vip(message.from_user.id)
    info = VIP_LEVELS[vip["level"]]
    bot.send_message(message.chat.id, f"💎 {info['prefix']} **{message.from_user.first_name}**\nУровень: {info['color']} {info['name']}\n💰 {get_balance(message.from_user.id)['balance']:,} 🧱", parse_mode="Markdown")

@bot.message_handler(commands=['vipcolor'])
def vipcolor_cmd(message):
    if not is_vip(message.from_user.id): return
    args = message.text.split()
    if len(args) < 2: bot.reply_to(message, f"❌ /vipcolor [{'/'.join(VIP_COLORS)}]"); return
    if args[1].lower() not in VIP_COLORS: bot.reply_to(message, "❌ Недоступный цвет!"); return
    vip_data[str(message.from_user.id)]["color"] = args[1].lower()
    save_all_data()
    bot.reply_to(message, f"✅ Цвет: {args[1]}")

@bot.message_handler(commands=['spotlight'])
def spotlight_cmd(message):
    if not is_vip(message.from_user.id): return
    args = message.text.split(maxsplit=1)
    if len(args) < 2: bot.reply_to(message, "❌ /spotlight [текст]"); return
    bot.send_message(message.chat.id, f"🔦 **В центре внимания:**\n\n✨ {args[1]} ✨", parse_mode="Markdown")

@bot.message_handler(commands=['loud'])
def loud_cmd(message):
    if not is_vip(message.from_user.id): return
    args = message.text.split(maxsplit=1)
    if len(args) < 2: bot.reply_to(message, "❌ /loud [текст]"); return
    bot.send_message(message.chat.id, f"📢 {args[1].upper()} 📢")

@bot.message_handler(commands=['ghost'])
def ghost_cmd(message):
    if not is_vip(message.from_user.id): return
    args = message.text.split(maxsplit=1)
    if len(args) < 2: bot.reply_to(message, "❌ /ghost [текст]"); return
    try: bot.delete_message(message.chat.id, message.message_id)
    except: pass
    bot.send_message(message.chat.id, f"👻 **Призрак шепчет:** {args[1]}", parse_mode="Markdown")

@bot.message_handler(commands=['magic'])
def magic_cmd(message):
    if not is_vip(message.from_user.id): return
    args = message.text.split(maxsplit=1)
    if len(args) < 2: bot.reply_to(message, "❌ /magic [текст]"); return
    emojis = ["✨", "🌟", "💫", "⭐", "🔮", "💎", "🎩", "🪄"]
    text = ' '.join(f"{char} {random.choice(emojis)}" for char in args[1])
    bot.send_message(message.chat.id, f"🎩 {text}")

@bot.message_handler(commands=['slow'])
def slow_cmd(message):
    if not is_vip(message.from_user.id): return
    args = message.text.split(maxsplit=1)
    if len(args) < 2: bot.reply_to(message, "❌ /slow [текст]"); return
    for char in args[1]: bot.send_message(message.chat.id, char); time.sleep(0.3)

@bot.message_handler(commands=['announce'])
def announce_cmd(message):
    if get_vip(message.from_user.id)["level"] < 2: return
    args = message.text.split(maxsplit=1)
    if len(args) < 2: bot.reply_to(message, "❌ /announce [текст]"); return
    msg = bot.send_message(message.chat.id, f"📢 **ОБЪЯВЛЕНИЕ**\n\n{args[1]}", parse_mode="Markdown")
    try: bot.pin_chat_message(message.chat.id, msg.message_id)
    except: pass

@bot.message_handler(commands=['rainbow'])
def rainbow_cmd(message):
    if get_vip(message.from_user.id)["level"] < 2: return
    args = message.text.split(maxsplit=1)
    if len(args) < 2: bot.reply_to(message, "❌ /rainbow [текст]"); return
    colors = ["🔴", "🟠", "🟡", "🟢", "🔵", "🟣"]
    bot.send_message(message.chat.id, ' '.join(f"{colors[i % len(colors)]} {char}" for i, char in enumerate(args[1])))

@bot.message_handler(commands=['reverse'])
def reverse_cmd(message):
    if get_vip(message.from_user.id)["level"] < 2: return
    args = message.text.split(maxsplit=1)
    if len(args) < 2: bot.reply_to(message, "❌ /reverse [текст]"); return
    bot.send_message(message.chat.id, args[1][::-1])

@bot.message_handler(commands=['secret'])
def secret_cmd(message):
    if get_vip(message.from_user.id)["level"] < 2: return
    args = message.text.split(maxsplit=1)
    if len(args) < 2: bot.reply_to(message, "❌ /secret [текст]"); return
    bot.send_message(message.chat.id, f"🔒 ||{args[1]}||", parse_mode="Markdown")

@bot.message_handler(commands=['countdown'])
def countdown_cmd(message):
    if get_vip(message.from_user.id)["level"] < 2: return
    args = message.text.split()
    if len(args) < 2: bot.reply_to(message, "❌ /countdown [сек]"); return
    try: secs = min(int(args[1]), 10)
    except: bot.reply_to(message, "❌ Число!"); return
    msg = bot.send_message(message.chat.id, f"⏳ {secs}...")
    for i in range(secs-1, 0, -1): time.sleep(1); bot.edit_message_text(f"⏳ {i}...", message.chat.id, msg.message_id)
    bot.edit_message_text("🚀 ПУСК!", message.chat.id, msg.message_id)

@bot.message_handler(commands=['say'])
def say_cmd(message):
    if get_vip(message.from_user.id)["level"] < 3: return
    args = message.text.split(maxsplit=1)
    if len(args) < 2: bot.reply_to(message, "❌ /say [текст]"); return
    try: bot.delete_message(message.chat.id, message.message_id)
    except: pass
    bot.send_message(message.chat.id, args[1])

@bot.message_handler(commands=['echo'])
def echo_cmd(message):
    if get_vip(message.from_user.id)["level"] < 3: return
    args = message.text.split(maxsplit=2)
    if len(args) < 3: bot.reply_to(message, "❌ /echo [число] [текст]"); return
    try: count = min(int(args[1]), 5)
    except: bot.reply_to(message, "❌ Число!"); return
    for _ in range(count): bot.send_message(message.chat.id, args[2]); time.sleep(0.5)

@bot.message_handler(commands=['bomb'])
def bomb_cmd(message):
    if get_vip(message.from_user.id)["level"] < 3: return
    args = message.text.split()
    secs = min(int(args[1]) if len(args) > 1 else 5, 10)
    msg = bot.send_message(message.chat.id, f"💣 {secs}...")
    for i in range(secs-1, 0, -1): time.sleep(1); bot.edit_message_text(f"💣 {i}...", message.chat.id, msg.message_id)
    bot.edit_message_text("💥 БУМ! 😄", message.chat.id, msg.message_id)

@bot.message_handler(commands=['weather'])
def weather_cmd(message):
    if get_vip(message.from_user.id)["level"] < 3: return
    weathers = ["☀️ Солнечно", "🌧 Дождь", "⛈ Гроза", "❄️ Снег", "🌪 Ураган", "🌈 Радуга", "🌙 Ночь"]
    bot.send_message(message.chat.id, f"🌤 {random.choice(weathers)}", parse_mode="Markdown")

# ===== СООБЩЕНИЯ В ЛС =====
@bot.message_handler(commands=['msg'])
def msg_cmd(message):
    if message.from_user.id != OWNER_ID: return
    args = message.text.split(maxsplit=2)
    if len(args) < 3: bot.reply_to(message, "❌ /msg [юзернейм/ID] [текст]"); return
    target, text = args[1], args[2]
    target_id = None
    if target.startswith("@"): target = target[1:]
    else:
        try: target_id = int(target)
        except: bot.reply_to(message, "❌ Неверно!"); return
    try:
        if target_id: bot.send_message(target_id, f"📨 **Сообщение от администрации:**\n\n{text}", parse_mode="Markdown")
        else: bot.send_message(f"@{target}", f"📨 **Сообщение от администрации:**\n\n{text}", parse_mode="Markdown")
        bot.reply_to(message, f"✅ {target}")
    except Exception as e: bot.reply_to(message, f"❌ {e}")

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
    status_msg = bot.reply_to(message, "⏳ Начинаю рассылку...")
    
    for uid in list(economy.keys()):
        try:
            bot.send_message(int(uid), f"📢 **Массовое уведомление:**\n\n{text}", parse_mode="Markdown")
            sent += 1
            time.sleep(0.05)
        except:
            failed += 1
    
    try:
        bot.edit_message_text(
            f"✅ Рассылка завершена!\n📤 Отправлено: {sent}\n❌ Не удалось: {failed}",
            message.chat.id,
            status_msg.message_id
        )
    except:
        bot.send_message(message.chat.id, f"✅ Рассылка завершена!\n📤 Отправлено: {sent}\n❌ Не удалось: {failed}")

@bot.message_handler(commands=['botlink'])
def botlink_cmd(message):
    bot.reply_to(message, 
        "🤖 Чтобы получать уведомления от бота, напиши ему в ЛС:\n"
        "👉 @Wall_bot\n"
        "И нажми /start\n\n"
        "После этого ты будешь получать важные объявления!")

# ===== ОБЩИЕ КОМАНДЫ =====
@bot.message_handler(commands=['help'])
def help_cmd(message):
    text = """🧱 **Wall**
👤 /id, /info, /report, /rules, /staff, /translate, /anonym, /nick, /bio, /profile, /top, /meme, /balance, /work, /daily, /pay, /casino, /clan, /lyrics, /song, /youtube, /botlink
🛡️ Ранг 1: /mute, /mutetime, /warn, /kick. Ранг 2: + /bantime, /pin, /unpin. Ранг 3: + /ban, /unban. Ранг 4: + /raising, /downgrade, /gg
💬 RP: /hug, /kiss, /slap, /pat, /kill, /revive, /hugme, /cry, /laugh, /dance, /poke, /tickle, /highfive, /wink, /blush, /facepalm, /shrug, /angry, /bored, /confused, /hungry, /sleep, /wakeup, /yawn, /think
💎 VIP: /viphelp"""
    bot.reply_to(message, text, parse_mode="Markdown")

@bot.message_handler(commands=['id'])
def id_cmd(message):
    if message.reply_to_message: bot.reply_to(message, f"🆔 `{message.reply_to_message.from_user.id}`", parse_mode="Markdown")
    else: bot.reply_to(message, f"🆔 `{message.from_user.id}`\nЧат: `{message.chat.id}`", parse_mode="Markdown")

@bot.message_handler(commands=['info'])
def info_cmd(message):
    u = message.reply_to_message.from_user if message.reply_to_message else message.from_user
    cid, uid = message.chat.id, u.id
    profile, vip, clan = get_profile(uid), get_vip(uid), get_user_clan(uid)
    try: status = bot.get_chat_member(cid, uid).status
    except: status = "?"
    warns = warns_data.get(uid, {}).get(cid, [])
    mute_info = mutes_data.get(uid, {}).get(cid)
    muted = f"Да (до {mute_info.strftime('%H:%M')})" if mute_info else "Нет"
    banned = bans_data.get(uid, {}).get(cid, False)
    rank = get_rank(cid, uid)
    rn = {0:"Участник", 1:"Модератор", 2:"Мл. владелец", 3:"Пом. владельца", 4:"Владелец"}
    vip_text = f"{VIP_LEVELS[vip['level']]['color']} {VIP_LEVELS[vip['level']]['name']}" if vip['level'] > 0 else "Нет"
    text = f"""📊 **Информация**
👤 {get_vip_display(uid, profile['nick'] or u.first_name)}
🆔 `{uid}`
💎 VIP: {vip_text}
🏰 Клан: {clan or 'Нет'}
👑 Статус: {status}
🎖 Ранг: {rn[rank]} ({rank})
⚠️ Варны: {len(warns)}/3
🔇 Мут: {muted}
🚫 Бан: {'Да' if banned else 'Нет'}"""
    bot.reply_to(message, text, parse_mode="Markdown")

@bot.message_handler(commands=['rules'])
def rules_cmd(message): bot.reply_to(message, f"📜 **Правила:**\n\n{get_chat_data(message.chat.id)['rules']}", parse_mode="Markdown")

@bot.message_handler(commands=['report'])
def report_cmd(message):
    if not message.reply_to_message: bot.reply_to(message, "❌ Ответь!"); return
    args = message.text.split(maxsplit=1)
    reason = args[1] if len(args) > 1 else "Не указана"
    for adm in bot.get_chat_administrators(message.chat.id):
        try: bot.send_message(adm.user.id, f"🚨 Репорт от {message.from_user.first_name}\nНа: {message.reply_to_message.from_user.first_name}\nПричина: {reason}")
        except: pass
    bot.reply_to(message, "✅ Отправлено!")

@bot.message_handler(commands=['staff'])
def staff_list(message):
    cid = message.chat.id
    staff = staff_data.get(cid, {})
    if not staff: bot.reply_to(message, "📭 Нет."); return
    rn = {1:"Модератор", 2:"Мл. владелец", 3:"Пом. владельца"}
    text = "🛡️ **Персонал:**\n\n"
    for uid, rank in sorted(staff.items(), key=lambda x: x[1], reverse=True):
        text += f"• {get_vip_display(uid, get_user_name(uid, cid))} — {rn[rank]} ({rank})\n"
    bot.reply_to(message, text, parse_mode="Markdown")

# ===== ТОП =====
@bot.message_handler(commands=['top'])
def top_cmd(message):
    cid, today = message.chat.id, datetime.now().strftime("%Y-%m-%d")
    stats = daily_stats.get(cid, {}).get(today, {})
    text = "🏆 **Топ-10 богачей**\n\n"
    for i, (uid, data) in enumerate(sorted(economy.items(), key=lambda x: x[1].get("balance", 0), reverse=True)[:10], 1):
        name = get_user_name(int(uid), cid)
        text += f"{i}. {get_vip_display(int(uid), name)} — {data.get('balance', 0):,} 🧱\n"
    text += "\n📊 **Топ активных:**\n"
    if stats and stats.get("users"):
        for i, (uid, count) in enumerate(sorted(stats["users"].items(), key=lambda x: x[1], reverse=True)[:5], 1):
            text += f"{i}. {get_user_name(uid, cid)} — {count} сообщ.\n"
    else: text += "Нет данных.\n"
    bot.reply_to(message, text, parse_mode="Markdown")

# ===== ПЕРЕВОДЧИК / АНОНИМ / МЕМ =====
@bot.message_handler(commands=['translate'])
def translate_cmd(message):
    args = message.text.split(maxsplit=1)
    if not message.reply_to_message and len(args) < 2: bot.reply_to(message, "❌ /translate [текст]"); return
    text = message.reply_to_message.text if message.reply_to_message else args[1]
    if not text: bot.reply_to(message, "❌ Нет текста!"); return
    try:
        url = f"https://api.mymemory.translated.net/get?q={text}&langpair=auto|ru"
        translated = requests.get(url).json()['responseData']['translatedText']
        bot.reply_to(message, f"🌐 {translated}", parse_mode="Markdown")
    except: bot.reply_to(message, "❌ Ошибка!")

@bot.message_handler(commands=['anonym'])
def anonym_cmd(message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2: bot.reply_to(message, "❌ /anonym [текст]"); return
    try: bot.delete_message(message.chat.id, message.message_id)
    except: pass
    bot.send_message(message.chat.id, f"🕵️ **Аноним:**\n\n{args[1]}", parse_mode="Markdown")

@bot.message_handler(commands=['meme'])
def meme_cmd(message):
    try:
        data = requests.get("https://meme-api.com/gimme").json()
        bot.send_photo(message.chat.id, data['url'], caption=f"😄 {data['title']}")
    except: bot.reply_to(message, "❌ Не удалось!")

# ===== PIN / UNPIN =====
@bot.message_handler(commands=['pin'])
def pin_cmd(message):
    if not has_rank(message.chat.id, message.from_user.id, 2): return
    if not message.reply_to_message: bot.reply_to(message, "❌ Ответь!"); return
    try: bot.pin_chat_message(message.chat.id, message.reply_to_message.message_id); bot.reply_to(message, "📌")
    except: bot.reply_to(message, "❌")

@bot.message_handler(commands=['unpin'])
def unpin_cmd(message):
    if not has_rank(message.chat.id, message.from_user.id, 2): return
    try: bot.unpin_chat_message(message.chat.id); bot.reply_to(message, "📌 Откреплено!")
    except: bot.reply_to(message, "❌")

# ===== BANLIST / MUTELIST =====
@bot.message_handler(commands=['banlist'])
def banlist_cmd(message):
    if not has_rank(message.chat.id, message.from_user.id, 2): return
    cid = message.chat.id
    banned = [uid for uid, chats in bans_data.items() if cid in chats and chats[cid]]
    if not banned: bot.reply_to(message, "📭 Нет."); return
    text = "🚫 **Забаненные:**\n\n"
    for uid in banned[:20]: text += f"• {get_user_name(int(uid), cid)} (`{uid}`)\n"
    bot.reply_to(message, text, parse_mode="Markdown")

@bot.message_handler(commands=['mutelist'])
def mutelist_cmd(message):
    if not has_rank(message.chat.id, message.from_user.id, 2): return
    cid = message.chat.id
    muted = [uid for uid, chats in mutes_data.items() if cid in chats and chats[cid] and datetime.now() < chats[cid]]
    if not muted: bot.reply_to(message, "📭 Нет."); return
    text = "🔇 **Замученные:**\n\n"
    for uid in muted[:20]:
        mins = (mutes_data[uid][cid] - datetime.now()).seconds // 60
        text += f"• {get_user_name(uid, cid)} — ещё {mins} мин.\n"
    bot.reply_to(message, text, parse_mode="Markdown")

# ===== RP-КОМАНДЫ =====
@bot.message_handler(commands=['hug','kiss','slap','pat','kill','revive','poke','tickle','highfive','wink'])
def rp_reply_cmd(message):
    cmd = message.text.split()[0][1:]
    if not message.reply_to_message: bot.reply_to(message, "❌ Ответь!"); return
    u1, u2 = message.from_user.first_name, message.reply_to_message.from_user.first_name
    actions = {
        'hug': f"🤗 {u1} обнимает {u2}!", 'kiss': f"💋 {u1} целует {u2}!",
        'slap': f"👋 {u1} даёт пощёчину {u2}!", 'pat': f"🤚 {u1} гладит {u2}!",
        'kill': random.choice([f"🔪 {u1} убивает {u2}!", f"💀 {u1} нокаутирует {u2}!"]),
        'revive': f"💖 {u1} воскрешает {u2}!", 'poke': f"👉 {u1} тыкает {u2}!",
        'tickle': f"🤣 {u1} щекочет {u2}!", 'highfive': f"🖐 {u1} даёт пять {u2}!",
        'wink': f"😉 {u1} подмигивает {u2}!"
    }
    bot.send_message(message.chat.id, actions.get(cmd, "🤷"))

@bot.message_handler(commands=['hugme','cry','laugh','dance','blush','facepalm','shrug','angry','bored','confused','hungry','sleep','wakeup','yawn','think'])
def rp_self_cmd(message):
    cmd = message.text.split()[0][1:]
    u = message.from_user.first_name
    actions = {
        'hugme': f"🤗 {u} обнимает себя...", 'cry': f"😢 {u} плачет...",
        'laugh': random.choice([f"😂 {u} смеётся!", f"🤣 {u} умирает со смеху!"]),
        'dance': f"💃 {u} танцует!", 'blush': f"😊 {u} краснеет...",
        'facepalm': f"🤦 {u} фейспалм", 'shrug': f"🤷 {u} пожимает плечами",
        'angry': f"😤 {u} злится!", 'bored': f"🥱 {u} скучает...",
        'confused': f"🤔 {u} в замешательстве", 'hungry': f"🍔 {u} голоден!",
        'sleep': f"😴 {u} спит...", 'wakeup': f"⏰ {u} просыпается!",
        'yawn': f"🥱 {u} зевает...", 'think': f"🤔 {u} задумался..."
    }
    bot.send_message(message.chat.id, actions.get(cmd, "🤷"))

# ===== ПОВЫШЕНИЕ/ПОНИЖЕНИЕ =====
@bot.message_handler(commands=['raising'])
def raising_cmd(message):
    if not is_owner_or_creator(message.chat.id, message.from_user.id): return
    if not message.reply_to_message: bot.reply_to(message, "❌ Ответь!"); return
    u, cid, cr = message.reply_to_message.from_user, message.chat.id, get_rank(message.chat.id, message.reply_to_message.from_user.id)
    if cr >= 3: bot.reply_to(message, "❌ Макс. ранг!"); return
    set_rank(cid, u.id, cr + 1)
    save_all_data()
    rn = {1:"Модератор", 2:"Мл. владелец", 3:"Пом. владельца"}
    bot.reply_to(message, f"⬆️ {u.first_name} → {rn[cr+1]}")

@bot.message_handler(commands=['downgrade'])
def downgrade_cmd(message):
    if not is_owner_or_creator(message.chat.id, message.from_user.id): return
    if not message.reply_to_message: bot.reply_to(message, "❌ Ответь!"); return
    u, cid, cr = message.reply_to_message.from_user, message.chat.id, get_rank(message.chat.id, message.reply_to_message.from_user.id)
    if cr <= 1: bot.reply_to(message, f"❌ Используй /gg"); return
    set_rank(cid, u.id, cr - 1)
    save_all_data()
    rn = {1:"Модератор", 2:"Мл. владелец"}
    bot.reply_to(message, f"⬇️ {u.first_name} → {rn.get(cr-1, 'Участник')}")

@bot.message_handler(commands=['gg'])
def gg_cmd(message):
    if not is_owner_or_creator(message.chat.id, message.from_user.id): return
    if not message.reply_to_message: bot.reply_to(message, "❌ Ответь!"); return
    u, cid = message.reply_to_message.from_user, message.chat.id
    if get_rank(cid, u.id) == 0: bot.reply_to(message, "❌ Без ранга!"); return
    set_rank(cid, u.id, 0)
    save_all_data()
    bot.reply_to(message, f"💀 {u.first_name} лишён ранга!")

# ===== МОДЕРАЦИЯ =====
@bot.message_handler(commands=['warn'])
def warn_cmd(message):
    if not has_rank(message.chat.id, message.from_user.id, 1): return
    if not message.reply_to_message: bot.reply_to(message, "❌ Ответь!"); return
    u, cid = message.reply_to_message.from_user, message.chat.id
    wr, tr = get_rank(cid, message.from_user.id), get_rank(cid, u.id)
    if tr >= wr: bot.reply_to(message, f"❌ {random.choice(DENY_PHRASES)}"); return
    args = message.text.split(maxsplit=1)
    reason = args[1] if len(args) > 1 else "Нарушение"
    warns_data.setdefault(u.id, {}).setdefault(cid, []).append({"reason": reason, "time": datetime.now().isoformat(), "by": message.from_user.id})
    wc = len(warns_data[u.id][cid])
    if wc >= MAX_WARNS:
        cr = get_rank(cid, u.id)
        if cr > 0:
            set_rank(cid, u.id, cr - 1); warns_data[u.id][cid] = []
            rn = {0:"Участник", 1:"Модератор", 2:"Мл. владелец", 3:"Пом. владельца"}
            bot.reply_to(message, f"🚨 3/3! Ранг → {cr-1} ({rn[cr-1]})")
        else:
            try:
                bot.restrict_chat_member(cid, u.id, until_date=datetime.now() + timedelta(hours=1))
                warns_data[u.id][cid] = []
                bot.reply_to(message, f"🚨 3/3! Мут 1 час")
            except: bot.reply_to(message, "⚠️ 3/3! Нужен мут!")
    else: bot.reply_to(message, f"⚠️ {u.first_name} — {wc}/3\n{reason}")
    save_all_data()

@bot.message_handler(commands=['mute'])
def mute_cmd(message):
    if not has_rank(message.chat.id, message.from_user.id, 1): return
    if not message.reply_to_message: bot.reply_to(message, "❌ Ответь!"); return
    u, cid = message.reply_to_message.from_user, message.chat.id
    if get_rank(cid, u.id) >= get_rank(cid, message.from_user.id): bot.reply_to(message, f"❌ {random.choice(DENY_PHRASES)}"); return
    try:
        bot.restrict_chat_member(cid, u.id, until_date=datetime.now() + timedelta(days=3650))
        mutes_data.setdefault(u.id, {})[cid] = datetime.now() + timedelta(days=3650)
        save_all_data()
        bot.reply_to(message, f"🔇 {u.first_name} мут навсегда!")
    except: bot.reply_to(message, "❌")

@bot.message_handler(commands=['mutetime'])
def mutetime_cmd(message):
    if not has_rank(message.chat.id, message.from_user.id, 1): return
    if not message.reply_to_message: bot.reply_to(message, "❌ Ответь!"); return
    u, cid = message.reply_to_message.from_user, message.chat.id
    if get_rank(cid, u.id) >= get_rank(cid, message.from_user.id): bot.reply_to(message, f"❌ {random.choice(DENY_PHRASES)}"); return
    args = message.text.split()
    if len(args) < 2: bot.reply_to(message, "❌ /mutetime [мин]"); return
    try: mins = int(args[1])
    except: bot.reply_to(message, "❌ Число!"); return
    try:
        bot.restrict_chat_member(cid, u.id, until_date=datetime.now() + timedelta(minutes=mins))
        mutes_data.setdefault(u.id, {})[cid] = datetime.now() + timedelta(minutes=mins)
        save_all_data()
        bot.reply_to(message, f"🔇 {u.first_name} мут {mins} мин!")
    except: bot.reply_to(message, "❌")

@bot.message_handler(commands=['unmute'])
def unmute_cmd(message):
    if not has_rank(message.chat.id, message.from_user.id, 1): return
    if not message.reply_to_message: bot.reply_to(message, "❌ Ответь!"); return
    u, cid = message.reply_to_message.from_user, message.chat.id
    try:
        bot.restrict_chat_member(cid, u.id, can_send_messages=True, can_send_photos=True, can_send_videos=True, can_send_voices=True, can_send_audios=True, can_send_documents=True, can_send_stickers=True, can_send_animations=True, can_send_games=True, can_send_polls=True)
        if u.id in mutes_data: mutes_data[u.id].pop(cid, None)
        save_all_data()
        bot.reply_to(message, f"🔊 {u.first_name} размучен!")
    except: bot.reply_to(message, "❌")

@bot.message_handler(commands=['bantime'])
def bantime_cmd(message):
    if not has_rank(message.chat.id, message.from_user.id, 2): return
    if not message.reply_to_message: bot.reply_to(message, "❌ Ответь!"); return
    u, cid = message.reply_to_message.from_user, message.chat.id
    if get_rank(cid, u.id) >= get_rank(cid, message.from_user.id): bot.reply_to(message, f"❌ {random.choice(DENY_PHRASES)}"); return
    args = message.text.split()
    if len(args) < 2: bot.reply_to(message, "❌ /bantime [мин]"); return
    try: mins = int(args[1])
    except: bot.reply_to(message, "❌ Число!"); return
    try: bot.ban_chat_member(cid, u.id, until_date=datetime.now() + timedelta(minutes=mins)); save_all_data(); bot.reply_to(message, f"🚫 {u.first_name} бан {mins} мин!")
    except: bot.reply_to(message, "❌")

@bot.message_handler(commands=['ban'])
def ban_cmd(message):
    if not has_rank(message.chat.id, message.from_user.id, 3): return
    if not message.reply_to_message: bot.reply_to(message, "❌ Ответь!"); return
    u, cid = message.reply_to_message.from_user, message.chat.id
    if get_rank(cid, u.id) >= get_rank(cid, message.from_user.id): bot.reply_to(message, f"❌ {random.choice(DENY_PHRASES)}"); return
    args = message.text.split(maxsplit=1)
    reason = args[1] if len(args) > 1 else "Нарушение"
    try: bot.ban_chat_member(cid, u.id); bans_data.setdefault(u.id, {})[cid] = True; save_all_data(); bot.reply_to(message, f"🚫 {u.first_name} забанен!\n{reason}")
    except: bot.reply_to(message, "❌")

@bot.message_handler(commands=['kick'])
def kick_cmd(message):
    if not has_rank(message.chat.id, message.from_user.id, 1): return
    if not message.reply_to_message: bot.reply_to(message, "❌ Ответь!"); return
    u, cid = message.reply_to_message.from_user, message.chat.id
    if get_rank(cid, u.id) >= get_rank(cid, message.from_user.id): bot.reply_to(message, f"❌ {random.choice(DENY_PHRASES)}"); return
    try: bot.ban_chat_member(cid, u.id); bot.unban_chat_member(cid, u.id); bot.reply_to(message, f"👢 {u.first_name} кикнут!")
    except: bot.reply_to(message, "❌")

@bot.message_handler(commands=['unban'])
def unban_cmd(message):
    if not has_rank(message.chat.id, message.from_user.id, 3): return
    args = message.text.split()
    if len(args) < 2: bot.reply_to(message, "❌ /unban [ID]"); return
    try:
        uid = int(args[1]); bot.unban_chat_member(message.chat.id, uid)
        if uid in bans_data: bans_data[uid].pop(message.chat.id, None)
        save_all_data(); bot.reply_to(message, f"✅ {uid} разбанен!")
    except: bot.reply_to(message, "❌")

# ===== НАСТРОЙКИ ЧАТА =====
@bot.message_handler(commands=['setrules'])
def setrules_cmd(message):
    if not is_owner_or_creator(message.chat.id, message.from_user.id): return
    args = message.text.split(maxsplit=1)
    if len(args) < 2: bot.reply_to(message, "❌ /setrules [текст]"); return
    get_chat_data(message.chat.id)['rules'] = args[1]; save_all_data()
    bot.reply_to(message, "✅")

@bot.message_handler(commands=['setwelcome'])
def setwelcome_cmd(message):
    if not is_owner_or_creator(message.chat.id, message.from_user.id): return
    args = message.text.split(maxsplit=1)
    if len(args) < 2: bot.reply_to(message, "❌ /setwelcome [текст]"); return
    get_chat_data(message.chat.id)['welcome'] = args[1]; save_all_data()
    bot.reply_to(message, "✅")

@bot.message_handler(commands=['welcome_on'])
def welcome_on(message):
    if not is_owner_or_creator(message.chat.id, message.from_user.id): return
    get_chat_data(message.chat.id)['welcome_enabled'] = True; save_all_data()
    bot.reply_to(message, "✅ Вкл!")

@bot.message_handler(commands=['welcome_off'])
def welcome_off(message):
    if not is_owner_or_creator(message.chat.id, message.from_user.id): return
    get_chat_data(message.chat.id)['welcome_enabled'] = False; save_all_data()
    bot.reply_to(message, "✅ Выкл!")

# ===== КАПЧА =====
@bot.message_handler(commands=['captcha'])
def captcha_cmd(message):
    if not has_rank(message.chat.id, message.from_user.id, 2): return
    cid = message.chat.id
    pending = captcha_data.get(cid, [])
    if not pending: bot.reply_to(message, "✅ Нет."); return
    text = "🔐 **Ожидают:**\n\n"
    for uid in pending: text += f"• {get_user_name(uid, cid)} (`{uid}`)\n"
    bot.reply_to(message, text + "\nИм нужно /start в ЛС.", parse_mode="Markdown")

# ===== ПРИВЕТСТВИЕ =====
@bot.message_handler(content_types=['new_chat_members'])
def welcome_new(message):
    cid, cd = message.chat.id, get_chat_data(message.chat.id)
    for nm in message.new_chat_members:
        if nm.is_bot: continue
        try: bot.restrict_chat_member(cid, nm.id, can_send_messages=False, can_send_photos=False, can_send_videos=False, can_send_voices=False, can_send_audios=False, can_send_documents=False, can_send_stickers=False, can_send_animations=False, can_send_games=False, can_send_polls=False)
        except: pass
        captcha_data.setdefault(cid, []).append(nm.id)
        try: bot.send_message(nm.id, "👋 Добро пожаловать!\nНапиши /start для доступа.")
        except: pass
        if cd.get('welcome_enabled', True): bot.send_message(cid, cd['welcome'].replace('{name}', nm.first_name))

# ===== АНТИСПАМ =====
@bot.message_handler(func=lambda m: True)
def auto_mod(message):
    uid, cid = message.from_user.id, message.chat.id
    if message.chat.type == 'private': return
    count_message(message)
    if uid in mutes_data and cid in mutes_data.get(uid, {}) and datetime.now() < mutes_data[uid][cid]:
        try: bot.delete_message(cid, message.message_id)
        except: pass
        return
    message_history.setdefault(uid, []).append({"text": message.text, "time": datetime.now()})
    if len(message_history[uid]) > 10: message_history[uid] = message_history[uid][-10:]
    recent = [m for m in message_history[uid] if (datetime.now() - m['time']).seconds < 5]
    if len(recent) >= 5:
        try:
            bot.delete_message(cid, message.message_id)
            if has_rank(cid, bot.get_me().id, 1): bot.restrict_chat_member(cid, uid, until_date=datetime.now() + timedelta(minutes=1))
        except: pass

# ===== ГЛОБАЛЬНЫЕ =====
@bot.message_handler(commands=['gban'])
def gban_cmd(message):
    if message.from_user.id != OWNER_ID: return
    if not message.reply_to_message: bot.reply_to(message, "❌ Ответь!"); return
    bot.reply_to(message, f"🌍 {message.reply_to_message.from_user.first_name} глобально забанен!")

@bot.message_handler(commands=['broadcast'])
def broadcast_cmd(message):
    if message.from_user.id != OWNER_ID: return
    args = message.text.split(maxsplit=1)
    if len(args) < 2: bot.reply_to(message, "❌ /broadcast [текст]"); return
    sent = 0
    for cid in list(chats_data.keys()):
        try: bot.send_message(cid, f"📢 {args[1]}"); sent += 1
        except: pass
    bot.reply_to(message, f"✅ {sent} чатов")

@bot.message_handler(commands=['uptime'])
def uptime_cmd(message):
    delta = datetime.now() - start_time
    bot.reply_to(message, f"⏱ {delta.days}д {delta.seconds//3600}ч {(delta.seconds%3600)//60}м", parse_mode="Markdown")

# ===== АВТО-ОТЧЁТ =====
def auto_daily_report():
    while True:
        now = datetime.now()
        target = now.replace(hour=23, minute=55, second=0, microsecond=0)
        if now > target: target += timedelta(days=1)
        time.sleep((target - now).total_seconds())
        today = datetime.now().strftime("%Y-%m-%d")
        for cid in list(chats_data.keys()):
            stats = daily_stats.get(cid, {}).get(today, {})
            if stats and stats["messages"] > 10:
                text = f"📰 **Итоги дня** ({today})\n💬 {stats['messages']} | 👥 {len(stats['users'])}\n🏆 "
                for i, (uid, _) in enumerate(sorted(stats["users"].items(), key=lambda x: x[1], reverse=True)[:5], 1):
                    text += f"{i}. {get_user_name(uid, cid)} "
                try: bot.send_message(cid, text, parse_mode="Markdown")
                except: pass

# ===== ЗАПУСК =====
print("🧱 Wall запущен!")
load_all_data()
threading.Thread(target=auto_daily_report, daemon=True).start()
threading.Thread(target=auto_save, daemon=True).start()
bot.infinity_polling()