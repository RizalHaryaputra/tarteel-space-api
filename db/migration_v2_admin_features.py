import sys
from pathlib import Path

# Add root folder to sys.path to enable imports
sys.path.append(str(Path(__file__).resolve().parent.parent))

from db.database import get_db_connection

def run_migration():
    print("[Migration v2] Memulai migrasi database fitur admin...")
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # 1. Alter users table: add role
        cursor.execute("DESCRIBE users")
        user_columns = [row[0] for row in cursor.fetchall()]
        if "role" not in user_columns:
            print("[Migration v2] Menambahkan kolom 'role' ke tabel 'users'...")
            cursor.execute("ALTER TABLE users ADD COLUMN role VARCHAR(20) NOT NULL DEFAULT 'user'")
            print("[Migration v2] Kolom 'role' berhasil ditambahkan.")
        else:
            print("[Migration v2] Kolom 'role' sudah ada di tabel 'users'.")

        # 2. Alter hijaiyah_letters table: add audio_url
        cursor.execute("DESCRIBE hijaiyah_letters")
        letter_columns = [row[0] for row in cursor.fetchall()]
        if "audio_url" not in letter_columns:
            print("[Migration v2] Menambahkan kolom 'audio_url' ke tabel 'hijaiyah_letters'...")
            cursor.execute("ALTER TABLE hijaiyah_letters ADD COLUMN audio_url VARCHAR(500) DEFAULT NULL")
            print("[Migration v2] Kolom 'audio_url' berhasil ditambahkan.")
        else:
            print("[Migration v2] Kolom 'audio_url' sudah ada di tabel 'hijaiyah_letters'.")

        # 3. Alter evaluations table: add top5_predictions and is_verified
        cursor.execute("DESCRIBE evaluations")
        eval_columns = [row[0] for row in cursor.fetchall()]
        if "top5_predictions" not in eval_columns:
            print("[Migration v2] Menambahkan kolom 'top5_predictions' ke tabel 'evaluations'...")
            cursor.execute("ALTER TABLE evaluations ADD COLUMN top5_predictions TEXT DEFAULT NULL")
            print("[Migration v2] Kolom 'top5_predictions' berhasil ditambahkan.")
        else:
            print("[Migration v2] Kolom 'top5_predictions' sudah ada di tabel 'evaluations'.")

        if "is_verified" not in eval_columns:
            print("[Migration v2] Menambahkan kolom 'is_verified' ke tabel 'evaluations'...")
            cursor.execute("ALTER TABLE evaluations ADD COLUMN is_verified TINYINT(1) NOT NULL DEFAULT 0")
            print("[Migration v2] Kolom 'is_verified' berhasil ditambahkan.")
        else:
            print("[Migration v2] Kolom 'is_verified' sudah ada di tabel 'evaluations'.")

        # 4. Create user_feedbacks table if not exists
        print("[Migration v2] Membuat tabel 'user_feedbacks' jika belum ada...")
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS `user_feedbacks` (
              `id` CHAR(36) NOT NULL DEFAULT (uuid()),
              `evaluation_id` CHAR(36) NOT NULL,
              `user_id` CHAR(36) NOT NULL,
              `comment` TEXT NOT NULL,
              `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
              PRIMARY KEY (`id`),
              KEY `idx_feedback_eval` (`evaluation_id`),
              KEY `idx_feedback_user` (`user_id`),
              CONSTRAINT `fk_feedback_eval` FOREIGN KEY (`evaluation_id`) REFERENCES `evaluations` (`id`) ON DELETE CASCADE,
              CONSTRAINT `fk_feedback_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
            """
        )
        print("[Migration v2] Tabel 'user_feedbacks' siap.")

        # 5. Create dataset_pool table if not exists
        print("[Migration v2] Membuat tabel 'dataset_pool' jika belum ada...")
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS `dataset_pool` (
              `id` INT AUTO_INCREMENT,
              `evaluation_id` CHAR(36) NOT NULL,
              `verified_label` VARCHAR(100) NOT NULL,
              `is_verified_correct` TINYINT(1) NOT NULL DEFAULT 1,
              `admin_notes` TEXT DEFAULT NULL,
              `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
              PRIMARY KEY (`id`),
              UNIQUE KEY `uq_dataset_eval` (`evaluation_id`),
              CONSTRAINT `fk_dataset_eval` FOREIGN KEY (`evaluation_id`) REFERENCES `evaluations` (`id`) ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
            """
        )
        print("[Migration v2] Tabel 'dataset_pool' siap.")

        conn.commit()
        print("[Migration v2] Migrasi database selesai dengan sukses!")

    except Exception as e:
        conn.rollback()
        print(f"[Migration v2] Migrasi gagal: {e}")
        sys.exit(1)
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    run_migration()
