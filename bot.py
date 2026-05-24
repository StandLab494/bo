import telebot
import random
from datetime import datetime, timedelta

# ===== НАСТРОЙКИ =====
TOKEN = "8906578550:AAGV7toADTAkBOw6aufuhV_PQbbnmzEuxrQ"
OWNER_ID = 8558737152
ADMIN_IDS = [8558737152]
START_MONEY = 100
NEXT_ID = 1000000

# ===== ПРОМОКОДЫ =====
PROMOCODES = {
    "START100": {"reward": 100, "uses": -1, "description": "100 кристаллов новичку"},
    "LUCKY2024": {"reward": 250, "uses": 50, "description": "+250 кристаллов"},
    "SUPERGAME": {"reward": 500, "uses": 20, "description": "+500 кристаллов"},
    "DAILYBONUS": {"reward": 198292738378373838, "uses": -1, "description": "+50 кристаллов"},
    "TOPPLAYER": {"reward": 1000, "uses": 5, "description": "+1000 кристаллов для топов"}
}

bot = telebot.TeleBot(TOKEN)
players_data = {}
clans_data = {}
BANNED_USERS = {}
FRIENDS = {}
FRIEND_REQUESTS = {}

# ===== ФУНКЦИИ =====
def is_admin(user_id):
    return user_id in ADMIN_IDS

def is_owner(user_id):
    return user_id == OWNER_ID

def is_banned(user_id):
    uid = str(user_id)
    if uid not in BANNED_USERS:
        return False
    ban_data = BANNED_USERS[uid]
    if ban_data["until"] is not None:
        if datetime.now() > ban_data["until"]:
            del BANNED_USERS[uid]
            return False
    return True

def get_ban_info(user_id):
    uid = str(user_id)
    if uid not in BANNED_USERS:
        return None
    return BANNED_USERS[uid]

def check_ban(message):
    if is_banned(message.from_user.id):
        ban_data = get_ban_info(message.from_user.id)
        reason = ban_data["reason"]
        until = ban_data["until"]
        by_admin = ban_data["by"]
        
        if until is not None:
            remaining = until - datetime.now()
            hours = remaining.seconds // 3600
            minutes = (remaining.seconds % 3600) // 60
            time_str = f"{hours} ч. {minutes} мин."
            time_info = f"⏳ Разбан через: {time_str}"
        else:
            time_info = "⏳ Разбан: навсегда"
        
        text = f"""🚫 **YOU BEEN BANNED!**
📝 Причина: {reason}
{time_info}
👤 Забанил: {by_admin}

Если считаешь бан несправедливым, свяжись с главным владельцем."""
        bot.reply_to(message, text, parse_mode="Markdown")
        return True
    return False

def get_new_id():
    global NEXT_ID
    new_id = NEXT_ID
    NEXT_ID += 1
    return new_id

def get_player(user_id):
    user_id = str(user_id)
    if user_id not in players_data:
        players_data[user_id] = {
            "name": "",
            "money": START_MONEY,
            "last_daily": None,
            "used_promos": [],
            "clan": None,
            "level": 1,
            "exp": 0,
            "game_id": get_new_id()
        }
    return players_data[user_id]

def add_exp(user_id, amount):
    player = get_player(user_id)
    player["exp"] += amount
    exp_needed = player["level"] * 100
    if player["exp"] >= exp_needed:
        player["level"] += 1
        player["exp"] -= exp_needed
        player["money"] += player["level"] * 50
        bot.send_message(user_id, f"🎉 Поздравляю! Ты достиг {player['level']} уровня! +{player['level']*50} 💎")

# ===== КНОПКИ / START =====
@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    if check_ban(message):
        return
    player = get_player(user_id)
    if player["name"] == "":
        player["name"] = message.from_user.first_name

    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(
        telebot.types.KeyboardButton("💰 Баланс"),
        telebot.types.KeyboardButton("🎁 Ежедневный бонус"),
        telebot.types.KeyboardButton("👥 Топ игроков"),
        telebot.types.KeyboardButton("⚔️ Ограбить"),
        telebot.types.KeyboardButton("👤 Мой профиль"),
        telebot.types.KeyboardButton("🏰 Кланы"),
        telebot.types.KeyboardButton("👫 Друзья"),
        telebot.types.KeyboardButton("🆔 Мой ID"),
        telebot.types.KeyboardButton("❓ Помощь")
    )

    bot.send_message(message.chat.id,
        f"🎮 Добро пожаловать в игру, {player['name']}!\nУ тебя {player['money']} 💎 кристаллов.\nТвой уровень: {player['level']}\nТвой ID: {player['game_id']}\n\nИспользуй кнопки ниже!",
        reply_markup=markup)

