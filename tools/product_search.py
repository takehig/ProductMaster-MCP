# ProductMaster MCP - Product Search Tool

import json
import time
from typing import Dict, Any, Tuple, List
from utils.database import get_db_connection, get_system_prompt
from utils.llm_util import llm_util
from models import MCPResponse
from psycopg2.extras import RealDictCursor
import logging

logger = logging.getLogger(__name__)

async def standardize_product_search_arguments(raw_input: str, debug_info: dict) -> Dict[str, Any]:
    """商品検索の引数を標準化（debug_info フラット化）"""
    print(f"[standardize_product_search_arguments] Raw input: {raw_input}")
    
    debug_info["stage1_input"] = raw_input
    
    try:
        # 第1段階: キーワード抽出
        stage1_prompt = await get_system_prompt("extract_product_keywords_pre")
        debug_info["stage1_prompt"] = stage1_prompt
        print(f"[standardize_product_search_arguments] Stage1 prompt取得成功")
        
        stage1_response = await llm_util.call_claude(stage1_prompt, raw_input)
        debug_info["stage1_response"] = stage1_response
        print(f"[standardize_product_search_arguments] Stage1 LLM Response: {stage1_response}")
        
        # 第2段階: パラメータ化
        debug_info["stage2_input"] = stage1_response
        stage2_prompt = await get_system_prompt("extract_product_info_pre")
        debug_info["stage2_prompt"] = stage2_prompt
        print(f"[standardize_product_search_arguments] Stage2 prompt取得成功")
        
        stage2_response = await llm_util.call_claude(stage2_prompt, stage1_response)
        debug_info["stage2_response"] = stage2_response
        print(f"[standardize_product_search_arguments] Stage2 LLM Response: {stage2_response}")
        
        # JSON解析
        standardized_params = json.loads(stage2_response)
        debug_info["final_params"] = standardized_params
        
        print(f"[standardize_product_search_arguments] Final Standardized Output: {standardized_params}")
        return standardized_params
        
    except Exception as e:
        print(f"[standardize_product_search_arguments] Error: {e}")
        
        # エラー時も既存ルール維持
        error_params = {
            "product_code": None,
            "product_name": f"処理エラー: {str(e)}",
            "maturity_date": None,
            "risk_level": None
        }
        
        debug_info["error"] = str(e)
        debug_info["final_params"] = error_params
        
        return error_params

async def format_product_search_results(products: list, debug_info: dict) -> str:
    """商品検索結果をテキスト化（SystemPrompt Management統合）"""
    if not products:
        return "商品検索結果: 該当する商品はありませんでした。"
    
    # SystemPrompt Management からプロンプト取得
    try:
        system_prompt = await get_system_prompt("format_product_search_results")
        debug_info["format_prompt"] = system_prompt
        print(f"[format_product_search_results] SystemPrompt Management からプロンプト取得成功")
        
        # 正常系: LLM処理実行
        data_json = json.dumps(products, ensure_ascii=False, default=str, indent=2)
        full_prompt = f"{system_prompt}\n\nData:\n{data_json}"
        
        result_text, execution_time = await llm_util.call_llm_simple(full_prompt)
        debug_info["format_execution_time_ms"] = execution_time
        print(f"[format_product_search_results] Execution time: {execution_time}ms")
        print(f"[format_product_search_results] Formatted result: {result_text[:200]}...")
        
        return result_text
        
    except Exception as e:
        print(f"[format_product_search_results] SystemPrompt Management 取得失敗: {e}")
        
        # 異常系: 固定エラーメッセージ返却
        error_message = f"商品検索結果フォーマットエラー: SystemPrompt Management接続失敗 ({str(e)})"
        debug_info["format_error"] = str(e)
        print(f"[format_product_search_results] 固定エラーメッセージ返却: {error_message}")
        
        return error_message

async def execute_product_search_query(standardized_params: Dict[str, Any], debug_info: dict) -> list:
    """商品検索クエリ実行（debug_info 対応）"""
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    query = "SELECT * FROM products WHERE 1=1"
    query_params = []
    
    # 検索条件構築
    if standardized_params.get("product_code"):
        query += " AND product_code = %s"
        query_params.append(standardized_params["product_code"])
    
    if standardized_params.get("product_name"):
        query += " AND product_name ILIKE %s"
        query_params.append(f"%{standardized_params['product_name']}%")
    
    query += " LIMIT 50"
    
    debug_info["search_query"] = query
    debug_info["search_params"] = query_params
    
    print(f"[execute_product_search_query] Executing query: {query}")
    print(f"[execute_product_search_query] Query params: {query_params}")
    
    cursor.execute(query, query_params)
    products = cursor.fetchall()
    cursor.close()
    conn.close()
    
    print(f"[execute_product_search_query] Found {len(products)} products")
    return products

async def get_product_details(params: Dict[str, Any]) -> MCPResponse:
    """商品詳細情報取得（debug_response フラット化）"""
    start_time = time.time()
    debug_info = {}  # 共有デバッグ情報
    
    print(f"[get_product_details] === FUNCTION START ===")
    print(f"[get_product_details] Received raw params: {params}")
    
    try:
        text_input = params.get("text_input", "")
        if not text_input:
            debug_info["error"] = "text_input未提供"
            debug_info["execution_time_ms"] = 0
            return MCPResponse(
                result="text_inputが必要です",
                debug_response=debug_info
            )
        
        debug_info["text_input"] = text_input
        
        # 引数標準化処理（debug_info 共有）
        standardized_params = await standardize_product_search_arguments(text_input, debug_info)
        
        if not standardized_params:
            debug_info["execution_time_ms"] = round((time.time() - start_time) * 1000, 2)
            return MCPResponse(
                result="引数標準化に失敗しました",
                debug_response=debug_info
            )
        
        # データベース検索（debug_info 共有）
        products = await execute_product_search_query(standardized_params, debug_info)
        
        # 結果テキスト化（debug_info 共有）
        result_text = await format_product_search_results(products, debug_info)
        
        # 最終情報追加
        debug_info["execution_time_ms"] = round((time.time() - start_time) * 1000, 2)
        debug_info["results_count"] = len(products)
        
        return MCPResponse(result=result_text, debug_response=debug_info)
        
    except Exception as e:
        logger.error(f"Product search error: {e}")
        debug_info["error"] = str(e)
        debug_info["execution_time_ms"] = round((time.time() - start_time) * 1000, 2)
        
        return MCPResponse(
            result=f"商品検索エラー: {str(e)}",
            debug_response=debug_info
        )
