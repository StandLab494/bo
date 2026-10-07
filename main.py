import os
import time
import random
import sqlite3
import threading
import logging
from html import escape

import telebot
from telebot import apihelper
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# ==================== КОНФИГ ====================
TOKEN = os.getenv("BOT_TOKEN", "")
DB_PATH = os.getenv(
    "DB_PATH",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "casino.db"),
)

START_BALANCE = 100_000
DAILY_BONUS = 50_000
DAILY_COOLDOWN = 24 * 3600
CURRENCY = "🪙"

MAX_BALANCE = 100_000_000_000_000   # 100T

WIN_MULTIPLIER = 0.8   # множитель выигрышей в слотах и минах

SLOT_MIN_BET = 10
MINES_MIN_BET = 10
CRASH_MIN_BET = 10

MINES_CELLS = 16
MINES_BOMBS = 4
MINES_GOAL = 3
MINES_MULT = [1.2, 1.8, 2.5]

CRASH_GROWTH = 0.3
CRASH_MAX = 30.0
CRASH_HOUSE_EDGE = 0.05
CRASH_INSTANT_CHANCE = 0.002

# ==================== МАГАЗИН ====================
SHOP_ITEMS = {
    "shield": {
        "name": "🛡 Щит",
        "price": 50_000,
        "desc": "Спасёт от одной мины в MINES",
        "buyable": True,
    },
    "booster": {
        "name": "🎯 Бустер ×2 (бета)",
        "price": 2_000_00,
        "desc": "Удвоит выигрыш в следующей игре",
        "buyable": False,
    },
    "case": {
        "name": "🎁 Кейс",
        "price": 1_000_00,
        "desc": "Случайная награда: от 100к до 50M",
        "buyable": True,
    },
}

CASE_REWARDS = [
    (100_000, 40),
    (500_000, 25),
    (2_000_000, 20),
    (5_000_000, 10),
    (20_000_000, 4),
    (50_000_000, 1),
]

CASE_ANIM_FRAMES = [
    "❤️ [🪙] 💎 💸",
    "🪙 [💎] 💸 ❤️",
    "💎 [💸] ❤️ 🪙",
    "💸 [❤️] 🪙 💎",
    "❤️ [💎] 🪙 💸",
    "🎁 [🎁] 🎁 🎁",
]

if not TOKEN:
    raise SystemExit("BOT_TOKEN не задан. export BOT_TOKEN=...")

# ==================== ЛОГИ ====================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("casino")

# ==================== TELEGRAM ====================
apihelper.API_URL = "https://api.telegram.org/bot{0}/{1}"
apihelper.FILE_URL = "https://api.telegram.org/file/bot{0}/{1}"

bot = telebot.TeleBot(TOKEN)

# ==================== БАЗА ====================
_local = threading.local()


def _conn():
    if not hasattr(_local, "conn"):
        c = sqlite3.connect(DB_PATH, check_same_thread=False, isolation_level=None)
        c.row_factory = sqlite3.Row
        c.execute("PRAGMA journal_mode=WAL")
        c.execute("PRAGMA busy_timeout=5000")
        _local.conn = c
    return _local.conn


def init_db():
    _conn().executescript("""
        CREATE TABLE IF NOT EXISTS users (
            user_id     INTEGER PRIMARY KEY,
            username    TEXT,
            balance     INTEGER NOT NULL DEFAULT 0 CHECK (balance >= 0),
            total_bets  INTEGER NOT NULL DEFAULT 0,
            total_won   INTEGER NOT NULL DEFAULT 0,
            total_lost  INTEGER NOT NULL DEFAULT 0,
            last_daily  INTEGER NOT NULL DEFAULT 0,
            banned      INTEGER NOT NULL DEFAULT 0
        );
        CREATE INDEX IF NOT EXISTS idx_balance ON users(balance DESC);

        CREATE TABLE IF NOT EXISTS inventory (
            user_id  INTEGER,
            item     TEXT,
            count    INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY (user_id, item)
        );
    """)


def get_user(user_id, username=None):
    c = _conn()
    c.execute(
        "INSERT OR IGNORE INTO users (user_id, username, balance) VALUES (?, ?, ?)",
        (user_id, username, START_BALANCE),
    )
    if username:
        c.execute(
            "UPDATE users SET username=? WHERE user_id=?",
            (username, user_id),
        )
    row = c.execute("SELECT * FROM users WHERE user_id=?", (user_id,)).fetchone()
    return dict(row)


def try_spend(user_id, amount):
    row = _conn().execute(
        "UPDATE users SET balance = balance - ? WHERE user_id=? AND balance >= ? RETURNING balance",
        (amount, user_id, amount),
    ).fetchone()
    return row["balance"] if row else None


