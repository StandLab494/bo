import telebot
from datetime import datetime, timedelta
import re

# ===== НАСТРОЙКИ =====
TOKEN = "8939220569:AAHLTwkf9rD7Gf22EK9CBqtgg2Q19v1LomI"
OWNER_ID = 8558737152  # Главный админ (имеет доступ ко всему)

bot = telebot.TeleBot(TOKEN)

# ===== БАЗЫ ДАННЫХ (в памяти, можно заменить на JSON) =====
# Настройки чатов: {chat_id: {rules: "...", welcome: "...", admins: [id1, id2]}}
chats_data = {}

# Варны: {user_id: {chat_id: [list of warnings]}}
warns_data = {}

# Муты: {user_id: {chat_id: datetime_until}}
mutes_data = {}

# Баны: {user_id: {chat_id: True/False}}
bans_data = {}

# ===== ФУНКЦИИ =====
def is_chat_admin(chat_id, user_id):
    """Проверяет, является ли пользователь админом в чате"""
    try:
        member = bot.get_chat_member(chat_id, user_id)
        return member.status in ['creator', 'administrator']
    except:
        return False

def is_global_admin(user_id):
    """Проверяет, является ли пользователь глобальным админом (владельцем)"""
    return user_id == OWNER_ID

def can_moderate(chat_id, user_id):
    """Может ли пользователь выполнять модераторские действия"""
    return is_global_admin(user_id) or is_chat_admin(chat_id, user_id)

def get_chat_data(chat_id):
    """Получает или создаёт данные чата"""
    if chat_id not in chats_data:
        chats_data[chat_id] = {
            "rules": "Правила чата ещё не установлены.",
            "welcome": "👋 Добро пожаловать в чат, {name}!",
            "welcome_enabled": True,
            "admins": []
        }
    return chats_data[chat_id]

# ===== ОСНОВНЫЕ КОМАНДЫ (для всех) =====
@bot.message_handler(commands=['start'])
def start(message):
    if message.chat.type == 'private':
        bot.reply_to(message,
            f"🤖 **CityGuard — Чат-менеджер**\n\n"
            f"Добавь меня в группу и выдай права админа!\n\n"
            f"📜 /help — список команд\n"
            f"📊 /info — информация о пользователе\n"
            f"🆔 /id — узнать свой ID\n",
            parse_mode="Markdown")

@bot.message_handler(commands=['help'])
def help_command(message):
    text = """🤖 **Команды CityGuard:**

👤 **Для всех:**
/id — узнать свой ID
/info — информация о пользователе
/report [причина] — пожаловаться на сообщение (реплай)
/rules — правила чата

🛡️ **Для админов чата:**
/warn [причина] — предупреждение (реплай)
/mute [минуты] — замутить (реплай)
/unmute — размутить (реплай)
/ban [причина] — забанить (реплай)
/kick — кикнуть (реплай)
/unban — разбанить (по ID)

⚙️ **Настройки чата (админы):**
/setrules [текст] — установить правила
/setwelcome [текст] — установить приветствие
/welcome_on — включить приветствие
/welcome_off — выключить приветствие
/admins — список админов чата

👑 **Глобальный админ:**
/gban — глобальный бан
/gunban — глобальный разбан
/broadcast [текст] — рассылка по чатам"""
    
    bot.reply_to(message, text, parse_mode="Markdown")

@bot.message_handler(commands=['id'])
def get_id(message):
    if message.reply_to_message:
        user = message.reply_to_message.from_user
        bot.reply_to(message, f"🆔 ID пользователя {user.first_name}: `{user.id}`", parse_mode="Markdown")
    else:
        bot.reply_to(message, f"🆔 Твой ID: `{message.from_user.id}`\nЧат ID: `{message.chat.id}`", parse_mode="Markdown")

@bot.message_handler(commands=['info'])
def info_command(message):
    if message.reply_to_message:
        user = message.reply_to_message.from_user
    else:
        user = message.from_user
    
    chat_id = message.chat.id
    user_id = user.id
    
    # Проверяем статус
    try:
        member = bot.get_chat_member(chat_id, user_id)
        status = member.status
    except:
        status = "неизвестно"
    
    # Проверяем варны
    warns = warns_data.get(user_id, {}).get(chat_id, [])
    
    # Проверяем мут
    mute_info = mutes_data.get(user_id, {}).get(chat_id)
    muted = "Да (до {})".format(mute_info.strftime("%H:%M")) if mute_info else "Нет"
    
    # Проверяем бан
    banned = bans_data.get(user_id, {}).get(chat_id, False)
    
    text = f"""📊 **Информация о пользователе**

👤 Имя: {user.first_name}
🆔 ID: `{user.id}`
👑 Статус: {status}
⚠️ Варны: {len(warns)}/3
🔇 Замучен: {muted}
🚫 Забанен: {'Да' if banned else 'Нет'}
"""
    bot.reply_to(message, text, parse_mode="Markdown")

