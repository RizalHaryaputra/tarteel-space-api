import sys
from pathlib import Path
import mysql.connector

# Add root folder to sys.path to enable imports
sys.path.append(str(Path(__file__).resolve().parent.parent))

from core.config import DB_CONFIG

def run_migration():
    print("[Migration] Memulai migrasi penghapusan kolom tajweed_grade dan ai_explanation...")
    db = mysql.connector.connect(**DB_CONFIG)
    cursor = db.cursor()

    try:
        cursor.execute("DESCRIBE evaluations")
        columns = [row[0] for row in cursor.fetchall()]
        print(f"[Migration] Kolom saat ini: {columns}")

        if "tajweed_grade" in columns:
            print("[Migration] Menghapus kolom 'tajweed_grade'...")
            cursor.execute("ALTER TABLE evaluations DROP COLUMN tajweed_grade")
            print("[Migration] Kolom 'tajweed_grade' berhasil dihapus.")
        else:
            print("[Migration] Kolom 'tajweed_grade' tidak ditemukan.")

        if "ai_explanation" in columns:
            print("[Migration] Menghapus kolom 'ai_explanation'...")
            cursor.execute("ALTER TABLE evaluations DROP COLUMN ai_explanation")
            print("[Migration] Kolom 'ai_explanation' berhasil dihapus.")
        else:
            print("[Migration] Kolom 'ai_explanation' tidak ditemukan.")

        db.commit()
        print("[Migration] Migrasi berhasil diselesaikan!")

    except Exception as e:
        db.rollback()
        print(f"[Migration] Gagal menjalankan migrasi: {e}")
        raise e
    finally:
        cursor.close()
        db.close()

if __name__ == "__main__":
    run_migration()