# ===== ПОМОЩЬ =====
@bot.message_handler(func=lambda m: m.text == "❓ Помощь")
@bot.message_handler(commands=['help'])
def help_command(message):
    if check_ban(message):
        return
    text = """📖 **Доступные команды:**

🎮 **Кнопки в меню:**
• 💰 Баланс — узнать свой баланс
• 🎁 Ежедневный бонус — получить бонус раз в день
• 👥 Топ игроков — топ-10 богачей
• ⚔️ Ограбить — попытка украсть у случайного игрока
• 👤 Мой профиль — карточка игрока
• 🏰 Кланы — управление кланами
• 👫 Друзья — список друзей и заявки
• 🆔 Мой ID — узнать свой игровой ID

💬 **Текстовые команды:**
• /promo КОД — активировать промокод
• /mypromos — список использованных промокодов
• /help — эта подсказка
• /addfriend ID — добавить друга
• /removefriend ID — удалить друга
• /myfriends — список друзей
• /id ID — найти игрока по ID

🏰 **Кланы:**
• Создать клан — 500 💎
• Выйти из клана — бесплатно

❓ По вопросам обращаться к администратору!"""
    bot.reply_to(message, text, parse_mode="Markdown")

# ===== ID =====
@bot.message_handler(func=lambda m: m.text == "🆔 Мой ID")
@bot.message_handler(commands=['myid'])
def my_id(message):
    if check_ban(message):
        return
    player = get_player(message.from_user.id)
    bot.reply_to(message, f"🆔 Твой игровой ID: **{player['game_id']}**\n📱 Твой Telegram ID: **{message.from_user.id}**\nИспользуй игровой ID для добавления в друзья!", parse_mode="Markdown")

@bot.message_handler(commands=['id'])
def find_id(message):
    if check_ban(message):
        return
    args = message.text.split()
    if len(args) != 2:
        bot.reply_to(message, "❌ Используй: /id [игровой ID]")
        return
    try:
        search_id = int(args[1])
        found = None
        for uid, data in players_data.items():
            if data.get("game_id") == search_id:
                found = uid
                break
        if found:
            bot.reply_to(message, f"🔍 Игрок с ID {search_id}: {players_data[found]['name']} (TG: {found})")
        else:
            bot.reply_to(message, "❌ Игрок с таким ID не найден!")
    except:
        bot.reply_to(message, "❌ Неверный ID!")

# ===== ДРУЗЬЯ =====
@bot.message_handler(func=lambda m: m.text == "👫 Друзья")
def friends_menu(message):
    if check_ban(message):
        return
    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(
        telebot.types.InlineKeyboardButton("📋 Мои друзья", callback_data="friend_list"),
        telebot.types.InlineKeyboardButton("📨 Входящие заявки", callback_data="friend_requests")
    )
    bot.send_message(message.chat.id, "👫 Управление друзьями:", reply_markup=markup)

@bot.callback_query_handler(func=lambda c: c.data == "friend_list")
def friend_list(call):
    user_id = call.from_user.id
    friends = FRIENDS.get(user_id, [])
    if not friends:
        text = "😔 У тебя пока нет друзей."
    else:
        text = "📋 Твои друзья:\n\n"
        for fid in friends:
            if str(fid) in players_data:
                text += f"• {players_data[str(fid)]['name']} (ID: {players_data[str(fid)]['game_id']}, TG: {fid})\n"
    bot.answer_callback_query(call.id)
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id)
    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(telebot.types.InlineKeyboardButton("🔙 Назад", callback_data="friends_back"))
    bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda c: c.data == "friend_requests")
