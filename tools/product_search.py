# ProductMaster MCP - Product Search Tool (ID検索専用)

import json
import time
import re
from typing import Dict, Any, List
from utils.database import get_db_connection
from utils.system_prompt import get_system_prompt
from utils.llm_util import llm_util
from models import MCPResponse
from psycopg2.extras import RealDictCursor
import logging

logger = logging.getLogger(__name__)

async def format_product_search_results(products: list, debug_info: dict) -> str:
    """商品検索結果を整形"""
    try:
        # SystemPrompt Management からプロンプト取得
        system_prompt = await get_system_prompt("format_product_search_results")
        debug_info["format_prompt"] = system_prompt
        print(f"[format_product_search_results] SystemPrompt Management からプロンプト取得成功")
        
        # 商品データをJSON形式で準備
        products_json = json.dumps(products, ensure_ascii=False, default=str)
        full_prompt = f"{system_prompt}\n\n商品データ: {products_json}"
        
        debug_info["format_llm_request"] = full_prompt
        
        # LLM呼び出し
        response, execution_time = await llm_util.call_llm_simple(full_prompt)
        debug_info["format_llm_response"] = response
        debug_info["format_execution_time_ms"] = execution_time
        
        print(f"[format_product_search_results] LLM整形完了 ({execution_time:.1f}ms)")
        
        return response.strip()
        
    except Exception as e:
        error_message = f"商品検索結果の整形中にエラーが発生しました: {str(e)}"
        debug_info["format_error"] = str(e)
        print(f"[format_product_search_results] 固定エラーメッセージ返却: {error_message}")
        
        return error_message

async def execute_product_search_query(product_ids: list, debug_info: dict) -> list:
    """商品IDの配列から商品詳細を取得"""
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    query = "SELECT * FROM products WHERE product_id = ANY(%s)"
    query_params = [product_ids]
    
    debug_info["search_query"] = query
    debug_info["search_params"] = query_params
    
    print(f"[execute_product_search_query] Executing query: {query}")
    print(f"[execute_product_search_query] Query params: {product_ids}")
    
    cursor.execute(query, query_params)
    products = cursor.fetchall()
    cursor.close()
    conn.close()
    
    print(f"[execute_product_search_query] Found {len(products)} products")
    return products

async def get_product_details_byid(params: Dict[str, Any]) -> MCPResponse:
    """商品ID配列から詳細情報取得"""
    start_time = time.time()
    debug_info = {}
    
    try:
        # 入力パラメータ取得
        text_input = params.get("text_input", "")
        if not text_input:
            return MCPResponse(
                result="text_input が必要です",
                error="text_input が必要です",
                debug_response=debug_info
            )
        
        print(f"[get_product_details_byid] === FUNCTION START ===")
        print(f"[get_product_details_byid] Received raw params: {params}")
        
        # ID配列を抽出（カンマ区切りまたは配列形式を想定）
        if isinstance(text_input, list):
            product_ids = [int(id) for id in text_input]
        else:
            # 文字列からID抽出（例: "1,2,3" または "[1,2,3]"）
            ids = re.findall(r'\d+', str(text_input))
            product_ids = [int(id) for id in ids]
        
        if not product_ids:
            return MCPResponse(
                result="商品IDが見つかりません",
                error="商品IDが見つかりません",
                debug_response=debug_info
            )
        
        print(f"[get_product_details_byid] Extracted product IDs: {product_ids}")
        
        # 商品詳細取得
        products = await execute_product_search_query(product_ids, debug_info)
        
        if not products:
            return MCPResponse(
                result="指定されたIDの商品が見つかりません",
                debug_response=debug_info
            )
        
        # 結果整形
        formatted_result = await format_product_search_results(products, debug_info)
        
        debug_info["execution_time_ms"] = int((time.time() - start_time) * 1000)
        
        print(f"[get_product_details_byid] === FUNCTION COMPLETE === ({debug_info['execution_time_ms']}ms)")
        
        return MCPResponse(
            result=formatted_result,
            debug_response=debug_info
        )
        
    except Exception as e:
        debug_info["error"] = str(e)
        debug_info["execution_time_ms"] = int((time.time() - start_time) * 1000)
        
        print(f"[get_product_details_byid] Error: {e}")
        
        error_message = f"商品詳細取得中にエラーが発生しました: {str(e)}"
        
        return MCPResponse(
            result=error_message,
            error=error_message,
            debug_response=debug_info
        )
