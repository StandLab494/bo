import telebot
import requests
import time
import threading
from datetime import datetime, timedelta

# ===== НАСТРОЙКИ =====
TOKEN = "8804412117:AAFClU1wzf_qQWymrcmEQ3_pVBCNdxOP1pM"
OWNER_ID = 8558737152

bot = telebot.TeleBot(TOKEN)

# ===== БАЗЫ ДАННЫХ =====
staff_data = {}
warns_data = {}
mutes_data = {}
bans_data = {}
chats_data = {}
message_history = {}
daily_stats = {}
MAX_WARNS = 3

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

# ===== КОМАНДЫ ДЛЯ ВСЕХ =====
@bot.message_handler(commands=['start'])
def start(message):
    if message.chat.type == 'private':
        bot.reply_to(message,
            "🤖 **CityGuard — Чат-менеджер**\n\n"
            "Добавь меня в группу и выдай права админа!\n\n"
            "📜 /help — список команд\n"
            "📊 /info — информация\n"
            "🆔 /id — узнать ID",
            parse_mode="Markdown")

@bot.message_handler(commands=['help'])
def help_cmd(message):
    text = """🤖 **CityGuard — Команды**

👤 **Для всех:**
/id — свой ID
/info — информация
/report — пожаловаться
/rules — правила
/staff — персонал
/daily — статистика дня

🌐 **Утилиты:**
/translate — перевод
/anonym — анонимное сообщение

🛡️ **Модерация:**
Ранг 1: /mute, /mutetime, /warn, /kick
Ранг 2: + /bantime
Ранг 3: + /ban, /unban
Ранг 4: + /raising, /downgrade, /gg
Ранг 4: /setrules, /setwelcome"""
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
    text = f"""📊 **Информация**
👤 {u.first_name}
🆔 `{uid}`
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
        try:
            u = bot.get_chat_member(cid, uid).user
            text += f"• {u.first_name} — {rn[rank]} (ранг {rank})\n"
        except:
            text += f"• ID:{uid} — {rn[rank]}\n"
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
        
        bot.reply_to(message, 
            f"🌐 **Перевод**\n\n📥 {original_lang}: {text}\n📤 RU: {translated}",
            parse_mode="Markdown")
    except:
        bot.reply_to(message, "❌ Не удалось перевести. Попробуйте позже.")

# ===== АНОНИМНОЕ СООБЩЕНИЕ =====
@bot.message_handler(commands=['anonym'])
def anonym_cmd(message):
    args = message.text.split(maxsplit=1)
    
    if len(args) < 2:
        bot.reply_to(message, "❌ Напишите текст!\nПример: /anonym Привет всем!")
        return
    
    try:
        bot.delete_message(message.chat.id, message.message_id)
    except:
        pass
    
    bot.send_message(
        message.chat.id,
        f"🕵️ **Аноним:**\n\n{args[1]}",
        parse_mode="Markdown"
    )

# ===== ЕЖЕДНЕВНАЯ ГАЗЕТА =====
@bot.message_handler(commands=['daily'])
def daily_report_cmd(message):
    if not has_rank(message.chat.id, message.from_user.id, 2):
        bot.reply_to(message, "❌ Нужен ранг 2+!")
        return
    
    cid = message.chat.id
    today = datetime.now().strftime("%Y-%m-%d")
    stats = daily_stats.get(cid, {}).get(today, {})
    
    if not stats:
        bot.reply_to(message, "📭 Статистика за сегодня пока пуста.")
        return
    
    total_msgs = stats["messages"]
    total_users = len(stats["users"])
    top_users = sorted(stats["users"].items(), key=lambda x: x[1], reverse=True)[:5]
    
    text = f"""📰 **Газета чата** ({today})
━━━━━━━━━━━━━━━━
💬 Сообщений: {total_msgs}
👥 Активных: {total_users}

