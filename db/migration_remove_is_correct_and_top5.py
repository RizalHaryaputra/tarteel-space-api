import sys
from pathlib import Path
import mysql.connector

# Add root folder to sys.path to enable imports
sys.path.append(str(Path(__file__).resolve().parent.parent))

from core.config import DB_CONFIG

def run_migration():
    print("[Migration] Memulai migrasi penghapusan kolom is_correct dan top5_predictions...")
    db = mysql.connector.connect(**DB_CONFIG)
    cursor = db.cursor()

    try:
        cursor.execute("DESCRIBE evaluations")
        columns = [row[0] for row in cursor.fetchall()]
        print(f"[Migration] Kolom saat ini: {columns}")

        if "is_correct" in columns:
            print("[Migration] Menghapus kolom 'is_correct'...")
            cursor.execute("ALTER TABLE evaluations DROP COLUMN is_correct")
            print("[Migration] Kolom 'is_correct' berhasil dihapus.")
        else:
            print("[Migration] Kolom 'is_correct' tidak ditemukan.")

        if "top5_predictions" in columns:
            print("[Migration] Menghapus kolom 'top5_predictions'...")
            cursor.execute("ALTER TABLE evaluations DROP COLUMN top5_predictions")
            print("[Migration] Kolom 'top5_predictions' berhasil dihapus.")
        else:
            print("[Migration] Kolom 'top5_predictions' tidak ditemukan.")

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

