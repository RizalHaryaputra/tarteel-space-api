import json
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File

from api.deps import get_db, get_current_admin
from services.cloudinary_service import upload_audio_to_cloudinary
from schemas.admin import UserRoleUpdate, LetterCreate, LetterUpdate, DatasetPoolCreate

router = APIRouter(prefix="/admin", tags=["Dashboard Admin"])

# ──────────────────────────────────────────────────────────────────────────
# 1. OVERVIEW & STATS
# ──────────────────────────────────────────────────────────────────────────

@router.get("/stats", dependencies=[Depends(get_current_admin)])
def get_admin_stats(db=Depends(get_db)):
    cursor = db.cursor(dictionary=True)
    
    # 1. Total Users
    cursor.execute("SELECT COUNT(*) AS total FROM users")
    total_users = cursor.fetchone()["total"] or 0
    
    # 2. Total Evaluations
    cursor.execute("SELECT COUNT(*) AS total, ROUND(AVG(accuracy_score), 2) AS avg_accuracy FROM evaluations")
    eval_stats = cursor.fetchone()
    total_evaluations = eval_stats["total"] or 0
    average_accuracy = eval_stats["avg_accuracy"] or 0.0
    
    # 3. Total Feedbacks
    cursor.execute("SELECT COUNT(*) AS total FROM user_feedbacks")
    total_feedbacks = cursor.fetchone()["total"] or 0
    
    # 4. Total Dataset Pool
    cursor.execute("SELECT COUNT(*) AS total FROM dataset_pool")
    total_dataset_pool = cursor.fetchone()["total"] or 0
    
    from datetime import datetime, timedelta
    
    # 5. Daily Trend (Last 7 Days)
    cursor.execute("""
        SELECT DATE_FORMAT(created_at, '%Y-%m-%d') as date, COUNT(*) as count 
        FROM evaluations 
        WHERE created_at >= DATE_SUB(CURDATE(), INTERVAL 6 DAY)
        GROUP BY DATE(created_at)
    """)
    trend_rows = cursor.fetchall()
    trend_dict = {row["date"]: row["count"] for row in trend_rows}
    
    daily_trend = []
    today = datetime.now()
    # Ensure days are ordered from 6 days ago to today
    for i in range(6, -1, -1):
        d = today - timedelta(days=i)
        date_str = d.strftime('%Y-%m-%d')
        # Map weekday to Indonesian short string
        day_names = ["Sen", "Sel", "Rab", "Kam", "Jum", "Sab", "Min"]
        day_str = day_names[d.weekday()]
        
        daily_trend.append({
            "date": date_str,
            "day": day_str,
            "count": trend_dict.get(date_str, 0)
        })
    
    return {
        "total_users": total_users,
        "total_evaluations": total_evaluations,
        "average_accuracy": float(average_accuracy),
        "total_feedbacks": total_feedbacks,
        "total_dataset_pool": total_dataset_pool,
        "daily_trend": daily_trend
    }


# ──────────────────────────────────────────────────────────────────────────
# 2. USER MANAGEMENT
# ──────────────────────────────────────────────────────────────────────────

@router.get("/users", dependencies=[Depends(get_current_admin)])
def get_all_users(limit: int = 50, offset: int = 0, db=Depends(get_db)):
    cursor = db.cursor(dictionary=True)
    cursor.execute(
        """
        SELECT u.id, u.name, u.email, u.role, CAST(u.created_at AS CHAR) AS created_at,
               COUNT(e.id) AS total_evaluations,
               ROUND(AVG(e.accuracy_score), 2) AS average_accuracy
        FROM users u
        LEFT JOIN evaluations e ON u.id = e.user_id
        GROUP BY u.id
        ORDER BY u.created_at DESC
        LIMIT %s OFFSET %s
        """,
        (limit, offset)
    )
    users = cursor.fetchall()
    
    # Cast decimal average_accuracy to float
    for user in users:
        user["average_accuracy"] = float(user["average_accuracy"]) if user["average_accuracy"] else 0.0
        
    return users