def friend_requests(call):
    user_id = call.from_user.id
    requests = FRIEND_REQUESTS.get(user_id, [])
    if not requests:
        text = "📭 У тебя нет входящих заявок."
        bot.answer_callback_query(call.id)
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id)
        markup = telebot.types.InlineKeyboardMarkup()
        markup.add(telebot.types.InlineKeyboardButton("🔙 Назад", callback_data="friends_back"))
        bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=markup)
    else:
        text = "📨 Входящие заявки в друзья:\n\n"
        markup = telebot.types.InlineKeyboardMarkup()
        for rid in requests:
            if str(rid) in players_data:
                text += f"• {players_data[str(rid)]['name']} (ID: {players_data[str(rid)]['game_id']}, TG: {rid})\n"
                markup.add(
                    telebot.types.InlineKeyboardButton(f"✅ Принять {players_data[str(rid)]['name']}", callback_data=f"accept_{rid}"),
                    telebot.types.InlineKeyboardButton(f"❌ Отклонить {players_data[str(rid)]['name']}", callback_data=f"decline_{rid}")
                )
        markup.add(telebot.types.InlineKeyboardButton("🔙 Назад", callback_data="friends_back"))
        bot.answer_callback_query(call.id)
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda c: c.data.startswith("accept_"))
def accept_friend(call):
    user_id = call.from_user.id
    friend_id = int(call.data.split("_")[1])
    
    if user_id not in FRIEND_REQUESTS or friend_id not in FRIEND_REQUESTS[user_id]:
        bot.answer_callback_query(call.id, "❌ Заявка уже недействительна!")
        return
    
    FRIEND_REQUESTS[user_id].remove(friend_id)
    if user_id not in FRIENDS:
        FRIENDS[user_id] = []
    if friend_id not in FRIENDS:
        FRIENDS[friend_id] = []
    FRIENDS[user_id].append(friend_id)
    FRIENDS[friend_id].append(user_id)
    
    bot.answer_callback_query(call.id, "✅ Друг добавлен!")
    bot.send_message(friend_id, f"✅ {players_data[str(user_id)]['name']} принял твою заявку в друзья!")
    bot.edit_message_text("✅ Друг добавлен!", call.message.chat.id, call.message.message_id)

@bot.callback_query_handler(func=lambda c: c.data.startswith("decline_"))
def decline_friend(call):
    user_id = call.from_user.id
    friend_id = int(call.data.split("_")[1])
    
    if user_id in FRIEND_REQUESTS and friend_id in FRIEND_REQUESTS[user_id]:
        FRIEND_REQUESTS[user_id].remove(friend_id)
    
    bot.answer_callback_query(call.id, "❌ Заявка отклонена!")
    bot.edit_message_text("❌ Заявка отклонена.", call.message.chat.id, call.message.message_id)

@bot.callback_query_handler(func=lambda c: c.data == "friends_back")
def friends_back(call):
    friends_menu(call.message)
    bot.answer_callback_query(call.id)

@bot.message_handler(commands=['addfriend'])
def add_friend(message):
    if check_ban(message):
        return
    args = message.text.split()
    if len(args) != 2:
        bot.reply_to(message, "❌ Используй: /addfriend [игровой ID]")
        return
    try:
        friend_game_id = int(args[1])
        friend_uid = None
        for uid, data in players_data.items():
            if data.get("game_id") == friend_game_id:
                friend_uid = int(uid)
                break
        
        if not friend_uid:
            bot.reply_to(message, "❌ Игрок с таким ID не найден!")
            return
        if friend_uid == message.from_user.id:
            bot.reply_to(message, "❌ Нельзя добавить самого себя!")
            return
        if friend_uid in FRIENDS.get(message.from_user.id, []):
            bot.reply_to(message, "❌ Этот игрок уже у тебя в друзьях!")
            return
        if message.from_user.id in FRIEND_REQUESTS.get(friend_uid, []):
            bot.reply_to(message, "❌ Ты уже отправил заявку этому игроку!")
            return
        
        if friend_uid not in FRIEND_REQUESTS:
            FRIEND_REQUESTS[friend_uid] = []
        FRIEND_REQUESTS[friend_uid].append(message.from_user.id)
        
        bot.reply_to(message, f"✅ Заявка в друзья отправлена игроку с ID {friend_game_id}!")
        bot.send_message(friend_uid, f"📨 Новый запрос в друзья от {players_data[str(message.from_user.id)]['name']} (ID: {players_data[str(message.from_user.id)]['game_id']}, TG: {message.from_user.id})!\nПроверь раздел 👫 Друзья!")
    except:
        bot.reply_to(message, "❌ Неверный ID!")

