"""The Lab's HTTP app: the MCP server at /mcp (under the app root; uvicorn's root_path is the config's rootPath). The Lab has no page
and no agent of its own: the bearer token gives the role, and every call goes to the records instance (lab/mcp_server.py)."""
from starlette.applications import Starlette
from starlette.routing import Mount

from .mcp_server import LabMCP
from .records import Records


def create_app(config, model=None, transport=None):
    """model is accepted and ignored (callers of the earlier chat app passed one); transport is the records client's, for tests."""
    records = Records(config['recordsUrl'], transport)
    mcp = LabMCP(config, records)
    return Starlette(routes=[Mount('/mcp', app=mcp)], lifespan=lambda app: mcp.manager.run())
