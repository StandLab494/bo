import telebot
import time
import threading
import json
import os
import random
from datetime import datetime, timedelta

TOKEN = "8804412117:AAFClU1wzf_qQWymrcmEQ3_pVBCNdxOP1pM"
OWNER_ID = 8558737152
DB_FILE = "wall_db.json"
MAX_WARNS = 3

bot = telebot.TeleBot(TOKEN)

staff_data = {}
warns_data = {}
mutes_data = {}
bans_data = {}
chats_data = {}
vip_data = {}
pending_payments = {}
captcha_data = {}
start_time = datetime.now()

VIP_LEVELS = {
    1: {"name": "VIP", "prefix": "[VIP]", "color": "🟣", "price": "100 ⭐"},
    2: {"name": "VIP+", "prefix": "[VIP+]", "color": "🟡", "price": "250 ⭐"},
    3: {"name": "LEGEND+", "prefix": "[LEGEND+]", "color": "🔴", "price": "500 ⭐"},
}

DENY_PHRASES = [
    "Твой ранг недостаточен для этого.",
    "Цель выше или равна тебе по званию.",
    "Ты не можешь наказать равного или старшего.",
    "Попытка засчитана, результат — нет.",
    "Только младший по рангу может быть наказан.",
    "Твои полномочия здесь заканчиваются.",
    "Отказано. Требуется ранг строго выше.",
    "Ты не можешь наказать того, кто старше.",
    "Субординация нарушена.",
    "Твой ранг не позволяет.",
    "Цель защищена статусом.",
    "Повысь ранг, затем возвращайся.",
    "Недостаточно прав.",
    "Иерархия есть иерархия.",
    "Равный не может наказать равного.",
    "Требуется превосходство по рангу.",
]

def save_all_data():
    clean_mutes = {}
    for uid, chats in mutes_data.items():
        clean_mutes[str(uid)] = {}
        for cid, dt in chats.items():
            clean_mutes[str(uid)][str(cid)] = dt.isoformat() if dt else None
    data = {
        "staff_data": staff_data, "warns_data": warns_data,
        "mutes_data": clean_mutes, "bans_data": bans_data,
        "chats_data": chats_data, "vip_data": vip_data,
        "pending_payments": pending_payments
    }
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def load_all_data():
    global staff_data, warns_data, mutes_data, bans_data, chats_data, vip_data, pending_payments
    if not os.path.exists(DB_FILE): return
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
                if dt_str: mutes_data[int(uid)][int(cid)] = datetime.fromisoformat(dt_str)
        chats_data = {int(cid): chat for cid, chat in data.get("chats_data", {}).items()}
        vip_data = data.get("vip_data", {})
        pending_payments = data.get("pending_payments", {})
    except: pass

def auto_save():
    while True:
        time.sleep(30)
        try: save_all_data()
        except: pass

def get_vip(uid):
    return vip_data.get(str(uid), {"level": 0, "color": "purple"})

def is_vip(uid):
    return get_vip(uid)["level"] >= 1

def get_rank(chat_id, user_id):
    if user_id == OWNER_ID: return 4
    try:
        if bot.get_chat_member(chat_id, user_id).status == 'creator': return 4
    except: pass
    return staff_data.get(chat_id, {}).get(user_id, 0)

def set_rank(chat_id, user_id, rank):
    if chat_id not in staff_data: staff_data[chat_id] = {}
    if rank == 0: staff_data[chat_id].pop(user_id, None)
    else: staff_data[chat_id][user_id] = rank

def has_rank(chat_id, user_id, min_rank): return get_rank(chat_id, user_id) >= min_rank
def is_owner_or_creator(chat_id, user_id): return get_rank(chat_id, user_id) >= 4

def get_chat_data(chat_id):
    if chat_id not in chats_data:
        chats_data[chat_id] = {"rules": "Правила чата ещё не установлены.", "welcome": "Добро пожаловать, {name}!", "welcome_enabled": True}
    return chats_data[chat_id]

def get_user_name(uid, cid=None):
    try:
        if cid: return bot.get_chat_member(cid, uid).user.first_name
    except: pass
    try: return bot.get_chat(uid).first_name
    except: pass
    return f"ID:{uid}"

def parse_time(time_str):
    time_str = time_str.lower()
    if time_str.endswith('с') or time_str.endswith('s'):
        try: return int(time_str[:-1]) / 60
        except: return None
    if time_str.endswith('м') or time_str.endswith('m'):
        try: return int(time_str[:-1])
        except: return None
    if time_str.endswith('ч') or time_str.endswith('h'):
        try: return int(time_str[:-1]) * 60
        except: return None
    if time_str.endswith('д') or time_str.endswith('d'):
        try: return int(time_str[:-1]) * 1440
        except: return None
    try: return int(time_str)
    except: return None

