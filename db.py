import sqlite3
import os
DB_PATH = os.getenv("DB_PATH", "chat.db")


def init_db():
    """建表（第一次运行时调用）"""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        conversation_id TEXT NOT NULL,   -- 哪段对话
        role TEXT NOT NULL,
        content TEXT NOT NULL
    )""")
    conn.commit()
    conn.close()


def save_message(conversation_id, role, content):
    """存一条消息"""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO messages (conversation_id, role, content) VALUES (?, ?, ?)",
        (conversation_id, role, content),
    )
    conn.commit()
    conn.close()


def load_history(conversation_id, limit=20):
    """取某段对话最近的 limit 条（SQL 版滑动窗口）"""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        "SELECT role, content FROM messages WHERE conversation_id = ? ORDER BY id DESC LIMIT ?",
        (conversation_id, limit),
    )
    rows = cur.fetchall()
    conn.close()
    return [{"role": r[0], "content": r[1]} for r in reversed(rows)]
