import telebot
import random
from datetime import datetime, timedelta

# ===== НАСТРОЙКИ =====
TOKEN = "8939220569:AAHLTwkf9rD7Gf22EK9CBqtgg2Q19v1LomI"
OWNER_ID = 8558737152
ADMIN_IDS = [8558737152]
START_MONEY = 5000000  # 5 миллионов стартового капитала
START_ROAD = 5  # 5 метров дороги бесплатно

# ===== ПРОМОКОДЫ =====
PROMOCODES = {
    "START100": {"reward": 100000, "uses": -1, "description": "100.000$ новичку"},
    "LUCKY2024": {"reward": 250000, "uses": 50, "description": "+250.000$"},
    "SUPERGAME": {"reward": 500000, "uses": 20, "description": "+500.000$"},
    "DAILYBONUS": {"reward": 50000, "uses": -1, "description": "+50.000$"},
    "TOPPLAYER": {"reward": 1000000, "uses": 5, "description": "+1.000.000$"},
    "CITYMASTER": {"reward": 2000000, "uses": 10, "description": "+2.000.000$ для мэров"},
    "ROADKING": {"reward": 500000, "uses": -1, "description": "+500.000$ на дороги"},
}

# ===== ЗДАНИЯ =====
BUILDINGS = {
    "house": {"name": "🏠 Дом", "price": 50000, "income": 50, "population": 10, "joy": 1},
    "shop": {"name": "🏪 Магазин", "price": 100000, "income": 200, "population": 0, "joy": 2},
    "power": {"name": "⚡ Электростанция", "price": 200000, "income": 0, "population": 0, "joy": 0, "energy": 50},
    "factory": {"name": "🏭 Завод", "price": 150000, "income": 500, "population": 0, "joy": -5, "energy_cost": 10},
    "park": {"name": "🌳 Парк", "price": 75000, "income": 10, "population": 0, "joy": 10},
    "bank": {"name": "🏦 Банк", "price": 500000, "income": 1000, "population": 0, "joy": 5},
    "cosmo": {"name": "🚀 Космоцентр", "price": 1000000, "income": 2000, "population": 0, "joy": 50},
}

# ===== ДОРОГА (ЦЕНЫ ЗА ПАКЕТЫ МЕТРОВ) =====
ROAD_PACKS = [
    {"meters": 5, "price": 5000},
    {"meters": 10, "price": 13000},
    {"meters": 30, "price": 50000},
    {"meters": 100, "price": 100000},
]

bot = telebot.TeleBot(TOKEN)
players_data = {}
clans_data = {}
BANNED_USERS = {}
FRIENDS = {}
FRIEND_REQUESTS = {}
NEXT_ID = 1000000

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

