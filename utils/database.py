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

async def get_system_prompt(prompt_key: str) -> str:
    """システムプロンプトをデータベースから取得"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute(
            "SELECT prompt_text FROM system_prompts WHERE prompt_key = %s",
            (prompt_key,)
        )
        
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if result:
            return result['prompt_text']
        else:
            logger.warning(f"System prompt not found: {prompt_key}")
            return f"システムプロンプト '{prompt_key}' が見つかりません。"
            
    except Exception as e:
        logger.error(f"Failed to get system prompt {prompt_key}: {e}")
        return f"システムプロンプト取得エラー: {str(e)}"
