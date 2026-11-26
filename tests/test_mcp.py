"""Exercise the real MCP SDK over local HTTP, without calling arXiv."""
import socket
import threading
import time
import uvicorn
from mcp.server.fastmcp import FastMCP
from researchagent.tools import MCPPaperSearch


async def test_mcp_real_http_transport():
    sock = socket.socket()
    sock.bind(('127.0.0.1', 0))
    port = sock.getsockname()[1]
    sock.close()
    mcp = FastMCP('test', host='127.0.0.1', port=port)

    @mcp.tool()
    def search_papers(query: str) -> dict:
        return {'results': [{'title': 'Test paper', 'url': 'https://example.org/a',
                             'text': 'Evidence about '+query}]}

    server = uvicorn.Server(uvicorn.Config(mcp.streamable_http_app(), host='127.0.0.1',
                                          port=port, log_level='error'))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    try:
        for _ in range(100):
            if server.started:
                break
            time.sleep(0.02)
        assert server.started
        results = await MCPPaperSearch(f'http://127.0.0.1:{port}/mcp').search('thermal')
        assert results[0]['text'] == 'Evidence about thermal'
    finally:
        server.should_exit = True
        thread.join(timeout=5)