def check_ban(message):
    if is_banned(message.from_user.id):
        ban_data = BANNED_USERS.get(str(message.from_user.id))
        if ban_data:
            reason = ban_data["reason"]
            until = ban_data["until"]
            if until:
                remaining = until - datetime.now()
                hours = remaining.seconds // 3600
                minutes = (remaining.seconds % 3600) // 60
                time_info = f"⏳ Разбан через: {hours} ч. {minutes} мин."
            else:
                time_info = "⏳ Разбан: навсегда"
            text = f"""🚫 **YOU BEEN BANNED!**
📝 Причина: {reason}
{time_info}
👤 Забанил: {ban_data['by']}

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
            "road": START_ROAD,
            "used_road": 0,
            "buildings": {},  # {"house": 0, "shop": 0, ...}
            "income": 0,
            "population": 0,
            "joy": 0,
            "energy": 0,
            "energy_used": 0,
            "last_daily": None,
            "used_promos": [],
            "clan": None,
            "level": 1,
            "exp": 0,
            "game_id": get_new_id()
        }
    return players_data[user_id]

def get_main_keyboard():
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(
        telebot.types.KeyboardButton("🏙️ Мой город"),
        telebot.types.KeyboardButton("🏗️ Постройки"),
        telebot.types.KeyboardButton("🛣️ Дорога"),
        telebot.types.KeyboardButton("📦 Кейсы"),
    )
    markup.add(
        telebot.types.KeyboardButton("🎁 Бонус"),
        telebot.types.KeyboardButton("👥 Топ городов"),
        telebot.types.KeyboardButton("🏰 Кланы"),
        telebot.types.KeyboardButton("👫 Друзья"),
    )
    markup.add(
        telebot.types.KeyboardButton("👤 Профиль"),
        telebot.types.KeyboardButton("🆔 Мой ID"),
        telebot.types.KeyboardButton("❓ Помощь"),
    )
    return markup

# ===== КНОПКИ / START =====
@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    if check_ban(message):
        return
    player = get_player(user_id)
    if player["name"] == "":
        player["name"] = message.from_user.first_name

    bot.send_message(message.chat.id,
        f"🏙️ Добро пожаловать в город, мэр {player['name']}!\n\n"
        f"💰 Баланс: {player['money']:,}$\n"
        f"🛣️ Дороги: {player['used_road']}/{player['road']}м\n"
        f"👥 Население: {player['population']}\n"
        f"😊 Радость: {player['joy']}\n"
        f"🆔 ID: {player['game_id']}\n\n"
        f"Используй кнопки для управления!",
        reply_markup=get_main_keyboard())

# ===== ОБНОВЛЕНИЕ =====
@bot.message_handler(commands=['update'])
def update_keyboard(message):
    if check_ban(message):
        return
    bot.send_message(message.chat.id, "✅ Кнопки обновлены!", reply_markup=get_main_keyboard())

# ===== МОЙ ГОРОД =====
@bot.message_handler(func=lambda m: m.text == "🏙️ Мой город")
def my_city(message):
    if check_ban(message):
        return
    player = get_player(message.from_user.id)
    
    # Пересчитываем доход, население, энергию
    income = 0
    population = 0
    joy = 0
    energy = 0
    energy_used = 0
    
    for bkey, bdata in BUILDINGS.items():
        count = player["buildings"].get(bkey, 0)
        if count > 0:
            income += bdata.get("income", 0) * count
            population += bdata.get("population", 0) * count
            joy += bdata.get("joy", 0) * count
            if "energy" in bdata:
                energy += bdata["energy"] * count
            if "energy_cost" in bdata:
                energy_used += bdata["energy_cost"] * count
    
    player["income"] = income
    player["population"] = population
    player["joy"] = joy
    player["energy"] = energy
    player["energy_used"] = energy_used
    
    text = f"""🏙️ **Город {player['name']}**

💰 Баланс: {player['money']:,}$
📈 Доход: {income}$/ч
🛣️ Дороги: {player['used_road']}/{player['road']}м
👥 Население: {population}
😊 Радость: {joy}
⚡ Энергия: {energy} (исп. {energy_used})