🏆 **Топ болтунов:**
"""
    for i, (uid, count) in enumerate(top_users, 1):
        try:
            user = bot.get_chat_member(cid, uid).user
            name = user.first_name
        except:
            name = f"ID:{uid}"
        text += f"{i}. {name} — {count} сообщ.\n"
    
    bot.reply_to(message, text, parse_mode="Markdown")

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
    args = message.text.split(maxsplit=1)
    reason = args[1] if len(args) > 1 else "Нарушение"
    
    if u.id not in warns_data:
        warns_data[u.id] = {}
    if cid not in warns_data[u.id]:
        warns_data[u.id][cid] = []
    
    warns_data[u.id][cid].append({
        "reason": reason,
        "time": datetime.now().isoformat(),
        "by": message.from_user.id
    })
    
    wc = len(warns_data[u.id][cid])
    if wc >= MAX_WARNS:
        cr = get_rank(cid, u.id)
        if cr > 0:
            set_rank(cid, u.id, cr - 1)
            warns_data[u.id][cid] = []
            rn = {0: "Участник", 1: "Модератор", 2: "Мл. владелец", 3: "Пом. владельца"}
            bot.reply_to(message, f"🚨 {u.first_name} 3/3!\n⬇️ Ранг → {cr-1} ({rn[cr-1]})")
        else:
            try:
                bot.restrict_chat_member(cid, u.id, until_date=datetime.now() + timedelta(hours=1))
                warns_data[u.id][cid] = []
                bot.reply_to(message, f"🚨 {u.first_name} 3/3!\n🔇 Мут 1 час (нет ранга)")
            except:
                bot.reply_to(message, f"⚠️ 3/3! Нужен мут, но нет прав!")
    else:
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
    try:
        bot.restrict_chat_member(cid, u.id, until_date=datetime.now() + timedelta(days=3650))
        if u.id not in mutes_data:
            mutes_data[u.id] = {}
        mutes_data[u.id][cid] = datetime.now() + timedelta(days=3650)
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
    args = message.text.split()
    if len(args) < 2:
        bot.reply_to(message, "❌ /mutetime [минуты]")
        return
    try:
        mins = int(args[1])
    except:
        bot.reply_to(message, "❌ Число!")
        return
    u = message.reply_to_message.from_user
    cid = message.chat.id
    try:
        bot.restrict_chat_member(cid, u.id, until_date=datetime.now() + timedelta(minutes=mins))
        if u.id not in mutes_data:
            mutes_data[u.id] = {}
        mutes_data[u.id][cid] = datetime.now() + timedelta(minutes=mins)
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
    args = message.text.split()
    if len(args) < 2:
        bot.reply_to(message, "❌ /bantime [минуты]")
        return
    try:
        mins = int(args[1])
    except:
        bot.reply_to(message, "❌ Число!")
        return
    u = message.reply_to_message.from_user
    cid = message.chat.id
    try:
        bot.ban_chat_member(cid, u.id, until_date=datetime.now() + timedelta(minutes=mins))
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
    args = message.text.split(maxsplit=1)
    reason = args[1] if len(args) > 1 else "Нарушение"
    try:
        bot.ban_chat_member(cid, u.id)
        if u.id not in bans_data:
            bans_data[u.id] = {}
        bans_data[u.id][cid] = True
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
    bot.reply_to(message, "✅ Приветствие обновлено!")

@bot.message_handler(commands=['welcome_on'])
def welcome_on(message):
    if not is_owner_or_creator(message.chat.id, message.from_user.id):
        bot.reply_to(message, "❌ Только владелец!")
        return
    get_chat_data(message.chat.id)['welcome_enabled'] = True
    bot.reply_to(message, "✅ Приветствие включено!")

@bot.message_handler(commands=['welcome_off'])
def welcome_off(message):
    if not is_owner_or_creator(message.chat.id, message.from_user.id):
        bot.reply_to(message, "❌ Только владелец!")
        return
    get_chat_data(message.chat.id)['welcome_enabled'] = False
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

# ===== АВТО-ОТЧЁТ =====
def auto_daily_report():
    while True:
        now = datetime.now()
        target = now.replace(hour=23, minute=55, second=0, microsecond=0)
        if now > target:
            target += timedelta(days=1)
        time.sleep((target - now).total_seconds())
        
        today = datetime.now().strftime("%Y-%m-%d")
        for cid, chat_data in daily_stats.items():
            stats = chat_data.get(today, {})
            if stats and stats["messages"] > 10:
                total_msgs = stats["messages"]
                total_users = len(stats["users"])
                top_users = sorted(stats["users"].items(), key=lambda x: x[1], reverse=True)[:5]
                
                text = f"📰 **Итоги дня** ({today})\n💬 {total_msgs} сообщ. | 👥 {total_users} акт.\n🏆 Топ: "
                for i, (uid, _) in enumerate(top_users):
                    try:
                        name = bot.get_chat_member(cid, uid).user.first_name
                    except:
                        name = f"ID:{uid}"
                    text += f"{i+1}. {name} "
                
                try:
                    bot.send_message(cid, text, parse_mode="Markdown")
                except:
                    pass

# ===== ЗАПУСК =====
print("🤖 CityGuard запущен!")
threading.Thread(target=auto_daily_report, daemon=True).start()
bot.infinity_polling()