@bot.message_handler(commands=['rules'])
def rules_command(message):
    chat_data = get_chat_data(message.chat.id)
    bot.reply_to(message, f"📜 **Правила чата:**\n\n{chat_data['rules']}", parse_mode="Markdown")

@bot.message_handler(commands=['report'])
def report_command(message):
    if not message.reply_to_message:
        bot.reply_to(message, "❌ Ответьте на сообщение, чтобы пожаловаться!")
        return
    
    args = message.text.split(maxsplit=1)
    reason = args[1] if len(args) > 1 else "Не указана"
    
    reported_user = message.reply_to_message.from_user
    
    # Уведомляем админов чата
    admins = bot.get_chat_administrators(message.chat.id)
    for admin in admins:
        try:
            bot.send_message(admin.user.id,
                f"🚨 **Репорт в чате {message.chat.id}**\n"
                f"От: {message.from_user.first_name}\n"
                f"На: {reported_user.first_name}\n"
                f"Причина: {reason}",
                parse_mode="Markdown")
        except:
            pass
    
    bot.reply_to(message, "✅ Жалоба отправлена администраторам!")

# ===== МОДЕРАЦИЯ =====
@bot.message_handler(commands=['warn'])
def warn_command(message):
    if message.chat.type == 'private':
        bot.reply_to(message, "❌ Эта команда работает только в группах!")
        return
    
    if not can_moderate(message.chat.id, message.from_user.id):
        bot.reply_to(message, "❌ У вас нет прав!")
        return
    
    if not message.reply_to_message:
        bot.reply_to(message, "❌ Ответьте на сообщение пользователя!")
        return
    
    user = message.reply_to_message.from_user
    chat_id = message.chat.id
    
    args = message.text.split(maxsplit=1)
    reason = args[1] if len(args) > 1 else "Нарушение правил"
    
    if user.id not in warns_data:
        warns_data[user.id] = {}
    if chat_id not in warns_data[user.id]:
        warns_data[user.id][chat_id] = []
    
    warns_data[user.id][chat_id].append({
        "reason": reason,
        "time": datetime.now().isoformat(),
        "by": message.from_user.id
    })
    
    warn_count = len(warns_data[user.id][chat_id])
    
    if warn_count >= 3:
        # Авто-бан
        try:
            bot.ban_chat_member(chat_id, user.id)
            bans_data[user.id] = bans_data.get(user.id, {})
            bans_data[user.id][chat_id] = True
            bot.reply_to(message, f"🚫 {user.first_name} получил 3 предупреждения и был забанен!")
        except:
            bot.reply_to(message, f"⚠️ {user.first_name} получил {warn_count}/3 предупреждений. Нужен бан, но не хватает прав!")
    else:
        bot.reply_to(message, f"⚠️ {user.first_name} получил предупреждение ({warn_count}/3)\nПричина: {reason}")

@bot.message_handler(commands=['mute'])
def mute_command(message):
    if message.chat.type == 'private':
        bot.reply_to(message, "❌ Эта команда работает только в группах!")
        return
    
    if not can_moderate(message.chat.id, message.from_user.id):
        bot.reply_to(message, "❌ У вас нет прав!")
        return
    
    if not message.reply_to_message:
        bot.reply_to(message, "❌ Ответьте на сообщение пользователя!")
        return
    
    user = message.reply_to_message.from_user
    chat_id = message.chat.id
    
    args = message.text.split()
    minutes = int(args[1]) if len(args) > 1 else 30
    
    try:
        bot.restrict_chat_member(chat_id, user.id, until_date=datetime.now() + timedelta(minutes=minutes))
        
        if user.id not in mutes_data:
            mutes_data[user.id] = {}
        mutes_data[user.id][chat_id] = datetime.now() + timedelta(minutes=minutes)
        
        bot.reply_to(message, f"🔇 {user.first_name} замучен на {minutes} минут!")
    except:
        bot.reply_to(message, "❌ Не удалось замутить пользователя!")

