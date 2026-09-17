import os,json
os.environ.setdefault('DJANGO_SETTINGS_MODULE','config.settings')
import django
django.setup()
from django.contrib.auth import get_user_model
from mcp.server.fastmcp import FastMCP
from asgiref.sync import sync_to_async
from core.mcp.auth import verify_actor_token
from accounts.services import allowed_project_ids
from core.rag.service import retrieve
mcp=FastMCP('AI Knowledge - Knowledge Server', host='0.0.0.0', port=8001)
@mcp.tool()
async def search_knowledge(actor_token:str,question:str,project_ids:list[int])->str:
 """Busca somente no escopo solicitado e autorizado; falha fechada em tentativa de ampliação."""
 actor=verify_actor_token(actor_token)
 user=await sync_to_async(get_user_model().objects.get)(pk=actor['uid'],username=actor['username'],is_active=True)
 allowed=await allowed_project_ids(user)
 requested={int(x) for x in (project_ids or [])}
 if not requested:
  return json.dumps([],ensure_ascii=False)
 if not requested.issubset(allowed):
  raise PermissionError('Escopo MCP contém projeto não autorizado.')
 sources=await retrieve(question,requested)
 safe=[{k:s[k] for k in ('chunk_id','project_id','project','title','url','source_type','content','similarity')} for s in sources]
 return json.dumps(safe,ensure_ascii=False)
@mcp.tool()
async def list_authorized_projects(actor_token:str)->str:
 actor=verify_actor_token(actor_token); user=await sync_to_async(get_user_model().objects.get)(pk=actor['uid'],username=actor['username'],is_active=True)
 ids=await allowed_project_ids(user)
 from knowledge.models import Project
 rows=await sync_to_async(list)(Project.objects.filter(id__in=ids,enabled=True).values('id','path_with_namespace','provider'))
 return json.dumps(rows,ensure_ascii=False)
if __name__=='__main__':
 mcp.run(transport=os.getenv('MCP_TRANSPORT','streamable-http'))
