import sys
from pathlib import Path

# Add root folder to sys.path to enable imports
sys.path.append(str(Path(__file__).resolve().parent.parent))

from db.database import get_db_connection

def run_migration():
    print("[Migration v4] Memulai migrasi fitur status training dataset pool...")
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # 1. Alter dataset_pool table: add is_used_for_training
        cursor.execute("DESCRIBE dataset_pool")
        dataset_pool_columns = [row[0] for row in cursor.fetchall()]
        if "is_used_for_training" not in dataset_pool_columns:
            print("[Migration v4] Menambahkan kolom 'is_used_for_training' ke tabel 'dataset_pool'...")
            cursor.execute("ALTER TABLE dataset_pool ADD COLUMN is_used_for_training TINYINT(1) NOT NULL DEFAULT 0")
            print("[Migration v4] Kolom 'is_used_for_training' berhasil ditambahkan.")
        else:
            print("[Migration v4] Kolom 'is_used_for_training' sudah ada di tabel 'dataset_pool'.")

        conn.commit()
        print("[Migration v4] Migrasi database selesai dengan sukses!")

    except Exception as e:
        conn.rollback()
        print(f"[Migration v4] Migrasi gagal: {e}")
        sys.exit(1)
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    run_migration()
