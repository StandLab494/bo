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
marriages = {}
rep_data = {}
start_time = datetime.now()

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
        "owner_settings": owner_settings,
        "marriages": marriages,
        "rep_data": rep_data
    }
    
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def temp_data_serializable():
    result = {}
    for uid, data in temp_data.items():
        result[str(uid)] = {}
        for key, value in data.items():
            if "until" in value and value["until"]:
                result[str(uid)][key] = {"level": value["level"], "until": value["until"].isoformat()}
            else:
                result[str(uid)][key] = value
    return result

def load_all_data():
    global staff_data, warns_data, mutes_data, bans_data, chats_data, daily_stats, user_profiles, vip_data, economy, temp_data, clans_data, captcha_data, owner_settings, marriages, rep_data
    
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
        marriages = data.get("marriages", {})
        marriages = {int(k): v for k, v in marriages.items()}
        rep_data = data.get("rep_data", {})
        rep_data = {int(k): v for k, v in rep_data.items()}
        
        temp_data = {}
        for uid, items in data.get("temp_data", {}).items():
            temp_data[int(uid)] = {}
            for key, value in items.items():
                if "until" in value and value["until"]:
                    temp_data[int(uid)][key] = {"level": value["level"], "until": datetime.fromisoformat(value["until"])}
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

# ===== START =====
@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    
    for cid, users in list(captcha_data.items()):
        if user_id in users:
            try:
                bot.restrict_chat_member(cid, user_id,
                    can_send_messages=True, can_send_photos=True, can_send_videos=True,
                    can_send_voices=True, can_send_audios=True, can_send_documents=True,
                    can_send_stickers=True, can_send_animations=True, can_send_games=True,
                    can_send_polls=True)
                captcha_data[cid].remove(user_id)
                if not captcha_data[cid]:
                    del captcha_data[cid]
                bot.send_message(user_id, "✅ Капча пройдена! Можешь общаться в чате.")
                save_all_data()
            except:
                pass
    
    get_balance(user_id)
    save_all_data()
    
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
👤 **Для всех:** /id, /info, /report, /rules, /staff, /translate, /anonym, /nick, /bio, /profile, /top, /meme, /balance, /work, /daily, /pay, /casino, /clan, /lyrics, /song, /youtube, /botlink
🛡️ **Модерация:** Ранг 1: /mute, /mutetime, /warn, /kick. Ранг 2: + /bantime, /pin, /unpin. Ранг 3: + /ban, /unban. Ранг 4: + /raising, /downgrade, /gg
💬 **RP:** /hug, /kiss, /slap, /pat, /kill, /revive, /hugme, /cry, /laugh, /dance, /poke, /tickle, /highfive, /wink, /blush, /facepalm, /shrug, /angry, /bored, /confused, /hungry, /sleep, /wakeup, /yawn, /think
💍 **Соц:** /marry, /divorce, /couple, /rep, /toprep
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
            callback_data=f"buyvip_{level}"))
    bal = get_balance(message.from_user.id)["balance"]
    bot.send_message(message.chat.id,
        f"💎 **Покупка VIP**\n\nТвой баланс: {bal:,} 🧱\n\nВыбери уровень:",
        parse_mode="Markdown", reply_markup=markup)

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
    partner_id = marriages.get(message.from_user.id)
    partner_text = get_user_name(partner_id) if partner_id else "Нет"
    rep = rep_data.get(message.from_user.id, {}).get("count", 0)
    text = f"""👤 **Профиль**
Имя: {profile['nick'] or message.from_user.first_name}
ID: `{message.from_user.id}`
💰 Баланс: {bal['balance']:,} 🧱
💎 VIP: {vip_text}
🏰 Клан: {clan if clan else 'Нет'}
💍 Пара: {partner_text}
⭐ Репутация: {rep}
📝 Статус: {profile['bio'] or 'Не установлен'}"""
    bot.reply_to(message, text, parse_mode="Markdown")

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

# ===== ОБЩИЙ ОБРАБОТЧИК ЛС =====
@bot.message_handler(func=lambda m: m.chat.type == 'private')
def private_handler(message):
    get_balance(message.from_user.id)
    save_all_data()
    if message.text and not message.text.startswith('/'):
        bot.reply_to(message,
            "👋 Привет! Используй кнопки ниже или напиши /help",
            reply_markup=get_private_keyboard())

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
        bot.reply_to(message, "❌ /pay [ID] [сумма]"); return
    try:
        target = int(args[1]); amount = int(args[2])
    except:
        bot.reply_to(message, "❌ Неверные данные!"); return
    if amount <= 0:
        bot.reply_to(message, "❌ Сумма > 0!"); return
    if not spend_bricks(message.from_user.id, amount):
        bot.reply_to(message, "❌ Недостаточно!"); return
    add_bricks(target, amount)
    save_all_data()
    bot.reply_to(message, f"✅ {amount} 🧱 → {target}")

# ===== ПРОФИЛЬ =====
@bot.message_handler(commands=['profile'])
def profile_cmd(message):
    u = message.reply_to_message.from_user if message.reply_to_message else message.from_user
    uid, cid = u.id, message.chat.id
    profile, vip, clan, rank = get_profile(uid), get_vip(uid), get_user_clan(uid), get_rank(cid, uid)
    total_msgs = sum(data.get("users", {}).get(uid, 0) for chat_id, days in daily_stats.items() for day, data in days.items())
    reg_date = "Неизвестно"
    if str(uid) in economy:
        eco = economy[str(uid)]
        dates = [d for d in [eco.get("last_work", ""), eco.get("last_daily", "")] if d]
        if dates: reg_date = sorted(dates)[0][:10]
    vip_text = f"{VIP_LEVELS[vip['level']]['color']} {VIP_LEVELS[vip['level']]['name']}" if vip['level'] > 0 else "Нет"
    rn = {0:"Участник", 1:"Модератор", 2:"Мл. владелец", 3:"Пом. владельца", 4:"Владелец"}
    partner_id = marriages.get(uid)
    partner_text = get_user_name(partner_id) if partner_id else "Нет"
    rep = rep_data.get(uid, {}).get("count", 0)
    text = f"""📇 **Профиль**
━━━━━━━━━━━━━━━━
👤 Имя: {profile['nick'] or u.first_name}
🆔 ID: `{uid}`
💎 VIP: {vip_text}
🏰 Клан: {clan or 'Нет'}
💍 Пара: {partner_text}
⭐ Репутация: {rep}
🎖 Ранг: {rn[rank]}
📅 В боте с: {reg_date}
💬 Сообщений: {total_msgs}
━━━━━━━━━━━━━━━━"""
    bot.reply_to(message, text, parse_mode="Markdown")

