# ProductMaster MCP Database Utilities

import psycopg2
from psycopg2.extras import RealDictCursor
from config import DB_CONFIG
import logging

logger = logging.getLogger(__name__)

def get_db_connection():
    """データベース接続を取得"""
    try:
        return psycopg2.connect(**DB_CONFIG)
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        raise

async def execute_query(query: str, params: list = None):
    """SQLクエリを実行して結果を返す"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        
        results = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        # 辞書形式で返却
        return [dict(row) for row in results]
        
    except Exception as e:
        logger.error(f"Query execution failed: {e}")
        raise