@router.patch("/users/{user_id}/role", dependencies=[Depends(get_current_admin)])
def update_user_role(user_id: str, data: UserRoleUpdate, db=Depends(get_db)):
    if data.role not in ("user", "admin"):
        raise HTTPException(400, "Role tidak valid. Gunakan 'user' atau 'admin'.")
        
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT id FROM users WHERE id = %s", (user_id,))
    if not cursor.fetchone():
        raise HTTPException(404, "User tidak ditemukan")
        
    cursor.execute("UPDATE users SET role = %s WHERE id = %s", (data.role, user_id))
    db.commit()
    return {"message": "Role pengguna berhasil diperbarui"}

@router.delete("/users/{user_id}")
def delete_user(user_id: str, current_admin: dict = Depends(get_current_admin), db=Depends(get_db)):
    if user_id == current_admin["id"]:
        raise HTTPException(400, "Anda tidak bisa menghapus akun Anda sendiri.")
        
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT id FROM users WHERE id = %s", (user_id,))
    if not cursor.fetchone():
        raise HTTPException(404, "User tidak ditemukan")
        
    cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))
    db.commit()
    return {"message": "User berhasil dihapus beserta seluruh riwayatnya"}


# ──────────────────────────────────────────────────────────────────────────
# 3. HIJAIYAH LETTERS CRUD
# ──────────────────────────────────────────────────────────────────────────

@router.post("/letters", status_code=201, dependencies=[Depends(get_current_admin)])
def create_letter(letter: LetterCreate, db=Depends(get_db)):
    cursor = db.cursor(dictionary=True)
    
    # Cek unique constraint (base_letter & harakat)
    cursor.execute(
        "SELECT id FROM hijaiyah_letters WHERE base_letter = %s AND harakat = %s",
        (letter.base_letter, letter.harakat)
    )
    if cursor.fetchone():
        raise HTTPException(400, "Huruf hijaiyah dengan kombinasi harakat ini sudah ada.")
        
    cursor.execute(
        """
        INSERT INTO hijaiyah_letters (base_letter, harakat, pronunciation, arabic_script, model_label)
        VALUES (%s, %s, %s, %s, %s)
        """,
        (letter.base_letter, letter.harakat, letter.pronunciation, letter.arabic_script, letter.model_label)
    )
    db.commit()
    return {"message": "Huruf hijaiyah berhasil ditambahkan", "letter_id": cursor.lastrowid}

@router.put("/letters/{letter_id}", dependencies=[Depends(get_current_admin)])
def update_letter(letter_id: int, letter: LetterUpdate, db=Depends(get_db)):
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM hijaiyah_letters WHERE id = %s", (letter_id,))
    existing_letter = cursor.fetchone()
    if not existing_letter:
        raise HTTPException(404, "Huruf tidak ditemukan")
        
    # Build dynamic update statement
    fields = []
    values = []
    
    for key, value in letter.model_dump(exclude_unset=True).items():
        fields.append(f"{key} = %s")
        values.append(value)
        
    if not fields:
        return {"message": "Tidak ada perubahan data"}
        
    values.append(letter_id)
    cursor.execute(f"UPDATE hijaiyah_letters SET {', '.join(fields)} WHERE id = %s", tuple(values))
    db.commit()
    return {"message": "Data huruf hijaiyah berhasil diperbarui"}

@router.delete("/letters/{letter_id}", dependencies=[Depends(get_current_admin)])
def delete_letter(letter_id: int, db=Depends(get_db)):
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT id FROM hijaiyah_letters WHERE id = %s", (letter_id,))
    if not cursor.fetchone():
        raise HTTPException(404, "Huruf tidak ditemukan")
        
    cursor.execute("DELETE FROM hijaiyah_letters WHERE id = %s", (letter_id,))
    db.commit()
    return {"message": "Huruf hijaiyah berhasil dihapus"}


# ──────────────────────────────────────────────────────────────────────────
# 4. REFERENCE AUDIO UPLOAD
# ──────────────────────────────────────────────────────────────────────────

@router.post("/letters/{letter_id}/audio", dependencies=[Depends(get_current_admin)])
async def upload_reference_audio(letter_id: int, audio: UploadFile = File(...), db=Depends(get_db)):
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM hijaiyah_letters WHERE id = %s", (letter_id,))
    letter = cursor.fetchone()
    if not letter:
        raise HTTPException(404, "Huruf tidak ditemukan")
        
    # Read audio bytes
    audio_bytes = await audio.read()
    if len(audio_bytes) < 100:
        raise HTTPException(400, "File audio tidak valid")
        
    filename = f"ustadz_ref_{letter_id}"
    
    # Upload to Cloudinary
    audio_url = upload_audio_to_cloudinary(audio_bytes, filename, folder="letters_reference")
    
    # Save to database
    cursor.execute("UPDATE hijaiyah_letters SET audio_url = %s WHERE id = %s", (audio_url, letter_id))
    db.commit()
    
    return {"message": "Audio referensi berhasil diunggah", "audio_url": audio_url}