@bot.message_handler(commands=['removefriend'])
def remove_friend(message):
    if check_ban(message):
        return
    args = message.text.split()
    if len(args) != 2:
        bot.reply_to(message, "❌ Используй: /removefriend [игровой ID]")
        return
    try:
        friend_game_id = int(args[1])
        friend_uid = None
        for uid, data in players_data.items():
            if data.get("game_id") == friend_game_id:
                friend_uid = int(uid)
                break
        
        if not friend_uid:
            bot.reply_to(message, "❌ Игрок с таким ID не найден!")
            return
        if message.from_user.id in FRIENDS:
            if friend_uid in FRIENDS[message.from_user.id]:
                FRIENDS[message.from_user.id].remove(friend_uid)
                if friend_uid in FRIENDS:
                    FRIENDS[friend_uid].remove(message.from_user.id)
                bot.reply_to(message, f"✅ Игрок с ID {friend_game_id} удалён из друзей!")
            else:
                bot.reply_to(message, "❌ Этот игрок не у тебя в друзьях!")
        else:
            bot.reply_to(message, "❌ У тебя нет друзей!")
    except:
        bot.reply_to(message, "❌ Неверный ID!")

@bot.message_handler(commands=['myfriends'])
def my_friends(message):
    if check_ban(message):
        return
    friends = FRIENDS.get(message.from_user.id, [])
    if not friends:
        bot.reply_to(message, "😔 У тебя пока нет друзей.")
    else:
        text = "📋 Твои друзья:\n\n"
        for fid in friends:
            if str(fid) in players_data:
                text += f"• {players_data[str(fid)]['name']} (ID: {players_data[str(fid)]['game_id']}, TG: {fid}, Ур. {players_data[str(fid)]['level']})\n"
        bot.reply_to(message, text)

# ===== БАЛАНС =====
@bot.message_handler(func=lambda m: m.text == "💰 Баланс")
def balance(message):
    if check_ban(message):
        return
    player = get_player(message.from_user.id)
    bot.reply_to(message, f"У тебя {player['money']} 💎 кристаллов\nУровень: {player['level']}")

# ===== ЕЖЕДНЕВНЫЙ БОНУС =====
@bot.message_handler(func=lambda m: m.text == "🎁 Ежедневный бонус")
def daily(message):
    if check_ban(message):
        return
    user_id = message.from_user.id
    player = get_player(user_id)
    today = datetime.now().strftime("%Y-%m-%d")
    if player["last_daily"] == today:
        bot.reply_to(message, "❌ Ты уже получал бонус сегодня! Приходи завтра.")
        return
    bonus = random.randint(50, 200)
    player["money"] += bonus
    player["last_daily"] = today
    add_exp(user_id, 10)
    bot.reply_to(message, f"🎉 Ты получил {bonus} 💎 кристаллов!\nТеперь у тебя {player['money']} 💎")

# ===== ОГРАБЛЕНИЕ =====
@bot.message_handler(func=lambda m: m.text == "⚔️ Ограбить")
def rob(message):
    if check_ban(message):
        return
    user_id = message.from_user.id
    player = get_player(user_id)
    other_players = [pid for pid in players_data if pid != str(user_id)]
    if not other_players:
        bot.reply_to(message, "❌ Нет других игроков для ограбления!")
        return
    victim_id = random.choice(other_players)
    victim = players_data[victim_id]
    if player["money"] < 50:
        bot.reply_to(message, "❌ Нужно минимум 50 кристаллов для ограбления!")
        return
    if random.random() < 0.6:
        stolen = min(random.randint(20, 100), victim["money"])
        victim["money"] -= stolen
        player["money"] += stolen
        add_exp(user_id, 10)
        bot.reply_to(message, f"✅ Успех! Ты украл {stolen} 💎 у {victim['name']}!")
    else:
        penalty = random.randint(20, 80)
        player["money"] -= penalty
        bot.reply_to(message, f"❌ Провал! Тебя поймали и оштрафовали на {penalty} 💎")

# ===== ТОП ИГРОКОВ =====
@bot.message_handler(func=lambda m: m.text == "👥 Топ игроков")
def top(message):
    if check_ban(message):
        return
    players = [(uid, p["name"], p["money"], p.get("game_id", "?")) for uid, p in players_data.items()]
    players.sort(key=lambda x: x[2], reverse=True)
    text = "🏆 Топ 10 богачей 🏆\n\n"
    for i, (uid, name, money, gid) in enumerate(players[:10], 1):
        text += f"{i}. {name}\n   💎 {money} | 🆔 ID: {gid} | 📱 TG: {uid}\n"
    bot.reply_to(message, text)

