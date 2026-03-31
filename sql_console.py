import sqlite3

conn = sqlite3.connect("dnsbot.db")
cur = conn.cursor()

while True:
    q = input("SQL> ")
    if q.lower() in ["exit","quit"]:
        break

    try:
        cur.execute(q)
        rows = cur.fetchall()
        for r in rows:
            print(r)
        conn.commit()
    except Exception as e:
        print("Error:", e)