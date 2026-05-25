# app/tools/web_reader.py
import httpx
from langchain_core.tools import tool

@tool
async def read_web_page(url: str) -> str:
    """
    当 search_web 返回的摘要信息不足以回答用户时，使用此工具打开具体的 URL 链接，
    获取网页的全文 Markdown 内容。这对于深入研究某个技术点或阅读详细新闻非常有用。
    """
    # 巧妙利用 r.jina.ai 插件，免去自己写解析器的痛苦
    reader_url = f"https://r.jina.ai/{url}"
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get(reader_url)
            response.raise_for_status()
            content = response.text
            
            # 为了防止 Token 溢出，我们只取前 5000 个字符
            return content[:5000] 
        except Exception as e:
            return f"无法读取网页内容: {str(e)}"