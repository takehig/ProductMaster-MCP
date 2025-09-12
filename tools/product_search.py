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

async def get_prompt_from_management(prompt_name: str) -> str:
    """SystemPrompt Management からプロンプト取得"""
    import httpx
    async with httpx.AsyncClient() as client:
        response = await client.get(f"http://localhost:8007/api/prompts/{prompt_name}")
        if response.status_code == 200:
            prompt_data = response.json()
            return prompt_data.get("content", "")
        else:
            raise Exception(f"HTTP {response.status_code}")

async def standardize_product_search_arguments(raw_input: str) -> Tuple[Dict[str, Any], str, str, str]:
    """商品検索の引数を標準化（2段階処理・debug_response拡張）"""
    print(f"[standardize_product_search_arguments] Raw input: {raw_input}")
    
    debug_response = {
        "stage1_input": raw_input,
        "stage1_prompt": "",
        "stage1_response": "",
        "stage2_input": "",
        "stage2_prompt": "",
        "stage2_response": "",
        "final_params": {}
    }
    
    try:
        # 第1段階: キーワード抽出
        stage1_prompt = await get_prompt_from_management("extract_product_keywords_pre")
        debug_response["stage1_prompt"] = stage1_prompt
        print(f"[standardize_product_search_arguments] Stage1 prompt取得成功")
        
        stage1_response = await llm_util.call_claude(stage1_prompt, raw_input)
        debug_response["stage1_response"] = stage1_response
        print(f"[standardize_product_search_arguments] Stage1 LLM Response: {stage1_response}")
        
        # 第2段階: パラメータ化
        stage2_prompt = await get_prompt_from_management("extract_product_info_pre")
        debug_response["stage2_prompt"] = stage2_prompt
        debug_response["stage2_input"] = stage1_response  # キーワードをパラメータ化の入力に
        print(f"[standardize_product_search_arguments] Stage2 prompt取得成功")
        
        stage2_response = await llm_util.call_claude(stage2_prompt, stage1_response)
        debug_response["stage2_response"] = stage2_response
        print(f"[standardize_product_search_arguments] Stage2 LLM Response: {stage2_response}")
        
        # JSON解析
        standardized_params = json.loads(stage2_response)
        debug_response["final_params"] = standardized_params
        
        full_prompt_text = f"Stage1: Keywords Extraction\nStage2: Parameter Standardization"
        
        print(f"[standardize_product_search_arguments] Final Standardized Output: {standardized_params}")
        return standardized_params, full_prompt_text, stage2_response, json.dumps(debug_response, ensure_ascii=False, indent=2)
        
    except Exception as e:
        print(f"[standardize_product_search_arguments] Error: {e}")
        
        # エラー時も既存ルール維持
        error_params = {
            "product_code": None,
            "product_name": f"処理エラー: {str(e)}",
            "maturity_date": None,
            "risk_level": None
        }
        
        debug_response["error"] = str(e)
        debug_response["final_params"] = error_params
        
        return error_params, f"Error: {str(e)}", str(e), json.dumps(debug_response, ensure_ascii=False, indent=2)

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