🏗️ **Постройки:**
"""
    for bkey, bdata in BUILDINGS.items():
        count = player["buildings"].get(bkey, 0)
        if count > 0:
            text += f"  {bdata['name']}: {count} шт.\n"
    
    if all(v == 0 for v in player["buildings"].values()):
        text += "  Пока ничего не построено.\n"
    
    bot.reply_to(message, text, parse_mode="Markdown", reply_markup=get_main_keyboard())

# ===== ПОСТРОЙКИ =====
@bot.message_handler(func=lambda m: m.text == "🏗️ Постройки")
def buildings_menu(message):
    if check_ban(message):
        return
    markup = telebot.types.InlineKeyboardMarkup(row_width=2)
    for bkey, bdata in BUILDINGS.items():
        markup.add(telebot.types.InlineKeyboardButton(
            f"{bdata['name']} ({bdata['price']:,}$)",
            callback_data=f"build_{bkey}"
        ))
    bot.send_message(message.chat.id, "🏗️ Выбери здание для постройки:", reply_markup=markup)

@bot.callback_query_handler(func=lambda c: c.data.startswith("build_"))
def build_building(call):
    user_id = call.from_user.id
    player = get_player(user_id)
    bkey = call.data.split("_")[1]
    bdata = BUILDINGS[bkey]
    
    # Проверяем место
    if player["used_road"] >= player["road"]:
        bot.answer_callback_query(call.id, "❌ Не хватает дороги! Купи землю в разделе 🛣️ Дорога.")
        return
    
    # Проверяем деньги
    if player["money"] < bdata["price"]:
        bot.answer_callback_query(call.id, "❌ Не хватает денег!")
        return
    
    # Строим
    player["money"] -= bdata["price"]
    player["buildings"][bkey] = player["buildings"].get(bkey, 0) + 1
    player["used_road"] += 1
    
    bot.answer_callback_query(call.id, f"✅ {bdata['name']} построен!")
    bot.send_message(call.message.chat.id, f"✅ Построено: {bdata['name']}!\nОсталось денег: {player['money']:,}$\nЗанято дороги: {player['used_road']}/{player['road']}м")

# ===== ДОРОГА =====
@bot.message_handler(func=lambda m: m.text == "🛣️ Дорога")
def road_menu(message):
    if check_ban(message):
        return
    player = get_player(message.from_user.id)
    markup = telebot.types.InlineKeyboardMarkup()
    for pack in ROAD_PACKS:
        markup.add(telebot.types.InlineKeyboardButton(
            f"{pack['meters']}м — {pack['price']:,}$",
            callback_data=f"road_{pack['meters']}"
        ))
    bot.send_message(message.chat.id,
        f"🛣️ Покупка земли под застройку\n\nУ тебя: {player['road']}м (занято {player['used_road']}м)\nСвободно: {player['road'] - player['used_road']}м\n\nВыбери пакет:",
        reply_markup=markup)

@bot.callback_query_handler(func=lambda c: c.data.startswith("road_"))
def buy_road(call):
    user_id = call.from_user.id
    player = get_player(user_id)
    meters = int(call.data.split("_")[1])
    
    # Находим цену
    pack = next((p for p in ROAD_PACKS if p["meters"] == meters), None)
    if not pack:
        bot.answer_callback_query(call.id, "❌ Ошибка!")
        return
    
    if player["money"] < pack["price"]:
        bot.answer_callback_query(call.id, "❌ Не хватает денег!")
        return
    
    player["money"] -= pack["price"]
    player["road"] += meters
    
    bot.answer_callback_query(call.id, f"✅ Куплено {meters}м дороги!")
    bot.send_message(call.message.chat.id, f"✅ Куплено {meters}м дороги за {pack['price']:,}$!\nВсего дороги: {player['road']}м\nСвободно: {player['road'] - player['used_road']}м")

# ===== КЕЙСЫ =====
@bot.message_handler(func=lambda m: m.text == "📦 Кейсы")
def cases_menu(message):
    if check_ban(message):
        return
    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(telebot.types.InlineKeyboardButton("📦 Обычный (10.000$)", callback_data="case_normal"))
    markup.add(telebot.types.InlineKeyboardButton("🔮 Редкий (50.000$)", callback_data="case_rare"))
    markup.add(telebot.types.InlineKeyboardButton("🚀 Космический (500.000$)", callback_data="case_cosmo"))
    bot.send_message(message.chat.id, "📦 Выбери кейс для открытия:", reply_markup=markup)

@bot.callback_query_handler(func=lambda c: c.data.startswith("case_"))
def open_case(call):
    user_id = call.from_user.id
    player = get_player(user_id)
    case_type = call.data.split("_")[1]
    
    prices = {"normal": 10000, "rare": 50000, "cosmo": 500000}
    rewards = {
        "normal": [(5000, 20000), ("house", 1), ("park", 1)],
        "rare": [(20000, 80000), ("shop", 2), ("power", 1), ("factory", 1)],
        "cosmo": [(100000, 500000), ("bank", 1), ("cosmo", 1), ("money", 1000000)],
    }
    
    if case_type not in prices:
        bot.answer_callback_query(call.id, "❌ Ошибка!")
        return
    
    price = prices[case_type]
    if player["money"] < price:
        bot.answer_callback_query(call.id, "❌ Не хватает денег!")
        return
    
    player["money"] -= price
    
    # Выбираем награду
    reward_pool = rewards[case_type]
    choice = random.choice(reward_pool)
    
    if isinstance(choice[0], int):  # Деньги
        win_amount = random.randint(choice[0], choice[1])
        player["money"] += win_amount
        text = f"💰 Вы выиграли {win_amount:,}$!"
    elif choice[0] == "money":  # Фиксированная сумма
        player["money"] += choice[1]
        text = f"💰 Вы выиграли {choice[1]:,}$!"
    else:  # Здание
        bkey = choice[0]
        count = choice[1]
        if player["used_road"] + count <= player["road"]:
            player["buildings"][bkey] = player["buildings"].get(bkey, 0) + count
            player["used_road"] += count
            text = f"🏗️ Вы выиграли {BUILDINGS[bkey]['name']} x{count}!"
        else:
            # Если нет места — даём деньги вместо здания
            compensation = BUILDINGS[bkey]["price"] * count // 2
            player["money"] += compensation
            text = f"🏗️ Вы выиграли {BUILDINGS[bkey]['name']} x{count}, но нет места!\n💰 Компенсация: {compensation:,}$"
    
    bot.answer_callback_query(call.id, "🎉 Кейс открыт!")
    bot.send_message(call.message.chat.id, f"📦 Открыт кейс за {price:,}$!\n\n{text}\n\nБаланс: {player['money']:,}$")

# ===== БОНУС =====
@bot.message_handler(func=lambda m: m.text == "🎁 Бонус")
def daily_bonus(message):
    if check_ban(message):
        return
    user_id = message.from_user.id
    player = get_player(user_id)
    today = datetime.now().strftime("%Y-%m-%d")
    
    if player["last_daily"] == today:
        bot.reply_to(message, "❌ Ты уже получал бонус сегодня! Приходи завтра.", reply_markup=get_main_keyboard())
        return
    
    bonus = random.randint(50000, 200000)
    player["money"] += bonus
    player["last_daily"] = today
    
    # Иногда даём бесплатное здание
    extra = ""
    if random.random() < 0.2:
        free_building = random.choice(["house", "park"])
        if player["used_road"] < player["road"]:
            player["buildings"][free_building] = player["buildings"].get(free_building, 0) + 1
            player["used_road"] += 1
            extra = f"\n🎁 Бонус: {BUILDINGS[free_building]['name']} бесплатно!"
        else:
            extra = "\n🎁 Бонусное здание не влезло (нет дороги)!"
    
    bot.reply_to(message,
        f"🎉 Ты получил {bonus:,}$!\nТеперь у тебя {player['money']:,}${extra}",
        reply_markup=get_main_keyboard())

# ===== ТОП ГОРОДОВ =====
@bot.message_handler(func=lambda m: m.text == "👥 Топ городов")
def top_cities(message):
    if check_ban(message):
        return
    
    # Сортируем по доходу
    cities = []
    for uid, data in players_data.items():
        income = sum(BUILDINGS[bkey]["income"] * data["buildings"].get(bkey, 0) for bkey in BUILDINGS)
        cities.append((uid, data["name"], data["money"], income, data["game_id"]))
    
    cities.sort(key=lambda x: x[2], reverse=True)
    
    text = "🏆 Топ 10 городов 🏆\n\n"
    for i, (uid, name, money, income, gid) in enumerate(cities[:10], 1):
        text += f"{i}. {name}\n   💰 {money:,}$ | 📈 {income}$/ч | 🆔 {gid}\n"
    
    bot.reply_to(message, text, reply_markup=get_main_keyboard())

# ===== ПРОФИЛЬ =====
@bot.message_handler(func=lambda m: m.text == "👤 Профиль")
def profile(message):
    if check_ban(message):
        return
    player = get_player(message.from_user.id)
    clan_name = player.get("clan", "Нет")
    if clan_name in clans_data:
        clan_name = clans_data[clan_name]["name"]
    
    friends_count = len(FRIENDS.get(message.from_user.id, []))
    
    text = f"""📇 **Профиль мэра**