def add_balance(user_id, amount):
    row = _conn().execute(
        "UPDATE users SET balance = MIN(balance + ?, ?) WHERE user_id=? RETURNING balance",
        (amount, MAX_BALANCE, user_id),
    ).fetchone()
    return row["balance"] if row else 0


def log_game(user_id, bet, net):
    won = max(net, 0)
    lost = max(-net, 0)
    _conn().execute(
        """UPDATE users SET total_bets = total_bets + ?,
                            total_won  = total_won  + ?,
                            total_lost = total_lost + ?
           WHERE user_id=?""",
        (bet, won, lost, user_id),
    )


def get_top(limit=10):
    rows = _conn().execute(
        "SELECT username, balance FROM users WHERE banned=0 ORDER BY balance DESC LIMIT ?",
        (limit,),
    ).fetchall()
    return [dict(r) for r in rows]


def is_banned(user_id):
    row = _conn().execute("SELECT banned FROM users WHERE user_id=?", (user_id,)).fetchone()
    return bool(row and row["banned"])


# ==================== ИНВЕНТАРЬ ====================
def get_inventory(user_id):
    rows = _conn().execute(
        "SELECT item, count FROM inventory WHERE user_id = ?",
        (user_id,),
    ).fetchall()
    return {r["item"]: r["count"] for r in rows}


def add_item(user_id, item, count=1):
    c = _conn()
    c.execute(
        "INSERT OR IGNORE INTO inventory (user_id, item, count) VALUES (?, ?, 0)",
        (user_id, item),
    )
    c.execute(
        "UPDATE inventory SET count = count + ? WHERE user_id = ? AND item = ?",
        (count, user_id, item),
    )


def use_item(user_id, item):
    row = _conn().execute(
        """UPDATE inventory SET count = count - 1
           WHERE user_id = ? AND item = ? AND count > 0
           RETURNING count""",
        (user_id, item),
    ).fetchone()
    return row is not None


def has_item(user_id, item):
    row = _conn().execute(
        "SELECT count FROM inventory WHERE user_id = ? AND item = ?",
        (user_id, item),
    ).fetchone()
    return bool(row and row["count"] > 0)


# ==================== АКТИВНЫЕ ИГРЫ ====================
_game_lock = threading.RLock()
mines_games = {}
crash_games = {}


# ==================== УТИЛИТЫ ====================
def fmt_money(value):
    return f"{int(value):,}".replace(",", " ")


def apply_win_multiplier(payout):
    """Применяет глобальный множитель выигрышей."""
    return int(payout * WIN_MULTIPLIER)


def init_user(message):
    return get_user(message.from_user.id, message.from_user.username)


def allowed(message):
    if is_banned(message.from_user.id):
        bot.reply_to(message, "🚫 Вы заблокированы.")
        return False
    return True


def parse_bet_argument(message, command_name, minimum):
    parts = message.text.split(maxsplit=1)
    if len(parts) != 2:
        bot.reply_to(message, f"❌ Использование: /{command_name} {minimum}")
        return None
    try:
        bet = int(parts[1].strip())
    except ValueError:
        bot.reply_to(message, "❌ Ставка должна быть целым числом.")
        return None
    if bet < minimum:
        bot.reply_to(message, f"❌ Минимальная ставка: {minimum} {CURRENCY}.")
        return None
    if bet > 10_000_000_000_000:
        bot.reply_to(message, "❌ Ставка слишком большая.")
        return None
    return bet


def parse_text_bet(message, prefix, minimum):
    parts = message.text.strip().split(maxsplit=1)
    if len(parts) != 2:
        bot.reply_to(message, f"❌ Использование: {prefix} {minimum}")
        return None
    try:
        bet = int(parts[1].strip())
    except ValueError:
        bot.reply_to(message, "❌ Ставка должна быть целым числом.")
        return None
    if bet < minimum:
        bot.reply_to(message, f"❌ Минимальная ставка: {minimum} {CURRENCY}.")
        return None
    if bet > 10_000_000_000_000:
        bot.reply_to(message, "❌ Ставка слишком большая.")
        return None
    return bet


def safe_edit(chat_id, message_id, text, **kwargs):
    try:
        return bot.edit_message_text(
            text,
            chat_id=chat_id,
            message_id=message_id,
            **kwargs,
        )
    except Exception as exc:
        log.warning("edit_message %s/%s failed: %s", chat_id, message_id, exc)
        return None


def safe_send(chat_id, text, **kwargs):
    try:
        return bot.send_message(chat_id, text, **kwargs)
    except Exception as exc:
        log.warning("send_message %s failed: %s", chat_id, exc)
        return None


