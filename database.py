import sqlite3
import json

# إنشاء الاتصال بقاعدة البيانات
conn = sqlite3.connect('bot_database.db', check_same_thread=False)
cursor = conn.cursor()

# إنشاء الجداول لو مش موجودة
cursor.execute('''
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    points INTEGER DEFAULT 0,
    promo_done INTEGER DEFAULT 0,
    last_checkin TEXT
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS referrals (
    user_id INTEGER,
    referrer_id INTEGER
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS promo_submissions (
    user_id INTEGER,
    promo_id TEXT,
    screenshot_id TEXT,
    reviewed INTEGER DEFAULT 0,
    accepted INTEGER DEFAULT 0
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS withdrawals (
    user_id INTEGER,
    number TEXT,
    amount INTEGER,
    status TEXT DEFAULT 'pending'
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS temp_states (
    user_id INTEGER PRIMARY KEY,
    state TEXT,
    data TEXT
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS task_submissions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    id_text TEXT,
    screenshot_id TEXT,
    task_title TEXT,
    reviewed INTEGER DEFAULT 0,
    accepted INTEGER DEFAULT 0
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT,
    points INTEGER
)
''')

conn.commit()

# -----------------------------
# دوال المستخدمين
# -----------------------------
def register_user(user_id, username, referrer_id=None):
    cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
    exists = cursor.fetchone()
    if not exists:
        cursor.execute("INSERT INTO users (user_id, username) VALUES (?, ?)", (user_id, username))
        if referrer_id:
            cursor.execute("INSERT INTO referrals (user_id, referrer_id) VALUES (?, ?)", (user_id, referrer_id))
        conn.commit()
        return True
    return False

def get_points(user_id):
    cursor.execute("SELECT points FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    return row[0] if row else 0

def add_points(user_id, amount):
    cursor.execute("UPDATE users SET points = points + ? WHERE user_id = ?", (amount, user_id))
    conn.commit()

def reset_user_points(user_id):
    cursor.execute("UPDATE users SET points = 0 WHERE user_id = ?", (user_id,))
    conn.commit()

# -----------------------------
# دوال البريمو
# -----------------------------
def has_done_promo(user_id):
    cursor.execute("SELECT promo_done FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    return row[0] == 1 if row else False

def mark_promo_done(user_id):
    cursor.execute("UPDATE users SET promo_done = 1 WHERE user_id = ?", (user_id,))
    conn.commit()

def save_promo_submission(user_id, promo_id, screenshot_id):
    cursor.execute("INSERT INTO promo_submissions (user_id, promo_id, screenshot_id) VALUES (?, ?, ?)", (user_id, promo_id, screenshot_id))
    conn.commit()

def get_pending_promos():
    cursor.execute("SELECT user_id, promo_id, screenshot_id FROM promo_submissions WHERE reviewed = 0")
    return cursor.fetchall()

def approve_promo(user_id):
    cursor.execute("UPDATE promo_submissions SET reviewed = 1, accepted = 1 WHERE user_id = ?", (user_id,))
    mark_promo_done(user_id)
    conn.commit()

def reject_promo(user_id):
    cursor.execute("UPDATE promo_submissions SET reviewed = 1, accepted = 0 WHERE user_id = ?", (user_id,))
    conn.commit()

# -----------------------------
# دوال المهام اليومية
# -----------------------------
def has_checked_in_today(user_id, today):
    cursor.execute("SELECT last_checkin FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    return row and row[0] == today

def update_daily_checkin(user_id, today):
    cursor.execute("UPDATE users SET last_checkin = ? WHERE user_id = ?", (today, user_id))
    conn.commit()

# -----------------------------
# دوال الحالة المؤقتة
# -----------------------------
def set_temp_state(user_id, state):
    cursor.execute("INSERT OR REPLACE INTO temp_states (user_id, state, data) VALUES (?, ?, ?)", (user_id, state, json.dumps({})))
    conn.commit()

def get_temp_state(user_id):
    cursor.execute("SELECT state FROM temp_states WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    return row[0] if row else None

def clear_temp_state(user_id):
    cursor.execute("DELETE FROM temp_states WHERE user_id = ?", (user_id,))
    conn.commit()

def set_temp_data(user_id, data: dict):
    cursor.execute("UPDATE temp_states SET data = ? WHERE user_id = ?", (json.dumps(data), user_id))
    conn.commit()

def get_temp_data(user_id):
    cursor.execute("SELECT data FROM temp_states WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    return json.loads(row[0]) if row and row[0] else {}

# -----------------------------
# دوال السحب
# -----------------------------
def get_pending_withdrawals():
    cursor.execute("SELECT user_id, number, amount FROM withdrawals WHERE status = 'pending'")
    return cursor.fetchall()

def confirm_withdraw(user_id):
    cursor.execute("UPDATE withdrawals SET status = 'confirmed' WHERE user_id = ?", (user_id,))
    conn.commit()

def cancel_withdraw(user_id):
    cursor.execute("UPDATE withdrawals SET status = 'cancelled' WHERE user_id = ?", (user_id,))
    conn.commit()

# -----------------------------
# دوال المهام العامة
# -----------------------------
def add_task_to_db(title, points):
    cursor.execute("INSERT INTO tasks (title, points) VALUES (?, ?)", (title, points))
    conn.commit()

def get_all_users():
    cursor.execute("SELECT user_id FROM users")
    return [row[0] for row in cursor.fetchall()]

def save_task_submission(user_id, id_value, screenshot_id, task_title):
    cursor.execute(
        "INSERT INTO task_submissions (user_id, id_text, screenshot_id, task_title, reviewed, accepted) VALUES (?, ?, ?, ?, 0, 0)",
        (user_id, id_value, screenshot_id, task_title)
    )
    conn.commit()

def mark_task_as_approved(user_id, task_title):
    cursor.execute('''
        UPDATE task_submissions
        SET reviewed = 1, accepted = 1
        WHERE user_id = ? AND task_title = ?
    ''', (user_id, task_title))
    conn.commit()

def get_task_title_from_callback(caption):
    for line in caption.split('\n'):
        if line.startswith("📝"):
            return line.replace("📝", "").strip()
    return ""