def get_private_keyboard():
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("Помощь", "Купить VIP", "Профиль")
    return markup

@bot.message_handler(commands=['start'])
def start(message):
    uid = message.from_user.id
    for cid, users in list(captcha_data.items()):
        if uid in users:
            try:
                bot.restrict_chat_member(cid, uid, can_send_messages=True, can_send_photos=True, can_send_videos=True, can_send_voices=True, can_send_audios=True, can_send_documents=True, can_send_stickers=True, can_send_animations=True, can_send_games=True, can_send_polls=True)
                captcha_data[cid].remove(uid)
                if not captcha_data[cid]: del captcha_data[cid]
                bot.send_message(uid, "Капча пройдена!")
                save_all_data()
            except: pass
    if message.chat.type == 'private':
        bot.send_message(message.chat.id, "Wall - Чат-менеджер\n\nДобавь меня в группу и выдай права админа!", reply_markup=get_private_keyboard())

# КНОПКИ ЛС
@bot.message_handler(func=lambda m: m.chat.type == 'private' and m.text == "Помощь")
def help_private(message):
    bot.reply_to(message, "Wall - Команды\n\nМодерация: варн / мут / размут / бан / кик\nИнфо: проф / правила / персонал\nРанги: повысить / понизить / снять ранг\n\nКупить VIP: нажми кнопку 'Купить VIP'")

@bot.message_handler(func=lambda m: m.chat.type == 'private' and m.text == "Профиль")
def profile_private(message):
    v = get_vip(message.from_user.id)
    vt = f"{VIP_LEVELS[v['level']]['color']} {VIP_LEVELS[v['level']]['name']}" if v['level'] > 0 else "Нет"
    bot.reply_to(message, f"Профиль\nID: {message.from_user.id}\nVIP: {vt}")

@bot.message_handler(func=lambda m: m.chat.type == 'private' and m.text == "Купить VIP")
def buy_vip_menu(message):
    text = ("Покупка VIP\n\n"
            "Цены:\n"
            "⭐ VIP — 100 звёзд\n"
            "🌟 VIP+ — 250 звёзд\n"
            "💎 LEGEND+ — 500 звёзд\n\n"
            "Как купить:\n"
            "1. Отправьте нужное количество звёзд на @IKeutoy228\n"
            "2. Напишите мне: оплатил 1 (или 2, или 3)\n"
            "3. Владелец проверит и выдаст VIP")
    bot.reply_to(message, text)

# ОПЛАТА
@bot.message_handler(func=lambda m: m.text and m.text.lower().startswith('оплатил'))
def paid_word(message):
    uid = message.from_user.id
    parts = message.text.split()
    if len(parts) < 2:
        bot.reply_to(message, "Укажите уровень: оплатил 1\n1 - VIP (100 ⭐)\n2 - VIP+ (250 ⭐)\n3 - LEGEND+ (500 ⭐)")
        return
    try: level = int(parts[1])
    except: bot.reply_to(message, "Уровень: 1, 2 или 3"); return
    if level < 1 or level > 3: bot.reply_to(message, "Неверный уровень."); return
    
    pending_payments[str(uid)] = {"level": level, "time": datetime.now().isoformat()}
    save_all_data()
    
    prices = {1: "100 ⭐", 2: "250 ⭐", 3: "500 ⭐"}
    names = {1: "VIP", 2: "VIP+", 3: "LEGEND+"}
    
    bot.reply_to(message, f"Заявка на {names[level]} ({prices[level]}) принята!\nОжидайте подтверждения.")
    try: bot.send_message(OWNER_ID, f"Новая заявка!\n{message.from_user.first_name} (ID: {uid})\nУровень: {names[level]} ({prices[level]})\nОдобрить: одобрить {uid} {level}")
    except: pass

@bot.message_handler(func=lambda m: m.text and m.text.lower().startswith('одобрить'))
def approve_word(message):
    if message.from_user.id != OWNER_ID: bot.reply_to(message, "Только владелец."); return
    parts = message.text.split()
    if len(parts) < 3: bot.reply_to(message, "одобрить [ID] [уровень]"); return
    try: target_id = int(parts[1]); level = int(parts[2])
    except: bot.reply_to(message, "Неверные данные."); return
    if level < 1 or level > 3: bot.reply_to(message, "Уровень: 1, 2, 3"); return
    
    info = VIP_LEVELS[level]
    vip_data[str(target_id)] = {"level": level, "color": "purple"}
    pending_payments.pop(str(target_id), None)
    save_all_data()
    
    bot.reply_to(message, f"{info['color']} {info['name']} выдан {target_id}!")
    try: bot.send_message(target_id, f"Оплата подтверждена!\nВам выдан {info['color']} {info['name']}!")
    except: pass

