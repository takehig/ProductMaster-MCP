import httpx

async def get_system_prompt(prompt_key: str) -> str:
    """SystemPrompt Management APIからプロンプト取得"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"http://localhost:8007/api/system-prompts/{prompt_key}",
                timeout=10.0
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"[get_system_prompt] SUCCESS: Found prompt for key: {prompt_key}")
                return data["prompt_text"]
            else:
                error_msg = f"システムプロンプトが取得できませんでした (key: {prompt_key}, status: {response.status_code})"
                print(f"[get_system_prompt] ERROR: {error_msg}")
                return error_msg
                
    except Exception as e:
        error_msg = f"システムプロンプトが取得できませんでした (key: {prompt_key}, error: {str(e)})"
        print(f"[get_system_prompt] EXCEPTION: {error_msg}")
        return error_msg
