import json
from django.conf import settings
from .auth import issue_actor_token


async def search_knowledge_via_mcp(user, question, project_ids):
    """Search through MCP using an already resolved scope; MCP revalidates it."""
    if not settings.MCP_ENABLED:
        raise RuntimeError('MCP desabilitado')
    try:
        from mcp import ClientSession
        from mcp.client.streamable_http import streamablehttp_client
    except ImportError as exc:
        raise RuntimeError('SDK MCP não instalado') from exc
    actor_token = issue_actor_token(user)
    async with streamablehttp_client(settings.MCP_KNOWLEDGE_URL) as (read, write, *_):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(
                'search_knowledge',
                arguments={
                    'actor_token': actor_token,
                    'question': question,
                    'project_ids': sorted(project_ids),
                },
            )
    text = ''.join(
        getattr(x, 'text', '') for x in getattr(result, 'content', [])
        if getattr(x, 'type', None) == 'text'
    )
    return json.loads(text) if text else []