# ==================== МЕНЮ ====================
def main_menu():
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("💰 Баланс", callback_data="menu:balance"),
        InlineKeyboardButton("🎁 Бонус", callback_data="menu:bonus"),
        InlineKeyboardButton("🏆 Топ", callback_data="menu:top"),
        InlineKeyboardButton("🛒 Магазин", callback_data="menu:shop"),
    )
    return kb


# ==================== START / HELP ====================
@bot.message_handler(commands=["start"])
def cmd_start(message):
    if not allowed(message):
        return
    user = init_user(message)
    text = (
        f"👋 Привет, {escape(message.from_user.first_name or 'игрок')}!\n\n"
        f"🎰 <b>Казино</b>\n\n"
        f"<b>Команды:</b>\n"
        f"• /balance — баланс\n"
        f"• /daily — ежедневный бонус\n"
        f"• /top — рейтинг\n"
        f"• /shop — магазин\n"
        f"• /inventory — инвентарь\n"
        f"• /slots 100 — слоты\n"
        f"• /mines 100 — мины\n"
        f"• /crash 100 — краш\n\n"
        f"<b>Текстом:</b>\n"
        f"• Слоты 100\n"
        f"• Мины 100\n"
        f"• Краш 100\n\n"
        f"💵 Баланс: <b>{fmt_money(user['balance'])} {CURRENCY}</b>"
    )
    bot.send_message(message.chat.id, text, reply_markup=main_menu(), parse_mode="HTML")


@bot.message_handler(commands=["help"])
def cmd_help(message):
    if not allowed(message):
        return
    bot.reply_to(
        message,
        "Использование:\n\n"
        "<code>/slots 100</code> — слоты\n"
        "<code>/mines 100</code> — мины\n"
        "<code>/crash 100</code> — краш\n"
        "<code>/shop</code> — магазин\n"
        "<code>/inventory</code> — инвентарь\n\n"
        "Или текстом: <code>Слоты 100</code>, <code>Мины 100</code>, <code>Краш 100</code>",
        parse_mode="HTML",
    )


# ==================== BALANCE / DAILY / TOP ====================
@bot.message_handler(commands=["balance", "bal"])
def cmd_balance(message):
    if not allowed(message):
        return
    user = init_user(message)
    bot.reply_to(
        message,
        f"💰 Баланс: <b>{fmt_money(user['balance'])} {CURRENCY}</b>",
        parse_mode="HTML",
    )


@bot.message_handler(commands=["daily"])
def cmd_daily(message):
    if not allowed(message):
        return
    user_id = message.from_user.id
    init_user(message)
    now = int(time.time())

    row = _conn().execute(
        """UPDATE users SET balance = MIN(balance + ?, ?), last_daily = ?
           WHERE user_id=? AND last_daily <= ?
           RETURNING balance""",
        (DAILY_BONUS, MAX_BALANCE, now, user_id, now - DAILY_COOLDOWN),
    ).fetchone()

    if row:
        bot.reply_to(
            message,
            f"🎁 Бонус: <b>+{fmt_money(DAILY_BONUS)} {CURRENCY}</b>\n"
            f"💵 Баланс: <b>{fmt_money(row['balance'])} {CURRENCY}</b>",
            parse_mode="HTML",
        )
        return

    user = get_user(user_id)
    left = max(0, DAILY_COOLDOWN - (now - user["last_daily"]))
    h, m = left // 3600, (left % 3600) // 60
    bot.reply_to(message, f"⏳ Следующий бонус через {h}ч {m}м.")


@bot.message_handler(commands=["top", "rating"])
def cmd_top(message):
    if not allowed(message):
        return
    rows = get_top(10)
    if not rows:
        bot.reply_to(message, "Рейтинг пуст.")
        return
    lines = ["🏆 <b>Топ игроков</b>\n"]
    for i, row in enumerate(rows, 1):
        name = escape(row["username"] or "Игрок")
        lines.append(f"{i}. @{name} — <b>{fmt_money(row['balance'])} {CURRENCY}</b>")
    bot.reply_to(message, "\n".join(lines), parse_mode="HTML")