@bot.message_handler(func=lambda m: m.text and m.text.lower().startswith('заявки'))
def pending_word(message):
    if message.from_user.id != OWNER_ID: return
    if not pending_payments:
        bot.reply_to(message, "Нет ожидающих заявок.")
        return
    text = "Заявки на VIP:\n\n"
    for uid, data in pending_payments.items():
        names = {1: "VIP", 2: "VIP+", 3: "LEGEND+"}
        text += f"{get_user_name(int(uid))} (ID: {uid}) — {names[data['level']]}\n"
    text += "\nОдобрить: одобрить [ID] [уровень]"
    bot.reply_to(message, text)

# МОДЕРАЦИЯ
@bot.message_handler(func=lambda m: m.text and m.text.lower().startswith('варн'))
def warn_word(message):
    if not message.reply_to_message: bot.reply_to(message, "Ответь на сообщение нарушителя."); return
    if not has_rank(message.chat.id, message.from_user.id, 1): return
    u, cid = message.reply_to_message.from_user, message.chat.id
    if get_rank(cid, u.id) >= get_rank(cid, message.from_user.id): bot.reply_to(message, random.choice(DENY_PHRASES)); return
    reason = message.text.split(maxsplit=1)[1] if len(message.text.split()) > 1 else "Нарушение"
    warns_data.setdefault(u.id, {}).setdefault(cid, []).append({"reason": reason, "time": datetime.now().isoformat(), "by": message.from_user.id})
    wc = len(warns_data[u.id][cid])
    if wc >= MAX_WARNS:
        cr = get_rank(cid, u.id)
        if cr > 0: set_rank(cid, u.id, cr-1); warns_data[u.id][cid] = []; bot.reply_to(message, f"{u.first_name} получил 3/3. Ранг понижен.")
        else:
            try: bot.restrict_chat_member(cid, u.id, until_date=datetime.now()+timedelta(hours=1)); warns_data[u.id][cid] = []; bot.reply_to(message, f"{u.first_name} получил 3/3. Мут 1 час.")
            except: bot.reply_to(message, f"{u.first_name} получил 3/3.")
        try: bot.send_message(u.id, f"Вы получили 3 предупреждения и были наказаны.")
        except: pass
    else:
        bot.reply_to(message, f"{u.first_name} получил варн ({wc}/3): {reason}")
        try: bot.send_message(u.id, f"Вы получили предупреждение ({wc}/3).\nПричина: {reason}\nМодератор: {message.from_user.first_name}")
        except: pass
    save_all_data()

@bot.message_handler(func=lambda m: m.text and m.text.lower().startswith('мут'))
def mute_word(message):
    if not message.reply_to_message: bot.reply_to(message, "Ответь на сообщение."); return
    if not has_rank(message.chat.id, message.from_user.id, 1): return
    u, cid = message.reply_to_message.from_user, message.chat.id
    if get_rank(cid, u.id) >= get_rank(cid, message.from_user.id): bot.reply_to(message, random.choice(DENY_PHRASES)); return
    parts = message.text.split(maxsplit=2)
    time_str, mins, reason = None, None, "Нарушение"
    if len(parts) > 1:
        parsed = parse_time(parts[1])
        if parsed is not None: time_str, mins, reason = parts[1], parsed, parts[2] if len(parts) > 2 else "Нарушение"
        else: reason = ' '.join(parts[1:])
    
    if mins and mins > 0:
        total_seconds = int(mins * 60)
        until = datetime.now() + timedelta(seconds=total_seconds)
        try: bot.restrict_chat_member(cid, u.id, until_date=until); mutes_data.setdefault(u.id, {})[cid] = until
        except: bot.reply_to(message, "Не удалось."); return
        if total_seconds < 60: td = f"{total_seconds} сек."
        elif total_seconds < 3600: td = f"{int(mins)} мин."
        elif total_seconds < 86400: td = f"{int(mins//60)} ч."
        else: td = f"{int(mins//1440)} дн."
    else:
        try: bot.restrict_chat_member(cid, u.id, until_date=datetime.now()+timedelta(days=3650)); mutes_data.setdefault(u.id, {})[cid] = datetime.now()+timedelta(days=3650)
        except: bot.reply_to(message, "Не удалось."); return
        td = "навсегда"
    
    bot.reply_to(message, f"{u.first_name} замучен на {td}.\nПричина: {reason}\nМодератор: {message.from_user.first_name}")
    try: bot.send_message(u.id, f"Вы замучены на {td}.\nПричина: {reason}\nМодератор: {message.from_user.first_name}")
    except: pass
    save_all_data()

