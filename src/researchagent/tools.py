import asyncio
import json
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client


class MCPPaperSearch:
    """Call only an explicitly configured Streamable HTTP MCP tool."""
    def __init__(self, url, tool_name='search_papers', timeout=30):
        self.url, self.tool_name, self.timeout = url, tool_name, timeout

    async def search(self, question):
        if not self.url:
            raise RuntimeError('External search requested but RA_MCP_URL is not configured')
        async with asyncio.timeout(self.timeout):
            async with streamable_http_client(self.url) as (read, write, _):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    result = await session.call_tool(self.tool_name, {'query': question})
                    if result.isError:
                        raise RuntimeError('MCP search failed')
                    structured = getattr(result, 'structuredContent', None)
                    if structured is not None:
                        rows = structured.get('results', []) if isinstance(structured, dict) else structured
                    else:
                        text = '\n'.join(c.text for c in result.content if c.type == 'text')
                        parsed = json.loads(text)
                        rows = parsed.get('results', []) if isinstance(parsed, dict) else parsed
                    if not isinstance(rows, list):
                        raise ValueError('MCP tool must return a JSON results list')
                    clean = []
                    for row in rows[:10]:
                        if (isinstance(row, dict) and isinstance(row.get('text'), str)
                                and str(row.get('url', '')).startswith(('https://', 'http://'))):
                            clean.append(dict(title=str(row.get('title', 'External paper'))[:300],
                                              text=row['text'][:6000], url=row['url']))
                    return clean
