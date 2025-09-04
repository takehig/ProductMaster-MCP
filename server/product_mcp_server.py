#!/usr/bin/env python3
"""
ProductMaster MCP Server - 商品詳細情報取得API（1ツール体制）
Port: 8003
"""

import asyncio
import json
import logging
import os
import time
from datetime import datetime
from typing import Dict, List, Any, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import psycopg2
from psycopg2.extras import RealDictCursor
import boto3

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="ProductMaster MCP Server", version="2.0.0")

# CORS設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# データベース接続設定
DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'wealthai',
    'user': 'wealthai_user',
    'password': 'wealthai123'
}

# Bedrock設定
bedrock_client = boto3.client('bedrock-runtime', region_name='us-east-1')

class MCPRequest(BaseModel):
    jsonrpc: str = "2.0"
    id: int
    method: str
    params: Optional[Dict[str, Any]] = None

class MCPResponse(BaseModel):
    jsonrpc: str = "2.0"
    id: Optional[int] = None
    result: Optional[Any] = None
    error: Optional[str] = None
    debug_response: Optional[Dict[str, Any]] = None

async def format_products_to_text(products_array: List[Dict]) -> str:
    """商品配列をテキスト形式に変換（Standardizeの逆）"""
    if not products_array:
        return "商品情報: 該当する商品はありませんでした。"
    
    system_prompt = """商品検索の結果配列を、後続のツールが使いやすいシンプルなテキスト形式に変換してください。

以下の形式で出力:
```
商品情報:
- 商品コード: JP001, 商品名: ソフトバンク社債, 種類: bond, 通貨: JPY, 満期日: 2026-12-15
- 商品コード: US002, 商品名: 米国債, 種類: bond, 通貨: USD, 満期日: 2027-06-30

合計: 2件の商品
```

簡潔で読みやすく、次のツールが商品情報を理解しやすい形式にしてください。"""
    
    try:
        array_text = json.dumps(products_array, ensure_ascii=False, indent=2)
        
        bedrock = boto3.client('bedrock-runtime', region_name='us-east-1')
        body = json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 1000,
            "system": system_prompt,
            "messages": [{"role": "user", "content": array_text}]
        })
        
        response = bedrock.invoke_model(
            body=body,
            modelId='anthropic.claude-3-sonnet-20240229-v1:0',
            accept='application/json',
            contentType='application/json'
        )
        
        response_body = json.loads(response.get('body').read())
        return response_body['content'][0]['text']
    except Exception as e:
        return f"商品情報のテキスト化に失敗: {str(e)}"

def get_db_connection():
    """データベース接続を取得"""
    return psycopg2.connect(**DB_CONFIG)

@app.get("/tools/descriptions")
async def get_tool_descriptions():
    """AIChat用ツール情報（1ツール・text_input対応）"""
    return {
        "tools": [
            {
                "name": "get_product_details",
                "description": "商品の詳細情報を取得",
                "usage_context": "特定の商品について詳しく知りたい、商品コードから詳細を調べたい時に使用",
                "parameters": {
                    "text_input": {"type": "string", "description": "商品指定のテキスト（商品コード、商品名など）"}
                }
            }
        ]
    }

@app.get("/tools")
async def list_available_tools():
    """MCPプロトコル準拠のツール一覧（1ツール）"""
    return {
        "tools": [
            {
                "name": "get_product_details",
                "description": "商品の詳細情報を取得します",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "text_input": {"type": "string", "description": "商品指定のテキスト（商品コード、商品名など）"}
                    },
                    "required": ["text_input"]
                }
            }
        ]
    }