# ==================== МЕНЮ (callback) ====================
@bot.callback_query_handler(func=lambda c: c.data.startswith("menu:"))
def callback_menu(call):
    uid = call.from_user.id
    action = call.data.split(":", 1)[1]

    if is_banned(uid):
        bot.answer_callback_query(call.id, "🚫 Заблокирован", show_alert=True)
        return

    user = get_user(uid, call.from_user.username)

    if action == "balance":
        bot.answer_callback_query(call.id, f"Баланс: {fmt_money(user['balance'])} {CURRENCY}", show_alert=True)

    elif action == "top":
        rows = get_top(10)
        lines = ["🏆 <b>Топ игроков</b>\n"]
        for i, row in enumerate(rows, 1):
            name = escape(row["username"] or "Игрок")
            lines.append(f"{i}. @{name} — {fmt_money(row['balance'])} {CURRENCY}")
        bot.answer_callback_query(call.id)
        safe_edit(call.message.chat.id, call.message.message_id, "\n".join(lines), parse_mode="HTML", reply_markup=main_menu())

    elif action == "bonus":
        now = int(time.time())
        row = _conn().execute(
            """UPDATE users SET balance = MIN(balance + ?, ?), last_daily = ?
               WHERE user_id=? AND last_daily <= ?
               RETURNING balance""",
            (DAILY_BONUS, MAX_BALANCE, now, uid, now - DAILY_COOLDOWN),
        ).fetchone()
        if not row:
            bot.answer_callback_query(call.id, "⏳ Бонус уже получен", show_alert=True)
            return
        bot.answer_callback_query(call.id, f"🎁 +{fmt_money(DAILY_BONUS)} {CURRENCY}", show_alert=True)
        safe_edit(
            call.message.chat.id,
            call.message.message_id,
            f"🎁 Бонус получен!\n💵 Баланс: <b>{fmt_money(row['balance'])} {CURRENCY}</b>",
            parse_mode="HTML",
            reply_markup=main_menu(),
        )

    elif action == "shop":
        bot.answer_callback_query(call.id)
        show_shop(call.message.chat.id, call.message.message_id)


# ==================== МАГАЗИН ====================
def shop_keyboard():
    kb = InlineKeyboardMarkup(row_width=1)
    for item_id, item in SHOP_ITEMS.items():
        if item["buyable"]:
            label = f"{item['name']} — {fmt_money(item['price'])} {CURRENCY}"
            kb.add(InlineKeyboardButton(label, callback_data=f"shop:buy:{item_id}"))
        else:
            label = f"{item['name']} — недоступно"
            kb.add(InlineKeyboardButton(label, callback_data="noop"))
    kb.add(InlineKeyboardButton("🔙 Назад", callback_data="menu:top"))
    return kb


def shop_text():
    lines = ["🛒 <b>Магазин</b>\n"]
    for item_id, item in SHOP_ITEMS.items():
        if item["buyable"]:
            price = f"<b>{fmt_money(item['price'])} {CURRENCY}</b>"
        else:
            price = "<i>скоро</i>"
        lines.append(f"{item['name']} — {price}\n<i>{item['desc']}</i>\n")
    return "\n".join(lines)


def show_shop(chat_id, message_id):
    safe_edit(chat_id, message_id, shop_text(), parse_mode="HTML", reply_markup=shop_keyboard())


@bot.message_handler(commands=["shop"])
def cmd_shop(message):
    if not allowed(message):
        return
    init_user(message)
    bot.reply_to(message, shop_text(), parse_mode="HTML", reply_markup=shop_keyboard())


@bot.message_handler(commands=["inventory", "inv"])
def cmd_inventory(message):
    if not allowed(message):
        return
    uid = message.from_user.id
    init_user(message)
    inv = get_inventory(uid)
    items = [(item_id, count) for item_id, count in inv.items() if count > 0]
    if not items:
        bot.reply_to(message, "🎒 Инвентарь пуст.")
        return
    lines = ["🎒 <b>Инвентарь</b>\n"]
    for item_id, count in items:
        item = SHOP_ITEMS.get(item_id)
        name = item["name"] if item else item_id
        lines.append(f"{name} × <b>{count}</b>")
    bot.reply_to(message, "\n".join(lines), parse_mode="HTML")


