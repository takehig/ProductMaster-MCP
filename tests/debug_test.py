#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'server'))

from simple_mcp_server import SimpleProductMasterMCP

def debug_test():
    print("=== デバッグテスト ===")
    
    mcp = SimpleProductMasterMCP()
    
    # 基本接続テスト
    print("\n1. 基本接続テスト:")
    data = mcp.get_all_products()
    print(f"  APIレスポンス: {type(data)}")
    print(f"  キー: {list(data.keys()) if isinstance(data, dict) else 'Not dict'}")
    
    if "error" in data:
        print(f"  エラー: {data['error']}")
        return
    
    products = data.get("products", [])
    print(f"  商品数: {len(products)}")
    
    if products:
        print(f"  最初の商品: {products[0].get('product_name', 'Unknown')}")
    
    # 簡単な検索テスト
    print("\n2. 簡単検索テスト:")
    result = mcp.search_products_flexible(limit=3)
    print(f"  検索結果タイプ: {type(result)}")
    print(f"  検索結果キー: {list(result.keys()) if isinstance(result, dict) else 'Not dict'}")
    
    if "error" in result:
        print(f"  検索エラー: {result['error']}")
    else:
        print(f"  総件数: {result.get('total_found', 'Unknown')}")
        print(f"  返却件数: {result.get('returned', 'Unknown')}")

if __name__ == "__main__":
    debug_test()
