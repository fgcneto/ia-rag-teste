from django.conf import settings
from django.core import signing
def issue_actor_token(user): return signing.dumps({'uid':user.pk,'username':user.get_username()},key=settings.SECRET_KEY,salt='mcp-actor')
def verify_actor_token(token): return signing.loads(token,key=settings.SECRET_KEY,salt='mcp-actor',max_age=settings.MCP_ACTOR_TOKEN_TTL)