@bot.callback_query_handler(func=lambda c: c.data.startswith("shop:buy:"))
def callback_shop_buy(call):
    uid = call.from_user.id
    if is_banned(uid):
        bot.answer_callback_query(call.id, "🚫 Заблокирован", show_alert=True)
        return

    item_id = call.data.split(":", 2)[2]
    item = SHOP_ITEMS.get(item_id)
    if not item or not item["buyable"]:
        bot.answer_callback_query(call.id, "❌ Товар недоступен", show_alert=True)
        return

    init_user(call.from_user)
    price = item["price"]

    if try_spend(uid, price) is None:
        bot.answer_callback_query(call.id, "❌ Недостаточно монет", show_alert=True)
        return

    if item_id == "case":
        rewards = [r for r, _ in CASE_REWARDS]
        weights = [w for _, w in CASE_REWARDS]
        reward = random.choices(rewards, weights)[0]

        bot.answer_callback_query(call.id, "🎁 Открываем...")
        chat_id = call.message.chat.id
        msg_id = call.message.message_id

        for frame in CASE_ANIM_FRAMES:
            safe_edit(
                chat_id, msg_id,
                f"🎁 <b>Открываем кейс...</b>\n\n{frame}",
                parse_mode="HTML",
            )
            time.sleep(0.35)

        add_balance(uid, reward)
        log_game(uid, price, reward - price)
        user = get_user(uid)

        safe_edit(
            chat_id, msg_id,
            f"🎁 <b>Кейс открыт!</b>\n\n"
            f"💰 Награда: <b>+{fmt_money(reward)} {CURRENCY}</b>\n"
            f"💵 Баланс: <b>{fmt_money(user['balance'])} {CURRENCY}</b>",
            parse_mode="HTML",
            reply_markup=shop_keyboard(),
        )
        return

    add_item(uid, item_id, 1)
    user = get_user(uid)
    bot.answer_callback_query(call.id, f"✅ Куплено: {item['name']}", show_alert=True)
    safe_edit(
        call.message.chat.id,
        call.message.message_id,
        f"✅ <b>Куплено:</b> {item['name']}\n\n"
        f"💵 Баланс: <b>{fmt_money(user['balance'])} {CURRENCY}</b>",
        parse_mode="HTML",
        reply_markup=shop_keyboard(),
    )


# ==================== SLOTS ====================
SLOT_SYMBOLS = ["🍒", "🍋", "🍊", "🍉", "🔔", "⭐", "💎"]
SLOT_MULT = {
    "🍒": 2, "🍋": 2, "🍊": 3, "🍉": 4, "🔔": 5, "⭐": 8, "💎": 12,
}


def play_slots(message, bet):
    uid = message.from_user.id
    init_user(message)

    if try_spend(uid, bet) is None:
        bot.reply_to(message, "❌ Недостаточно средств.")
        return

    result = [random.choice(SLOT_SYMBOLS) for _ in range(3)]
    line = " | ".join(result)

    if result[0] == result[1] == result[2]:
        gross = bet * SLOT_MULT[result[0]]
        payout = apply_win_multiplier(gross)
        add_balance(uid, payout)
        log_game(uid, bet, payout - bet)
        result_text = f"🎉 <b>ДЖЕКПОТ!</b>\n💰 Выигрыш: <b>+{fmt_money(payout)} {CURRENCY}</b>"
        if gross != payout:
            result_text += (
                f"\n🎰 Множитель выигрыша: <b>×{WIN_MULTIPLIER}</b> "
                f"(было {fmt_money(gross)})"
            )
    elif result[0] == result[1] or result[1] == result[2] or result[0] == result[2]:
        add_balance(uid, bet)
        log_game(uid, bet, 0)
        result_text = f"🙂 Два одинаковых. Возврат: <b>{bet} {CURRENCY}</b>"
    else:
        log_game(uid, bet, -bet)
        result_text = f"😔 Проигрыш: <b>{bet} {CURRENCY}</b>"

    user = get_user(uid)
    bot.reply_to(
        message,
        f"🎰 <b>SLOTS</b>\n\n{line}\n\n{result_text}\n"
        f"💵 Баланс: <b>{fmt_money(user['balance'])} {CURRENCY}</b>",
        parse_mode="HTML",
    )


@bot.message_handler(commands=["slots", "slot"])
def cmd_slots(message):
    if not allowed(message):
        return
    bet = parse_bet_argument(message, "slots", SLOT_MIN_BET)
    if bet is not None:
        play_slots(message, bet)


@bot.message_handler(
    func=lambda m: m.text and m.text.strip().lower().startswith("слоты")
)
def text_slots(message):
    if not allowed(message):
        return
    bet = parse_text_bet(message, "Слоты", )
def text_slots(message):
    if not allowed(message):
        return
    bet = parse_text_bet(message, "Слоты", SLOT_MIN_BET)
    if bet is not None:
        play_slots(message, bet)


