import sqlite3

conn = sqlite3.connect("test.db")       # 连接数据库（没有就创建这个文件）
cur = conn.cursor()                     # 拿操作手柄

# 建表：messages，三列
cur.execute("""CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,   
    role TEXT NOT NULL,                      
    content TEXT NOT NULL                    
)""")

# 插入两行
cur.execute("INSERT INTO messages (role, content) VALUES (?, ?)", ("user", "你好"))
cur.execute("INSERT INTO messages (role, content) VALUES (?, ?)", ("assistant", "你好！我是学习助手"))
conn.commit()                            # 提交！不提交 = 没写盘

# 查出来
cur.execute("SELECT id, role, content FROM messages")
for row in cur.fetchall():
    print(row)

conn.close()                             # 关闭