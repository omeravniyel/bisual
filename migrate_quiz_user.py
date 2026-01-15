import sqlite3

def migrate_quiz_user():
    conn = sqlite3.connect('bisual.db')
    cursor = conn.cursor()
    
    try:
        cursor.execute("PRAGMA table_info(quizzes)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'user_id' not in columns:
            print("Adding 'user_id' column to 'quizzes' table...")
            # Add column, nullable first to avoid constraint errors on existing data
            cursor.execute("ALTER TABLE quizzes ADD COLUMN user_id INTEGER REFERENCES users(id)")
            
            # Link existing quizzes to admin (id=1)
            cursor.execute("UPDATE quizzes SET user_id = 1 WHERE user_id IS NULL")
            
            conn.commit()
            print("Migration successful.")
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    migrate_quiz_user()