# ===== ПРОФИЛЬ =====
@bot.message_handler(func=lambda m: m.text == "👤 Мой профиль")
def profile(message):
    if check_ban(message):
        return
    user_id = message.from_user.id
    player = get_player(user_id)
    clan_name = player.get("clan", "Нет")
    if clan_name in clans_data:
        clan_name = clans_data[clan_name]["name"]
    else:
        clan_name = "Нет"
    friends_count = len(FRIENDS.get(user_id, []))
    text = f"""📇 **Профиль игрока**
━━━━━━━━━━━━━━━━
🆔 ID: {player['game_id']}
📱 TG: {user_id}
👤 Имя: {player['name']}
💰 Кристаллы: {player['money']}
⭐ Уровень: {player['level']}
📊 Опыт: {player['exp']}/{player['level']*100}
👫 Друзей: {friends_count}
🏰 Клан: {clan_name}
🎫 Промокодов: {len(player['used_promos'])}
━━━━━━━━━━━━━━━━"""
    bot.reply_to(message, text, parse_mode="Markdown")

# ===== ПРОМОКОДЫ =====
@bot.message_handler(commands=['promo'])
def use_promo(message):
    if check_ban(message):
        return
    user_id = message.from_user.id
    player = get_player(user_id)
    args = message.text.split()
    if len(args) != 2:
        bot.reply_to(message, "❌ Используй: /promo КОД")
        return
    code = args[1].upper()
    if code not in PROMOCODES:
        bot.reply_to(message, "❌ Такого промокода нет!")
        return
    if code in player["used_promos"]:
        bot.reply_to(message, "❌ Ты уже использовал этот промокод!")
        return
    promo = PROMOCODES[code]
    if promo["uses"] != -1:
        total = sum(1 for p in players_data.values() if code in p["used_promos"])
        if total >= promo["uses"]:
            bot.reply_to(message, f"❌ Промокод {code} закончился!")
            return
    player["money"] += promo["reward"]
    player["used_promos"].append(code)
    bot.reply_to(message, f"🎉 Промокод активирован! +{promo['reward']} 💎\nТеперь у тебя {player['money']} 💎")

@bot.message_handler(commands=['mypromos'])
def my_promos(message):
    if check_ban(message):
        return
    player = get_player(message.from_user.id)
    if not player["used_promos"]:
        bot.reply_to(message, "📭 Ты ещё не использовал промокоды.")
    else:
        text = "🎫 Твои промокоды:\n" + "\n".join(f"• {c}" for c in player["used_promos"])
        bot.reply_to(message, text)

@bot.message_handler(commands=['promostats'])
def promo_stats(message):
    if not is_admin(message.from_user.id):
        return
    stats = {p: 0 for p in PROMOCODES}
    for p in players_data.values():
        for c in p["used_promos"]:
            if c in stats:
                stats[c] += 1
    text = "📊 Статистика промокодов:\n\n" + "\n".join(
        f"{c}: {n}/{PROMOCODES[c]['uses'] if PROMOCODES[c]['uses'] != -1 else '∞'}" for c, n in stats.items()
    )
    bot.reply_to(message, text)

# ===== АДМИН-КОМАНДЫ =====
@bot.message_handler(commands=['adminhelp'])
def admin_help(message):
    if not is_admin(message.from_user.id):
        return
    text = """🔐 **Справка для администраторов**

👑 **Главный владелец (только он):**
/newadmin [ID] — добавить админа
/removeadmin [ID] — убрать админа

💰 **Управление балансом:**
/addmoney [ID] [сумма] — выдать кристаллы
/setmoney [ID] [сумма] — установить баланс

🚫 **Баны:**
/ban [ID] [причина] — забанить навсегда
/bantime [ID] [часы] [причина] — временный бан
/unban [ID] — разбанить

🆔 **Управление ID:**
/changeid [tg_id] [новый_id] — изменить игровой ID

📋 **Информация:**
/info [ID] — инфо об игроке
/stats — статистика бота
/adminlist — список админов
/broadcast [текст] — рассылка

🏰 **Кланы:**
/delclan [название] — удалить клан

❓ /adminhelp — эта справка"""
    bot.reply_to(message, text, parse_mode="Markdown")

