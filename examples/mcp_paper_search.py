"""A real arXiv metadata search MCP server, no paid API key required.

Run: python examples/mcp_paper_search.py
Then set RA_MCP_URL=http://127.0.0.1:8001/mcp . External search remains opt-in.
"""
import xml.etree.ElementTree as ET
import httpx
from mcp.server.fastmcp import FastMCP

mcp = FastMCP('arxiv-paper-search', host='127.0.0.1', port=8001)


@mcp.tool()
async def search_papers(query: str) -> dict:
    """Search arXiv titles and abstracts; return external evidence, not PDF pages."""
    if not query.strip() or len(query) > 4000:
        raise ValueError('Invalid query')
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.get('https://export.arxiv.org/api/query',
            params={'search_query': 'all:'+query, 'start': 0, 'max_results': 5})
        response.raise_for_status()
    root = ET.fromstring(response.content)
    ns = {'a': 'http://www.w3.org/2005/Atom'}
    rows = []
    for entry in root.findall('a:entry', ns):
        rows.append({'title': ' '.join(entry.findtext('a:title', '', ns).split()),
                     'url': entry.findtext('a:id', '', ns).replace('http://', 'https://'),
                     'text': ' '.join(entry.findtext('a:summary', '', ns).split())})
    return {'results': rows}


if __name__ == '__main__':
    mcp.run(transport='streamable-http')