@bot.message_handler(commands=['nick'])
def nick_cmd(message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2: bot.reply_to(message, "❌ /nick [имя]"); return
    get_profile(message.from_user.id)['nick'] = args[1]; save_all_data()
    bot.reply_to(message, f"✅ Ник: {args[1]}")

@bot.message_handler(commands=['bio'])
def bio_cmd(message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2: bot.reply_to(message, "❌ /bio [статус]"); return
    get_profile(message.from_user.id)['bio'] = args[1]; save_all_data()
    bot.reply_to(message, f"✅ Статус: {args[1]}")

# ===== БРАКИ =====
@bot.message_handler(commands=['marry'])
def marry_cmd(message):
    if not message.reply_to_message:
        bot.reply_to(message, "❌ Ответь на сообщение того, с кем хочешь вступить в брак!")
        return
    user_id = message.from_user.id
    partner = message.reply_to_message.from_user
    if partner.id == user_id:
        bot.reply_to(message, "❌ Нельзя жениться на себе!"); return
    if user_id in marriages:
        bot.reply_to(message, "❌ Ты уже в браке! /divorce"); return
    if partner.id in marriages:
        bot.reply_to(message, f"❌ {partner.first_name} уже в браке!"); return
    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(
        telebot.types.InlineKeyboardButton("💍 Да!", callback_data=f"marry_yes_{user_id}"),
        telebot.types.InlineKeyboardButton("❌ Нет", callback_data=f"marry_no_{user_id}"))
    bot.send_message(message.chat.id, f"💍 {partner.first_name}, {message.from_user.first_name} предлагает тебе вступить в брак!", reply_markup=markup)

@bot.callback_query_handler(func=lambda c: c.data.startswith("marry_"))
def marry_callback(call):
    parts = call.data.split("_")
    action = parts[1]
    proposer_id = int(parts[2])
    partner_id = call.from_user.id
    if action == "yes":
        if partner_id in marriages or proposer_id in marriages:
            bot.answer_callback_query(call.id, "❌ Кто-то уже в браке!"); return
        marriages[proposer_id] = partner_id
        marriages[partner_id] = proposer_id
        save_all_data()
        bot.edit_message_text(f"💒 **Поздравляем!** {get_user_name(proposer_id, call.message.chat.id)} и {get_user_name(partner_id, call.message.chat.id)} теперь в браке!", call.message.chat.id, call.message.message_id, parse_mode="Markdown")
    else:
        bot.edit_message_text("💔 Предложение отклонено.", call.message.chat.id, call.message.message_id)
    bot.answer_callback_query(call.id)

@bot.message_handler(commands=['divorce'])
def divorce_cmd(message):
    user_id = message.from_user.id
    if user_id not in marriages:
        bot.reply_to(message, "❌ Ты не в браке!"); return
    partner_id = marriages[user_id]
    partner_name = get_user_name(partner_id, message.chat.id)
    del marriages[user_id]
    del marriages[partner_id]
    save_all_data()
    bot.send_message(message.chat.id, f"💔 **Развод!** {message.from_user.first_name} и {partner_name} больше не вместе.", parse_mode="Markdown")

@bot.message_handler(commands=['couple'])
def couple_cmd(message):
    uid = message.reply_to_message.from_user.id if message.reply_to_message else message.from_user.id
    if uid not in marriages:
        bot.reply_to(message, "💔 Не в браке."); return
    partner_id = marriages[uid]
    bot.reply_to(message, f"💍 **Пара:** {get_user_name(uid, message.chat.id)} 💕 {get_user_name(partner_id, message.chat.id)}", parse_mode="Markdown")

# ===== РЕПУТАЦИЯ =====
@bot.message_handler(commands=['rep'])
def rep_cmd(message):
    if not message.reply_to_message:
        bot.reply_to(message, "❌ Ответь на сообщение!"); return
    user_id = message.from_user.id
    target = message.reply_to_message.from_user
    if target.id == user_id:
        bot.reply_to(message, "❌ Нельзя себе!"); return
    if user_id not in rep_data:
        rep_data[user_id] = {"last_rep": None}
    last_rep = rep_data[user_id].get("last_rep")
    if last_rep:
        last_time = datetime.fromisoformat(last_rep)
        if datetime.now() - last_time < timedelta(hours=12):
            remaining = timedelta(hours=12) - (datetime.now() - last_time)
            bot.reply_to(message, f"⏳ Жди {remaining.seconds//3600}ч {(remaining.seconds%3600)//60}м"); return
    if target.id not in rep_data:
        rep_data[target.id] = {"count": 0}
    rep_data[target.id]["count"] = rep_data[target.id].get("count", 0) + 1
    rep_data[user_id]["last_rep"] = datetime.now().isoformat()
    save_all_data()
    bot.reply_to(message, f"⭐ {message.from_user.first_name} повысил репутацию {target.first_name}!\nРепутация: {rep_data[target.id]['count']}")

@bot.message_handler(commands=['toprep'])
def toprep_cmd(message):
    if not rep_data:
        bot.reply_to(message, "📭 Нет данных."); return
    ranked = [(uid, data.get("count", 0)) for uid, data in rep_data.items() if data.get("count", 0) > 0]
    ranked.sort(key=lambda x: x[1], reverse=True)
    if not ranked:
        bot.reply_to(message, "📭 Нет данных."); return
    text = "🏆 **Топ-10 по репутации:**\n\n" + "\n".join(f"{i}. {get_user_name(uid, message.chat.id)} — {count} ⭐" for i, (uid, count) in enumerate(ranked[:10], 1))
    bot.reply_to(message, text, parse_mode="Markdown")

# ===== КЛАНЫ =====
@bot.message_handler(commands=['clan'])
def clan_cmd(message):
    args = message.text.split(maxsplit=2)
    if len(args) < 2:
        bot.reply_to(message, "🏰 /clan create [имя] (2000🧱) | join | leave | info | members | kick | promote | disband | bank | donate | list | top", parse_mode="Markdown"); return
    a, uid = args[1].lower(), message.from_user.id
    try:
        if a == "create":
            if len(args) < 3: bot.reply_to(message, "❌ /clan create [имя]"); return
            n = args[2][:30]
            if n in clans_data: bot.reply_to(message, "❌ Есть!"); return
            if get_user_clan(uid): bot.reply_to(message, "❌ Уже в клане!"); return
            if not spend_bricks(uid, 2000): bot.reply_to(message, "❌ 2000🧱!"); return
            clans_data[n] = {"owner": uid, "members": [uid], "bank": 0, "created": datetime.now().isoformat()}
            save_all_data(); bot.reply_to(message, f"🏰 **{n}** создан!", parse_mode="Markdown")
        elif a == "join":
            if len(args) < 3: bot.reply_to(message, "❌ /clan join [имя]"); return
            n = args[2]
            if n not in clans_data: bot.reply_to(message, "❌ Нет!"); return
            if get_user_clan(uid): bot.reply_to(message, "❌ Уже в клане!"); return
            clans_data[n]["members"].append(uid); save_all_data(); bot.reply_to(message, f"✅ Вступил в **{n}**!")
        elif a == "leave":
            c = get_user_clan(uid)
            if not c: bot.reply_to(message, "❌ Не в клане!"); return
            if clans_data[c]["owner"] == uid: bot.reply_to(message, "❌ Глава! /clan disband"); return
            clans_data[c]["members"].remove(uid); save_all_data(); bot.reply_to(message, f"🚪 Покинул **{c}**.")
        elif a == "info":
            c = get_user_clan(uid)
            if not c: bot.reply_to(message, "❌ Не в клане!"); return
            d = clans_data[c]
            bot.reply_to(message, f"🏰 **{c}**\n👑 {get_user_name(d['owner'])}\n👥 {len(d['members'])}\n💰 {d['bank']:,}🧱\n📅 {d['created'][:10]}", parse_mode="Markdown")
        elif a == "members":
            c = get_user_clan(uid)
            if not c: bot.reply_to(message, "❌ Не в клане!"); return
            text = f"👥 **{c}:**\n\n" + "\n".join(f"• {get_user_name(m)}{' 👑' if m == clans_data[c]['owner'] else ''}" for m in clans_data[c]["members"])
            bot.reply_to(message, text, parse_mode="Markdown")
        elif a == "kick":
            if len(args) < 3: bot.reply_to(message, "❌ /clan kick [ID]"); return
            c = get_user_clan(uid)
            if not c or clans_data[c]["owner"] != uid: bot.reply_to(message, "❌ Только глава!"); return
            t = int(args[2])
            if t not in clans_data[c]["members"]: bot.reply_to(message, "❌ Не в клане!"); return
            clans_data[c]["members"].remove(t); save_all_data(); bot.reply_to(message, f"👢 {get_user_name(t)} исключён!")
        elif a == "promote":
            if len(args) < 3: bot.reply_to(message, "❌ /clan promote [ID]"); return
            c = get_user_clan(uid)
            if not c or clans_data[c]["owner"] != uid: bot.reply_to(message, "❌ Только глава!"); return
            t = int(args[2])
            if t not in clans_data[c]["members"]: bot.reply_to(message, "❌ Не в клане!"); return
            clans_data[c]["owner"] = t; save_all_data(); bot.reply_to(message, f"👑 {get_user_name(t)} — глава!")
        elif a == "disband":
            c = get_user_clan(uid)
            if not c or clans_data[c]["owner"] != uid: bot.reply_to(message, "❌ Только глава!"); return
            del clans_data[c]; save_all_data(); bot.reply_to(message, f"💀 **{c}** распущен.")
        elif a == "bank":
            c = get_user_clan(uid)
            if not c: bot.reply_to(message, "❌ Не в клане!"); return
            bot.reply_to(message, f"💰 {clans_data[c]['bank']:,}🧱")
        elif a == "donate":
            if len(args) < 3: bot.reply_to(message, "❌ /clan donate [сумма]"); return
            c = get_user_clan(uid)
            if not c: bot.reply_to(message, "❌ Не в клане!"); return
            amt = int(args[2])
            if amt <= 0 or not spend_bricks(uid, amt): bot.reply_to(message, "❌ Недостаточно!"); return
            clans_data[c]["bank"] += amt; save_all_data(); bot.reply_to(message, f"✅ {amt:,}🧱 в казну!")
        elif a == "list":
            if not clans_data: bot.reply_to(message, "📭 Нет кланов."); return
            text = "🏰 **Кланы:**\n\n" + "\n".join(f"• **{n}** — {len(d['members'])} чел. | 💰{d['bank']:,}" for n, d in sorted(clans_data.items(), key=lambda x: len(x[1]["members"]), reverse=True))
            bot.reply_to(message, text, parse_mode="Markdown")
        elif a == "top":
            if not clans_data: bot.reply_to(message, "📭 Нет кланов."); return
            text = "🏆 **Топ:**\n\n" + "\n".join(f"{i}. **{n}** — {d['bank']:,}🧱" for i, (n, d) in enumerate(sorted(clans_data.items(), key=lambda x: x[1]["bank"], reverse=True)[:10], 1))
            bot.reply_to(message, text, parse_mode="Markdown")
    except Exception as e:
        bot.reply_to(message, f"❌ Ошибка! {e}")

# ===== МУЗЫКА =====
@bot.message_handler(commands=['lyrics'])
def lyrics_cmd(message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2: bot.reply_to(message, "❌ /lyrics [песня]"); return
    try:
        r = requests.get(f"https://api.lyrics.ovh/v1/{args[1]}").json()
        if "lyrics" in r: bot.reply_to(message, f"🎵 **{args[1]}**\n\n{r['lyrics'][:4000]}", parse_mode="Markdown")
        else: bot.reply_to(message, "❌ Не найдено!")
    except: bot.reply_to(message, "❌ Ошибка!")

@bot.message_handler(commands=['song'])
def song_cmd(message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2: bot.reply_to(message, "❌ /song [название]"); return
    try:
        r = requests.get(f"http://ws.audioscrobbler.com/2.0/?method=track.search&track={args[1]}&api_key=1d3e5c5e5c5e5c5e5c5e5c5e5c5e5c5e&format=json").json()
        tracks = r.get("results", {}).get("trackmatches", {}).get("track", [])
        if tracks: bot.reply_to(message, f"🎵 **{tracks[0]['name']}**\n👤 {tracks[0]['artist']}\n🔗 [Last.fm]({tracks[0]['url']})", parse_mode="Markdown")
        else: bot.reply_to(message, "❌ Не найдено!")
    except: bot.reply_to(message, "❌ Ошибка!")

@bot.message_handler(commands=['youtube'])
def youtube_cmd(message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2: bot.reply_to(message, "❌ /youtube [запрос]"); return
    bot.reply_to(message, f"🔍 [YouTube: {args[1]}](https://www.youtube.com/results?search_query={args[1].replace(' ', '+')})", parse_mode="Markdown", disable_web_page_preview=False)

# ===== ВЫДАЧА (ВЛАДЕЛЕЦ) =====
@bot.message_handler(commands=['gift'])
def gift_cmd(message):
    if message.from_user.id != OWNER_ID: return
    args = message.text.split()
    if len(args) < 3: bot.reply_to(message, "❌ /gift [ID] [vip/bricks/rank/unwarn/reset] [кол-во]"); return
    try: tid, act = int(args[1]), args[2].lower()
    except: bot.reply_to(message, "❌ ID!"); return
    
    if act == "vip":
        lvl = int(args[3])
        if lvl < 1 or lvl > 3: bot.reply_to(message, "❌ 1-3!"); return
        ts = args[4] if len(args) > 4 else "perm"
        until = None
        if ts != "perm":
            m = re.match(r'(\d+)(h|d)', ts)
            if m: until = datetime.now() + timedelta(hours=int(m.group(1))) if m.group(2)=='h' else datetime.now() + timedelta(days=int(m.group(1)))
            else: bot.reply_to(message, "❌ 1h/1d/7d"); return
        vip_data[str(tid)] = {"level": lvl, "color": "purple"}
        if until: temp_data.setdefault(str(tid), {})["vip"] = {"level": lvl, "until": until}
        save_all_data(); bot.reply_to(message, f"✅ {VIP_LEVELS[lvl]['name']} → {tid}")
    elif act == "bricks":
        add_bricks(tid, int(args[3])); save_all_data(); bot.reply_to(message, f"✅ {int(args[3]):,}🧱 → {tid}")
    elif act == "rank":
        rl = int(args[3]); ts = args[4] if len(args) > 4 else "perm"
        until = None
        if ts != "perm":
            m = re.match(r'(\d+)(h|d)', ts)
            if m: until = datetime.now() + timedelta(hours=int(m.group(1))) if m.group(2)=='h' else datetime.now() + timedelta(days=int(m.group(1)))
        for cid in chats_data: set_rank(int(cid), tid, rl)
        if until: temp_data.setdefault(str(tid), {})["rank"] = {"level": rl, "until": until}
        save_all_data(); bot.reply_to(message, f"✅ Ранг {rl} → {tid}")
    elif act == "unwarn":
        if str(tid) in warns_data: warns_data[str(tid)] = {}; save_all_data(); bot.reply_to(message, f"✅ Варны сняты!")
        else: bot.reply_to(message, "❌ Нет варнов!")
    elif act == "reset":
        for d in [economy, vip_data, warns_data, mutes_data, bans_data, user_profiles, temp_data]: d.pop(str(tid), None)
        for cid in staff_data: staff_data[cid].pop(tid, None)
        save_all_data(); bot.reply_to(message, f"💀 {tid} сброшен!")

# ===== ПАНЕЛЬ ВЛАДЕЛЬЦА =====
@bot.message_handler(commands=['owner'])
def owner_panel(message):
    if message.from_user.id != OWNER_ID: return
    bot.reply_to(message, f"""👑 **Панель**
/setboss [HP] | /killboss
/setcasinoodds [0.1-0.9] (сейчас: {owner_settings['casino_odds']})
/setstealchance [0.1-0.9] (сейчас: {owner_settings['steal_chance']})
/setworkmin [N] ({owner_settings['work_min']}) | /setworkmax [N] ({owner_settings['work_max']})
/setdailybonusmin [N] ({owner_settings['daily_bonus_min']}) | /setdailybonusmax [N] ({owner_settings['daily_bonus_max']})
/gift | /msg | /dmall | /broadcast | /gban""", parse_mode="Markdown")

@bot.message_handler(commands=['setboss','killboss','setcasinoodds','setstealchance','setworkmin','setworkmax','setdailybonusmin','setdailybonusmax'])
def owner_settings_cmd(message):
    if message.from_user.id != OWNER_ID: return
    cmd = message.text.split()[0][1:]
    try:
        if cmd == "setboss":
            cid = message.chat.id; hp = int(message.text.split()[1])
            boss_data[cid] = {"hp": hp, "max_hp": hp, "players": [OWNER_ID], "active": True, "started": True, "damage_dealt": {}}
            bot.reply_to(message, f"🐉 HP: {hp}")
        elif cmd == "killboss":
            cid = message.chat.id
            if cid in boss_data: del boss_data[cid]; bot.reply_to(message, "💀")
            else: bot.reply_to(message, "❌ Нет босса!")
        else:
            key_map = {"setcasinoodds": "casino_odds", "setstealchance": "steal_chance", "setworkmin": "work_min", "setworkmax": "work_max", "setdailybonusmin": "daily_bonus_min", "setdailybonusmax": "daily_bonus_max"}
            val = float(message.text.split()[1]) if "odds" in cmd or "chance" in cmd else int(message.text.split()[1])
            owner_settings[key_map[cmd]] = val; save_all_data()
            bot.reply_to(message, f"✅ {key_map[cmd]} = {val}")
    except: bot.reply_to(message, "❌ Ошибка!")

# ===== КАЗИНО / КРАЖА / БОСС =====
@bot.message_handler(commands=['casino'])
def casino_cmd(message):
    args = message.text.split()
    if len(args) < 2: bot.reply_to(message, "❌ /casino [ставка]"); return
    bet = int(args[1])
    if bet < 10: bot.reply_to(message, "❌ Мин. 10🧱!"); return
    uid = message.from_user.id
    if not spend_bricks(uid, bet): bot.reply_to(message, "❌ Недостаточно!"); return
    if random.random() < owner_settings["casino_odds"]:
        win = bet * 2; add_bricks(uid, win); save_all_data()
        bot.reply_to(message, f"🎰 +{win}🧱 | Баланс: {get_balance(uid)['balance']:,}")
    else:
        save_all_data(); bot.reply_to(message, f"🎰 -{bet}🧱 | Баланс: {get_balance(uid)['balance']:,}")

@bot.message_handler(commands=['steal'])
def steal_cmd(message):
    if get_vip(message.from_user.id)["level"] < 2: bot.reply_to(message, "❌ VIP+!"); return
    uid = message.from_user.id
    last = steal_times.get(uid)
    if last and datetime.now() - last < timedelta(minutes=10):
        r = timedelta(minutes=10) - (datetime.now() - last); bot.reply_to(message, f"⏳ {r.seconds//60}м {r.seconds%60}с"); return
    if not message.reply_to_message: bot.reply_to(message, "❌ Ответь!"); return
    v = message.reply_to_message.from_user
    if v.id == uid: bot.reply_to(message, "❌ Нельзя себе!"); return
    vb = get_balance(v.id)
    if vb["balance"] < 10: bot.reply_to(message, "❌ <10🧱!"); return
    amt = random.randint(10, min(100, vb["balance"]))
    if random.random() < owner_settings["steal_chance"]:
        vb["balance"] -= amt; add_bricks(uid, amt); steal_times[uid] = datetime.now(); save_all_data()
        bot.reply_to(message, f"🦹 +{amt}🧱 | Баланс: {get_balance(uid)['balance']:,}")
    else:
        pen = random.randint(5, 20)
        if get_balance(uid)["balance"] >= pen:
            spend_bricks(uid, pen); add_bricks(v.id, pen); steal_times[uid] = datetime.now(); save_all_data()
            bot.reply_to(message, f"🚨 Штраф {pen}🧱 → {v.first_name}")
        else: bot.reply_to(message, "🚨 Провал! Нет денег на штраф.")

@bot.message_handler(commands=['boss'])
def boss_cmd(message):
    if get_vip(message.from_user.id)["level"] < 3: bot.reply_to(message, "❌ LEGEND+!"); return
    cid, uid = message.chat.id, message.from_user.id
    if cid in boss_data and boss_data[cid].get("active"): bot.reply_to(message, "⚔️ Уже есть! /joinboss"); return
    hp = random.choice([2500, 3000])
    boss_data[cid] = {"hp": hp, "max_hp": hp, "players": [uid], "active": True, "started": False, "damage_dealt": {}}
    mk = telebot.types.InlineKeyboardMarkup()
    mk.add(telebot.types.InlineKeyboardButton("⚔️ Присоединиться!", callback_data="joinboss"))
    mk.add(telebot.types.InlineKeyboardButton("👊 Атаковать!", callback_data="attackboss"))
    bot.send_message(cid, f"🐉 **БОСС!**\n❤️ {hp}/{hp}\n👥 1/4", parse_mode="Markdown", reply_markup=mk)

@bot.callback_query_handler(func=lambda c: c.data == "joinboss")
def join_boss(call):
    cid, uid = call.message.chat.id, call.from_user.id
    if cid not in boss_data or not boss_data[cid].get("active"): bot.answer_callback_query(call.id, "❌"); return
    b = boss_data[cid]
    if uid in b["players"]: bot.answer_callback_query(call.id, "❌ Уже в битве!"); return
    if b["started"]: bot.answer_callback_query(call.id, "❌ Началась!"); return
    b["players"].append(uid)
    mk = telebot.types.InlineKeyboardMarkup()
    if len(b["players"]) >= 4:
        b["started"] = True; mk.add(telebot.types.InlineKeyboardButton("👊 Атаковать!", callback_data="attackboss"))
        bot.edit_message_text(f"🐉 **БОСС!**\n❤️ {b['hp']}/{b['max_hp']}\n👥 {', '.join(get_user_name(p,cid) for p in b['players'])}\nАтакуйте!", parse_mode="Markdown", chat_id=cid, message_id=call.message.message_id, reply_markup=mk)
        bot.answer_callback_query(call.id, "⚔️ Началась!")
    else:
        mk.add(telebot.types.InlineKeyboardButton("⚔️ Присоединиться!", callback_data="joinboss"))
        mk.add(telebot.types.InlineKeyboardButton("👊 Атаковать!", callback_data="attackboss"))
        bot.edit_message_text(f"🐉 **БОСС!**\n❤️ {b['hp']}/{b['max_hp']}\n👥 {len(b['players'])}/4\nНужно ещё {4-len(b['players'])}", parse_mode="Markdown", chat_id=cid, message_id=call.message.message_id, reply_markup=mk)
        bot.answer_callback_query(call.id, f"✅ {len(b['players'])}/4")

@bot.callback_query_handler(func=lambda c: c.data == "attackboss")
def attack_boss(call):
    cid, uid = call.message.chat.id, call.from_user.id
    if cid not in boss_data or not boss_data[cid].get("active") or uid not in boss_data[cid].get("players", []): bot.answer_callback_query(call.id, "❌"); return
    b = boss_data[cid]
    if not b["started"]: bot.answer_callback_query(call.id, "⏳ Ждём!"); return
    dmg = random.randint(50, 200); b["hp"] -= dmg
    b["damage_dealt"][uid] = b["damage_dealt"].get(uid, 0) + dmg
    if b["hp"] <= 0:
        b["hp"] = 0; b["active"] = False
        reward = random.randint(100, 500) // len(b["players"])
        for p in b["players"]: add_bricks(p, reward)
        top = sorted(b["damage_dealt"].items(), key=lambda x: x[1], reverse=True)
        text = f"🎉 **ПОБЕДА!**\n💰 {reward}🧱\n🏆 MVP: {get_user_name(top[0][0], cid)}\n📊 Урон:\n" + "\n".join(f"• {get_user_name(p,cid)}: {d}" for p,d in top)
        del boss_data[cid]; save_all_data()
        bot.edit_message_text(text, parse_mode="Markdown", chat_id=cid, message_id=call.message.message_id)
        bot.answer_callback_query(call.id, f"💥 +{dmg}!")
    else:
        mk = telebot.types.InlineKeyboardMarkup(); mk.add(telebot.types.InlineKeyboardButton("👊 Атаковать!", callback_data="attackboss"))
        bot.edit_message_text(f"🐉 **БОСС!**\n❤️ {b['hp']}/{b['max_hp']}\n👥 {', '.join(get_user_name(p,cid) for p in b['players'])}", parse_mode="Markdown", chat_id=cid, message_id=call.message.message_id, reply_markup=mk)
        bot.answer_callback_query(call.id, f"👊 -{dmg} | HP: {b['hp']}")

# ===== VIP-КОМАНДЫ =====
@bot.message_handler(commands=['viphelp'])
def vip_help(message):
    if not is_vip(message.from_user.id): return
    bot.reply_to(message, "💎 VIP: /flex, /vipcolor, /spotlight, /loud, /ghost, /magic, /slow\n🌟 VIP+: + /announce, /rainbow, /reverse, /secret, /countdown, /steal\n💎 LEGEND+: + /say, /echo, /bomb, /weather, /boss")

@bot.message_handler(commands=['flex'])
def flex_cmd(message):
    if not is_vip(message.from_user.id): return
    v = get_vip(message.from_user.id); i = VIP_LEVELS[v["level"]]
    bot.send_message(message.chat.id, f"💎 {i['prefix']} **{message.from_user.first_name}**\n{i['color']} {i['name']}\n💰 {get_balance(message.from_user.id)['balance']:,}🧱", parse_mode="Markdown")

@bot.message_handler(commands=['vipcolor'])
def vipcolor_cmd(message):
    if not is_vip(message.from_user.id): return
    c = message.text.split()[1].lower() if len(message.text.split()) > 1 else ""
    if c not in VIP_COLORS: bot.reply_to(message, f"❌ {', '.join(VIP_COLORS)}"); return
    vip_data[str(message.from_user.id)]["color"] = c; save_all_data(); bot.reply_to(message, f"✅ {c}")

@bot.message_handler(commands=['spotlight','loud','ghost','magic','slow','announce','rainbow','reverse','secret','countdown','say','echo','bomb','weather'])
def vip_commands(message):
    cmd = message.text.split()[0][1:]
    lvl = get_vip(message.from_user.id)["level"]
    if lvl < 1: return
    if cmd in ['announce','rainbow','reverse','secret','countdown'] and lvl < 2: bot.reply_to(message, "❌ VIP+!"); return
    if cmd in ['say','echo','bomb','weather'] and lvl < 3: bot.reply_to(message, "❌ LEGEND+!"); return
    
    args = message.text.split(maxsplit=1)[1] if len(message.text.split()) > 1 else ""
    if cmd == "spotlight" and args: bot.send_message(message.chat.id, f"🔦 **В центре внимания:**\n\n✨ {args} ✨", parse_mode="Markdown")
    elif cmd == "loud" and args: bot.send_message(message.chat.id, f"📢 {args.upper()} 📢")
    elif cmd == "ghost" and args:
        try: bot.delete_message(message.chat.id, message.message_id)
        except: pass
        bot.send_message(message.chat.id, f"👻 **Призрак:** {args}", parse_mode="Markdown")
    elif cmd == "magic" and args:
        emojis = ["✨", "🌟", "💫", "⭐", "🔮", "💎", "🎩", "🪄"]
        result = ' '.join(f"{c} {random.choice(emojis)}" for c in args)
        bot.send_message(message.chat.id, f"🎩 {result}")
    elif cmd == "slow" and args:
        for c in args: bot.send_message(message.chat.id, c); time.sleep(0.3)
    elif cmd == "announce" and args:
        msg = bot.send_message(message.chat.id, f"📢 **ОБЪЯВЛЕНИЕ**\n\n{args}", parse_mode="Markdown")
        try: bot.pin_chat_message(message.chat.id, msg.message_id)
        except: pass
    elif cmd == "rainbow" and args:
        colors = ["🔴", "🟠", "🟡", "🟢", "🔵", "🟣"]
        result = ' '.join(f"{colors[i % 6]} {c}" for i, c in enumerate(args))
        bot.send_message(message.chat.id, result)
    elif cmd == "reverse" and args: bot.send_message(message.chat.id, args[::-1])
    elif cmd == "secret" and args: bot.send_message(message.chat.id, f"🔒 ||{args}||", parse_mode="Markdown")
    elif cmd == "countdown":
        try: secs = min(int(args.split()[0]), 10)
        except: secs = 5
        msg = bot.send_message(message.chat.id, f"⏳ {secs}...")
        for i in range(secs-1, 0, -1): time.sleep(1); bot.edit_message_text(f"⏳ {i}...", message.chat.id, msg.message_id)
        bot.edit_message_text("🚀 ПУСК!", message.chat.id, msg.message_id)
    elif cmd == "say" and args:
        try: bot.delete_message(message.chat.id, message.message_id)
        except: pass
        bot.send_message(message.chat.id, args)
    elif cmd == "echo":
        parts = message.text.split(maxsplit=2)
        if len(parts) >= 3:
            try: count = min(int(parts[1]), 5)
            except: count = 1
            for _ in range(count): bot.send_message(message.chat.id, parts[2]); time.sleep(0.5)
    elif cmd == "bomb":
        secs = int(args.split()[0]) if args and args.split()[0].isdigit() else 5
        secs = min(secs, 10)
        msg = bot.send_message(message.chat.id, f"💣 {secs}...")
        for i in range(secs-1, 0, -1): time.sleep(1); bot.edit_message_text(f"💣 {i}...", message.chat.id, msg.message_id)
        bot.edit_message_text("💥 БУМ! 😄", message.chat.id, msg.message_id)
    elif cmd == "weather":
        weathers = ["☀️ Солнечно", "🌧 Дождь", "⛈ Гроза", "❄️ Снег", "🌪 Ураган", "🌈 Радуга", "🌙 Ночь"]
        bot.send_message(message.chat.id, f"🌤 {random.choice(weathers)}", parse_mode="Markdown")

# ===== СООБЩЕНИЯ В ЛС =====
@bot.message_handler(commands=['msg'])
def msg_cmd(message):
    if message.from_user.id != OWNER_ID: return
    parts = message.text.split(maxsplit=2)
    if len(parts) < 3: bot.reply_to(message, "❌ /msg [ID/юзернейм] [текст]"); return
    target, text = parts[1], parts[2]
    tid = None
    if target.startswith("@"): target = target[1:]
    else:
        try: tid = int(target)
        except: bot.reply_to(message, "❌ Неверно!"); return
    try:
        if tid: bot.send_message(tid, f"📨 **Сообщение администрации:**\n\n{text}", parse_mode="Markdown")
        else: bot.send_message(f"@{target}", f"📨 **Сообщение администрации:**\n\n{text}", parse_mode="Markdown")
        bot.reply_to(message, f"✅ {target}")
    except: bot.reply_to(message, "❌ Не удалось!")

@bot.message_handler(commands=['dmall'])
def dmall_cmd(message):
    if message.from_user.id != OWNER_ID: return
    args = message.text.split(maxsplit=1)
    if len(args) < 2: bot.reply_to(message, "❌ /dmall [текст]"); return
    text = args[1]; sent = 0; failed = 0
    status_msg = bot.reply_to(message, "⏳ Рассылка...")
    for uid in list(economy.keys()):
        try: bot.send_message(int(uid), f"📢 {text}", parse_mode="Markdown"); sent += 1; time.sleep(0.05)
        except: failed += 1
    try: bot.edit_message_text(f"✅ Отправлено: {sent}\n❌ Не удалось: {failed}", message.chat.id, status_msg.message_id)
    except: bot.send_message(message.chat.id, f"✅ {sent} | ❌ {failed}")

@bot.message_handler(commands=['botlink'])
def botlink_cmd(message):
    bot.reply_to(message, "🤖 Напиши @Wall_bot в ЛС и нажми /start чтобы получать уведомления!")

# ===== ОСНОВНЫЕ КОМАНДЫ =====
@bot.message_handler(commands=['help'])
def help_cmd(message):
    bot.reply_to(message, """🧱 **Wall**
👤 /id /info /report /rules /staff /translate /anonym /nick /bio /profile /top /meme /balance /work /daily /pay /casino /clan /lyrics /song /youtube /botlink
🛡️ Р1: /mute /mutetime /warn /kick | Р2: +/bantime /pin /unpin | Р3: +/ban /unban | Р4: +/raising /downgrade /gg
💬 RP: /hug /kiss /slap /pat /kill /revive /hugme /cry /laugh /dance /poke /tickle /highfive /wink /blush /facepalm /shrug /angry /bored /confused /hungry /sleep /wakeup /yawn /think
💍 Соц: /marry /divorce /couple /rep /toprep
💎 VIP: /viphelp""", parse_mode="Markdown")

@bot.message_handler(commands=['id'])
def id_cmd(message):
    if message.reply_to_message: bot.reply_to(message, f"🆔 `{message.reply_to_message.from_user.id}`", parse_mode="Markdown")
    else: bot.reply_to(message, f"🆔 `{message.from_user.id}`\nЧат: `{message.chat.id}`", parse_mode="Markdown")

@bot.message_handler(commands=['info'])
def info_cmd(message):
    u = message.reply_to_message.from_user if message.reply_to_message else message.from_user
    cid, uid = message.chat.id, u.id
    p, vip, clan = get_profile(uid), get_vip(uid), get_user_clan(uid)
    try: st = bot.get_chat_member(cid, uid).status
    except: st = "?"
    warns = warns_data.get(uid, {}).get(cid, [])
    mi = mutes_data.get(uid, {}).get(cid)
    muted = f"Да (до {mi.strftime('%H:%M')})" if mi else "Нет"
    banned = bans_data.get(uid, {}).get(cid, False)
    rn = {0:"Участник",1:"Модератор",2:"Мл. владелец",3:"Пом. владельца",4:"Владелец"}
    vt = f"{VIP_LEVELS[vip['level']]['color']} {VIP_LEVELS[vip['level']]['name']}" if vip['level']>0 else "Нет"
    partner_id = marriages.get(uid)
    partner_text = get_user_name(partner_id) if partner_id else "Нет"
    rep = rep_data.get(uid, {}).get("count", 0)
    text = f"""📊 **Инфо**
👤 {get_vip_display(uid, p['nick'] or u.first_name)}
🆔 `{uid}` | 💎 {vt}
🏰 {clan or 'Нет'} | 👑 {st}
💍 {partner_text} | ⭐ {rep}
🎖 {rn[get_rank(cid, uid)]} | ⚠️ {len(warns)}/3
🔇 {muted} | 🚫 {'Да' if banned else 'Нет'}"""
    bot.reply_to(message, text, parse_mode="Markdown")

@bot.message_handler(commands=['rules'])
def rules_cmd(message): bot.reply_to(message, f"📜 {get_chat_data(message.chat.id)['rules']}", parse_mode="Markdown")

@bot.message_handler(commands=['report'])
def report_cmd(message):
    if not message.reply_to_message: bot.reply_to(message, "❌ Ответь!"); return
    reason = message.text.split(maxsplit=1)[1] if len(message.text.split()) > 1 else "Не указана"
    for a in bot.get_chat_administrators(message.chat.id):
        try: bot.send_message(a.user.id, f"🚨 {message.from_user.first_name}\n→ {message.reply_to_message.from_user.first_name}\n{reason}")
        except: pass
    bot.reply_to(message, "✅")

@bot.message_handler(commands=['staff'])
def staff_list(message):
    cid = message.chat.id; st = staff_data.get(cid, {})
    if not st: bot.reply_to(message, "📭"); return
    rn = {1:"Мод",2:"Мл.вл",3:"Пом.вл"}
    text = "🛡️ **Персонал:**\n\n" + "\n".join(f"• {get_vip_display(u, get_user_name(u,cid))} — {rn[r]} ({r})" for u,r in sorted(st.items(), key=lambda x: x[1], reverse=True))
    bot.reply_to(message, text, parse_mode="Markdown")

# ===== ТОП =====
@bot.message_handler(commands=['top'])
def top_cmd(message):
    cid, today = message.chat.id, datetime.now().strftime("%Y-%m-%d")
    stats = daily_stats.get(cid, {}).get(today, {})
    text = "🏆 **Топ-10:**\n\n" + "\n".join(f"{i}. {get_vip_display(int(u), get_user_name(int(u),cid))} — {d.get('balance',0):,}🧱" for i,(u,d) in enumerate(sorted(economy.items(), key=lambda x: x[1].get("balance",0), reverse=True)[:10], 1))
    text += "\n📊 **Активные:**\n"
    if stats and stats.get("users"):
        text += "\n".join(f"{i}. {get_user_name(u,cid)} — {c}с" for i,(u,c) in enumerate(sorted(stats["users"].items(), key=lambda x: x[1], reverse=True)[:5], 1))
    else: text += "Нет данных."
    bot.reply_to(message, text, parse_mode="Markdown")

# ===== ПЕРЕВОДЧИК / АНОНИМ / МЕМ =====
@bot.message_handler(commands=['translate'])
def translate_cmd(message):
    args = message.text.split(maxsplit=1)
    text = message.reply_to_message.text if message.reply_to_message else (args[1] if len(args) > 1 else "")
    if not text: bot.reply_to(message, "❌ Нет текста!"); return
    try: bot.reply_to(message, f"🌐 {requests.get(f'https://api.mymemory.translated.net/get?q={text}&langpair=auto|ru').json()['responseData']['translatedText']}", parse_mode="Markdown")
    except: bot.reply_to(message, "❌")

@bot.message_handler(commands=['anonym'])
def anonym_cmd(message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2: bot.reply_to(message, "❌ /anonym [текст]"); return
    try: bot.delete_message(message.chat.id, message.message_id)
    except: pass
    bot.send_message(message.chat.id, f"🕵️ {args[1]}", parse_mode="Markdown")

@bot.message_handler(commands=['meme'])
def meme_cmd(message):
    try:
        d = requests.get("https://meme-api.com/gimme").json()
        bot.send_photo(message.chat.id, d['url'], caption=f"😄 {d['title']}")
    except: bot.reply_to(message, "❌")

# ===== PIN/UNPIN =====
@bot.message_handler(commands=['pin'])
def pin_cmd(message):
    if not has_rank(message.chat.id, message.from_user.id, 2): return
    if not message.reply_to_message: bot.reply_to(message, "❌ Ответь!"); return
    try: bot.pin_chat_message(message.chat.id, message.reply_to_message.message_id); bot.reply_to(message, "📌")
    except: bot.reply_to(message, "❌")

@bot.message_handler(commands=['unpin'])
def unpin_cmd(message):
    if not has_rank(message.chat.id, message.from_user.id, 2): return
    try: bot.unpin_chat_message(message.chat.id); bot.reply_to(message, "✅")
    except: bot.reply_to(message, "❌")

# ===== BANLIST/MUTELIST =====
@bot.message_handler(commands=['banlist'])
def banlist_cmd(message):
    if not has_rank(message.chat.id, message.from_user.id, 2): return
    cid = message.chat.id
    banned = [u for u,chs in bans_data.items() if cid in chs and chs[cid]]
    if not banned: bot.reply_to(message, "📭"); return
    bot.reply_to(message, "🚫 **Забанены:**\n\n" + "\n".join(f"• {get_user_name(int(u),cid)} (`{u}`)" for u in banned[:20]), parse_mode="Markdown")

@bot.message_handler(commands=['mutelist'])
def mutelist_cmd(message):
    if not has_rank(message.chat.id, message.from_user.id, 2): return
    cid = message.chat.id
    muted = [u for u,chs in mutes_data.items() if cid in chs and chs[cid] and datetime.now() < chs[cid]]
    if not muted: bot.reply_to(message, "📭"); return
    text = "🔇 **Замучены:**\n\n"
    for u in muted[:20]: text += f"• {get_user_name(u,cid)} — ещё {(mutes_data[u][cid]-datetime.now()).seconds//60}м\n"
    bot.reply_to(message, text, parse_mode="Markdown")

# ===== RP =====
@bot.message_handler(commands=['hug','kiss','slap','pat','kill','revive','poke','tickle','highfive','wink'])
def rp_reply(message):
    if not message.reply_to_message: bot.reply_to(message, "❌ Ответь!"); return
    u1, u2 = message.from_user.first_name, message.reply_to_message.from_user.first_name
    acts = {'hug':f"🤗 {u1} обнимает {u2}!",'kiss':f"💋 {u1} целует {u2}!",'slap':f"👋 {u1} даёт пощёчину {u2}!",'pat':f"🤚 {u1} гладит {u2}!",'kill':random.choice([f"🔪 {u1} убивает {u2}!",f"💀 {u1} нокаутирует {u2}!"]),'revive':f"💖 {u1} воскрешает {u2}!",'poke':f"👉 {u1} тыкает {u2}!",'tickle':f"🤣 {u1} щекочет {u2}!",'highfive':f"🖐 {u1} даёт пять {u2}!",'wink':f"😉 {u1} подмигивает {u2}!"}
    bot.send_message(message.chat.id, acts.get(message.text.split()[0][1:], "🤷"))

@bot.message_handler(commands=['hugme','cry','laugh','dance','blush','facepalm','shrug','angry','bored','confused','hungry','sleep','wakeup','yawn','think'])
def rp_self(message):
    u = message.from_user.first_name
    acts = {'hugme':f"🤗 {u} обнимает себя...",'cry':f"😢 {u} плачет...",'laugh':random.choice([f"😂 {u} смеётся!",f"🤣 {u} умирает со смеху!"]),'dance':f"💃 {u} танцует!",'blush':f"😊 {u} краснеет...",'facepalm':f"🤦 {u} фейспалм",'shrug':f"🤷 {u} пожимает плечами",'angry':f"😤 {u} злится!",'bored':f"🥱 {u} скучает...",'confused':f"🤔 {u} в замешательстве",'hungry':f"🍔 {u} голоден!",'sleep':f"😴 {u} спит...",'wakeup':f"⏰ {u} просыпается!",'yawn':f"🥱 {u} зевает...",'think':f"🤔 {u} задумался..."}
    bot.send_message(message.chat.id, acts.get(message.text.split()[0][1:], "🤷"))

# ===== ПОВЫШЕНИЕ/ПОНИЖЕНИЕ =====
@bot.message_handler(commands=['raising'])
def raising_cmd(message):
    if not is_owner_or_creator(message.chat.id, message.from_user.id): return
    if not message.reply_to_message: bot.reply_to(message, "❌ Ответь!"); return
    u, cid = message.reply_to_message.from_user, message.chat.id
    cr = get_rank(cid, u.id)
    if cr >= 3: bot.reply_to(message, "❌ Макс!"); return
    set_rank(cid, u.id, cr+1); save_all_data()
    bot.reply_to(message, f"⬆️ {u.first_name} → {cr+1}")

@bot.message_handler(commands=['downgrade'])
def downgrade_cmd(message):
    if not is_owner_or_creator(message.chat.id, message.from_user.id): return
    if not message.reply_to_message: bot.reply_to(message, "❌ Ответь!"); return
    u, cid = message.reply_to_message.from_user, message.chat.id
    cr = get_rank(cid, u.id)
    if cr <= 1: bot.reply_to(message, "❌ /gg"); return
    set_rank(cid, u.id, cr-1); save_all_data()
    bot.reply_to(message, f"⬇️ {u.first_name} → {cr-1}")

@bot.message_handler(commands=['gg'])
def gg_cmd(message):
    if not is_owner_or_creator(message.chat.id, message.from_user.id): return
    if not message.reply_to_message: bot.reply_to(message, "❌ Ответь!"); return
    u, cid = message.reply_to_message.from_user, message.chat.id
    if get_rank(cid, u.id) == 0: bot.reply_to(message, "❌ Без ранга!"); return
    set_rank(cid, u.id, 0); save_all_data()
    bot.reply_to(message, f"💀 {u.first_name} лишён!")

# ===== МОДЕРАЦИЯ =====
@bot.message_handler(commands=['warn'])
def warn_cmd(message):
    if not has_rank(message.chat.id, message.from_user.id, 1): return
    if not message.reply_to_message: bot.reply_to(message, "❌ Ответь!"); return
    u, cid = message.reply_to_message.from_user, message.chat.id
    if get_rank(cid, u.id) >= get_rank(cid, message.from_user.id): bot.reply_to(message, f"❌ {random.choice(DENY_PHRASES)}"); return
    reason = message.text.split(maxsplit=1)[1] if len(message.text.split()) > 1 else "Нарушение"
    warns_data.setdefault(u.id, {}).setdefault(cid, []).append({"reason": reason, "time": datetime.now().isoformat(), "by": message.from_user.id})
    wc = len(warns_data[u.id][cid])
    if wc >= MAX_WARNS:
        cr = get_rank(cid, u.id)
        if cr > 0: set_rank(cid, u.id, cr-1); warns_data[u.id][cid] = []; bot.reply_to(message, f"🚨 3/3! Ранг → {cr-1}")
        else:
            try: bot.restrict_chat_member(cid, u.id, until_date=datetime.now()+timedelta(hours=1)); warns_data[u.id][cid] = []; bot.reply_to(message, "🚨 3/3! Мут 1ч")
            except: bot.reply_to(message, "⚠️ 3/3!")
    else: bot.reply_to(message, f"⚠️ {u.first_name} — {wc}/3\n{reason}")
    save_all_data()

@bot.message_handler(commands=['mute'])
def mute_cmd(message):
    if not has_rank(message.chat.id, message.from_user.id, 1): return
    if not message.reply_to_message: bot.reply_to(message, "❌ Ответь!"); return
    u, cid = message.reply_to_message.from_user, message.chat.id
    if get_rank(cid, u.id) >= get_rank(cid, message.from_user.id): bot.reply_to(message, f"❌ {random.choice(DENY_PHRASES)}"); return
    try: bot.restrict_chat_member(cid, u.id, until_date=datetime.now()+timedelta(days=3650)); mutes_data.setdefault(u.id, {})[cid] = datetime.now()+timedelta(days=3650); save_all_data(); bot.reply_to(message, f"🔇 {u.first_name} навсегда!")
    except: bot.reply_to(message, "❌")

@bot.message_handler(commands=['mutetime'])
def mutetime_cmd(message):
    if not has_rank(message.chat.id, message.from_user.id, 1): return
    if not message.reply_to_message: bot.reply_to(message, "❌ Ответь!"); return
    u, cid = message.reply_to_message.from_user, message.chat.id
    if get_rank(cid, u.id) >= get_rank(cid, message.from_user.id): bot.reply_to(message, f"❌ {random.choice(DENY_PHRASES)}"); return
    try: mins = int(message.text.split()[1])
    except: bot.reply_to(message, "❌ /mutetime [мин]"); return
    try: bot.restrict_chat_member(cid, u.id, until_date=datetime.now()+timedelta(minutes=mins)); mutes_data.setdefault(u.id, {})[cid] = datetime.now()+timedelta(minutes=mins); save_all_data(); bot.reply_to(message, f"🔇 {u.first_name} {mins}м")
    except: bot.reply_to(message, "❌")

@bot.message_handler(commands=['unmute'])
def unmute_cmd(message):
    if not has_rank(message.chat.id, message.from_user.id, 1): return
    if not message.reply_to_message: bot.reply_to(message, "❌ Ответь!"); return
    u, cid = message.reply_to_message.from_user, message.chat.id
    try: bot.restrict_chat_member(cid, u.id, can_send_messages=True, can_send_photos=True, can_send_videos=True, can_send_voices=True, can_send_audios=True, can_send_documents=True, can_send_stickers=True, can_send_animations=True, can_send_games=True, can_send_polls=True); mutes_data.get(u.id, {}).pop(cid, None); save_all_data(); bot.reply_to(message, f"🔊 {u.first_name}")
    except: bot.reply_to(message, "❌")

@bot.message_handler(commands=['bantime'])
def bantime_cmd(message):
    if not has_rank(message.chat.id, message.from_user.id, 2): return
    if not message.reply_to_message: bot.reply_to(message, "❌ Ответь!"); return
    u, cid = message.reply_to_message.from_user, message.chat.id
    if get_rank(cid, u.id) >= get_rank(cid, message.from_user.id): bot.reply_to(message, f"❌ {random.choice(DENY_PHRASES)}"); return
    try: mins = int(message.text.split()[1])
    except: bot.reply_to(message, "❌ /bantime [мин]"); return
    try: bot.ban_chat_member(cid, u.id, until_date=datetime.now()+timedelta(minutes=mins)); save_all_data(); bot.reply_to(message, f"🚫 {u.first_name} {mins}м")
    except: bot.reply_to(message, "❌")

@bot.message_handler(commands=['ban'])
def ban_cmd(message):
    if not has_rank(message.chat.id, message.from_user.id, 3): return
    if not message.reply_to_message: bot.reply_to(message, "❌ Ответь!"); return
    u, cid = message.reply_to_message.from_user, message.chat.id
    if get_rank(cid, u.id) >= get_rank(cid, message.from_user.id): bot.reply_to(message, f"❌ {random.choice(DENY_PHRASES)}"); return
    reason = message.text.split(maxsplit=1)[1] if len(message.text.split()) > 1 else "Нарушение"
    try: bot.ban_chat_member(cid, u.id); bans_data.setdefault(u.id, {})[cid] = True; save_all_data(); bot.reply_to(message, f"🚫 {u.first_name}!\n{reason}")
    except: bot.reply_to(message, "❌")

@bot.message_handler(commands=['kick'])
def kick_cmd(message):
    if not has_rank(message.chat.id, message.from_user.id, 1): return
    if not message.reply_to_message: bot.reply_to(message, "❌ Ответь!"); return
    u, cid = message.reply_to_message.from_user, message.chat.id
    if get_rank(cid, u.id) >= get_rank(cid, message.from_user.id): bot.reply_to(message, f"❌ {random.choice(DENY_PHRASES)}"); return
    try: bot.ban_chat_member(cid, u.id); bot.unban_chat_member(cid, u.id); bot.reply_to(message, f"👢 {u.first_name}")
    except: bot.reply_to(message, "❌")

@bot.message_handler(commands=['unban'])
def unban_cmd(message):
    if not has_rank(message.chat.id, message.from_user.id, 3): return
    try: uid = int(message.text.split()[1]); bot.unban_chat_member(message.chat.id, uid); bans_data.get(uid, {}).pop(message.chat.id, None); save_all_data(); bot.reply_to(message, f"✅ {uid}")
    except: bot.reply_to(message, "❌ /unban [ID]")

# ===== НАСТРОЙКИ ЧАТА =====
@bot.message_handler(commands=['setrules'])
def setrules_cmd(message):
    if not is_owner_or_creator(message.chat.id, message.from_user.id): return
    args = message.text.split(maxsplit=1)
    if len(args) < 2: bot.reply_to(message, "❌ /setrules [текст]"); return
    get_chat_data(message.chat.id)['rules'] = args[1]; save_all_data(); bot.reply_to(message, "✅")

@bot.message_handler(commands=['setwelcome'])
def setwelcome_cmd(message):
    if not is_owner_or_creator(message.chat.id, message.from_user.id): return
    args = message.text.split(maxsplit=1)
    if len(args) < 2: bot.reply_to(message, "❌ /setwelcome [текст]"); return
    get_chat_data(message.chat.id)['welcome'] = args[1]; save_all_data(); bot.reply_to(message, "✅")

@bot.message_handler(commands=['welcome_on'])
def welcome_on(message):
    if not is_owner_or_creator(message.chat.id, message.from_user.id): return
    get_chat_data(message.chat.id)['welcome_enabled'] = True; save_all_data(); bot.reply_to(message, "✅ Вкл")

@bot.message_handler(commands=['welcome_off'])
def welcome_off(message):
    if not is_owner_or_creator(message.chat.id, message.from_user.id): return
    get_chat_data(message.chat.id)['welcome_enabled'] = False; save_all_data(); bot.reply_to(message, "✅ Выкл")

# ===== КАПЧА =====
@bot.message_handler(commands=['captcha'])
def captcha_cmd(message):
    if not has_rank(message.chat.id, message.from_user.id, 2): return
    pending = captcha_data.get(message.chat.id, [])
    if not pending: bot.reply_to(message, "✅ Нет"); return
    bot.reply_to(message, "🔐 **Ожидают:**\n\n" + "\n".join(f"• {get_user_name(u, message.chat.id)} (`{u}`)" for u in pending) + "\n\nНужно /start в ЛС", parse_mode="Markdown")

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
    if len([m for m in message_history[uid] if (datetime.now() - m['time']).seconds < 5]) >= 5:
        try: bot.delete_message(cid, message.message_id)
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
    bot.reply_to(message, f"⏱ {delta.days}д {delta.seconds//3600}ч {(delta.seconds%3600)//60}м")

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
                text = f"📰 **Итоги** ({today})\n💬 {stats['messages']} | 👥 {len(stats['users'])}\n🏆 " + " ".join(f"{i}. {get_user_name(u,cid)}" for i,(u,_) in enumerate(sorted(stats["users"].items(), key=lambda x: x[1], reverse=True)[:5], 1))
                try: bot.send_message(cid, text, parse_mode="Markdown")
                except: pass

# ===== ЗАПУСК =====
print("🧱 Wall запущен!")
load_all_data()
threading.Thread(target=auto_daily_report, daemon=True).start()
threading.Thread(target=auto_save, daemon=True).start()
bot.infinity_polling()