@app.post("/mcp")
async def mcp_endpoint(request: MCPRequest):
    """MCPプロトコルエンドポイント"""
    try:
        method = request.method
        params = request.params or {}
        
        if method == "tools/call":
            tool_name = params.get("name")
            arguments = params.get("arguments", {})
            
            if tool_name == "get_product_details":
                result = await get_product_details(arguments)
                # get_product_detailsは既にMCPResponseを返すので、idだけ設定
                result.id = request.id
                return result
            else:
                return MCPResponse(id=request.id, error=f"Unknown tool: {tool_name}")
                
        elif method == "tools/list":
            result = await list_available_tools()
            return MCPResponse(id=request.id, result=result)
        else:
            return MCPResponse(id=request.id, error=f"Unknown method: {method}")
            
    except Exception as e:
        logger.error(f"MCP endpoint error: {e}")
        return MCPResponse(id=request.id, error=str(e))

async def get_product_details(params: Dict[str, Any]):
    """商品詳細情報取得（text_input対応・LLM正規化）"""
    start_time = time.time()
    text_input = params.get("text_input", "")
    
    if not text_input:
        error_message = "text_inputが必要です"
        tool_debug = {
            "executed_query": "N/A (text_input未提供)",
            "executed_query_results": error_message,
            "format_prompt": "N/A (text_input未提供)",
            "format_response": "N/A (text_input未提供)",
            "standardize_prompt": "N/A (text_input未提供)",
            "standardize_response": "N/A (text_input未提供)",
            "standardize_parameter": "N/A (text_input未提供)",
            "execution_time_ms": round((time.time() - start_time) * 1000, 2),
            "results_count": 0
        }
        return MCPResponse(result=error_message, debug_response=tool_debug)
    
    # LLM正規化処理
    normalized_params, full_prompt_text, standardize_response, standardize_parameter = await standardize_product_arguments(text_input)
    product_code = normalized_params.get("product_code")
    product_name = normalized_params.get("product_name")
    
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    query = "SELECT * FROM products WHERE 1=1"
    query_params = []
    
    if product_code:
        query += " AND product_code = %s"
        query_params.append(product_code)
    elif product_name:
        query += " AND product_name ILIKE %s"
        query_params.append(f"%{product_name}%")
    
    # SQL実行部分
    try:
        logger.info(f"[DEBUG] Executing query: {query}")
        logger.info(f"[DEBUG] Query params: {query_params}")
        cursor.execute(query, query_params)
        products = cursor.fetchall()
        logger.info(f"[DEBUG] Products fetched: {len(products)} rows")
        conn.close()
    except Exception as sql_error:
        conn.close()
        error_message = f"SQLエラー: {str(sql_error)}"
        
        tool_debug = {
            "executed_query": query,
            "executed_query_results": error_message,
            "format_prompt": "N/A (SQLエラーのため未実行)",
            "format_response": "N/A (SQLエラーのため未実行)",
            "standardize_prompt": full_prompt_text,
            "standardize_response": standardize_response,
            "standardize_parameter": standardize_parameter,
            "execution_time_ms": round((time.time() - start_time) * 1000, 2),
            "results_count": 0,
            "error_type": "SQL_ERROR"
        }
        
        return MCPResponse(result=error_message, debug_response=tool_debug)
    
    # 配列作成部分
    try:
        result_array = []
        for product in products:
            logger.info(f"[DEBUG] Processing product: {list(product.keys())}")
            result_array.append({
                "product_code": product['product_code'],
                "product_name": product['product_name'],
                "product_type": product['product_type'],
                "currency": product.get('currency', 'N/A'),
                "description": product.get('description', 'N/A'),  # 安全なアクセス
                "maturity_date": str(product['maturity_date']) if product.get('maturity_date') else None,
                "interest_rate": float(product['interest_rate']) if product.get('interest_rate') else None,
                "risk_level": product.get('risk_level', 'N/A')
            })
    except Exception as parse_error:
        error_message = f"配列パースエラー: {str(parse_error)}"
        
        tool_debug = {
            "executed_query": query,
            "executed_query_results": f"SQL成功({len(products)}件) → 配列パースエラー: {str(parse_error)}",
            "format_prompt": "N/A (配列パースエラーのため未実行)",
            "format_response": "N/A (配列パースエラーのため未実行)",
            "standardize_prompt": full_prompt_text,
            "standardize_response": standardize_response,
            "standardize_parameter": standardize_parameter,
            "execution_time_ms": round((time.time() - start_time) * 1000, 2),
            "results_count": 0,
            "error_type": "ARRAY_PARSE_ERROR"
        }
        
        return MCPResponse(result=error_message, debug_response=tool_debug)
    
    # テキスト化部分
    try:
        result_text = await format_products_to_text(result_array)
    except Exception as format_error:
        error_message = f"テキスト化エラー: {str(format_error)}"
        
        tool_debug = {
            "executed_query": query,
            "executed_query_results": result_array,
            "format_prompt": "商品配列をテキスト形式に変換",
            "format_response": error_message,
            "standardize_prompt": full_prompt_text,
            "standardize_response": standardize_response,
            "standardize_parameter": standardize_parameter,
            "execution_time_ms": round((time.time() - start_time) * 1000, 2),
            "results_count": len(result_array),
            "error_type": "FORMAT_ERROR"
        }
        
        return MCPResponse(result=error_message, debug_response=tool_debug)
    
    # 正常処理
    execution_time = time.time() - start_time
    
    tool_debug = {
        "executed_query": query,
        "executed_query_results": result_array,  # デバッグ用は配列
        "format_prompt": "商品配列をテキスト形式に変換",
        "format_response": result_text,
        "standardize_prompt": full_prompt_text,
        "standardize_response": standardize_response,
        "standardize_parameter": standardize_parameter,
        "execution_time_ms": round(execution_time * 1000, 2),
        "results_count": len(result_array),
        "error_type": "NONE"
    }
    
    return MCPResponse(result=result_text, debug_response=tool_debug)

