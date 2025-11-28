import os
from  loguru import logger
from openai import OpenAI
from pipecat.services.llm_service import FunctionCallParams


async def web_search(params: FunctionCallParams):
    """
    Search the web for current, up-to-date information. Use this when the user asks about recent events, news, current facts, or anything that requires real-time information beyond your training data.
    
    Args:
        query (str): The search query or question to look up on the web.
    """
    try:
        args = getattr(params, "arguments", {}) or {}
        query = args.get("query", "")
        
        if not query:
            await params.result_callback({"error": "No search query provided"})
            return
        
        # Initialize OpenAI client
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        
        # Perform web search using OpenAI's responses API
        response = client.responses.create(
            model="gpt-4o",
            tools=[{"type": "web_search"}],
            input=query
        )
        
        result_text = response.output_text if hasattr(response, 'output_text') else str(response)
        
        logger.info(f"Web search completed for query: {query}")
        await params.result_callback({
            "query": query,
            "result": result_text
        })
    except Exception as e:
        logger.error(f"web_search failed: {e}")
        await params.result_callback({"error": "web_search_failed", "detail": str(e)})