@bot.message_handler(commands=['unmute'])
def unmute_command(message):
    if not can_moderate(message.chat.id, message.from_user.id):
        bot.reply_to(message, "❌ У вас нет прав!")
        return
    
    if not message.reply_to_message:
        bot.reply_to(message, "❌ Ответьте на сообщение пользователя!")
        return
    
    user = message.reply_to_message.from_user
    chat_id = message.chat.id
    
    try:
        bot.restrict_chat_member(chat_id, user.id, can_send_messages=True)
        
        if user.id in mutes_data and chat_id in mutes_data[user.id]:
            del mutes_data[user.id][chat_id]
        
        bot.reply_to(message, f"🔊 {user.first_name} размучен!")
    except:
        bot.reply_to(message, "❌ Не удалось размутить!")

@bot.message_handler(commands=['ban'])
def ban_command(message):
    if message.chat.type == 'private':
        bot.reply_to(message, "❌ Эта команда работает только в группах!")
        return
    
    if not can_moderate(message.chat.id, message.from_user.id):
        bot.reply_to(message, "❌ У вас нет прав!")
        return
    
    if not message.reply_to_message:
        bot.reply_to(message, "❌ Ответьте на сообщение пользователя!")
        return
    
    user = message.reply_to_message.from_user
    chat_id = message.chat.id
    
    args = message.text.split(maxsplit=1)
    reason = args[1] if len(args) > 1 else "Нарушение правил"
    
    try:
        bot.ban_chat_member(chat_id, user.id)
        
        if user.id not in bans_data:
            bans_data[user.id] = {}
        bans_data[user.id][chat_id] = True
        
        bot.reply_to(message, f"🚫 {user.first_name} забанен!\nПричина: {reason}")
    except:
        bot.reply_to(message, "❌ Не удалось забанить пользователя!")

@bot.message_handler(commands=['kick'])
def kick_command(message):
    if message.chat.type == 'private':
        bot.reply_to(message, "❌ Эта команда работает только в группах!")
        return
    
    if not can_moderate(message.chat.id, message.from_user.id):
        bot.reply_to(message, "❌ У вас нет прав!")
        return
    
    if not message.reply_to_message:
        bot.reply_to(message, "❌ Ответьте на сообщение пользователя!")
        return
    
    user = message.reply_to_message.from_user
    chat_id = message.chat.id
    
    try:
        bot.ban_chat_member(chat_id, user.id)
        bot.unban_chat_member(chat_id, user.id)  # Кик = бан + разбан
        bot.reply_to(message, f"👢 {user.first_name} кикнут из чата!")
    except:
        bot.reply_to(message, "❌ Не удалось кикнуть!")

@bot.message_handler(commands=['unban'])
def unban_command(message):
    if not can_moderate(message.chat.id, message.from_user.id):
        bot.reply_to(message, "❌ У вас нет прав!")
        return
    
    args = message.text.split()
    if len(args) < 2:
        bot.reply_to(message, "❌ Используй: /unban [ID пользователя]")
        return
    
    try:
        user_id = int(args[1])
        bot.unban_chat_member(message.chat.id, user_id)
        
        if user_id in bans_data and message.chat.id in bans_data[user_id]:
            del bans_data[user_id][message.chat.id]
        
        bot.reply_to(message, f"✅ Пользователь {user_id} разбанен!")
    except:
        bot.reply_to(message, "❌ Неверный ID или пользователь не забанен!")

# ===== НАСТРОЙКИ ЧАТА =====
@bot.message_handler(commands=['setrules'])
def set_rules(message):
    if not can_moderate(message.chat.id, message.from_user.id):
        bot.reply_to(message, "❌ У вас нет прав!")
        return
    
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        bot.reply_to(message, "❌ Используй: /setrules [текст правил]")
        return
    
    chat_data = get_chat_data(message.chat.id)
    chat_data['rules'] = args[1]
    bot.reply_to(message, "✅ Правила чата обновлены!")

@bot.message_handler(commands=['setwelcome'])
def set_welcome(message):
    if not can_moderate(message.chat.id, message.from_user.id):
        bot.reply_to(message, "❌ У вас нет прав!")
        return
    
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        bot.reply_to(message, "❌ Используй: /setwelcome [текст приветствия]\nМожно использовать {name} для имени пользователя")
        return
    
    chat_data = get_chat_data(message.chat.id)
    chat_data['welcome'] = args[1]
    bot.reply_to(message, "✅ Приветствие обновлено!")

