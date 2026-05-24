import telebot
import json
import os
import random
import time
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
QUESTS_FILE = "quests.json"

# ===== ЗАГЛУШКА ДЛЯ SOON =====
def soon_reply(message):
    bot.reply_to(message, "⏳ Эта функция скоро появится... (Soon)")

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

def load_quests():
    if os.path.exists(QUESTS_FILE):
        with open(QUESTS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_quests(data):
    with open(QUESTS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def get_player(user_id):
    data = load_data()
    user_id = str(user_id)
    if user_id not in data:
        data[user_id] = {
            "name": "",
            "money": START_MONEY,
            "items": [],
            "last_daily": None,
            "last_work": None,
            "used_promos": [],
            "clan": None,
            "level": 1,
            "exp": 0,
            "quests_completed": 0,
            "last_quest_reset": None
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
    player, _ = get_player(user_id)
    
    if player["name"] == "":
        player["name"] = message.from_user.first_name
        save_player(user_id, player, _)
    
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn1 = telebot.types.KeyboardButton("💰 Баланс")
    btn2 = telebot.types.KeyboardButton("🎁 Ежедневный бонус")
    btn3 = telebot.types.KeyboardButton("🛒 Магазин")
    btn4 = telebot.types.KeyboardButton("👥 Топ игроков")
    btn5 = telebot.types.KeyboardButton("💼 Работа")
    btn6 = telebot.types.KeyboardButton("⚔️ Ограбить")
    btn7 = telebot.types.KeyboardButton("👤 Мой профиль")
    btn8 = telebot.types.KeyboardButton("🏰 Кланы")
    btn9 = telebot.types.KeyboardButton("📜 Квесты")
    btn10 = telebot.types.KeyboardButton("🎰 Казино")
    markup.add(btn1, btn2, btn3, btn4, btn5, btn6, btn7, btn8, btn9, btn10)
    
    bot.send_message(message.chat.id, 
        f"🎮 Добро пожаловать в игру, {player['name']}!\nУ тебя {player['money']} 💎 кристаллов.\nТвой уровень: {player['level']}\n\nИспользуй кнопки ниже!",
        reply_markup=markup)

# ===== СТАРЫЕ ФУНКЦИИ (Баланс, бонус, работа, грабёж, магазин, топ) =====
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

@bot.message_handler(func=lambda message: message.text == "💼 Работа")
def work(message):
    user_id = message.from_user.id
    player, all_data = get_player(user_id)
    last_work = player.get("last_work")
    if last_work:
        last_time = datetime.fromisoformat(last_work)
        if datetime.now() - last_time < timedelta(minutes=30):
            remaining = int(30 - (datetime.now() - last_time).seconds / 60)
            bot.reply_to(message, f"⌛ Ты устал! Отдохни {remaining} минут.")
            return
    earnings = random.randint(30, 150)
    player["money"] += earnings
    player["last_work"] = datetime.now().isoformat()
    save_player(user_id, player, all_data)
    add_exp(user_id, 5)
    jobs = ["код писал", "кирпичи таскал", "игроков учил", "баги фиксил", "кофе варил"]
    job = random.choice(jobs)
    bot.reply_to(message, f"💪 Ты {job} и заработал {earnings} 💎!\nТеперь у тебя {player['money']} 💎")

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

@bot.message_handler(func=lambda message: message.text == "🛒 Магазин")
def shop(message):
    markup = telebot.types.InlineKeyboardMarkup()
    btn1 = telebot.types.InlineKeyboardButton("🍕 Пицца (50💎)", callback_data="buy_pizza")
    btn2 = telebot.types.InlineKeyboardButton("🎣 Удочка (150💎)", callback_data="buy_rod")
    btn3 = telebot.types.InlineKeyboardButton("🐉 Дракон (500💎)", callback_data="buy_dragon")
    btn4 = telebot.types.InlineKeyboardButton("📦 Список покупок", callback_data="my_items")
    markup.add(btn1, btn2, btn3, btn4)
    bot.send_message(message.chat.id, "🛍️ Добро пожаловать в магазин!", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("buy_"))
def buy_item(call):
    user_id = call.from_user.id
    player, all_data = get_player(user_id)
    items = {
        "pizza": {"name": "🍕 Пицца", "price": 50},
        "rod": {"name": "🎣 Удочка", "price": 150},
        "dragon": {"name": "🐉 Дракон", "price": 500}
    }
    item_key = call.data.split("_")[1]
    item = items[item_key]
    if player["money"] >= item["price"]:
        player["money"] -= item["price"]
        player["items"].append(item["name"])
        save_player(user_id, player, all_data)
        bot.answer_callback_query(call.id, f"✅ Куплено: {item['name']}!")
        bot.edit_message_text(f"🎉 Ты купил {item['name']}!\nОсталось {player['money']} 💎", 
                               call.message.chat.id, call.message.message_id)
    else:
        bot.answer_callback_query(call.id, "❌ Не хватает кристаллов!")

@bot.callback_query_handler(func=lambda call: call.data == "my_items")
def my_items(call):
    user_id = call.from_user.id
    player, _ = get_player(user_id)
    if not player["items"]:
        text = "📦 У тебя пока нет предметов. Купи что-нибудь в магазине!"
    else:
        text = "📦 Твои предметы:\n" + "\n".join(f"• {item}" for item in player["items"])
    bot.answer_callback_query(call.id)
    bot.send_message(call.message.chat.id, text)

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

# ===== НОВЫЕ ФУНКЦИИ =====
# 1. ПРОФИЛЬ (КАРТОЧКА)
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
🎒 Предметов: {len(player['items'])}
🏰 Клан: {clan_name if clan_name else 'Нет'}
🎫 Промокодов: {len(player['used_promos'])}
━━━━━━━━━━━━━━━━"""
    bot.reply_to(message, text, parse_mode="Markdown")

# 2. КЛАНОВЫ
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
    player, _ = get_player(user_id)
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
    save_player(user_id, player, _)
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
    player, _ = get_player(user_id)
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
    save_player(user_id, player, _)
    bot.answer_callback_query(call.id, "Ты покинул клан!")
    bot.edit_message_text("🚪 Ты вышел из клана.", call.message.chat.id, call.message.message_id)

# 3. КВЕСТЫ
@bot.message_handler(func=lambda message: message.text == "📜 Квесты")
def quests_menu(message):
    user_id = message.from_user.id
    player, _ = get_player(user_id)
    today = datetime.now().strftime("%Y-%m-%d")
    quests = load_quests()
    if user_id not in quests or quests[user_id].get("date") != today:
        quests[user_id] = {
            "date": today,
            "quests": [
                {"name": "💰 Заработай 200 монет", "progress": 0, "target": 200, "reward": 100, "done": False},
                {"name": "💼 Сработай 3 раза", "progress": 0, "target": 3, "reward": 150, "done": False},
                {"name": "⚔️ Ограбь 2 раза", "progress": 0, "target": 2, "reward": 120, "done": False}
            ]
        }
        save_quests(quests)
    user_quests = quests[user_id]["quests"]
    text = "📜 Ежедневные квесты:\n\n"
    for i, q in enumerate(user_quests, 1):
        status = "✅" if q["done"] else f"{q['progress']}/{q['target']}"
        text += f"{i}. {q['name']}\n   {status} | Награда: {q['reward']}💎\n\n"
    markup = telebot.types.InlineKeyboardMarkup()
    for i in range(len(user_quests)):
        if not user_quests[i]["done"]:
            btn = telebot.types.InlineKeyboardButton(f"Забрать награду {i+1}", callback_data=f"quest_{i}")
            markup.add(btn)
    bot.send_message(message.chat.id, text, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("quest_"))
def claim_quest(call):
    user_id = call.from_user.id
    quests = load_quests()
    today = datetime.now().strftime("%Y-%m-%d")
    if user_id not in quests or quests[user_id].get("date") != today:
        bot.answer_callback_query(call.id, "Квесты уже обновились!")
        return
    idx = int(call.data.split("_")[1])
    q = quests[user_id]["quests"][idx]
    if q["done"]:
        bot.answer_callback_query(call.id, "Ты уже получил награду!")
        return
    if q["progress"] >= q["target"]:
        q["done"] = True
        player, all_data = get_player(user_id)
        player["money"] += q["reward"]
        save_player(user_id, player, all_data)
        save_quests(quests)
        bot.answer_callback_query(call.id, f"✅ Получено {q['reward']} 💎!")
        bot.edit_message_text("Награда зачислена!", call.message.chat.id, call.message.message_id)
    else:
        bot.answer_callback_query(call.id, "Квест ещё не выполнен!")

# Обновление прогресса квестов
def update_quest_progress(user_id, quest_name, amount=1):
    quests = load_quests()
    today = datetime.now().strftime("%Y-%m-%d")
    if user_id not in quests or quests[user_id].get("date") != today:
        return
    for q in quests[user_id]["quests"]:
        if quest_name in q["name"] and not q["done"]:
            q["progress"] += amount
    save_quests(quests)

# ВСТАВИТЬ В ФУНКЦИИ work и rob:
# work: update_quest_progress(user_id, "Сработай", 1)
# rob: update_quest_progress(user_id, "Ограбь", 1)
# daily: update_quest_progress(user_id, "Заработай", bonus) - если хотите

# 4. КАЗИНО
@bot.message_handler(func=lambda message: message.text == "🎰 Казино")
def casino(message):
    markup = telebot.types.InlineKeyboardMarkup()
    btn1 = telebot.types.InlineKeyboardButton("🎲 Угадай число (1-6)", callback_data="casino_number")
    btn2 = telebot.types.InlineKeyboardButton("🎨 Ставка на цвет", callback_data="casino_color")
    markup.add(btn1, btn2)
    bot.send_message(message.chat.id, "🎰 Выбери игру:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "casino_number")
def casino_number(call):
    msg = bot.send_message(call.message.chat.id, "Введи число от 1 до 6 и сумму ставки:\nПример: `3 100`", parse_mode="Markdown")
    bot.register_next_step_handler(msg, process_casino_number)

def process_casino_number(message):
    try:
        guess, bet = map(int, message.text.split())
        if guess < 1 or guess > 6 or bet < 10:
            bot.reply_to(message, "❌ Число от 1 до 6, ставка минимум 10 💎")
            return
        user_id = message.from_user.id
        player, all_data = get_player(user_id)
        if bet > player["money"]:
            bot.reply_to(message, "❌ Не хватает кристаллов!")
            return
        result = random.randint(1, 6)
        player["money"] -= bet
        if guess == result:
            win = bet * 3
            player["money"] += win
            bot.reply_to(message, f"🎉 Выпало {result}! Ты угадал! +{win} 💎")
            add_exp(user_id, 15)
        else:
            bot.reply_to(message, f"😢 Выпало {result}. Ты проиграл {bet} 💎")
        save_player(user_id, player, all_data)
    except:
        bot.reply_to(message, "❌ Неправильный формат! Пример: `3 100`")

@bot.callback_query_handler(func=lambda call: call.data == "casino_color")
def casino_color(call):
    markup = telebot.types.InlineKeyboardMarkup()
    btn1 = telebot.types.InlineKeyboardButton("🔴 Красное", callback_data="color_red")
    btn2 = telebot.types.InlineKeyboardButton("⚫ Чёрное", callback_data="color_black")
    markup.add(btn1, btn2)
    msg = bot.send_message(call.message.chat.id, "Выбери цвет и напиши сумму ставки (числом):", reply_markup=markup)
    bot.register_next_step_handler(msg, process_casino_color)

def process_casino_color(message):
    try:
        bet = int(message.text)
        if bet < 10:
            bot.reply_to(message, "❌ Ставка минимум 10 💎")
            return
        user_id = message.from_user.id
        player, all_data = get_player(user_id)
        if bet > player["money"]:
            bot.reply_to(message, "❌ Не хватает кристаллов!")
            return
        # Ждём цвет
        bot.register_next_step_handler(message, lambda m: finish_color_bet(m, bet))
    except:
        bot.reply_to(message, "❌ Введи число (сумму ставки)")

def finish_color_bet(message, bet):
    color = message.text.lower()
    if color not in ["красное", "чёрное", "красный", "черный"]:
        bot.reply_to(message, "❌ Напиши 'Красное' или 'Чёрное'")
        return
    user_id = message.from_user.id
    player, all_data = get_player(user_id)
    result = random.choice(["красное", "чёрное"])
    player["money"] -= bet
    if (color in ["красное", "красный"] and result == "красное") or (color in ["чёрное", "черный"] and result == "чёрное"):
        win = bet * 2
        player["money"] += win
        bot.reply_to(message, f"🎉 Выпало {result}! Ты выиграл {win} 💎")
        add_exp(user_id, 10)
    else:
        bot.reply_to(message, f"😢 Выпало {result}. Ты проиграл {bet} 💎")
    save_player(user_id, player, all_data)

# ===== SOON =====
@bot.message_handler(func=lambda message: message.text in ["🐉 Питомцы", "⛏️ Шахта", "💰 Инвестиции", "🔫 Криминал", "👑 Гильдии", "🤝 Передать валюту", "🎁 Рефералы", "🏅 Достижения", "📈 Бизнес"])
def soon(message):
    soon_reply(message)

# ===== ЗАПУСК =====
print("🎮 Игровой бот запущен с новыми функциями!")
bot.infinity_polling()