@bot.message_handler(commands=['newadmin'])
def new_admin(message):
    if not is_owner(message.from_user.id):
        bot.reply_to(message, "❌ Только главный владелец может добавлять админов!")
        return
    try:
        new_id = int(message.text.split()[1])
        if new_id not in ADMIN_IDS:
            ADMIN_IDS.append(new_id)
            bot.reply_to(message, f"✅ Админ {new_id} добавлен!")
        else:
            bot.reply_to(message, "❌ Уже админ!")
    except:
        bot.reply_to(message, "❌ Используй: /newadmin ID")

@bot.message_handler(commands=['removeadmin'])
def remove_admin(message):
    if not is_owner(message.from_user.id):
        bot.reply_to(message, "❌ Только главный владелец может удалять админов!")
        return
    try:
        rm_id = int(message.text.split()[1])
        if rm_id == OWNER_ID:
            bot.reply_to(message, "❌ Нельзя удалить главного владельца!")
        elif rm_id in ADMIN_IDS:
            ADMIN_IDS.remove(rm_id)
            bot.reply_to(message, f"✅ Админ {rm_id} удалён!")
        else:
            bot.reply_to(message, "❌ Не админ!")
    except:
        bot.reply_to(message, "❌ Используй: /removeadmin ID")

@bot.message_handler(commands=['changeid'])
def change_game_id(message):
    if not is_owner(message.from_user.id):
        bot.reply_to(message, "❌ Только главный владелец может менять ID!")
        return
    try:
        parts = message.text.split()
        if len(parts) != 3:
            bot.reply_to(message, "❌ Используй: /changeid [телеграм ID игрока] [новый игровой ID]")
            return
        tg_id = int(parts[1])
        new_game_id = int(parts[2])
        
        player = get_player(tg_id)
        old_id = player["game_id"]
        
        for uid, data in players_data.items():
            if uid != str(tg_id) and data.get("game_id") == new_game_id:
                bot.reply_to(message, f"❌ Игровой ID {new_game_id} уже занят!")
                return
        
        player["game_id"] = new_game_id
        bot.reply_to(message, f"✅ Игровой ID игрока {tg_id} изменён!\nСтарый ID: {old_id} → Новый ID: {new_game_id}")
        bot.send_message(tg_id, f"🔔 Администратор изменил твой игровой ID!\nСтарый ID: {old_id} → Новый ID: {new_game_id}")
    except:
        bot.reply_to(message, "❌ Используй: /changeid [телеграм ID игрока] [новый игровой ID]")

@bot.message_handler(commands=['addmoney'])
def add_money(message):
    if not is_admin(message.from_user.id):
        return
    try:
        _, uid, amount = message.text.split()
        uid, amount = int(uid), int(amount)
        player = get_player(uid)
        player["money"] += amount
        bot.reply_to(message, f"✅ Игроку {uid} выдано {amount} 💎\nНовый баланс: {player['money']}")
        bot.send_message(uid, f"🎁 Админ выдал тебе {amount} 💎!\nТвой баланс: {player['money']}")
    except:
        bot.reply_to(message, "❌ Используй: /addmoney ID СУММА")

@bot.message_handler(commands=['setmoney'])
def set_money(message):
    if not is_admin(message.from_user.id):
        return
    try:
        _, uid, amount = message.text.split()
        uid, amount = int(uid), int(amount)
        player = get_player(uid)
        player["money"] = amount
        bot.reply_to(message, f"✅ Баланс игрока {uid} установлен на {amount} 💎")
    except:
        bot.reply_to(message, "❌ Используй: /setmoney ID СУММА")

@bot.message_handler(commands=['reset'])
def reset_player(message):
    if not is_admin(message.from_user.id):
        return
    try:
        uid = int(message.text.split()[1])
        players_data.pop(str(uid), None)
        BANNED_USERS.pop(str(uid), None)
        FRIENDS.pop(uid, None)
        for f in FRIENDS.values():
            if uid in f:
                f.remove(uid)
        bot.reply_to(message, f"✅ Игрок {uid} полностью сброшен!")
    except:
        bot.reply_to(message, "❌ Используй: /reset ID")

