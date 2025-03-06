import sqlite3

# Подключение к базе данных
conn = sqlite3.connect('bot.db', check_same_thread=False)
cursor = conn.cursor()

# Создание таблиц
cursor.execute('''
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    phone TEXT NOT NULL UNIQUE,
    name TEXT,
    role TEXT NOT NULL DEFAULT 'client'
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category TEXT NOT NULL,
    description TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'free',
    client_id INTEGER NOT NULL,
    worker_id INTEGER,
    is_deleted INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (client_id) REFERENCES users (user_id),
    FOREIGN KEY (worker_id) REFERENCES users (user_id)
)
''')

conn.commit()

# Функции для работы с базой данных
def add_user(user_id, phone, name=None, role='client'):
    cursor.execute('INSERT INTO users (user_id, phone, name, role) VALUES (?, ?, ?, ?)', (user_id, phone, name, role))
    conn.commit()

def get_user_by_user_id(user_id):
    cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
    return cursor.fetchone()

def get_user_by_phone(phone):
    cursor.execute('SELECT * FROM users WHERE phone = ?', (phone,))
    return cursor.fetchone()

def add_request(category, description, client_id):
    cursor.execute('INSERT INTO requests (category, description, client_id) VALUES (?, ?, ?)', (category, description, client_id))
    conn.commit()

def get_available_requests():
    cursor.execute('SELECT * FROM requests WHERE status = "free" AND is_deleted = 0')
    return cursor.fetchall()

def take_request(request_id, worker_id):
    cursor.execute('UPDATE requests SET status = "in_progress", worker_id = ? WHERE id = ?', (worker_id, request_id))
    conn.commit()

def get_user_requests(user_id):
    cursor.execute('SELECT * FROM requests WHERE client_id = ? AND is_deleted = 0', (user_id,))
    return cursor.fetchall()

def add_worker(user_id, phone):
    cursor.execute('INSERT INTO users (user_id, phone, role) VALUES (?, ?, "worker")', (user_id, phone))
    conn.commit()

def get_all_workers():
    cursor.execute('SELECT * FROM users WHERE role = "worker"')
    return cursor.fetchall()

def delete_worker(worker_id):
    cursor.execute('DELETE FROM users WHERE user_id = ?', (worker_id,))
    conn.commit()

def get_all_requests(include_deleted=False):
    if include_deleted:
        cursor.execute('SELECT * FROM requests')
    else:
        cursor.execute('SELECT * FROM requests WHERE is_deleted = 0')
    return cursor.fetchall()

def delete_request(request_id):
    cursor.execute('UPDATE requests SET is_deleted = 1 WHERE id = ?', (request_id,))
    conn.commit()

def get_request_by_id(request_id):
    cursor.execute('SELECT * FROM requests WHERE id = ?', (request_id,))
    return cursor.fetchone()