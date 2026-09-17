from .base import SourceControlProvider
class GitLabProvider(SourceControlProvider):
 """Contrato preparado para a migração institucional. Implementação REST entra na próxima etapa."""
 async def repository(self,full_name): raise NotImplementedError('GitLab provider ainda não configurado')
 async def repositories(self): raise NotImplementedError('GitLab provider ainda não configurado')
 async def branch(self,full_name,branch): raise NotImplementedError('GitLab provider ainda não configurado')
 async def repository_tree(self,full_name,tree_sha): raise NotImplementedError('GitLab provider ainda não configurado')
 async def raw_file(self,full_name,file_path,ref): raise NotImplementedError('GitLab provider ainda não configurado')
 async def issues(self,full_name,updated_after=None): raise NotImplementedError('GitLab provider ainda não configurado')
 async def merge_requests(self,full_name): raise NotImplementedError('GitLab provider ainda não configurado')