# ==================== MINES ====================
def render_mines(game, reveal=False):
    opened = game["opened"]
    bombs = game["bombs"]
    bet = game["bet"]

    keyboard = InlineKeyboardMarkup(row_width=4)
    for i in range(MINES_CELLS):
        if i in opened:
            keyboard.add(InlineKeyboardButton("💎", callback_data="noop"))
        elif reveal and i in bombs:
            keyboard.add(InlineKeyboardButton("💣", callback_data="noop"))
        else:
            cb = "noop" if reveal else f"mine:{i}"
            keyboard.add(InlineKeyboardButton("⬜", callback_data=cb))

    count = len(opened)
    if 0 < count < MINES_GOAL and not reveal:
        mult = MINES_MULT[min(count - 1, len(MINES_MULT) - 1)]
        cash = apply_win_multiplier(int(bet * mult))
        keyboard.add(InlineKeyboardButton(f"💰 Забрать {cash} {CURRENCY}", callback_data="mine:cash"))

    if count:
        mult = MINES_MULT[min(count - 1, len(MINES_MULT) - 1)]
    else:
        mult = 1.0
    potential = apply_win_multiplier(int(bet * mult))
    left = max(0, MINES_GOAL - count)

    text = (
        f"💣 <b>MINES</b>\n\n"
        f"💵 Ставка: <b>{bet} {CURRENCY}</b>\n"
        f"✅ Открыто: <b>{count}</b>/{MINES_GOAL}\n"
        f"📦 Осталось: <b>{left}</b>\n"
        f"📈 Множитель: <b>x{mult:.2f}</b>\n"
        f"💰 Можно забрать: <b>{potential} {CURRENCY}</b>"
    )
    return text, keyboard


def start_mines(message, bet):
    uid = message.from_user.id
    init_user(message)

    with _game_lock:
        if uid in mines_games:
            bot.reply_to(message, "❌ У вас уже есть активная игра Mines.")
            return
        if try_spend(uid, bet) is None:
            bot.reply_to(message, "❌ Недостаточно средств.")
            return

        game = {
            "user_id": uid,
            "chat_id": message.chat.id,
            "message_id": None,
            "bet": bet,
            "bombs": set(random.sample(range(MINES_CELLS), MINES_BOMBS)),
            "opened": set(),
        }
        mines_games[uid] = game

    text, kb = render_mines(game)
    sent = bot.reply_to(message, text, parse_mode="HTML", reply_markup=kb)

    with _game_lock:
        cur = mines_games.get(uid)
        if cur is not None:
            cur["message_id"] = sent.message_id


@bot.message_handler(commands=["mines", "mine"])
def cmd_mines(message):
    if not allowed(message):
        return
    bet = parse_bet_argument(message, "mines", MINES_MIN_BET)
    if bet is not None:
        start_mines(message, bet)


@bot.message_handler(
    func=lambda m: m.text and m.text.strip().lower().startswith("мины")
)
def text_mines(message):
    if not allowed(message):
        return
    bet = parse_text_bet(message, "Мины", MINES_MIN_BET)
    if bet is not None:
        start_mines(message, bet)