━━━━━━━━━━━━━━━━
🆔 ID: {player['game_id']}
📱 TG: {message.from_user.id}
👤 Имя: {player['name']}
💰 Баланс: {player['money']:,}$
📈 Доход: {player['income']}$/ч
🛣️ Дороги: {player['used_road']}/{player['road']}м
👥 Население: {player['population']}
😊 Радость: {player['joy']}
⚡ Энергия: {player['energy']} / {player['energy_used']}
👫 Друзей: {friends_count}
🏰 Клан: {clan_name}
🎫 Промокодов: {len(player['used_promos'])}
━━━━━━━━━━━━━━━━"""
    bot.reply_to(message, text, parse_mode="Markdown", reply_markup=get_main_keyboard())

# ===== ОСТАЛЬНЫЕ ФУНКЦИИ (ID, ДРУЗЬЯ, КЛАНЫ, ПРОМОКОДЫ, АДМИНКА) =====
# Вставьте сюда все старые функции: my_id, find_id, friends_menu, friend_list,
# friend_requests, accept_friend, decline_friend, friends_back,
# add_friend, remove_friend, my_friends,
# clans_menu, clan_list, clan_create, process_clan_create, clan_leave,
# use_promo, my_promos, promo_stats,
# admin_help, new_admin, remove_admin, change_game_id, add_money, set_money,
# reset_player, ban_user, ban_time, unban_user, player_info, delete_clan,
# stats, broadcast, admin_list
# 
# Все они ОСТАЮТСЯ БЕЗ ИЗМЕНЕНИЙ из предыдущего кода!
# Просто скопируйте их сюда.

# ===== ЗАПУСК =====
print("🏙️ Бот 'Мой Город' запущен!")
if __name__ == '__main__':
    bot.infinity_polling()