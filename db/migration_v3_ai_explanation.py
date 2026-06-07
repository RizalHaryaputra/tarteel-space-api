import mysql.connector
from core.config import DB_CONFIG

def migrate():
    print("Connecting to database...")
    db = mysql.connector.connect(**DB_CONFIG)
    cursor = db.cursor()
    
    print("Adding ai_explanation column to evaluations table...")
    try:
        cursor.execute("ALTER TABLE evaluations ADD COLUMN ai_explanation TEXT DEFAULT NULL;")
        db.commit()
        print("Successfully added ai_explanation column.")
    except mysql.connector.Error as err:
        if err.errno == 1060: # Duplicate column name
            print("Column ai_explanation already exists.")
        else:
            print(f"Error: {err}")
    finally:
        cursor.close()
        db.close()

if __name__ == "__main__":
    migrate()