@bot.callback_query_handler(func=lambda c: c.data.startswith("mine:"))
def callback_mines(call):
    uid = call.from_user.id
    action = call.data.split(":", 1)[1]

    with _game_lock:
        game = mines_games.get(uid)
        if game is None:
            bot.answer_callback_query(call.id, "❌ Игра уже завершена.", show_alert=True)
            return
        if not game["message_id"]:
            bot.answer_callback_query(call.id, "⏳ Игра ещё запускается.", show_alert=True)
            return

        if action == "cash":
            count = len(game["opened"])
            if count == 0:
                bot.answer_callback_query(call.id, "❌ Сначала откройте клетку.", show_alert=True)
                return
            mult = MINES_MULT[min(count - 1, len(MINES_MULT) - 1)]
            gross = int(game["bet"] * mult)
            payout = apply_win_multiplier(gross)
            bet = game["bet"]
            chat_id = game["chat_id"]
            msg_id = game["message_id"]
            snapshot = {"bet": bet, "bombs": set(game["bombs"]), "opened": set(game["opened"])}
            mines_games.pop(uid, None)

            add_balance(uid, payout)
            log_game(uid, bet, payout - bet)
            user = get_user(uid)

            mult_line = ""
            if gross != payout:
                mult_line = f"\n🎰 Множитель выигрыша: <b>×{WIN_MULTIPLIER}</b> (было {fmt_money(gross)})"

            bot.answer_callback_query(call.id, "💰 Забрано!")
            safe_edit(
                chat_id, msg_id,
                f"💰 <b>Выигрыш забран!</b>\n\n"
                f"📈 Множитель: <b>x{mult:.2f}</b>\n"
                f"🎉 Выплата: <b>{fmt_money(payout)} {CURRENCY}</b>{mult_line}\n"
                f"💵 Баланс: <b>{fmt_money(user['balance'])} {CURRENCY}</b>",
                parse_mode="HTML",
                reply_markup=render_mines(snapshot, reveal=True)[1],
            )
            return

        try:
            index = int(action)
        except ValueError:
            bot.answer_callback_query(call.id, "❌ Некорректная кнопка.")
            return

        if not 0 <= index < MINES_CELLS:
            bot.answer_callback_query(call.id, "❌ Некорректная клетка.")
            return

        if index in game["opened"]:
            bot.answer_callback_query(call.id, "Уже открыто.")
            return

        # --- БОМБА ---
        if index in game["bombs"]:
            if has_item(uid, "shield"):
                use_item(uid, "shield")
                game["bombs"].discard(index)
                game["opened"].add(index)
                bot.answer_callback_query(call.id, "🛡 Щит поглотил удар!")
                text, kb = render_mines(game)
                safe_edit(game["chat_id"], game["message_id"], text, parse_mode="HTML", reply_markup=kb)
                return

            game["opened"].add(index)
            bet = game["bet"]
            chat_id = game["chat_id"]
            msg_id = game["message_id"]
            snapshot = {"bet": bet, "bombs": set(game["bombs"]), "opened": set(game["opened"])}
            mines_games.pop(uid, None)

            log_game(uid, bet, -bet)
            bot.answer_callback_query(call.id, "💥 Бомба!")
            safe_edit(
                chat_id, msg_id,
                f"💥 <b>БУМ!</b> Мина.\n\n"
                f"😢 Ставка <b>{bet} {CURRENCY}</b> потеряна.",
                parse_mode="HTML",
                reply_markup=render_mines(snapshot, reveal=True)[1],
            )
            return

        # --- БЕЗОПАСНО ---
        game["opened"].add(index)
        count = len(game["opened"])

        if count >= MINES_GOAL:
            mult = MINES_MULT[-1]
            gross = int(game["bet"] * mult)
            payout = apply_win_multiplier(gross)
            bet = game["bet"]
            chat_id = game["chat_id"]
            msg_id = game["message_id"]
            snapshot = {"bet": bet, "bombs": set(game["bombs"]), "opened": set(game["opened"])}
            mines_games.pop(uid, None)

            booster_used = False
            if has_item(uid, "booster"):
                use_item(uid, "booster")
                payout *= 2
                booster_used = True

            add_balance(uid, payout)
            log_game(uid, bet, payout - bet)
            user = get_user(uid)
            bot.answer_callback_query(call.id, f"🎉 +{fmt_money(payout)} {CURRENCY}")

            mult_line = ""
            if gross != payout and not booster_used:
                mult_line = f"\n🎰 Множитель выигрыша: <b>×{WIN_MULTIPLIER}</b> (было {fmt_money(gross)})"
            booster_line = "\n🎯 <b>Бустер ×2 сработал!</b>" if booster_used else ""

            safe_edit(
                chat_id, msg_id,
                f"🎉 <b>Победа!</b>\n\n"
                f"📈 Множитель: <b>x{mult:.2f}</b>\n"
                f"💰 Выигрыш: <b>{fmt_money(payout)} {CURRENCY}</b>"
                f"{mult_line}{booster_line}\n"
                f"💵 Баланс: <b>{fmt_money(user['balance'])} {CURRENCY}</b>",
                parse_mode="HTML",
                reply_markup=render_mines(snapshot, reveal=True)[1],
            )
            return

        # --- ПРОДОЛЖАЕМ ---
        bot.answer_callback_query(call.id, "💎 Безопасно!")
        text, kb = render_mines(game)
        safe_edit(game["chat_id"], game["message_id"], text, parse_mode="HTML", reply_markup=kb)


# ==================== CRASH ====================
def crash_multiplier(game):
    elapsed = time.monotonic() - game["started_at"]
    return min(CRASH_MAX, 1.0 + elapsed * CRASH_GROWTH)


def _gen_crash_point():
    if random.random() < CRASH_INSTANT_CHANCE:
        return 1.0
    r = random.random()
    crash = (1.0 - CRASH_HOUSE_EDGE) / (1.0 - r)
    return min(CRASH_MAX, max(1.01, round(crash, 2)))


def crash_keyboard(payout):
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton(f"💰 Забрать {payout} {CURRENCY}", callback_data="crash:cash"))
    return kb


def start_crash(message, bet):
    uid = message.from_user.id
    init_user(message)

    with _game_lock:
        if uid in crash_games:
            bot.reply_to(message, "❌ У вас уже есть активный Crash.")
            return
        if try_spend(uid, bet) is None:
            bot.reply_to(message, "❌ Недостаточно средств.")
            return

        game = {
            "user_id": uid,
            "chat_id": message.chat.id,
            "message_id": None,
            "bet": bet,
            "started_at": time.monotonic(),
            "crash_at": _gen_crash_point(),
            "finished": False,
        }
        crash_games[uid] = game

    sent = bot.reply_to(
        message,
        f"🚀 <b>CRASH начался!</b>\n\n"
        f"📈 Множитель: <b>1.00x</b>\n"
        f"💵 Ставка: <b>{bet} {CURRENCY}</b>\n\n"
        f"<i>Успей забрать до краха!</i>",
        parse_mode="HTML",
        reply_markup=crash_keyboard(bet),
    )

    with _game_lock:
        cur = crash_games.get(uid)
        if cur is not None:
            cur["message_id"] = sent.message_id

    threading.Thread(target=crash_loop, args=(uid,), daemon=True).start()


