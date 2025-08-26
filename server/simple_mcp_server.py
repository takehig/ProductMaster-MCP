#!/usr/bin/env python3
"""
簡単なProductMaster MCP Server
"""

import asyncio
import json
import requests
from typing import Dict, List, Any

class SimpleProductMasterMCP:
    def __init__(self):
        self.base_url = "http://localhost:8001"
    
    def get_all_products(self) -> Dict[str, Any]:
        """全商品取得"""
        try:
            response = requests.get(f"{self.base_url}/api/products", timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {"error": str(e), "products": []}
    
    def search_products_flexible(self, **kwargs) -> Dict[str, Any]:
        """柔軟な商品検索"""
        data = self.get_all_products()
        if "error" in data:
            return data
        
        products = data.get("products", [])
        filtered = self._apply_filters(products, **kwargs)
        sorted_products = self._apply_sorting(filtered, kwargs.get("sort_by", "relevance"))
        
        limit = kwargs.get("limit", 10)
        limited = sorted_products[:limit]
        
        return {
            "products": limited,
            "total_found": len(filtered),
            "returned": len(limited),
            "filters_applied": {k: v for k, v in kwargs.items() if v},
            "query": kwargs.get("query", "")
        }
    
    def _apply_filters(self, products: List[Dict], **kwargs) -> List[Dict]:
        """フィルター適用"""
        filtered = products.copy()
        
        # 商品タイプフィルター
        if product_types := kwargs.get("product_types"):
            filtered = [p for p in filtered if p.get("product_type") in product_types]
        
        # 通貨フィルター
        if currencies := kwargs.get("currencies"):
            filtered = [p for p in filtered if p.get("currency") in currencies]
        
        # 投資額フィルター
        if investment_range := kwargs.get("investment_range"):
            min_inv = investment_range.get("min")
            max_inv = investment_range.get("max")
            if min_inv is not None:
                filtered = [p for p in filtered if (p.get("minimum_investment") or 0) >= min_inv]
            if max_inv is not None:
                filtered = [p for p in filtered if (p.get("minimum_investment") or 0) <= max_inv]
        
        # リスクレベルフィルター
        if risk_levels := kwargs.get("risk_levels"):
            filtered = [p for p in filtered if p.get("risk_level") in risk_levels]
        
        # 発行者キーワードフィルター
        if issuer_keywords := kwargs.get("issuer_keywords"):
            filtered = [p for p in filtered 
                       if any(keyword.lower() in (p.get("issuer") or "").lower() 
                             for keyword in issuer_keywords)]
        
        # 自然言語クエリフィルター
        if query := kwargs.get("query"):
            query_lower = query.lower()
            filtered = [p for p in filtered 
                       if any(query_lower in str(p.get(field, "")).lower() 
                             for field in ["product_name", "description", "issuer", "product_code"])]
        
        return filtered
    
    def _apply_sorting(self, products: List[Dict], sort_by: str) -> List[Dict]:
        """ソート適用"""
        if sort_by == "investment_desc":
            return sorted(products, key=lambda p: p.get("minimum_investment", 0), reverse=True)
        elif sort_by == "investment_asc":
            return sorted(products, key=lambda p: p.get("minimum_investment", 0))
        elif sort_by == "risk_desc":
            return sorted(products, key=lambda p: p.get("risk_level", 0), reverse=True)
        elif sort_by == "risk_asc":
            return sorted(products, key=lambda p: p.get("risk_level", 0))
        else:
            return products
    
    def get_product_details(self, product_code: str) -> Dict[str, Any]:
        """商品詳細取得"""
        data = self.get_all_products()
        if "error" in data:
            return data
        
        products = data.get("products", [])
        product = next((p for p in products if p.get("product_code") == product_code), None)
        
        if not product:
            return {"error": f"Product with code '{product_code}' not found"}
        
        return {"product": product, "found": True}
    
    def get_statistics(self) -> Dict[str, Any]:
        """統計情報取得"""
        data = self.get_all_products()
        if "error" in data:
            return data
        
        products = data.get("products", [])
        
        # 統計情報生成
        stats = {
            "total_products": len(products),
            "by_type": self._group_by_field(products, "product_type"),
            "by_currency": self._group_by_field(products, "currency"),
            "by_risk_level": self._group_by_field(products, "risk_level"),
            "investment_stats": self._calculate_investment_stats(products)
        }
        
        return stats
    
    def _group_by_field(self, products: List[Dict], field: str) -> Dict[str, int]:
        """指定フィールドでグループ化"""
        groups = {}
        for product in products:
            value = product.get(field, "Unknown")
            groups[str(value)] = groups.get(str(value), 0) + 1
        return groups
    
    def _calculate_investment_stats(self, products: List[Dict]) -> Dict[str, Any]:
        """投資額統計計算"""
        investments = [p.get("minimum_investment", 0) for p in products if p.get("minimum_investment")]
        
        if not investments:
            return {"count": 0}
        
        return {
            "count": len(investments),
            "min": min(investments),
            "max": max(investments),
            "average": sum(investments) / len(investments)
        }
