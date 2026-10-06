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

START_BALANCE = 1000
DAILY_BONUS = 500
DAILY_COOLDOWN = 24 * 3600
CURRENCY = "🪙"

SLOT_MIN_BET = 10
MINES_MIN_BET = 10
CRASH_MIN_BET = 10

MINES_CELLS = 16
MINES_BOMBS = 4
MINES_GOAL = 3
MINES_MULT = [1.2, 1.8, 2.5]

CRASH_GROWTH = 0.3
CRASH_MAX = 20.0

if not TOKEN:
    raise SystemExit("BOT_TOKEN не задан. export BOT_TOKEN=...")

# ==================== ЛОГИ ====================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("casino")

# ==================== TELEGRAM ====================
# Настоящий api.telegram.org, без Mechagram.
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
        "UPDATE users SET balance = balance + ? WHERE user_id=? RETURNING balance",
        (amount, user_id),
    ).fetchone()
    return row["balance"] if row else 0


def log_game(user_id, bet, net):
    """
    bet — размер ставки.
    net — чистое изменение баланса:
          +N при выигрыше, -N при проигрыше, 0 при возврате.
    """
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


# ==================== АКТИВНЫЕ ИГРЫ ====================
_game_lock = threading.RLock()
mines_games = {}
crash_games = {}


# ==================== УТИЛИТЫ ====================
def fmt_money(value):
    return f"{int(value):,}".replace(",", " ")


def init_user(message):
    return get_user(message.from_user.id, message.from_user.username)


def allowed(message):
    if is_banned(message.from_user.id):
        bot.reply_to(message, "🚫 Вы заблокированы.")
        return False
    return True


def parse_bet_argument(message, command_name, minimum):
    """Для /slots 100, /mines 100, /crash 100. Возвращает bet или None."""
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
    if bet > 10_000_000:
        bot.reply_to(message, "❌ Ставка слишком большая.")
        return None
    return bet


def parse_text_bet(message, prefix, minimum):
    """Для 'Слоты 100', 'Мины 100', 'Краш 100'. Возвращает bet или None."""
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
    if bet > 10_000_000:
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
        "<code>/crash 100</code> — краш\n\n"
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
        """UPDATE users SET balance = balance + ?, last_daily = ?
           WHERE user_id=? AND last_daily <= ?
           RETURNING balance""",
        (DAILY_BONUS, now, user_id, now - DAILY_COOLDOWN),
    ).fetchone()

    if row:
        bot.reply_to(
            message,
            f"🎁 Бонус: <b>+{DAILY_BONUS} {CURRENCY}</b>\n"
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
            """UPDATE users SET balance = balance + ?, last_daily = ?
               WHERE user_id=? AND last_daily <= ?
               RETURNING balance""",
            (DAILY_BONUS, now, uid, now - DAILY_COOLDOWN),
        ).fetchone()
        if not row:
            bot.answer_callback_query(call.id, "⏳ Бонус уже получен", show_alert=True)
            return
        bot.answer_callback_query(call.id, f"🎁 +{DAILY_BONUS} {CURRENCY}", show_alert=True)
        safe_edit(
            call.message.chat.id,
            call.message.message_id,
            f"🎁 Бонус получен!\n💵 Баланс: <b>{fmt_money(row['balance'])} {CURRENCY}</b>",
            parse_mode="HTML",
            reply_markup=main_menu(),
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
        payout = bet * SLOT_MULT[result[0]]
        add_balance(uid, payout)
        log_game(uid, bet, payout - bet)
        result_text = f"🎉 <b>ДЖЕКПОТ!</b>\n💰 Выигрыш: <b>+{fmt_money(payout)} {CURRENCY}</b>"
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
        cash = int(bet * mult)
        keyboard.add(InlineKeyboardButton(f"💰 Забрать {cash} {CURRENCY}", callback_data="mine:cash"))

    if count:
        mult = MINES_MULT[min(count - 1, len(MINES_MULT) - 1)]
    else:
        mult = 1.0
    potential = int(bet * mult)
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
            payout = int(game["bet"] * mult)
            bet = game["bet"]
            chat_id = game["chat_id"]
            msg_id = game["message_id"]
            snapshot = {"bet": bet, "bombs": set(game["bombs"]), "opened": set(game["opened"])}
            mines_games.pop(uid, None)

            add_balance(uid, payout)
            log_game(uid, bet, payout - bet)
            user = get_user(uid)

            bot.answer_callback_query(call.id, "💰 Забрано!")
            safe_edit(
                chat_id, msg_id,
                f"💰 <b>Выигрыш забран!</b>\n\n"
                f"📈 Множитель: <b>x{mult:.2f}</b>\n"
                f"🎉 Выплата: <b>{payout} {CURRENCY}</b>\n"
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

        if index in game["bombs"]:
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

        game["opened"].add(index)
        count = len(game["opened"])

        if count >= MINES_GOAL:
            mult = MINES_MULT[-1]
            payout = int(game["bet"] * mult)
            bet = game["bet"]
            chat_id = game["chat_id"]
            msg_id = game["message_id"]
            snapshot = {"bet": bet, "bombs": set(game["bombs"]), "opened": set(game["opened"])}
            mines_games.pop(uid, None)

            add_balance(uid, payout)
            log_game(uid, bet, payout - bet)
            user = get_user(uid)
            bot.answer_callback_query(call.id, f"🎉 +{payout} {CURRENCY}")
            safe_edit(
                chat_id, msg_id,
                f"🎉 <b>Победа!</b>\n\n"
                f"📈 Множитель: <b>x{mult:.2f}</b>\n"
                f"💰 Выигрыш: <b>{payout} {CURRENCY}</b>\n"
                f"💵 Баланс: <b>{fmt_money(user['balance'])} {CURRENCY}</b>",
                parse_mode="HTML",
                reply_markup=render_mines(snapshot, reveal=True)[1],
            )
            return

        # продолжаем
        bot.answer_callback_query(call.id, "💎 Безопасно!")
        text, kb = render_mines(game)
        safe_edit(game["chat_id"], game["message_id"], text, parse_mode="HTML", reply_markup=kb)


# ==================== CRASH ====================
def crash_multiplier(game):
    elapsed = time.monotonic() - game["started_at"]
    return min(CRASH_MAX, 1.0 + elapsed * CRASH_GROWTH)


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
            "crash_at": random.uniform(1.3, CRASH_MAX),
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

    bot.answer_callback_query(call.id, f"💰 +{payout} {CURRENCY}")
    safe_edit(
        chat_id, msg_id,
        f"💰 <b>Забрал!</b>\n\n"
        f"📈 Множитель: <b>{mult:.2f}x</b>\n"
        f"🎉 Выплата: <b>{payout} {CURRENCY}</b>\n"
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