@bot.message_handler(commands=['welcome_on'])
def welcome_on(message):
    if not can_moderate(message.chat.id, message.from_user.id):
        bot.reply_to(message, "❌ У вас нет прав!")
        return
    chat_data = get_chat_data(message.chat.id)
    chat_data['welcome_enabled'] = True
    bot.reply_to(message, "✅ Приветствие включено!")

@bot.message_handler(commands=['welcome_off'])
def welcome_off(message):
    if not can_moderate(message.chat.id, message.from_user.id):
        bot.reply_to(message, "❌ У вас нет прав!")
        return
    chat_data = get_chat_data(message.chat.id)
    chat_data['welcome_enabled'] = False
    bot.reply_to(message, "✅ Приветствие выключено!")

@bot.message_handler(commands=['admins'])
def admins_list(message):
    if message.chat.type == 'private':
        bot.reply_to(message, "❌ Эта команда работает только в группах!")
        return
    
    admins = bot.get_chat_administrators(message.chat.id)
    text = "👑 **Админы чата:**\n\n"
    for admin in admins:
        status = "Создатель" if admin.status == 'creator' else "Админ"
        text += f"• {admin.user.first_name} — {status}\n"
    
    bot.reply_to(message, text, parse_mode="Markdown")

# ===== ПРИВЕТСТВИЕ НОВЫХ УЧАСТНИКОВ =====
@bot.message_handler(content_types=['new_chat_members'])
def welcome_new_member(message):
    chat_data = get_chat_data(message.chat.id)
    
    if not chat_data['welcome_enabled']:
        return
    
    for new_member in message.new_chat_members:
        welcome_text = chat_data['welcome'].replace('{name}', new_member.first_name)
        bot.send_message(message.chat.id, welcome_text)

# ===== АВТОМОДЕРАЦИЯ (антиспам) =====
# Словарь для отслеживания сообщений: {user_id: [список последних сообщений]}
message_history = {}

@bot.message_handler(func=lambda m: True)  # Обрабатывает все сообщения
def auto_moderation(message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    
    if message.chat.type == 'private':
        return
    
    # Проверка на мут
    if user_id in mutes_data and chat_id in mutes_data.get(user_id, {}):
        mute_until = mutes_data[user_id][chat_id]
        if datetime.now() < mute_until:
            try:
                bot.delete_message(chat_id, message.message_id)
            except:
                pass
            return
    
    # Проверка на спам (одинаковые сообщения)
    if user_id not in message_history:
        message_history[user_id] = []
    
    message_history[user_id].append({
        "text": message.text,
        "time": datetime.now()
    })
    
    # Оставляем только последние 10 сообщений
    if len(message_history[user_id]) > 10:
        message_history[user_id] = message_history[user_id][-10:]
    
    # Проверяем, не спамит ли пользователь
    recent = [m for m in message_history[user_id] if (datetime.now() - m['time']).seconds < 5]
    
    if len(recent) >= 5:
        # Спам-режим! Удаляем последнее сообщение
        try:
            bot.delete_message(chat_id, message.message_id)
            # Если можно, мутим на 1 минуту
            if can_moderate(chat_id, bot.get_me().id):
                bot.restrict_chat_member(chat_id, user_id, until_date=datetime.now() + timedelta(minutes=1))
        except:
            pass

# ===== ГЛОБАЛЬНЫЕ КОМАНДЫ (только владелец) =====
@bot.message_handler(commands=['gban'])
def global_ban(message):
    if not is_global_admin(message.from_user.id):
        bot.reply_to(message, "❌ Только владелец бота!")
        return
    
    if not message.reply_to_message:
        bot.reply_to(message, "❌ Ответьте на сообщение пользователя!")
        return
    
    user = message.reply_to_message.from_user
    # В реальном приложении — записать в глобальную базу банов
    bot.reply_to(message, f"🌍 {user.first_name} глобально забанен!")

@bot.message_handler(commands=['broadcast'])
def broadcast(message):
    if not is_global_admin(message.from_user.id):
        bot.reply_to(message, "❌ Только владелец бота!")
        return
    
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        bot.reply_to(message, "❌ Используй: /broadcast [текст]")
        return
    
    text = args[1]
    sent = 0
    for chat_id in list(chats_data.keys()):
        try:
            bot.send_message(chat_id, f"📢 {text}")
            sent += 1
        except:
            pass
    
    bot.reply_to(message, f"✅ Рассылка отправлена в {sent} чатов!")

# ===== ЗАПУСК =====
print("🤖 CityGuard запущен!")
bot.infinity_polling()