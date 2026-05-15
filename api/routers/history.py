from typing import List
from fastapi import APIRouter, Depends
from api.deps import get_db, get_current_user
from schemas.history import HistoryItem, DashboardStats

router = APIRouter(prefix="/history", tags=["Riwayat & Dashboard"])

@router.get("/", response_model=List[HistoryItem])
def get_history(
    limit: int = 20,
    offset: int = 0,
    current_user: dict = Depends(get_current_user),
    db=Depends(get_db),
):
    cursor = db.cursor(dictionary=True)
    cursor.execute(
        """
        SELECT e.id, h.base_letter, h.harakat, h.arabic_script,
               e.accuracy_score, e.is_correct,
               CAST(e.created_at AS CHAR) AS created_at
        FROM evaluations e
        JOIN hijaiyah_letters h ON e.letter_id = h.id
        WHERE e.user_id = %s
        ORDER BY e.created_at DESC
        LIMIT %s OFFSET %s
        """,
        (current_user["id"], limit, offset)
    )
    return cursor.fetchall()

@router.get("/weekly")
def get_weekly_scores(current_user: dict = Depends(get_current_user), db=Depends(get_db)):
    cursor = db.cursor(dictionary=True)
    cursor.execute(
        """
        SELECT
            DATE(created_at) AS tanggal,
            ROUND(AVG(accuracy_score), 2) AS rata_rata,
            COUNT(*) AS jumlah_latihan
        FROM evaluations
        WHERE user_id = %s
          AND created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)
        GROUP BY DATE(created_at)
        ORDER BY tanggal ASC
        """,
        (current_user["id"],)
    )
    return cursor.fetchall()

@router.get("/dashboard", response_model=DashboardStats)
def get_dashboard(current_user: dict = Depends(get_current_user), db=Depends(get_db)):
    cursor = db.cursor(dictionary=True)
    uid = current_user["id"]

    cursor.execute(
        "SELECT COUNT(*) AS total, ROUND(AVG(accuracy_score),2) AS avg_score FROM evaluations WHERE user_id=%s",
        (uid,)
    )
    stats = cursor.fetchone()

    cursor.execute(
        """
        SELECT h.base_letter, ROUND(AVG(e.accuracy_score),2) AS avg_score
        FROM evaluations e JOIN hijaiyah_letters h ON e.letter_id = h.id
        WHERE e.user_id = %s
        GROUP BY h.base_letter
        HAVING COUNT(*) >= 3
        ORDER BY avg_score ASC LIMIT 1
        """, (uid,)
    )
    lemah = cursor.fetchone()

    cursor.execute(
        """
        SELECT h.base_letter, ROUND(AVG(e.accuracy_score),2) AS avg_score
        FROM evaluations e JOIN hijaiyah_letters h ON e.letter_id = h.id
        WHERE e.user_id = %s
        GROUP BY h.base_letter
        HAVING COUNT(*) >= 3
        ORDER BY avg_score DESC LIMIT 1
        """, (uid,)
    )
    kuat = cursor.fetchone()

    cursor.execute(
        """
        SELECT COUNT(DISTINCT DATE(created_at)) AS streak
        FROM evaluations
        WHERE user_id = %s AND created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)
        """, (uid,)
    )
    streak_row = cursor.fetchone()

    return DashboardStats(
        total_latihan=stats["total"] or 0,
        rata_rata_akurasi=stats["avg_score"] or 0.0,
        streak_hari=streak_row["streak"] or 0,
        huruf_terlemah=lemah["base_letter"] if lemah else None,
        huruf_terkuat=kuat["base_letter"] if kuat else None,
    )
