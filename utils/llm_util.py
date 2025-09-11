"""
LLM Utility - Bedrock Claude呼び出しユーティリティ

このファイルは他のリポジトリにコピー可能な汎用LLMユーティリティです。
"""

import json
import time
import logging
import boto3
from typing import Tuple
from config import BEDROCK_CONFIG

logger = logging.getLogger(__name__)


class LLMUtil:
    """LLM呼び出しユーティリティクラス"""
    
    def __init__(self, bedrock_client=None, model_id: str = None):
        if bedrock_client is None:
            self.bedrock_client = boto3.client('bedrock-runtime', region_name=BEDROCK_CONFIG["region_name"])
        else:
            self.bedrock_client = bedrock_client
        self.model_id = model_id or BEDROCK_CONFIG["model_id"]
    
    async def call_claude_with_llm_info(self, system_prompt: str, user_message: str, 
                                      max_tokens: int = 4000, temperature: float = 0.1) -> Tuple[str, str, str, float]:
        """
        Claude API呼び出し（デバッグ情報付き）
        
        Args:
            system_prompt: システムプロンプト
            user_message: ユーザーメッセージ
            max_tokens: 最大トークン数
            temperature: 温度パラメータ
            
        Returns:
            Tuple[応答, プロンプト, 応答, 実行時間ms]
        """
        start_time = time.time()
        full_prompt = f"System: {system_prompt}\\n\\nUser: {user_message}"
        
        try:
            response = await self.call_claude(system_prompt, user_message, max_tokens, temperature)
            execution_time = (time.time() - start_time) * 1000
            return response, full_prompt, response, execution_time
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            error_response = f"ERROR: {str(e)}"
            return error_response, full_prompt, error_response, execution_time
    
    async def call_claude(self, system_prompt: str, user_message: str, 
                         max_tokens: int = 4000, temperature: float = 0.1) -> str:
        """
        Claude API呼び出し（基本）
        
        Args:
            system_prompt: システムプロンプト
            user_message: ユーザーメッセージ
            max_tokens: 最大トークン数
            temperature: 温度パラメータ
            
        Returns:
            Claude応答文字列
        """
        try:
            body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": max_tokens,
                "system": system_prompt,
                "messages": [
                    {
                        "role": "user",
                        "content": user_message
                    }
                ],
                "temperature": temperature
            }
            
            response = self.bedrock_client.invoke_model(
                modelId=self.model_id,
                body=json.dumps(body)
            )
            
            response_body = json.loads(response['body'].read())
            return response_body['content'][0]['text']
            
        except Exception as e:
            logger.error(f"Claude API call failed: {e}")
            print(f"[ERROR] Bedrock call failed: {e}")
            return f"LLMエラー: {str(e)}"
    
    async def call_llm_simple(self, full_prompt: str, max_tokens: int = 4000, temperature: float = 0.1) -> Tuple[str, float]:
        """純粋なLLM呼び出し - 完全なプロンプトを受け取りレスポンスを返す"""
        start_time = time.time()
        
        try:
            body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": max_tokens,
                "system": full_prompt,
                "messages": [{"role": "user", "content": "Please respond."}],
                "temperature": temperature
            }
            
            response = self.bedrock_client.invoke_model(
                modelId=self.model_id,
                body=json.dumps(body)
            )
            
            response_body = json.loads(response['body'].read())
            execution_time = (time.time() - start_time) * 1000
            
            return response_body['content'][0]['text'], execution_time
            
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            logger.error(f"LLM call error: {e}")
            print(f"[ERROR] LLM call failed: {e}")
            return f"LLMエラー: {str(e)}", execution_time

# グローバルインスタンス（後方互換性）
llm_util = LLMUtil()
bedrock_client = llm_util  # 後方互換性のためのエイリアス
