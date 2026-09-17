import base64
from urllib.parse import quote
import httpx
from django.conf import settings
from .base import SourceControlProvider
class GitHubProvider(SourceControlProvider):
 def __init__(self,token=None): self.base=settings.GITHUB_API_URL.rstrip('/'); self.token=token or settings.GITHUB_SERVICE_TOKEN
 @property
 def headers(self):
  h={'Accept':'application/vnd.github+json','X-GitHub-Api-Version':settings.GITHUB_API_VERSION,'User-Agent':'ai-knowledge-readonly'}
  if self.token:h['Authorization']=f'Bearer {self.token}'
  return h
 async def _get(self,path,params=None):
  async with httpx.AsyncClient(timeout=60,verify=True,follow_redirects=False) as c:
   r=await c.get(self.base+path,headers=self.headers,params=params);r.raise_for_status();return r
 async def _paged(self,path,params=None):
  out=[]; params=dict(params or {}); params['per_page']=100
  for page in range(1,101):
   params['page']=page; data=(await self._get(path,params)).json(); out.extend(data)
   if len(data)<100:break
  return out
 async def repository(self,full_name):
  o,r=full_name.split('/',1);return (await self._get(f'/repos/{quote(o)}/{quote(r)}')).json()
 async def repositories(self): return [await self.repository(n) for n in sorted(settings.GITHUB_ALLOWED_REPOSITORIES)]
 async def branch(self,full_name,branch):
  o,r=full_name.split('/',1);return (await self._get(f'/repos/{quote(o)}/{quote(r)}/branches/{quote(branch,safe="")}')).json()
 async def repository_tree(self,full_name,tree_sha):
  o,r=full_name.split('/',1);return (await self._get(f'/repos/{quote(o)}/{quote(r)}/git/trees/{quote(tree_sha,safe="")}',{'recursive':'1'})).json().get('tree',[])
 async def raw_file(self,full_name,file_path,ref):
  o,r=full_name.split('/',1); d=(await self._get(f'/repos/{quote(o)}/{quote(r)}/contents/{quote(file_path,safe="/")}',{'ref':ref})).json(); return base64.b64decode(d['content']).decode('utf-8',errors='replace')
 async def issues(self,full_name,updated_after=None):
  o,r=full_name.split('/',1); p={'state':'all','sort':'updated','direction':'asc'}
  if updated_after:p['since']=updated_after
  return [x for x in await self._paged(f'/repos/{quote(o)}/{quote(r)}/issues',p) if 'pull_request' not in x]
 async def merge_requests(self,full_name):
  o,r=full_name.split('/',1);return await self._paged(f'/repos/{quote(o)}/{quote(r)}/pulls',{'state':'all','sort':'updated','direction':'asc'})
