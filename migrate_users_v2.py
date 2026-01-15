import sqlite3

def migrate_db():
    conn = sqlite3.connect("bisual.db")
    cursor = conn.cursor()
    
    columns = [
        ("first_name", "TEXT"),
        ("last_name", "TEXT"),
        ("email", "TEXT"),
        ("phone", "TEXT")
    ]
    
    for col_name, col_type in columns:
        try:
            cursor.execute(f"ALTER TABLE users ADD COLUMN {col_name} {col_type}")
            print(f"Added column: {col_name}")
        except sqlite3.OperationalError as e:
            print(f"Column {col_name} already exists or error: {e}")
            
    conn.commit()
    conn.close()
    print("Migration V2 (User Profile) completed.")

if __name__ == "__main__":
    migrate_db()
