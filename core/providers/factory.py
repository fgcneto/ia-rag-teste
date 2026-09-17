from django.conf import settings
from .github import GitHubProvider
def get_source_provider():
 if settings.SOURCE_PROVIDER=='github': return GitHubProvider()
 if settings.SOURCE_PROVIDER=='gitlab':
  from .gitlab import GitLabProvider
  return GitLabProvider()
 raise ValueError(f'Provider não suportado: {settings.SOURCE_PROVIDER}')