def crash_loop(uid):
    last_update = -1.0
    while True:
        time.sleep(0.2)

        with _game_lock:
            game = crash_games.get(uid)
            if game is None or game["finished"]:
                return
            if not game["message_id"]:
                continue

            elapsed = time.monotonic() - game["started_at"]
            mult = crash_multiplier(game)

            if mult >= game["crash_at"]:
                game["finished"] = True
                bet = game["bet"]
                chat_id = game["chat_id"]
                msg_id = game["message_id"]
                crash_at = game["crash_at"]
                crash_games.pop(uid, None)
                crashed = True
            else:
                crashed = False
                bet = game["bet"]
                chat_id = game["chat_id"]
                msg_id = game["message_id"]

        if crashed:
            log_game(uid, bet, -bet)
            safe_edit(
                chat_id, msg_id,
                f"💥 <b>КРАШ!</b>\n\n"
                f"📈 Остановился на <b>{crash_at:.2f}x</b>.\n"
                f"😢 Ставка <b>{bet} {CURRENCY}</b> потеряна.",
                parse_mode="HTML",
            )
            return

        if elapsed - last_update >= 1.0:
            last_update = elapsed
            payout = int(bet * mult)
            safe_edit(
                chat_id, msg_id,
                f"🚀 <b>CRASH идёт!</b>\n\n"
                f"📈 Множитель: <b>{mult:.2f}x</b>\n"
                f"💰 Можно забрать: <b>{payout} {CURRENCY}</b>",
                parse_mode="HTML",
                reply_markup=crash_keyboard(payout),
            )


@bot.message_handler(commands=["crash"])
def cmd_crash(message):
    if not allowed(message):
        return
    bet = parse_bet_argument(message, "crash", CRASH_MIN_BET)
    if bet is not None:
        start_crash(message, bet)


@bot.message_handler(
    func=lambda m: m.text and m.text.strip().lower().startswith("краш")
)
def text_crash(message):
    if not allowed(message):
        return
    bet = parse_text_bet(message, "Краш", CRASH_MIN_BET)
    if bet is not None:
        start_crash(message, bet)


@bot.callback_query_handler(func=lambda c: c.data == "crash:cash")
def callback_crash_cash(call):
    uid = call.from_user.id

    with _game_lock:
        game = crash_games.get(uid)
        if game is None or game["finished"]:
            bot.answer_callback_query(call.id, "❌ Игра уже завершена.", show_alert=True)
            return

        mult = crash_multiplier(game)
        if mult >= game["crash_at"]:
            bot.answer_callback_query(call.id, "💥 Слишком поздно!", show_alert=True)
            return

        game["finished"] = True
        bet = game["bet"]
        chat_id = game["chat_id"]
        msg_id = game["message_id"]
        payout = int(bet * mult)
        crash_games.pop(uid, None)

    add_balance(uid, payout)
    log_game(uid, bet, payout - bet)
    user = get_user(uid)

    bot.answer_callback_query(call.id, f"💰 +{fmt_money(payout)} {CURRENCY}")
    safe_edit(
        chat_id, msg_id,
        f"💰 <b>Забрал!</b>\n\n"
        f"📈 Множитель: <b>{mult:.2f}x</b>\n"
        f"🎉 Выплата: <b>{fmt_money(payout)} {CURRENCY}</b>\n"
        f"💵 Баланс: <b>{fmt_money(user['balance'])} {CURRENCY}</b>",
        parse_mode="HTML",
    )


# ==================== ЗАГЛУШКА ====================
@bot.callback_query_handler(func=lambda c: c.data == "noop")
def cb_noop(call):
    bot.answer_callback_query(call.id)


# ==================== ЗАПУСК ====================
def polling_loop():
    while True:
        try:
            log.info("🚀 Бот запущен. DB=%s", DB_PATH)
            log.info("WIN_MULTIPLIER=%s", WIN_MULTIPLIER)
            bot.infinity_polling(
                skip_pending=True,
                timeout=30,
                long_polling_timeout=30,
            )
        except Exception:
            log.exception("Polling упал, рестарт через 5 сек.")
            time.sleep(5)


if __name__ == "__main__":
    init_db()
    polling_loop()
