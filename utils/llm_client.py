# LLM Client for Bedrock

import boto3
import json
import logging
from typing import List

logger = logging.getLogger(__name__)

class BedrockLLMClient:
    def __init__(self, region: str = "us-east-1"):
        self.bedrock = boto3.client('bedrock-runtime', region_name=region)
        self.model_id = "anthropic.claude-3-sonnet-20240229-v1:0"
    
    async def extract_search_criteria(self, user_input: str) -> str:
        """STEP 1: 検索条件抽出"""
        system_prompt = """あなたは金融商品の検索条件を抽出する専門システムです。

## 入力
ユーザーの自然言語による要望（文字列）

## 処理内容
入力された要望から、商品名による検索に適した検索キーワードを抽出してください。

## 重要な制約
- 商品名に含まれる情報のみで検索可能な条件に変換する
- 企業の業績、財務状況、市場動向等の商品名に記載されない情報は除外する
- 地域、業界、商品種別など商品名から類推可能な要素のみ抽出する

## 出力形式
検索キーワードのみを文字列で返してください。説明や前置きは不要です。

## 例
入力: "ハイテクの米国株を持っている顧客を抽出したい"
出力: 米国のハイテク株

入力: "日本の自動車関連の投資商品を探している"  
出力: 日本の自動車関連商品

入力: "安定した債券投資を検討したい"
出力: 債券"""

        return await self._call_bedrock(system_prompt, user_input)
    
    async def filter_products(self, search_criteria: str, products: List[str]) -> List[str]:
        """STEP 2: 商品フィルタリング"""
        system_prompt = """あなたは商品名による曖昧検索を実行する専門システムです。

## 入力データ
1. 検索条件: 文字列
2. 商品リスト: ["id:商品名", "id:商品名", ...] の配列

## 処理内容
検索条件にマッチする商品を商品名のみから判断して抽出してください。

## 判断基準
- 商品名に含まれる企業名、地域名、業界名、商品種別から類推
- あなたの一般知識を使用して企業の業界・地域を判断
- 商品名から読み取れない情報（業績、財務状況等）は考慮しない

## 出力形式
マッチした商品のみを元の形式 ["id:商品名", "id:商品名", ...] の配列で返してください。
JSON形式で出力し、説明や前置きは不要です。

## 例
検索条件: "米国のハイテク株"
商品リスト: ["1:第394回10年国債", "6:Apple Inc.", "7:トヨタ自動車", "8:Microsoft Corporation", "10:Tesla Inc.", "15:Amazon.com", "16:NVIDIA Corporation"]
出力: ["6:Apple Inc.", "8:Microsoft Corporation", "10:Tesla Inc.", "15:Amazon.com", "16:NVIDIA Corporation"]

## 注意事項
- 配列形式を厳密に守ってください
- マッチしない場合は空配列 [] を返してください
- 商品名から判断できない場合は除外してください"""

        products_json = json.dumps(products, ensure_ascii=False)
        user_message = f"検索条件: {search_criteria}\n商品リスト: {products_json}"
        
        response = await self._call_bedrock(system_prompt, user_message)
        
        try:
            # JSON配列をパース
            filtered_products = json.loads(response)
            if isinstance(filtered_products, list):
                return filtered_products
            else:
                logger.error(f"Invalid response format: {response}")
                return []
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {e}, response: {response}")
            return []
    
    async def format_results(self, filtered_products: List[str]) -> str:
        """STEP 3: 結果整形"""
        system_prompt = """あなたは検索結果を整形する専門システムです。

## 入力データ
フィルタ済み商品リスト: ["id:商品名", "id:商品名", ...] の配列

## 処理内容
商品リストを読みやすいテキスト形式に整形してください。

## 出力形式
以下の形式で整形してください：

検索結果: X件

1. 商品名 (ID: Y)
2. 商品名 (ID: Y)
...

## 例
入力: ["6:Apple Inc.", "8:Microsoft Corporation", "10:Tesla Inc."]
出力:
検索結果: 3件

1. Apple Inc. (ID: 6)
2. Microsoft Corporation (ID: 8)  
3. Tesla Inc. (ID: 10)

## 特殊ケース
入力が空配列 [] の場合:
出力: 検索条件にマッチする商品が見つかりませんでした。

## 注意事項
- 番号は1から開始してください
- ID部分は必ず "(ID: X)" の形式にしてください
- 前置きや説明は追加しないでください"""

        products_json = json.dumps(filtered_products, ensure_ascii=False)
        return await self._call_bedrock(system_prompt, products_json)
    
    async def _call_bedrock(self, system_prompt: str, user_message: str) -> str:
        """Bedrock API呼び出し"""
        try:
            body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 4000,
                "system": system_prompt,
                "messages": [
                    {
                        "role": "user",
                        "content": user_message
                    }
                ]
            }
            
            response = self.bedrock.invoke_model(
                modelId=self.model_id,
                body=json.dumps(body)
            )
            
            response_body = json.loads(response['body'].read())
            return response_body['content'][0]['text'].strip()
            
        except Exception as e:
            logger.error(f"Bedrock API call failed: {e}")
            raise Exception(f"LLM processing error: {e}")
