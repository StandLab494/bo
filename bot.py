import telebot
import json
import os
import random
from datetime import datetime, timedelta

# ===== НАСТРОЙКИ =====
TOKEN = "8906578550:AAGV7toADTAkBOw6aufuhV_PQbbnmzEuxrQ"
ADMIN_ID = 8558737152
START_MONEY = 100

# ===== ПРОМОКОДЫ =====
PROMOCODES = {
    "START100": {"reward": 100, "uses": -1, "description": "100 кристаллов новичку"},
    "LUCKY2024": {"reward": 250, "uses": 50, "description": "+250 кристаллов"},
    "SUPERGAME": {"reward": 500, "uses": 20, "description": "+500 кристаллов"},
    "DAILYBONUS": {"reward": 198292738378373838, "uses": -1, "description": "+50 кристаллов"},
    "TOPPLAYER": {"reward": 1000, "uses": 5, "description": "+1000 кристаллов для топов"}
}

bot = telebot.TeleBot(TOKEN)
DATA_FILE = "players.json"
CLANS_FILE = "clans.json"

# ===== ЗАГРУЗКА/СОХРАНЕНИЕ =====
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def load_clans():
    if os.path.exists(CLANS_FILE):
        with open(CLANS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_clans(data):
    with open(CLANS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def get_player(user_id):
    data = load_data()
    user_id = str(user_id)
    if user_id not in data:
        data[user_id] = {
            "name": "",
            "money": START_MONEY,
            "last_daily": None,
            "used_promos": [],
            "clan": None,
            "level": 1,
            "exp": 0
        }
        save_data(data)
    return data[user_id], data

def save_player(user_id, player_data, all_data):
    all_data[str(user_id)] = player_data
    save_data(all_data)

def add_exp(user_id, amount):
    player, all_data = get_player(user_id)
    player["exp"] += amount
    exp_needed = player["level"] * 100
    if player["exp"] >= exp_needed:
        player["level"] += 1
        player["exp"] -= exp_needed
        player["money"] += player["level"] * 50
        bot.send_message(user_id, f"🎉 Поздравляю! Ты достиг {player['level']} уровня! +{player['level']*50} 💎")
    save_player(user_id, player, all_data)

# ===== КНОПКИ / START =====
@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    player, all_data = get_player(user_id)

    if player["name"] == "":
        player["name"] = message.from_user.first_name
        save_player(user_id, player, all_data)

    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn1 = telebot.types.KeyboardButton("💰 Баланс")
    btn2 = telebot.types.KeyboardButton("🎁 Ежедневный бонус")
    btn3 = telebot.types.KeyboardButton("👥 Топ игроков")
    btn4 = telebot.types.KeyboardButton("⚔️ Ограбить")
    btn5 = telebot.types.KeyboardButton("👤 Мой профиль")
    btn6 = telebot.types.KeyboardButton("🏰 Кланы")
    markup.add(btn1, btn2, btn3, btn4, btn5, btn6)

    bot.send_message(message.chat.id,
        f"🎮 Добро пожаловать в игру, {player['name']}!\nУ тебя {player['money']} 💎 кристаллов.\nТвой уровень: {player['level']}\n\nИспользуй кнопки ниже!",
        reply_markup=markup)

# ===== ОСНОВНЫЕ ФУНКЦИИ =====
@bot.message_handler(func=lambda message: message.text == "💰 Баланс")
def balance(message):
    user_id = message.from_user.id
    player, _ = get_player(user_id)
    bot.reply_to(message, f"У тебя {player['money']} 💎 кристаллов\nУровень: {player['level']}")

@bot.message_handler(func=lambda message: message.text == "🎁 Ежедневный бонус")
def daily(message):
    user_id = message.from_user.id
    player, all_data = get_player(user_id)
    today = datetime.now().strftime("%Y-%m-%d")
    if player["last_daily"] == today:
        bot.reply_to(message, "❌ Ты уже получал бонус сегодня! Приходи завтра.")
        return
    bonus = random.randint(50, 200)
    player["money"] += bonus
    player["last_daily"] = today
    save_player(user_id, player, all_data)
    add_exp(user_id, 10)
    bot.reply_to(message, f"🎉 Ты получил {bonus} 💎 кристаллов!\nТеперь у тебя {player['money']} 💎")

@bot.message_handler(func=lambda message: message.text == "⚔️ Ограбить")
def rob(message):
    user_id = message.from_user.id
    player, all_data = get_player(user_id)
    other_players = [pid for pid in all_data if pid != str(user_id)]
    if not other_players:
        bot.reply_to(message, "❌ Нет других игроков для ограбления!")
        return
    victim_id = random.choice(other_players)
    victim = all_data[victim_id]
    if player["money"] < 50:
        bot.reply_to(message, "❌ Нужно минимум 50 кристаллов для ограбления!")
        return
    success = random.random() < 0.6
    if success:
        stolen = random.randint(20, 100)
        stolen = min(stolen, victim["money"])
        victim["money"] -= stolen
        player["money"] += stolen
        save_player(victim_id, victim, all_data)
        save_player(user_id, player, all_data)
        add_exp(user_id, 10)
        bot.reply_to(message, f"✅ Успех! Ты украл {stolen} 💎 у {victim['name']}!")
    else:
        penalty = random.randint(20, 80)
        player["money"] -= penalty
        save_player(user_id, player, all_data)
        bot.reply_to(message, f"❌ Провал! Тебя поймали и оштрафовали на {penalty} 💎")

@bot.message_handler(func=lambda message: message.text == "👥 Топ игроков")
def top(message):
    all_data = load_data()
    players = []
    for pid, pdata in all_data.items():
        players.append((pdata["name"], pdata["money"]))
    players.sort(key=lambda x: x[1], reverse=True)
    top10 = players[:10]
    text = "🏆 Топ 10 богачей 🏆\n\n"
    for i, (name, money) in enumerate(top10, 1):
        text += f"{i}. {name} — {money} 💎\n"
    bot.reply_to(message, text)

@bot.message_handler(func=lambda message: message.text == "👤 Мой профиль")
def profile(message):
    user_id = message.from_user.id
    player, _ = get_player(user_id)
    clan_name = player.get("clan", "Нет клана")
    if clan_name:
        clans = load_clans()
        if clan_name in clans:
            clan_name = clans[clan_name]["name"]
    text = f"""📇 **Профиль игрока**
━━━━━━━━━━━━━━━━
👤 Имя: {player['name']}
💰 Кристаллы: {player['money']}
⭐ Уровень: {player['level']}
📊 Опыт: {player['exp']}/{player['level']*100}
🏰 Клан: {clan_name if clan_name else 'Нет'}
🎫 Промокодов: {len(player['used_promos'])}
━━━━━━━━━━━━━━━━"""
    bot.reply_to(message, text, parse_mode="Markdown")

# ===== ПРОМОКОДЫ =====
@bot.message_handler(commands=['promo'])
def use_promo(message):
    user_id = message.from_user.id
    player, all_data = get_player(user_id)
    args = message.text.split()
    if len(args) != 2:
        bot.reply_to(message, "❌ Используй: /promo КОД")
        return
    promo_code = args[1].upper()
    if promo_code not in PROMOCODES:
        bot.reply_to(message, "❌ Такого промокода не существует!")
        return
    if promo_code in player["used_promos"]:
        bot.reply_to(message, "❌ Ты уже использовал этот промокод!")
        return
    promo = PROMOCODES[promo_code]
    if promo["uses"] != -1:
        total_uses = sum(1 for p in all_data.values() if promo_code in p.get("used_promos", []))
        if total_uses >= promo["uses"]:
            bot.reply_to(message, f"❌ Промокод {promo_code} больше не действует!")
            return
    reward = promo["reward"]
    player["money"] += reward
    player["used_promos"].append(promo_code)
    save_player(user_id, player, all_data)
    bot.reply_to(message, f"🎉 Промокод активирован!\nПолучено: +{reward} 💎\n\nТеперь у тебя {player['money']} 💎")

@bot.message_handler(commands=['mypromos'])
def my_promos(message):
    user_id = message.from_user.id
    player, _ = get_player(user_id)
    used = player["used_promos"]
    if not used:
        bot.reply_to(message, "📭 Ты ещё не использовал ни одного промокода.")
        return
    text = "🎫 Твои активированные промокоды:\n\n"
    for code in used:
        promo = PROMOCODES.get(code, {})
        desc = promo.get("description", "Неизвестный промокод")
        text += f"• {code} — {desc}\n"
    bot.reply_to(message, text)

@bot.message_handler(commands=['promostats'])
def promo_stats(message):
    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "❌ Только для админа!")
        return
    all_data = load_data()
    stats = {promo: 0 for promo in PROMOCODES}
    for player in all_data.values():
        for code in player.get("used_promos", []):
            if code in stats:
                stats[code] += 1
    text = "📊 Статистика промокодов:\n\n"
    for code, count in stats.items():
        info = PROMOCODES[code]
        limit = "∞" if info["uses"] == -1 else info["uses"]
        text += f"{code}: {count}/{limit} использований\n"
    bot.reply_to(message, text)

# ===== КЛАНЫ =====
@bot.message_handler(func=lambda message: message.text == "🏰 Кланы")
def clans_menu(message):
    markup = telebot.types.InlineKeyboardMarkup()
    btn1 = telebot.types.InlineKeyboardButton("📋 Список кланов", callback_data="clan_list")
    btn2 = telebot.types.InlineKeyboardButton("➕ Создать клан", callback_data="clan_create")
    btn3 = telebot.types.InlineKeyboardButton("🚪 Выйти из клана", callback_data="clan_leave")
    markup.add(btn1, btn2, btn3)
    bot.send_message(message.chat.id, "🏰 Управление кланами:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "clan_list")
def clan_list(call):
    clans = load_clans()
    if not clans:
        bot.answer_callback_query(call.id, "Кланов пока нет!")
        return
    text = "📋 Список кланов:\n\n"
    for name, data in clans.items():
        text += f"🏰 {data['name']}\n👥 Участников: {len(data['members'])}\n💰 Казна: {data['money']}\n\n"
    bot.edit_message_text(text, call.message.chat.id, call.message.message_id)

@bot.callback_query_handler(func=lambda call: call.data == "clan_create")
def clan_create(call):
    bot.answer_callback_query(call.id)
    msg = bot.send_message(call.message.chat.id, "Введите название клана (до 20 символов):")
    bot.register_next_step_handler(msg, process_clan_create)

def process_clan_create(message):
    user_id = message.from_user.id
    player, all_data = get_player(user_id)
    clan_name = message.text.strip()[:20]
    clans = load_clans()
    if clan_name in clans:
        bot.reply_to(message, "❌ Клан с таким названием уже существует!")
        return
    if player["money"] < 500:
        bot.reply_to(message, "❌ Для создания клана нужно 500 💎!")
        return
    player["money"] -= 500
    player["clan"] = clan_name
    save_player(user_id, player, all_data)
    clans[clan_name] = {
        "name": clan_name,
        "owner": user_id,
        "members": [user_id],
        "money": 0
    }
    save_clans(clans)
    bot.reply_to(message, f"✅ Клан '{clan_name}' создан! Ты потратил 500 💎.")

@bot.callback_query_handler(func=lambda call: call.data == "clan_leave")
def clan_leave(call):
    user_id = call.from_user.id
    player, all_data = get_player(user_id)
    clan_name = player.get("clan")
    if not clan_name:
        bot.answer_callback_query(call.id, "Ты не состоишь в клане!")
        return
    clans = load_clans()
    if clan_name in clans:
        clans[clan_name]["members"].remove(user_id)
        if not clans[clan_name]["members"]:
            del clans[clan_name]
        else:
            save_clans(clans)
    player["clan"] = None
    save_player(user_id, player, all_data)
    bot.answer_callback_query(call.id, "Ты покинул клан!")
    bot.edit_message_text("🚪 Ты вышел из клана.", call.message.chat.id, call.message.message_id)

# ===== ЗАПУСК =====
print("🎮 Игровой бот запущен!")
if __name__ == '__main__':
    bot.infinity_polling()