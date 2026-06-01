import sys
from pathlib import Path

# Add root folder to sys.path to enable imports
sys.path.append(str(Path(__file__).resolve().parent.parent))

from db.database import get_db_connection

def run_migration():
    print("[Migration] Memulai migrasi database...")
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Check existing columns in evaluations table
        cursor.execute("DESCRIBE evaluations")
        columns = [row[0] for row in cursor.fetchall()]
        print(f"[Migration] Kolom saat ini: {columns}")

        # Add top3_predictions column if not exists
        if "top3_predictions" not in columns:
            print("[Migration] Menambahkan kolom 'top3_predictions'...")
            cursor.execute("ALTER TABLE evaluations ADD COLUMN top3_predictions TEXT DEFAULT NULL COMMENT 'JSON dari 3 prediksi teratas model'")
            print("[Migration] Kolom 'top3_predictions' berhasil ditambahkan.")
        else:
            print("[Migration] Kolom 'top3_predictions' sudah ada.")

        # Add tajweed_grade column if not exists
        if "tajweed_grade" not in columns:
            print("[Migration] Menambahkan kolom 'tajweed_grade'...")
            cursor.execute("ALTER TABLE evaluations ADD COLUMN tajweed_grade VARCHAR(50) DEFAULT NULL COMMENT 'Predikat tajwid: Mumtaz, dll'")
            print("[Migration] Kolom 'tajweed_grade' berhasil ditambahkan.")
        else:
            print("[Migration] Kolom 'tajweed_grade' sudah ada.")

        conn.commit()
        print("[Migration] Migrasi database selesai dengan sukses!")

    except Exception as e:
        conn.rollback()
        print(f"[Migration] Migrasi gagal: {e}")
        sys.exit(1)
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    run_migration()
