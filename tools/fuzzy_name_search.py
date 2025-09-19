# Fuzzy Product Name Search Tool

import time
import logging
from typing import Dict, Any
from models import MCPResponse
from utils.api_client import ProductMasterAPIClient
from utils.llm_client import BedrockLLMClient

logger = logging.getLogger(__name__)

async def search_products_by_name_fuzzy(params: Dict[str, Any]) -> MCPResponse:
    """商品名による曖昧検索"""
    start_time = time.time()
    
    logger.info(f"[search_products_by_name_fuzzy] === FUNCTION START ===")
    logger.info(f"[search_products_by_name_fuzzy] Received params: {params}")
    
    # デバッグ情報インスタンス（try外側で定義）
    tool_debug = {
        "function_name": "search_products_by_name_fuzzy",
        "input_params": params,
        "step1_search_criteria": None,
        "step2_products_count": 0,
        "step3_filtered_count": 0,
        "step4_final_result": None,
        "execution_time_ms": 0,
        "error": None
    }
    
    try:
        # パラメータ取得
        user_input = params.get('text_input', '').strip()
        if not user_input:
            raise ValueError("text_input parameter is required")
        
        logger.info(f"[search_products_by_name_fuzzy] Processing user input: {user_input}")
        
        # クライアント初期化
        api_client = ProductMasterAPIClient()
        llm_client = BedrockLLMClient()
        
        # STEP 1: 検索条件抽出
        logger.info(f"[search_products_by_name_fuzzy] STEP 1: Extracting search criteria")
        search_criteria = await llm_client.extract_search_criteria(user_input)
        tool_debug["step1_search_criteria"] = search_criteria
        logger.info(f"[search_products_by_name_fuzzy] Search criteria: {search_criteria}")
        
        if not search_criteria:
            raise ValueError("Failed to extract search criteria from user input")
        
        # STEP 2: 全商品データ取得
        logger.info(f"[search_products_by_name_fuzzy] STEP 2: Fetching all products")
        products = await api_client.get_all_products()
        tool_debug["step2_products_count"] = len(products)
        logger.info(f"[search_products_by_name_fuzzy] Retrieved {len(products)} products")
        
        if not products:
            raise ValueError("No products found in ProductMaster")
        
        # STEP 3: 商品データをLLM用形式に変換
        logger.info(f"[search_products_by_name_fuzzy] STEP 3: Formatting products for LLM")
        formatted_products = api_client.format_products_for_llm(products)
        
        # STEP 4: 商品フィルタリング
        logger.info(f"[search_products_by_name_fuzzy] STEP 4: Filtering products")
        filtered_products = await llm_client.filter_products(search_criteria, formatted_products)
        tool_debug["step3_filtered_count"] = len(filtered_products)
        logger.info(f"[search_products_by_name_fuzzy] Filtered to {len(filtered_products)} products")
        
        # STEP 5: 結果整形
        logger.info(f"[search_products_by_name_fuzzy] STEP 5: Formatting results")
        final_result = await llm_client.format_results(filtered_products)
        tool_debug["step4_final_result"] = final_result
        
        # 実行時間計算
        execution_time = int((time.time() - start_time) * 1000)
        tool_debug["execution_time_ms"] = execution_time
        
        logger.info(f"[search_products_by_name_fuzzy] === FUNCTION COMPLETE === ({execution_time}ms)")
        
        return MCPResponse(
            content=[{
                "type": "text",
                "text": final_result
            }],
            isError=False,
            _meta={
                "debug_info": tool_debug
            }
        )
        
    except Exception as e:
        # エラー情報をデバッグに記録
        tool_debug["error"] = str(e)
        tool_debug["execution_time_ms"] = int((time.time() - start_time) * 1000)
        
        logger.error(f"[search_products_by_name_fuzzy] Error: {e}")
        
        error_message = f"商品名曖昧検索でエラーが発生しました: {str(e)}"
        
        return MCPResponse(
            content=[{
                "type": "text", 
                "text": error_message
            }],
            isError=True,
            _meta={
                "debug_info": tool_debug
            }
        )
