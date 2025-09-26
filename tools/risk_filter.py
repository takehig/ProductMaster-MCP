import time
import json
import logging
from typing import Dict, Any
from models import MCPResponse
from utils.llm_util import LLMUtil
from utils.system_prompt import get_system_prompt
from utils.database import execute_query

logger = logging.getLogger(__name__)

async def filter_products_by_risk_and_type(params: Dict[str, Any]) -> MCPResponse:
    """リスクレベル・種別による商品フィルタリング"""
    start_time = time.time()
    
    # デバッグ情報初期化
    tool_debug = {
        "function_name": "filter_products_by_risk_and_type",
        "input_params": params,
        "step1_extract_conditions": {
            "llm_request": None,
            "llm_response": None,
            "parsed_conditions": None,
            "execution_time_ms": 0
        },
        "step2_sql_execution": {
            "sql_query": None,
            "sql_params": None,
            "executable_sql": None,
            "results_count": 0,
            "execution_time_ms": 0
        },
        "step3_format_results": {
            "llm_request": None,
            "llm_response": None,
            "execution_time_ms": 0
        },
        "total_execution_time_ms": 0,
        "error": None
    }
    
    try:
        # 入力パラメータ取得
        text_input = params.get("text_input", "")
        if not text_input:
            return MCPResponse(
                result="text_input が必要です",
                error="text_input が必要です",
                debug_response=tool_debug
            )
        
        # STEP 1: 条件抽出
        step1_start = time.time()
        conditions = await extract_search_conditions_with_llm(text_input, tool_debug)
        tool_debug["step1_extract_conditions"]["execution_time_ms"] = int((time.time() - step1_start) * 1000)
        
        if not conditions:
            return MCPResponse(
                result="検索条件の抽出に失敗しました",
                error="条件抽出失敗",
                debug_response=tool_debug
            )
        
        # STEP 2: SQL実行
        step2_start = time.time()
        results = await execute_sql_query(conditions, tool_debug)
        tool_debug["step2_sql_execution"]["execution_time_ms"] = int((time.time() - step2_start) * 1000)
        
        # STEP 3: 結果整形
        step3_start = time.time()
        formatted_response = await format_results_with_llm(results, text_input, conditions, tool_debug)
        tool_debug["step3_format_results"]["execution_time_ms"] = int((time.time() - step3_start) * 1000)
        
        # 実行時間計算
        total_execution_time = int((time.time() - start_time) * 1000)
        tool_debug["total_execution_time_ms"] = total_execution_time
        
        logger.info(f"[filter_products_by_risk_and_type] === FUNCTION COMPLETE === ({total_execution_time}ms)")
        
        return MCPResponse(
            result=formatted_response,
            debug_response=tool_debug
        )
        
    except Exception as e:
        # エラー情報をデバッグに記録
        tool_debug["error"] = str(e)
        tool_debug["total_execution_time_ms"] = int((time.time() - start_time) * 1000)
        
        logger.error(f"[filter_products_by_risk_and_type] Error: {e}")
        
        error_message = f"商品フィルタリング処理中にエラーが発生しました: {str(e)}"
        
        return MCPResponse(
            result=error_message,
            error=error_message,
            debug_response=tool_debug
        )

async def get_active_categories() -> list:
    """有効な商品カテゴリ一覧を取得"""
    try:
        query = "SELECT category_name FROM product_categories WHERE is_active = true ORDER BY display_order, category_name"
        results = await execute_query(query)
        return [row['category_name'] for row in results]
    except Exception as e:
        logger.error(f"カテゴリ取得エラー: {e}")
        return ["債券", "投資信託", "株式", "その他"]  # フォールバック