# ──────────────────────────────────────────────────────────────────────────
# 5. USER FEEDBACKS & DATASET POOL
# ──────────────────────────────────────────────────────────────────────────

@router.get("/feedbacks", dependencies=[Depends(get_current_admin)])
def get_user_feedbacks(limit: int = 50, offset: int = 0, db=Depends(get_db)):
    cursor = db.cursor(dictionary=True)
    cursor.execute(
        """
        SELECT f.id AS feedback_id, f.comment, CAST(f.created_at AS CHAR) AS created_at,
               u.name AS user_name, u.email AS user_email,
               e.id AS evaluation_id, e.accuracy_score, e.top_prediction, e.top5_predictions, e.is_correct, e.audio_path AS audio_url, e.is_verified,
               h.base_letter, h.harakat, h.arabic_script, h.pronunciation
        FROM user_feedbacks f
        JOIN users u ON f.user_id = u.id
        JOIN evaluations e ON f.evaluation_id = e.id
        JOIN hijaiyah_letters h ON e.letter_id = h.id
        ORDER BY f.created_at DESC
        LIMIT %s OFFSET %s
        """,
        (limit, offset)
    )
    feedbacks = cursor.fetchall()
    
    for fb in feedbacks:
        fb["accuracy_score"] = float(fb["accuracy_score"])
        # Parse top5_predictions
        if fb.get("top5_predictions"):
            try:
                fb["top5_predictions"] = json.loads(fb["top5_predictions"])
            except Exception:
                fb["top5_predictions"] = []
        else:
            fb["top5_predictions"] = []
            
    return feedbacks

@router.post("/dataset-pool", dependencies=[Depends(get_current_admin)])
def add_to_dataset_pool(data: DatasetPoolCreate, db=Depends(get_db)):
    cursor = db.cursor(dictionary=True)
    
    # Verify evaluation exists
    cursor.execute("SELECT id FROM evaluations WHERE id = %s", (data.evaluation_id,))
    if not cursor.fetchone():
        raise HTTPException(404, "Evaluasi tidak ditemukan")
        
    try:
        # Insert or Update if already exists
        cursor.execute(
            """
            INSERT INTO dataset_pool (evaluation_id, verified_label, is_verified_correct, admin_notes)
            VALUES (%s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                verified_label = VALUES(verified_label),
                is_verified_correct = VALUES(is_verified_correct),
                admin_notes = VALUES(admin_notes)
            """,
            (data.evaluation_id, data.verified_label, int(data.is_verified_correct), data.admin_notes)
        )
        
        # Mark evaluation as verified
        cursor.execute("UPDATE evaluations SET is_verified = 1 WHERE id = %s", (data.evaluation_id,))
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(500, f"Gagal menambahkan ke dataset pool: {str(e)}")
        
    return {"message": "Evaluasi berhasil diverifikasi dan ditambahkan ke dataset pool"}

@router.get("/dataset-pool/export", dependencies=[Depends(get_current_admin)])
def export_dataset_pool(db=Depends(get_db)):
    cursor = db.cursor(dictionary=True)
    cursor.execute(
        """
        SELECT dp.id, dp.evaluation_id, dp.verified_label, dp.is_verified_correct, dp.admin_notes,
               CAST(dp.created_at AS CHAR) AS verified_at,
               e.audio_path AS audio_url, e.accuracy_score, e.top_prediction,
               h.base_letter, h.harakat, h.model_label AS original_target_label
        FROM dataset_pool dp
        JOIN evaluations e ON dp.evaluation_id = e.id
        JOIN hijaiyah_letters h ON e.letter_id = h.id
        ORDER BY dp.created_at DESC
        """
    )
    dataset = cursor.fetchall()
    
    for item in dataset:
        item["accuracy_score"] = float(item["accuracy_score"])
        
    return dataset
