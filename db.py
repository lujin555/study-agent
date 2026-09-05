import sqlite3
import os
import json
from datetime import datetime
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
    # 错题本：按设备 ID 归属（前端固定 deviceId，换浏览器看不到）
    cur.execute("""CREATE TABLE IF NOT EXISTS wrong_answers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        device_id TEXT NOT NULL,      -- 归属哪台设备（浏览器）
        question TEXT NOT NULL,       -- 题干
        options TEXT NOT NULL,        -- 4 个选项（JSON 字符串：{"A":..,"B":..}）
        your_answer TEXT NOT NULL,    -- 用户答错的选项（如 "B"）
        correct_answer TEXT NOT NULL, -- 正确答案（如 "C"）
        explain TEXT,                 -- 解析（可空）
        created_at TEXT NOT NULL      -- 记录时间（ISO 字符串）
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


def save_wrong_answer(device_id, question, options, your_answer, correct_answer, explain):
    """存一道错题。options 是 dict（4 个选项），存前序列化成 JSON。"""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO wrong_answers (device_id, question, options, your_answer, correct_answer, explain, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (device_id, question, json.dumps(options, ensure_ascii=False), your_answer,
         correct_answer, explain or "", datetime.now().isoformat()),
    )
    conn.commit()
    conn.close()
    return cur.lastrowid  # 返回新记录的自增 id


def list_wrong_answers(device_id, limit=200):
    """取某设备的错题，按时间倒序（最新在前）。options 是 JSON 串，读出来转回 dict。"""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        "SELECT id, question, options, your_answer, correct_answer, explain, created_at "
        "FROM wrong_answers WHERE device_id = ? ORDER BY id DESC LIMIT ?",
        (device_id, limit),
    )
    rows = cur.fetchall()
    conn.close()
    return [
        {
            "id": r[0],
            "question": r[1],
            "options": json.loads(r[2]),   # JSON 串 → dict
            "your_answer": r[3],
            "correct_answer": r[4],
            "explain": r[5],
            "created_at": r[6],
        }
        for r in rows
    ]
