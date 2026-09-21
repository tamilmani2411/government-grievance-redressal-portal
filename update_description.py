import sqlite3

conn = sqlite3.connect("database.db")
cursor = conn.cursor()

cursor.execute(
    "UPDATE grievances SET description = ?",
    ("Street light not working properly",)
)

conn.commit()
conn.close()

print("Description updated successfully")