@app.get("/health")
async def health_check():
    """ヘルスチェックエンドポイント"""
    return {"status": "healthy", "service": "ProductMaster MCP"}

async def standardize_product_arguments(text_input: str) -> tuple[Dict[str, Any], str, str, str]:
    """商品検索引数をLLMで標準化"""
    system_prompt = """あなたは金融商品名抽出の専門家です。入力テキストから純粋な商品名のみを抽出してください。

## 抽出ルール
1. 商品コード（JP001、US002等）があれば product_code に設定
2. 商品名から修飾語句を除去して純粋な商品名のみ抽出
3. 企業名+商品種別の組み合わせを認識

## 除去すべき修飾語句
- "の詳細"、"について"、"を教えて"、"の情報"、"を知りたい"
- "に関して"、"はどう"、"とは"、"って何"

## 商品名認識パターン
- [企業名] + [社債/国債/株式/投信] → 企業名+商品種別
- [国名] + [国債] → 国名+国債
- [ファンド名] + [投信/ファンド] → ファンド名

## 変換例
入力: "ソフトバンク社債の詳細を教えて" → 出力: {"product_code": null, "product_name": "ソフトバンク社債"}
入力: "JP001について知りたい" → 出力: {"product_code": "JP001", "product_name": null}
入力: "日本国債10年の情報" → 出力: {"product_code": null, "product_name": "日本国債10年"}
入力: "米国債はどうですか" → 出力: {"product_code": null, "product_name": "米国債"}
入力: "トヨタ株式を教えて" → 出力: {"product_code": null, "product_name": "トヨタ株式"}

## 出力形式（必須）
JSON形式のみで回答してください。説明文は不要です。
{"product_code": "商品コード または null", "product_name": "商品名 または null"}"""
    
    # 合成プロンプトテキスト作成
    full_prompt_text = f"{system_prompt}\n\nUser Input: {text_input}"
    
    try:
        bedrock = boto3.client('bedrock-runtime', region_name='us-east-1')
        body = json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 200,
            "system": system_prompt,
            "messages": [{"role": "user", "content": text_input}]
        })
        
        response = bedrock.invoke_model(
            body=body,
            modelId='anthropic.claude-3-sonnet-20240229-v1:0',
            accept='application/json',
            contentType='application/json'
        )
        
        response_body = json.loads(response.get('body').read())
        raw_response = response_body['content'][0]['text']
        
        # JSON抽出
        import re
        json_match = re.search(r'\{[^}]+\}', raw_response)
        if json_match:
            standardized = json.loads(json_match.group())
            return standardized, full_prompt_text, raw_response, standardized
        else:
            error_message = f"LLM応答のJSONパース失敗: No JSON found in response"
            fallback = {"product_code": None, "product_name": text_input}
            return fallback, full_prompt_text, raw_response, error_message
        
    except Exception as e:
        error_message = f"LLM応答のJSONパース失敗: {str(e)}"
        fallback = {"product_code": None, "product_name": text_input}
        return fallback, full_prompt_text, raw_response if 'raw_response' in locals() else "LLM呼び出し失敗", error_message

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003)
    params: Dict[str, Any] = {}

