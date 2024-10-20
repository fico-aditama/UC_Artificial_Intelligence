import aiohttp
import asyncio

async def get_ollama_response_async(prompt, system_prompt, context):
    url = f"{self.base_url}/api/generate"
    payload = {
        'model': 'mistral',
        'prompt': prompt,
        'system': system_prompt,
        'context': context,
        'stream': False,
        'options': {
            'temperature': 0.7,
            'top_p': 0.9,
            'top_k': 40,
        }
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, timeout=300) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    logger.error(f"API error: {response.status}")
                    return f"Error: {response.status}"
    except asyncio.TimeoutError:
        logger.error("Timeout error: Server took too long to respond.")
        return "Error: Timeout"
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return f"Error: {str(e)}"

# To call this in your main function
loop = asyncio.get_event_loop()
response = loop.run_until_complete(get_ollama_response_async(prompt, system_prompt, context))