async def extract_search_conditions_with_llm(text_input: str, tool_debug: dict) -> dict:
    """STEP 1: テキストから検索条件を抽出"""
    try:
        llm_util = LLMUtil()
        
        # 有効な商品カテゴリを取得
        categories = await get_active_categories()
        categories_str = str(categories)
        
        # SystemPrompt基本部分を取得
        base_system_prompt = await get_system_prompt("filter_products_by_risk_and_type_extract_conditions")
        
        # 動的に商品種別情報を追記
        system_prompt = base_system_prompt + f"\n\n### 利用可能な商品種別\n- category_types: {categories_str} から該当するもの"
        
        if not system_prompt:
            logger.error("条件抽出用SystemPromptが取得できませんでした")
            return None
        
        tool_debug["step1_extract_conditions"]["llm_request"] = f"System: {system_prompt}\nUser: {text_input}"
        
        # LLM呼び出し
        response = await llm_util.call_claude(system_prompt, text_input, max_tokens=500, temperature=0.1)
        tool_debug["step1_extract_conditions"]["llm_response"] = response
        
        # JSON解析
        try:
            conditions = json.loads(response.strip())
            tool_debug["step1_extract_conditions"]["parsed_conditions"] = conditions
            return conditions
        except json.JSONDecodeError as e:
            logger.error(f"条件抽出JSON解析エラー: {e}")
            tool_debug["step1_extract_conditions"]["parsed_conditions"] = f"JSON解析エラー: {e}"
            return None
            
    except Exception as e:
        logger.error(f"条件抽出エラー: {e}")
        return None

async def execute_sql_query(conditions: dict, tool_debug: dict) -> list:
    """STEP 2: 検索条件からSQLクエリを実行"""
    try:
        # SQLクエリ構築
        query, params = build_risk_filter_query(conditions)
        
        # SQL実行（execute_query内でデバッグ情報統一設定）
        results = await execute_query(query, params, tool_debug)
        
        return results
        
    except Exception as e:
        logger.error(f"SQL実行エラー: {e}")
        return []

def build_risk_filter_query(conditions: dict) -> tuple:
    """検索条件からSQLクエリを構築"""
    base_query = "SELECT product_code AS id, product_name, category_name, risk_level, description FROM products_with_category WHERE 1=1"
    params = []
    
    # リスクレベルフィルタ（数値配列）
    if conditions.get("risk_levels"):
        risk_levels = conditions["risk_levels"]
        placeholders = ",".join(["%s"] * len(risk_levels))
        base_query += f" AND risk_level IN ({placeholders})"
        params.extend(risk_levels)
    
    # 商品種別フィルタ（日本語カテゴリ名で検索）
    if conditions.get("category_types"):
        types = conditions["category_types"]
        placeholders = ",".join(["%s"] * len(types))
        base_query += f" AND category_name IN ({placeholders})"
        params.extend(types)
    
    base_query += " ORDER BY risk_level, product_name LIMIT 20"
    
    return base_query, params

async def format_results_with_llm(results: list, original_text: str, conditions: dict, tool_debug: dict) -> str:
    """STEP 3: SQL結果をテキスト化"""
    try:
        llm_util = LLMUtil()
        
        # SystemPrompt取得（文字列として直接返却される）
        system_prompt = await get_system_prompt("filter_products_by_risk_and_type_format_results")
        
        if not system_prompt:
            logger.error("結果整形用SystemPromptが取得できませんでした")
            return f"検索結果: {len(results)}件の商品が見つかりました"
        
        # ユーザーメッセージ作成
        user_message = f"""元の質問: {original_text}

抽出された検索条件: {json.dumps(conditions, ensure_ascii=False)}

SQL検索結果: {json.dumps(results, ensure_ascii=False, indent=2)}"""
        
        tool_debug["step3_format_results"]["llm_request"] = f"System: {system_prompt}\nUser: {user_message}"
        
        # LLM呼び出し
        response = await llm_util.call_claude(system_prompt, user_message, max_tokens=2000, temperature=0.1)
        tool_debug["step3_format_results"]["llm_response"] = response
        
        return response.strip()
        
    except Exception as e:
        logger.error(f"結果整形エラー: {e}")
        return f"検索結果: {len(results)}件の商品が見つかりました（整形エラー）"
