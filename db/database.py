import mysql.connector
from mysql.connector import pooling
from core.config import DB_CONFIG

db_pool = pooling.MySQLConnectionPool(
    pool_name="tarteel_pool",
    pool_size=5,
    **DB_CONFIG
)

def get_db_connection():
    """Returns a connection from the connection pool."""
    return db_pool.get_connection()
