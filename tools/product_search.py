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

async def get_product_details_byid(params: Dict[str, Any]) -> MCPResponse:
    """商品ID配列から詳細情報取得（メイン関数）"""
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
        
        # LLMを使用してID配列を抽出
        product_ids = await extract_product_ids_with_llm(text_input, debug_info)
        
        # パースエラーまたはID未発見の場合の処理
        if not product_ids:
            # パースエラー情報があれば後続のフォーマット処理に渡す
            if debug_info.get("extract_ids_parsed_successfully") == False:
                # パースエラー情報を含む空の商品リストでフォーマット処理実行
                error_message = await format_product_search_results([], debug_info)
                debug_info["execution_time_ms"] = int((time.time() - start_time) * 1000)
                
                return MCPResponse(
                    result=error_message,
                    debug_response=debug_info
                )
            else:
                # 通常のID未発見エラー
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

async def extract_product_ids_with_llm(text_input: str, debug_info: dict) -> List[int]:
    """LLMを使用して商品ID配列を抽出（1番目に呼び出される関数）"""
    try:
        # SystemPrompt Management からプロンプト取得
        system_prompt = await get_system_prompt("get_product_details_byid_extract_ids")
        debug_info["extract_ids_prompt"] = system_prompt
        print(f"[extract_product_ids_with_llm] SystemPrompt取得成功")
        
        # LLM呼び出し
        response, execution_time = await llm_util.call_llm_simple(f"{system_prompt}\n\n入力テキスト: {text_input}")
        debug_info["extract_ids_llm_response"] = response
        debug_info["extract_ids_execution_time_ms"] = execution_time
        
        print(f"[extract_product_ids_with_llm] LLM応答: {response}")
        
        # LLM応答をJSON配列としてパース
        try:
            import ast
            # 安全な配列パース（ast.literal_eval使用）
            product_ids = ast.literal_eval(response.strip())
            
            if not isinstance(product_ids, list):
                raise ValueError("応答が配列形式ではありません")
            
            # 数値のみ抽出・重複除去
            product_ids = list(set([int(id) for id in product_ids if isinstance(id, (int, str)) and str(id).isdigit()]))
            
            debug_info["extract_ids_parsed_successfully"] = True
            debug_info["extract_ids_final_result"] = product_ids
            
            print(f"[extract_product_ids_with_llm] パース成功 - 抽出されたID: {product_ids}")
            
            return product_ids
            
        except (ValueError, SyntaxError, TypeError) as parse_error:
            # パースエラー時の処理
            debug_info["extract_ids_parsed_successfully"] = False
            debug_info["extract_ids_parse_error"] = str(parse_error)
            debug_info["extract_ids_final_result"] = f"パースエラー: {str(parse_error)} (LLM応答: {response})"
            
            print(f"[extract_product_ids_with_llm] パースエラー: {parse_error}")
            print(f"[extract_product_ids_with_llm] LLM応答: {response}")
            
            # パースエラー情報を後続処理に渡すため空配列を返す
            return []
        
    except Exception as e:
        debug_info["extract_ids_error"] = str(e)
        debug_info["extract_ids_final_result"] = f"システムエラー: {str(e)}"
        print(f"[extract_product_ids_with_llm] システムエラー: {e}")
        return []

async def execute_product_search_query(product_ids: list, debug_info: dict) -> list:
    """商品IDの配列から商品詳細を取得（2番目に呼び出される関数）"""
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

async def format_product_search_results(products: list, debug_info: dict) -> str:
    """商品検索結果を整形（3番目に呼び出される関数）"""
    try:
        # パースエラー情報がある場合の特別処理
        if debug_info.get("extract_ids_parsed_successfully") == False:
            parse_error_info = debug_info.get("extract_ids_final_result", "パースエラーが発生しました")
            return f"商品ID抽出でエラーが発生しました: {parse_error_info}"
        
        # 通常の商品データ整形処理
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
