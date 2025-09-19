# ProductMaster API Client

import requests
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class ProductMasterAPIClient:
    def __init__(self, base_url: str = "http://localhost:8001"):
        self.base_url = base_url
    
    async def get_all_products(self) -> List[Dict[str, Any]]:
        """ProductMaster APIから全商品データを取得"""
        try:
            response = requests.get(f"{self.base_url}/api/products", timeout=10)
            response.raise_for_status()
            
            products = response.json()
            logger.info(f"Retrieved {len(products)} products from ProductMaster API")
            return products
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch products from ProductMaster API: {e}")
            raise Exception(f"ProductMaster API error: {e}")
        except Exception as e:
            logger.error(f"Unexpected error in get_all_products: {e}")
            raise Exception(f"API client error: {e}")
    
    def format_products_for_llm(self, products: List[Dict[str, Any]]) -> List[str]:
        """商品データをLLM用の"id:name"形式に変換"""
        try:
            formatted = []
            for product in products:
                product_id = product.get('id', 'unknown')
                product_name = product.get('product_name', 'Unknown Product')
                formatted.append(f"{product_id}:{product_name}")
            
            logger.info(f"Formatted {len(formatted)} products for LLM processing")
            return formatted
            
        except Exception as e:
            logger.error(f"Error formatting products for LLM: {e}")
            raise Exception(f"Product formatting error: {e}")
