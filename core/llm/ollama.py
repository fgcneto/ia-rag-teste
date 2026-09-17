from collections.abc import AsyncIterator
import json,httpx
from django.conf import settings
def payload(system,user,stream): return {'model':settings.OLLAMA_CHAT_MODEL,'stream':stream,'messages':[{'role':'system','content':system},{'role':'user','content':user}],'options':{'temperature':0.1,'num_ctx':settings.OLLAMA_NUM_CTX,'num_predict':settings.OLLAMA_NUM_PREDICT,'num_thread':settings.OLLAMA_NUM_THREAD},'keep_alive':'30m'}
async def embed(texts):
    async with httpx.AsyncClient(timeout=120) as c:
        r=await c.post(settings.OLLAMA_URL.rstrip('/')+'/api/embed',json={'model':settings.OLLAMA_EMBED_MODEL,'input':texts});r.raise_for_status();return r.json()['embeddings']
async def chat(system,user):
    async with httpx.AsyncClient(timeout=httpx.Timeout(600,connect=15)) as c:
        r=await c.post(settings.OLLAMA_URL.rstrip('/')+'/api/chat',json=payload(system,user,False));r.raise_for_status();return r.json()['message']['content']
async def stream_chat(system,user)->AsyncIterator[str]:
    async with httpx.AsyncClient(timeout=httpx.Timeout(600,connect=15)) as c:
      async with c.stream('POST',settings.OLLAMA_URL.rstrip('/')+'/api/chat',json=payload(system,user,True)) as r:
       r.raise_for_status()
       async for line in r.aiter_lines():
        if not line: continue
        obj=json.loads(line); text=(obj.get('message') or {}).get('content') or ''
        if text: yield text