@bot.message_handler(func=lambda m: m.text and m.text.lower().startswith('размут'))
def unmute_word(message):
    if not message.reply_to_message: bot.reply_to(message, "Ответь на сообщение."); return
    if not has_rank(message.chat.id, message.from_user.id, 1): return
    u, cid = message.reply_to_message.from_user, message.chat.id
    try: bot.restrict_chat_member(cid, u.id, can_send_messages=True, can_send_photos=True, can_send_videos=True, can_send_voices=True, can_send_audios=True, can_send_documents=True, can_send_stickers=True, can_send_animations=True, can_send_games=True, can_send_polls=True); mutes_data.get(u.id, {}).pop(cid, None); save_all_data(); bot.reply_to(message, f"{u.first_name} размучен.")
    except: bot.reply_to(message, "Не удалось.")

@bot.message_handler(func=lambda m: m.text and m.text.lower().startswith('бан'))
def ban_word(message):
    if not message.reply_to_message: bot.reply_to(message, "Ответь на сообщение."); return
    if not has_rank(message.chat.id, message.from_user.id, 3): return
    u, cid = message.reply_to_message.from_user, message.chat.id
    if get_rank(cid, u.id) >= get_rank(cid, message.from_user.id): bot.reply_to(message, random.choice(DENY_PHRASES)); return
    parts = message.text.split(maxsplit=2)
    time_str, mins, reason = None, None, "Нарушение"
    if len(parts) > 1:
        parsed = parse_time(parts[1])
        if parsed is not None: time_str, mins, reason = parts[1], parsed, parts[2] if len(parts) > 2 else "Нарушение"
        else: reason = ' '.join(parts[1:])
    
    if mins and mins > 0:
        total_seconds = int(mins * 60)
        until = datetime.now() + timedelta(seconds=total_seconds)
        try: bot.ban_chat_member(cid, u.id, until_date=until)
        except: bot.reply_to(message, "Не удалось."); return
        if total_seconds < 60: td = f"{total_seconds} сек."
        elif total_seconds < 3600: td = f"{int(mins)} мин."
        elif total_seconds < 86400: td = f"{int(mins//60)} ч."
        else: td = f"{int(mins//1440)} дн."
    else:
        try: bot.ban_chat_member(cid, u.id); bans_data.setdefault(u.id, {})[cid] = True
        except: bot.reply_to(message, "Не удалось."); return
        td = "навсегда"
    
    bot.reply_to(message, f"{u.first_name} забанен на {td}.\nПричина: {reason}\nМодератор: {message.from_user.first_name}")
    try: bot.send_message(u.id, f"Вы забанены на {td}.\nПричина: {reason}\nМодератор: {message.from_user.first_name}")
    except: pass
    save_all_data()

@bot.message_handler(func=lambda m: m.text and m.text.lower().startswith('кик'))
def kick_word(message):
    if not message.reply_to_message: bot.reply_to(message, "Ответь на сообщение."); return
    if not has_rank(message.chat.id, message.from_user.id, 1): return
    u, cid = message.reply_to_message.from_user, message.chat.id
    if get_rank(cid, u.id) >= get_rank(cid, message.from_user.id): bot.reply_to(message, random.choice(DENY_PHRASES)); return
    reason = message.text.split(maxsplit=1)[1] if len(message.text.split()) > 1 else "Нарушение"
    try: bot.ban_chat_member(cid, u.id); bot.unban_chat_member(cid, u.id)
    except: bot.reply_to(message, "Не удалось."); return
    bot.reply_to(message, f"{u.first_name} кикнут.\nПричина: {reason}\nМодератор: {message.from_user.first_name}")
    try: bot.send_message(u.id, f"Вы кикнуты из чата.\nПричина: {reason}\nМодератор: {message.from_user.first_name}")
    except: pass

