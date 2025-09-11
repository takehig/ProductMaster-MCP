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

async def standardize_product_search_arguments(raw_input: str) -> Tuple[Dict[str, Any], str, str, str]:
    """商品検索の引数を標準化（LLMベース・統一パターン）"""
    print(f"[standardize_product_search_arguments] Raw input: {raw_input}")
    
    # システムプロンプト（将来的にはデータベース化）
    system_prompt = """商品検索の条件を以下のJSON形式で正規化してください。

入力例: "債券 満期2025年"
出力例: {"product_code": null, "product_name": "債券", "maturity_date": "2025"}

入力例: "PROD001"
出力例: {"product_code": "PROD001", "product_name": null, "maturity_date": null}

入力例: "投資信託 リスク低"
出力例: {"product_code": null, "product_name": "投資信託", "risk_level": "低", "maturity_date": null}

必須フィールド:
- product_code: 商品コード（明示的な場合のみ）
- product_name: 商品名（部分一致用）
- maturity_date: 満期日（YYYY形式）
- risk_level: リスクレベル

JSON形式で出力してください。"""
    
    response = await llm_util.call_claude(system_prompt, raw_input)
    print(f"[standardize_product_search_arguments] LLM Raw Response: {response}")
    
    full_prompt_text = f"{system_prompt}\n\nUser Input: {raw_input}"
    
    try:
        standardized_params = json.loads(response)
        print(f"[standardize_product_search_arguments] Final Standardized Output: {standardized_params}")
        return standardized_params, full_prompt_text, response, str(standardized_params)
    except json.JSONDecodeError as e:
        print(f"[standardize_product_search_arguments] JSON parse error: {e}")
        return {}, full_prompt_text, response, f"JSONパースエラー: {str(e)}"

async def format_product_search_results(products: list) -> str:
    """商品検索結果をテキスト化"""
    if not products:
        return "商品検索結果: 該当する商品はありませんでした。"
    
    # システムプロンプト（将来的にはデータベース化）
    system_prompt = """商品検索の結果配列を、読みやすいテキスト形式に変換してください。

要求:
1. 商品コード、商品名を明確に記載
2. 商品タイプ、通貨、リスクレベルを含める
3. 見やすい形式で整理

例:
商品検索結果 (3件):
1. [BOND001] 国債10年 (債券/JPY/低リスク)
2. [FUND002] 株式投信A (投資信託/JPY/中リスク)
3. [STOCK003] 米国株ETF (株式/USD/高リスク)"""

    # 呼び出し元でデータ結合（責任明確化）
    data_json = json.dumps(products, ensure_ascii=False, default=str, indent=2)
    full_prompt = f"{system_prompt}\n\nData:\n{data_json}"
    
    # 完全プロンプトでLLM呼び出し
    result_text, execution_time = await llm_util.call_llm_simple(full_prompt)
    print(f"[format_product_search_results] Execution time: {execution_time}ms")
    print(f"[format_product_search_results] Formatted result: {result_text[:200]}...")
    
    return result_text

async def get_product_details(params: Dict[str, Any]) -> MCPResponse:
    """商品詳細情報取得（統一パターン・簡潔版）"""
    start_time = time.time()
    
    print(f"[get_product_details] === FUNCTION START ===")
    print(f"[get_product_details] Received raw params: {params}")
    
    try:
        text_input = params.get("text_input", "")
        if not text_input:
            return MCPResponse(
                result="text_inputが必要です",
                debug_response={"error": "text_input未提供", "execution_time_ms": 0}
            )
        
        # 引数標準化処理（関数化）
        standardized_params, full_prompt_text, standardize_response, standardize_parameter = await standardize_product_search_arguments(text_input)
        
        if not standardized_params:
            return MCPResponse(
                result="引数標準化に失敗しました",
                debug_response={
                    "standardize_prompt": full_prompt_text,
                    "standardize_response": standardize_response,
                    "execution_time_ms": round((time.time() - start_time) * 1000, 2)
                }
            )
        
        # データベース検索（簡潔化）
        products = await execute_product_search_query(standardized_params)
        
        # 結果テキスト化（関数化）
        result_text = await format_product_search_results(products)
        
        # レスポンス作成
        execution_time = time.time() - start_time
        debug_response = {
            "standardize_prompt": full_prompt_text,
            "standardize_response": standardize_response,
            "standardize_parameter": standardize_parameter,
            "execution_time_ms": round(execution_time * 1000, 2),
            "results_count": len(products)
        }
        
        return MCPResponse(result=result_text, debug_response=debug_response)
        
    except Exception as e:
        logger.error(f"Product search error: {e}")
        execution_time = time.time() - start_time
        
        return MCPResponse(
            result=f"商品検索エラー: {str(e)}",
            debug_response={
                "error": str(e),
                "execution_time_ms": round(execution_time * 1000, 2)
            }
        )

async def execute_product_search_query(standardized_params: Dict[str, Any]) -> list:
    """商品検索クエリ実行（分離された関数）"""
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
    
    print(f"[execute_product_search_query] Executing query: {query}")
    print(f"[execute_product_search_query] Query params: {query_params}")
    
    cursor.execute(query, query_params)
    products = cursor.fetchall()
    cursor.close()
    conn.close()
    
    print(f"[execute_product_search_query] Found {len(products)} products")
    return products