@bot.message_handler(commands=['ban'])
def ban_user(message):
    if not is_admin(message.from_user.id):
        return
    try:
        parts = message.text.split(maxsplit=2)
        uid = int(parts[1])
        reason = parts[2] if len(parts) > 2 else "Нарушение правил"
        
        if uid == OWNER_ID:
            bot.reply_to(message, "❌ Нельзя забанить главного владельца!")
            return
        if uid in ADMIN_IDS and not is_owner(message.from_user.id):
            bot.reply_to(message, "❌ Только главный владелец может банить админов!")
            return
        
        BANNED_USERS[str(uid)] = {
            "reason": reason,
            "until": None,
            "by": message.from_user.id
        }
        bot.reply_to(message, f"🚫 Игрок {uid} забанен навсегда!\nПричина: {reason}")
        try:
            bot.send_message(uid, f"🚫 Вы были забанены!\nПричина: {reason}\nАдминистратор: {message.from_user.id}")
        except:
            pass
    except:
        bot.reply_to(message, "❌ Используй: /ban ID ПРИЧИНА")

@bot.message_handler(commands=['bantime'])
def ban_time(message):
    if not is_admin(message.from_user.id):
        return
    try:
        parts = message.text.split(maxsplit=3)
        uid = int(parts[1])
        hours = int(parts[2])
        reason = parts[3] if len(parts) > 3 else "Временное нарушение"
        
        if uid == OWNER_ID:
            bot.reply_to(message, "❌ Нельзя забанить главного владельца!")
            return
        
        until = datetime.now() + timedelta(hours=hours)
        BANNED_USERS[str(uid)] = {
            "reason": reason,
            "until": until,
            "by": message.from_user.id
        }
        time_str = f"{hours} ч."
        bot.reply_to(message, f"🚫 Игрок {uid} забанен на {time_str}!\nПричина: {reason}\nРазбан: {until.strftime('%d.%m.%Y %H:%M')}")
        try:
            bot.send_message(uid, f"🚫 Вы забанены на {time_str}!\nПричина: {reason}\nРазбан: {until.strftime('%d.%m.%Y %H:%M')}")
        except:
            pass
    except:
        bot.reply_to(message, "❌ Используй: /bantime ID ЧАСЫ ПРИЧИНА")

@bot.message_handler(commands=['unban'])
def unban_user(message):
    if not is_admin(message.from_user.id):
        return
    try:
        uid = int(message.text.split()[1])
        if str(uid) in BANNED_USERS:
            del BANNED_USERS[str(uid)]
            bot.reply_to(message, f"✅ Игрок {uid} разбанен!")
            try:
                bot.send_message(uid, "✅ Вы были разбанены! Добро пожаловать обратно!")
            except:
                pass
        else:
            bot.reply_to(message, "❌ Этот игрок не в бане!")
    except:
        bot.reply_to(message, "❌ Используй: /unban ID")

@bot.message_handler(commands=['info'])
def player_info(message):
    if not is_admin(message.from_user.id):
        return
    try:
        uid = int(message.text.split()[1])
        player = get_player(uid)
        banned = "🚫 Забанен" if is_banned(uid) else "✅ Активен"
        ban_info = get_ban_info(uid)
        clan = player.get("clan", "Нет")
        friends_count = len(FRIENDS.get(uid, []))
        
        text = f"""📋 **Информация об игроке {uid}**
🆔 Игровой ID: {player['game_id']}
📱 TG: {uid}
👤 Имя: {player['name']}
💰 Баланс: {player['money']} 💎
⭐ Уровень: {player['level']}
📊 Опыт: {player['exp']}/{player['level']*100}
👫 Друзей: {friends_count}
🏰 Клан: {clan}
🎫 Промокодов: {len(player['used_promos'])}
📅 Последний бонус: {player['last_daily']}
🚦 Статус: {banned}"""
        
        if ban_info:
            text += f"\n📝 Причина бана: {ban_info['reason']}"
            if ban_info['until']:
                text += f"\n⏳ Разбан: {ban_info['until'].strftime('%d.%m.%Y %H:%M')}"
            else:
                text += "\n⏳ Бан навсегда"
            text += f"\n👤 Забанил: {ban_info['by']}"
        
        bot.reply_to(message, text, parse_mode="Markdown")
    except:
        bot.reply_to(message, "❌ Используй: /info ID")

@bot.message_handler(commands=['delclan'])
def delete_clan(message):
    if not is_admin(message.from_user.id):
        return
    try:
        name = message.text.split(maxsplit=1)[1]
        if name in clans_data:
            for uid in clans_data[name]["members"]:
                if str(uid) in players_data:
                    players_data[str(uid)]["clan"] = None
            del clans_data[name]
            bot.reply_to(message, f"✅ Клан '{name}' удалён!")
        else:
            bot.reply_to(message, "❌ Клан не найден!")
    except:
        bot.reply_to(message, "❌ Используй: /delclan НАЗВАНИЕ")

