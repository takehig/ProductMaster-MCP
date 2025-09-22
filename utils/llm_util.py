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
    
    async def call_llm_simple(self, full_prompt: str, max_tokens: int = 4000, temperature: float = 0.1) -> Tuple[str, float]:
        """
        LLM呼び出し（シンプル版）
        
        Args:
            full_prompt: 完全なプロンプト（システム+ユーザー結合済み）
            max_tokens: 最大トークン数
            temperature: 温度パラメータ
            
        Returns:
            Tuple[応答, 実行時間ms]
        """
        start_time = time.time()
        
        try:
            # 防御構文: どんな入力でも文字列に変換
            if not isinstance(full_prompt, str):
                full_prompt = str(full_prompt)
            
            # プロンプトからシステム部分とユーザー部分を分離
            if "\n\nUser Input:" in full_prompt:
                system_part, user_part = full_prompt.split("\n\nUser Input:", 1)
                user_message = user_part.strip()
            elif "\n\nUser:" in full_prompt:
                system_part, user_part = full_prompt.split("\n\nUser:", 1)
                user_message = user_part.strip()
            else:
                # フォールバック: 全体をユーザーメッセージとして扱う
                system_part = ""
                user_message = full_prompt
            
            response = await self.call_claude(system_part, user_message, max_tokens, temperature)
            execution_time = (time.time() - start_time) * 1000
            return response, execution_time
            
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            error_response = f"ERROR: {str(e)}"
            logger.error(f"LLM call failed: {e}")
            return error_response, execution_time
    
    async def call_claude(self, system_prompt: str, user_message: str, 
                         max_tokens: int = 1000, temperature: float = 0.1) -> str:
        """
        Claude API呼び出し（基本）
        
        Args:
            system_prompt: システムプロンプト
            user_message: ユーザーメッセージ
            max_tokens: 最大トークン数
            temperature: 温度パラメータ
            
        Returns:
            str: Claude応答
        """
        try:
            # 防御構文: どんな入力でも文字列に変換
            if not isinstance(system_prompt, str):
                system_prompt = str(system_prompt)
            if not isinstance(user_message, str):
                user_message = str(user_message)
            
            body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": max_tokens,
                "temperature": temperature,
                "system": system_prompt,
                "messages": [
                    {
                        "role": "user",
                        "content": user_message
                    }
                ]
            }
            
            response = self.bedrock_client.invoke_model(
                modelId=self.model_id,
                body=json.dumps(body)
            )
            
            response_body = json.loads(response['body'].read())
            return response_body['content'][0]['text'].strip()
            
        except Exception as e:
            logger.error(f"Claude API call failed: {e}")
            raise e


# グローバルインスタンス
llm_util = LLMUtil()
