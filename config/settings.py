from pathlib import Path
import os
BASE_DIR = Path(__file__).resolve().parent.parent

def env(name, default=None): return os.getenv(name, default)
def env_bool(name, default=False): return env(name, str(default)).lower() in {'1','true','yes','on'}
SECRET_KEY = env('DJANGO_SECRET_KEY','dev-only-change-me')
DEBUG = env_bool('DJANGO_DEBUG', False)
ALLOWED_HOSTS = [x.strip() for x in env('DJANGO_ALLOWED_HOSTS','127.0.0.1,localhost').split(',') if x.strip()]
CSRF_TRUSTED_ORIGINS = [x.strip() for x in env('CSRF_TRUSTED_ORIGINS','http://127.0.0.1:8080').split(',') if x.strip()]
INSTALLED_APPS = [
 'django.contrib.admin','django.contrib.auth','django.contrib.contenttypes','django.contrib.sessions','django.contrib.messages','django.contrib.staticfiles',
 'accounts','knowledge','chatapp','auditlog',
]
MIDDLEWARE = [
 'django.middleware.security.SecurityMiddleware','django.contrib.sessions.middleware.SessionMiddleware','django.middleware.common.CommonMiddleware',
 'django.middleware.csrf.CsrfViewMiddleware','django.contrib.auth.middleware.AuthenticationMiddleware','django.contrib.messages.middleware.MessageMiddleware',
 'django.middleware.clickjacking.XFrameOptionsMiddleware',
]
ROOT_URLCONF='config.urls'
TEMPLATES=[{'BACKEND':'django.template.backends.django.DjangoTemplates','DIRS':[BASE_DIR/'templates'],'APP_DIRS':True,'OPTIONS':{'context_processors':['django.template.context_processors.request','django.contrib.auth.context_processors.auth','django.contrib.messages.context_processors.messages']}}]
WSGI_APPLICATION='config.wsgi.application'; ASGI_APPLICATION='config.asgi.application'
DATABASES={'default':{'ENGINE':'django.db.backends.postgresql','NAME':env('POSTGRES_DB','ai_knowledge'),'USER':env('POSTGRES_USER','ai_knowledge'),'PASSWORD':env('POSTGRES_PASSWORD','CHANGE_ME'),'HOST':env('POSTGRES_HOST','postgres'),'PORT':env('POSTGRES_PORT','5432')}}
AUTH_PASSWORD_VALIDATORS=[]
LANGUAGE_CODE='pt-br'; TIME_ZONE=env('TZ','America/Fortaleza'); USE_I18N=True; USE_TZ=True
STATIC_URL='static/'; STATIC_ROOT=BASE_DIR/'staticfiles'; DEFAULT_AUTO_FIELD='django.db.models.BigAutoField'
LOGIN_URL='/accounts/login/'; LOGIN_REDIRECT_URL='/'; LOGOUT_REDIRECT_URL='/accounts/login/'
SESSION_COOKIE_HTTPONLY=True; SESSION_COOKIE_SAMESITE='Lax'; CSRF_COOKIE_SAMESITE='Lax'
SESSION_COOKIE_SECURE=env_bool('COOKIE_SECURE',False); CSRF_COOKIE_SECURE=env_bool('COOKIE_SECURE',False)
SECURE_PROXY_SSL_HEADER=('HTTP_X_FORWARDED_PROTO','https')
CELERY_BROKER_URL=env('REDIS_URL','redis://redis:6379/0'); CELERY_RESULT_BACKEND=CELERY_BROKER_URL
CELERY_TASK_TRACK_STARTED=True; CELERY_TASK_TIME_LIMIT=3600
OLLAMA_URL=env('OLLAMA_URL','http://ollama:11434'); OLLAMA_CHAT_MODEL=env('OLLAMA_CHAT_MODEL','qwen3:4b'); OLLAMA_EMBED_MODEL=env('OLLAMA_EMBED_MODEL','nomic-embed-text')
OLLAMA_NUM_CTX=int(env('OLLAMA_NUM_CTX','4096')); OLLAMA_NUM_PREDICT=int(env('OLLAMA_NUM_PREDICT','192')); OLLAMA_NUM_THREAD=int(env('OLLAMA_NUM_THREAD','8'))
RAG_TOP_K=int(env('RAG_TOP_K','3')); RAG_MIN_SIMILARITY=float(env('RAG_MIN_SIMILARITY','0.48')); RAG_MAX_CONTEXT_CHARS=int(env('RAG_MAX_CONTEXT_CHARS','4500')); RAG_MAX_CHUNK_CHARS=int(env('RAG_MAX_CHUNK_CHARS','1800'))
MAX_QUESTION_CHARS=int(env('MAX_QUESTION_CHARS','4000'))
MCP_ENABLED=env_bool('MCP_ENABLED',True); MCP_KNOWLEDGE_URL=env('MCP_KNOWLEDGE_URL','http://mcp-knowledge:8001/mcp'); MCP_ACTOR_TOKEN_TTL=int(env('MCP_ACTOR_TOKEN_TTL','120'))
GITHUB_API_URL=env('GITHUB_API_URL','https://api.github.com'); GITHUB_API_VERSION=env('GITHUB_API_VERSION','2022-11-28'); GITHUB_SERVICE_TOKEN=env('GITHUB_SERVICE_TOKEN','')
GITHUB_ALLOWED_REPOSITORIES={x.strip().lower() for x in env('GITHUB_ALLOWED_REPOSITORIES','').split(',') if x.strip()}
SOURCE_PROVIDER=env('SOURCE_PROVIDER','github')
PRESIDIO_ENABLED=env_bool('PRESIDIO_ENABLED',True); PRESIDIO_ANALYZER_URL=env('PRESIDIO_ANALYZER_URL','http://presidio-analyzer:3000')
LOGGING={'version':1,'disable_existing_loggers':False,'formatters':{'jsonish':{'format':'%(asctime)s %(levelname)s %(name)s %(message)s'}},'handlers':{'console':{'class':'logging.StreamHandler','formatter':'jsonish'}},'root':{'handlers':['console'],'level':env('LOG_LEVEL','INFO')}}
