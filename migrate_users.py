import sqlite3

def migrate_users():
    conn = sqlite3.connect('bisual.db')
    cursor = conn.cursor()
    
    try:
        # Check columns
        cursor.execute("PRAGMA table_info(users)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'role' not in columns:
            print("Adding 'role' column...")
            cursor.execute("ALTER TABLE users ADD COLUMN role TEXT DEFAULT 'teacher'")
        
        if 'is_approved' not in columns:
            print("Adding 'is_approved' column...")
            cursor.execute("ALTER TABLE users ADD COLUMN is_approved BOOLEAN DEFAULT 0")
            
            # Auto-approve existing users (like admin)
            cursor.execute("UPDATE users SET is_approved = 1, role = 'super_admin' WHERE username = 'admin'")
            
        conn.commit()
        print("Migration successful.")
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    migrate_users()