@bot.message_handler(commands=['stats'])
def stats(message):
    if not is_admin(message.from_user.id):
        return
    total_players = len(players_data)
    total_clans = len(clans_data)
    total_banned = len([b for b in BANNED_USERS if is_banned(int(b))])
    total_admins = len(ADMIN_IDS)
    text = f"""📊 **Статистика бота**
👥 Игроков: {total_players}
🏰 Кланов: {total_clans}
🚫 Забанено: {total_banned}
👑 Админов: {total_admins}"""
    bot.reply_to(message, text, parse_mode="Markdown")

@bot.message_handler(commands=['broadcast'])
def broadcast(message):
    if not is_admin(message.from_user.id):
        return
    text = message.text.replace('/broadcast', '').strip()
    if not text:
        bot.reply_to(message, "❌ Напиши: /broadcast ТЕКСТ")
        return
    sent = 0
    for uid in list(players_data.keys()):
        try:
            if not is_banned(int(uid)):
                bot.send_message(int(uid), f"📢 Сообщение от администратора:\n\n{text}")
                sent += 1
        except:
            pass
    bot.reply_to(message, f"✅ Рассылка отправлена {sent} игрокам!")

@bot.message_handler(commands=['adminlist'])
def admin_list(message):
    if not is_admin(message.from_user.id):
        return
    text = "👑 Список админов:\n" + "\n".join(
        f"• {aid} {'(главный)' if aid == OWNER_ID else ''}" for aid in ADMIN_IDS
    )
    bot.reply_to(message, text)

# ===== КЛАНЫ =====
@bot.message_handler(func=lambda m: m.text == "🏰 Кланы")
def clans_menu(message):
    if check_ban(message):
        return
    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(
        telebot.types.InlineKeyboardButton("📋 Список кланов", callback_data="clan_list"),
        telebot.types.InlineKeyboardButton("➕ Создать клан", callback_data="clan_create"),
        telebot.types.InlineKeyboardButton("🚪 Выйти из клана", callback_data="clan_leave")
    )
    bot.send_message(message.chat.id, "🏰 Управление кланами:", reply_markup=markup)

@bot.callback_query_handler(func=lambda c: c.data == "clan_list")
def clan_list(call):
    if not clans_data:
        bot.answer_callback_query(call.id, "Кланов пока нет!")
        return
    text = "📋 Список кланов:\n\n" + "\n".join(
        f"🏰 {d['name']}\n👥 {len(d['members'])} участников\n💰 Казна: {d['money']}\n" for d in clans_data.values()
    )
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id)

@bot.callback_query_handler(func=lambda c: c.data == "clan_create")
def clan_create(call):
    bot.answer_callback_query(call.id)
    msg = bot.send_message(call.message.chat.id, "Введите название клана:")
    bot.register_next_step_handler(msg, process_clan_create)

def process_clan_create(message):
    user_id = message.from_user.id
    player = get_player(user_id)
    name = message.text.strip()[:20]
    if name in clans_data:
        bot.reply_to(message, "❌ Такой клан уже есть!")
        return
    if player["money"] < 500:
        bot.reply_to(message, "❌ Нужно 500 💎!")
        return
    player["money"] -= 500
    player["clan"] = name
    clans_data[name] = {"name": name, "owner": user_id, "members": [user_id], "money": 0}
    bot.reply_to(message, f"✅ Клан '{name}' создан! (-500 💎)")

@bot.callback_query_handler(func=lambda c: c.data == "clan_leave")
def clan_leave(call):
    user_id = call.from_user.id
    player = get_player(user_id)
    name = player.get("clan")
    if not name or name not in clans_data:
        bot.answer_callback_query(call.id, "Ты не в клане!")
        return
    clans_data[name]["members"].remove(user_id)
    if not clans_data[name]["members"]:
        del clans_data[name]
    player["clan"] = None
    bot.answer_callback_query(call.id, "Ты покинул клан!")
    bot.edit_message_text("🚪 Ты вышел из клана.", call.message.chat.id, call.message.message_id)

# ===== ЗАПУСК =====
print("🎮 Бот запущен!")
if __name__ == '__main__':
    bot.infinity_polling()