# ПРОФИЛЬ / ПРАВИЛА
@bot.message_handler(func=lambda m: m.text and m.text.lower().startswith('проф'))
def prof_word(message):
    target = message.reply_to_message.from_user if message.reply_to_message else message.from_user
    uid, cid = target.id, message.chat.id
    rank = get_rank(cid, uid)
    warns = warns_data.get(uid, {}).get(cid, [])
    mi = mutes_data.get(uid, {}).get(cid)
    banned = bans_data.get(uid, {}).get(cid, False)
    if banned: status = "Забанен"
    elif mi and datetime.now() < mi: status = f"Замучен ({(mi-datetime.now()).seconds//60} мин)"
    else: status = "Активен"
    rn = {0:"Участник",1:"Модератор",2:"Мл. владелец",3:"Пом. владельца",4:"Владелец"}
    bot.reply_to(message, f"Профиль {target.first_name}\n━━━━━━━━━━━━━━\nID: {uid}\nРанг: {rn.get(rank, 'Участник')}\nВарны: {len(warns)}/3\nСтатус: {status}\n━━━━━━━━━━━━━━")

@bot.message_handler(func=lambda m: m.text and m.text.lower().startswith('правила'))
def rules_word(message):
    bot.reply_to(message, get_chat_data(message.chat.id)['rules'])

# РАНГИ
@bot.message_handler(func=lambda m: m.text and m.text.lower().startswith('повысить'))
def raise_word(message):
    if not is_owner_or_creator(message.chat.id, message.from_user.id): return
    if not message.reply_to_message: bot.reply_to(message, "Ответь на сообщение."); return
    u, cid = message.reply_to_message.from_user, message.chat.id
    cr = get_rank(cid, u.id)
    if cr >= 3: bot.reply_to(message, f"{u.first_name} уже максимальный ранг."); return
    set_rank(cid, u.id, cr + 1); save_all_data()
    rn = {1:"Модератор",2:"Мл. владелец",3:"Пом. владельца"}
    bot.reply_to(message, f"{u.first_name} повышен до {rn[cr+1]} (ранг {cr+1}).")

@bot.message_handler(func=lambda m: m.text and m.text.lower().startswith('понизить'))
def lower_word(message):
    if not is_owner_or_creator(message.chat.id, message.from_user.id): return
    if not message.reply_to_message: bot.reply_to(message, "Ответь на сообщение."); return
    u, cid = message.reply_to_message.from_user, message.chat.id
    cr = get_rank(cid, u.id)
    if cr <= 1: bot.reply_to(message, f"{u.first_name} нельзя понизить. Используйте 'снять ранг'."); return
    set_rank(cid, u.id, cr - 1); save_all_data()
    rn = {1:"Модератор",2:"Мл. владелец"}
    bot.reply_to(message, f"{u.first_name} понижен до {rn.get(cr-1, 'Участник')} (ранг {cr-1}).")

@bot.message_handler(func=lambda m: m.text and m.text.lower().startswith('снять ранг'))
def remove_rank_word(message):
    if not is_owner_or_creator(message.chat.id, message.from_user.id): return
    if not message.reply_to_message: bot.reply_to(message, "Ответь на сообщение."); return
    u, cid = message.reply_to_message.from_user, message.chat.id
    if get_rank(cid, u.id) == 0: bot.reply_to(message, f"{u.first_name} и так без ранга."); return
    set_rank(cid, u.id, 0); save_all_data()
    bot.reply_to(message, f"{u.first_name} лишён ранга.")

@bot.message_handler(func=lambda m: m.text and m.text.lower().startswith('персонал'))
def staff_word(message):
    st = staff_data.get(message.chat.id, {})
    if not st: bot.reply_to(message, "Нет персонала."); return
    rn = {1:"Модератор",2:"Мл. владелец",3:"Пом. владельца"}
    text = "Персонал:\n\n" + "\n".join(f"{get_user_name(u, message.chat.id)} — {rn[r]} (ранг {r})" for u, r in sorted(st.items(), key=lambda x: x[1], reverse=True))
    bot.reply_to(message, text)

# КАПЧА
@bot.message_handler(content_types=['new_chat_members'])
def welcome_new(message):
    cid, cd = message.chat.id, get_chat_data(message.chat.id)
    for nm in message.new_chat_members:
        if nm.is_bot: continue
        try: bot.restrict_chat_member(cid, nm.id, can_send_messages=False, can_send_photos=False, can_send_videos=False, can_send_voices=False, can_send_audios=False, can_send_documents=False, can_send_stickers=False, can_send_animations=False, can_send_games=False, can_send_polls=False)
        except: pass
        captcha_data.setdefault(cid, []).append(nm.id)
        try: bot.send_message(nm.id, "Добро пожаловать!\nНапиши /start для доступа.")
        except: pass
        if cd.get('welcome_enabled', True): bot.send_message(cid, cd['welcome'].replace('{name}', nm.first_name))

# ЗАПУСК
print("Wall запущен!")
load_all_data()
threading.Thread(target=auto_save, daemon=True).start()
bot.infinity_polling()