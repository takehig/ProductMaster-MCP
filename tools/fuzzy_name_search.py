# Fuzzy Product Name Search Tool

import time
import json
import logging
from typing import Dict, Any
from models import MCPResponse
from utils.api_client import ProductMasterAPIClient
from utils.system_prompt import get_system_prompt
from utils.llm_util import llm_util

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
        "step1_extract_criteria": {
            "llm_request": None,
            "llm_response": None,
            "execution_time_ms": 0,
            "extracted_criteria": None
        },
        "step2_api_call": {
            "api_url": None,
            "products_count": 0,
            "products_sample": None
        },
        "step3_filter_products": {
            "llm_request": None,
            "llm_response": None,
            "execution_time_ms": 0,
            "filtered_products": None
        },
        "step4_format_results": {
            "llm_request": None,
            "llm_response": None,
            "execution_time_ms": 0,
            "final_result": None
        },
        "total_execution_time_ms": 0,
        "error": None
    }
    
    try:
        # パラメータ取得
        user_input = params.get('text_input', '').strip()
        if not user_input:
            raise ValueError("text_input parameter is required")
        
        logger.info(f"[search_products_by_name_fuzzy] Processing user input: {user_input}")
        
        # STEP 1: 検索条件抽出
        logger.info(f"[search_products_by_name_fuzzy] STEP 1: Extracting search criteria")
        system_prompt = await get_system_prompt("fuzzy_search_extract_criteria")
        full_prompt = f"{system_prompt}\n\nUser Input: {user_input}"
        tool_debug["step1_extract_criteria"]["llm_request"] = full_prompt
        
        response, execution_time = await llm_util.call_llm_simple(full_prompt)
        tool_debug["step1_extract_criteria"]["llm_response"] = response
        tool_debug["step1_extract_criteria"]["execution_time_ms"] = execution_time
        tool_debug["step1_extract_criteria"]["extracted_criteria"] = response
        
        search_criteria = response.strip()
        logger.info(f"[search_products_by_name_fuzzy] Search criteria: {search_criteria}")
        
        if not search_criteria:
            raise ValueError("Failed to extract search criteria from user input")
        
        # STEP 2: 全商品データ取得
        logger.info(f"[search_products_by_name_fuzzy] STEP 2: Fetching all products")
        api_client = ProductMasterAPIClient()
        tool_debug["step2_api_call"]["api_url"] = f"{api_client.base_url}/api/products"
        
        products_data = await api_client.get_all_products()
        # ProductMaster API レスポンス構造修正
        if isinstance(products_data, dict) and 'products' in products_data:
            products = products_data['products']
        else:
            products = products_data
        
        tool_debug["step2_api_call"]["products_count"] = len(products)
        tool_debug["step2_api_call"]["products_sample"] = products[:3] if products else []
        logger.info(f"[search_products_by_name_fuzzy] Retrieved {len(products)} products")
        
        if not products:
            raise ValueError("No products found in ProductMaster")
        
        # 商品データをLLM用形式に変換
        formatted_products = api_client.format_products_for_llm(products)
        
        # STEP 3: 商品フィルタリング
        logger.info(f"[search_products_by_name_fuzzy] STEP 3: Filtering products")
        system_prompt = await get_system_prompt("fuzzy_search_filter_products")
        products_json = json.dumps(formatted_products, ensure_ascii=False)
        full_prompt = f"{system_prompt}\n\nUser Input: 検索条件: {search_criteria}\n商品リスト: {products_json}"
        tool_debug["step3_filter_products"]["llm_request"] = full_prompt
        
        response, execution_time = await llm_util.call_llm_simple(full_prompt)
        tool_debug["step3_filter_products"]["llm_response"] = response
        tool_debug["step3_filter_products"]["execution_time_ms"] = execution_time
        
        # JSON解析の改善
        try:
            # 説明文を除去してJSON部分のみ抽出
            response_clean = response.strip()
            
            # JSON配列の開始位置を探す
            json_start = response_clean.find('[')
            json_end = response_clean.rfind(']')
            
            if json_start != -1 and json_end != -1 and json_end > json_start:
                json_part = response_clean[json_start:json_end+1]
                filtered_products = json.loads(json_part)
                if not isinstance(filtered_products, list):
                    filtered_products = []
            else:
                # JSON配列が見つからない場合
                logger.error(f"No JSON array found in LLM response: {response}")
                filtered_products = []
                
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {e}, response: {response}")
            filtered_products = []
        except Exception as e:
            logger.error(f"Unexpected error in JSON parsing: {e}, response: {response}")
            filtered_products = []
        
        tool_debug["step3_filter_products"]["filtered_products"] = filtered_products
        logger.info(f"[search_products_by_name_fuzzy] Filtered to {len(filtered_products)} products")
        
        # STEP 4: 結果整形
        logger.info(f"[search_products_by_name_fuzzy] STEP 4: Formatting results")
        system_prompt = await get_system_prompt("fuzzy_search_format_results")
        products_json = json.dumps(filtered_products, ensure_ascii=False)
        full_prompt = f"{system_prompt}\n\nUser Input: {products_json}"
        tool_debug["step4_format_results"]["llm_request"] = full_prompt
        
        response, execution_time = await llm_util.call_llm_simple(full_prompt)
        tool_debug["step4_format_results"]["llm_response"] = response
        tool_debug["step4_format_results"]["execution_time_ms"] = execution_time
        tool_debug["step4_format_results"]["final_result"] = response
        
        final_result = response.strip()
        
        # 実行時間計算
        total_execution_time = int((time.time() - start_time) * 1000)
        tool_debug["total_execution_time_ms"] = total_execution_time
        
        logger.info(f"[search_products_by_name_fuzzy] === FUNCTION COMPLETE === ({total_execution_time}ms)")
        
        return MCPResponse(
            result={
                "content": [{"type": "text", "text": final_result}],
                "isError": False
            },
            debug_response=tool_debug
        )
        
    except Exception as e:
        # エラー情報をデバッグに記録
        tool_debug["error"] = str(e)
        tool_debug["total_execution_time_ms"] = int((time.time() - start_time) * 1000)
        
        logger.error(f"[search_products_by_name_fuzzy] Error: {e}")
        
        error_message = f"商品名曖昧検索でエラーが発生しました: {str(e)}"
        
        return MCPResponse(
            result={
                "content": [{"type": "text", "text": error_message}],
                "isError": True
            },
            error=error_message,
            debug_response=tool_debug
        )
