import sqlite3

def add_columns():
    try:
        conn = sqlite3.connect('mathvis.db')
        c = conn.cursor()
        
        # Check if columns already exist
        c.execute("PRAGMA table_info(videos)")
        columns = [info[1] for info in c.fetchall()]
        
        if 'category_l1' not in columns:
            c.execute("ALTER TABLE videos ADD COLUMN category_l1 VARCHAR")
            print("Added column 'category_l1'.")
        else:
            print("Column 'category_l1' already exists.")
            
        if 'category_l2' not in columns:
            c.execute("ALTER TABLE videos ADD COLUMN category_l2 VARCHAR")
            print("Added column 'category_l2'.")
        else:
            print("Column 'category_l2' already exists.")
            
        conn.commit()
    except Exception as e:
        print(f"Error during migration: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    print("Migrating categories...")
    add_columns()
    print("Migration finished.")
