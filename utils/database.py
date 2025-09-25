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

async def execute_query(query: str, params: list = None, debug_info: dict = None):
    """SQLクエリを実行して結果を返す"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # デバッグ情報設定（統一）
        if debug_info is not None and "step2_sql_execution" in debug_info:
            debug_info["step2_sql_execution"]["sql_query"] = query
            debug_info["step2_sql_execution"]["sql_params"] = params
        
        if params:
            # パラメータ展開済みSQL生成
            executable_sql = cursor.mogrify(query, params).decode('utf-8')
            # executable_sql を即座に設定（execute前）
            if debug_info is not None and "step2_sql_execution" in debug_info:
                debug_info["step2_sql_execution"]["executable_sql"] = executable_sql
            cursor.execute(query, params)
        else:
            executable_sql = query
            # executable_sql を即座に設定（execute前）
            if debug_info is not None and "step2_sql_execution" in debug_info:
                debug_info["step2_sql_execution"]["executable_sql"] = executable_sql
            cursor.execute(query)
        
        results = cursor.fetchall()
        cursor.close()
        conn.close()
        
        # デバッグ情報設定（統一）
        if debug_info is not None and "step2_sql_execution" in debug_info:
            debug_info["step2_sql_execution"]["results_count"] = len(results)
        
        # 辞書形式で返却
        return [dict(row) for row in results]
        
    except Exception as e:
        logger.error(f"Query execution failed: {e}")
        raise