def get_db_connection():
    """データベース接続取得"""
    return psycopg2.connect(**DB_CONFIG)

async def call_claude(system_prompt: str, user_message: str) -> str:
    """Claude API呼び出し"""
    try:
        body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 4000,
            "system": system_prompt,
            "messages": [{"role": "user", "content": user_message}]
        }
        
        response = bedrock_client.invoke_model(
            modelId="anthropic.claude-3-sonnet-20240229-v1:0",
            body=json.dumps(body)
        )
        
        response_body = json.loads(response['body'].read())
        return response_body['content'][0]['text']
    except Exception as e:
        logger.error(f"Claude API error: {e}")
        return "{}"

async def standardize_product_details_arguments(text_input: str) -> Dict[str, Any]:
    """商品詳細検索の条件を正規化"""
    system_prompt = """商品詳細検索の条件を正規化してください。

入力テキストから以下を抽出:
- 商品コード（複数可能）
- 商品名での検索
- 複数商品の場合はOR条件として統合

JSON形式で回答:
{"product_codes": ["CODE1", "CODE2"], "product_names": ["名前1"], "search_logic": "OR条件の説明"}

例:
- "商品コード: JP001, JP002" → {"product_codes": ["JP001", "JP002"], "product_names": [], "search_logic": "複数商品コードのOR検索"}
- "日本国債" → {"product_codes": [], "product_names": ["日本国債"], "search_logic": "商品名での検索"}"""
    
    try:
        response = await call_claude(system_prompt, text_input)
        return json.loads(response)
    except:
        return {"product_codes": [], "product_names": [], "search_logic": "解析失敗"}

@app.get("/")
async def root():
    return {"service": "ProductMaster MCP Server", "version": "1.0.0", "protocol": "JSON-RPC 2.0 over HTTP"}

@app.get("/tools/descriptions")
async def get_tool_descriptions():
    """AIChat用ツール情報（1ツール・text_input対応）"""
    return {
        "tools": [
            {
                "name": "get_product_details",
                "description": "特定商品の詳細情報を取得",
                "usage_context": "商品について詳しく知りたい、商品コードや商品名から詳細を調べたい時に使用",
                "parameters": {
                    "text_input": {"type": "string", "description": "商品指定のテキスト（商品コード、商品名など）"}
                }
            }
        ]
    }

@app.post("/mcp")
async def mcp_endpoint(request: MCPRequest):
    """MCP エンドポイント"""
    try:
        if request.method == "tools/call":
            tool_name = request.params.get("name")
            arguments = request.params.get("arguments", {})
            
            if tool_name == "get_product_details":
                result = await get_product_details(arguments)
                # get_product_detailsは既にMCPResponseを返すので、idだけ設定
                result.id = request.id
                return result
            else:
                return MCPResponse(id=request.id, error=f"Unknown tool: {tool_name}")
        
        return MCPResponse(id=request.id, error="Unsupported method")
    except Exception as e:
        logger.error(f"MCP endpoint error: {e}")
        return MCPResponse(id=request.id, error=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003)
