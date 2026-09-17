from asgiref.sync import sync_to_async
from .models import Role
from knowledge.models import Project


def allowed_project_ids_sync(user):
    """Return the maximum project scope granted to a user. Deny by default."""
    if not user or not user.is_authenticated or not user.is_active:
        return set()
    if user.is_superuser:
        return set(Project.objects.filter(enabled=True).values_list('id', flat=True))
    try:
        profile = user.access_profile
    except Exception:
        return set()
    if not profile.active:
        return set()
    if profile.role == Role.ANALYST:
        return set(Project.objects.filter(enabled=True).values_list('id', flat=True))
    return set(
        profile.project_accesses.filter(can_query=True,project__enabled=True)
        .values_list('project_id', flat=True)
    )


def authorized_projects_sync(user):
    ids = allowed_project_ids_sync(user)
    return list(
        Project.objects.filter(id__in=ids, enabled=True)
        .order_by('path_with_namespace')
        .values('id', 'path_with_namespace', 'name', 'provider')
    )


def resolve_query_scope_sync(user, mode='all', requested_project_ids=None):
    """Resolve the effective query scope. Never trusts project IDs from the browser."""
    allowed = allowed_project_ids_sync(user)
    if not allowed:
        return set()
    mode = (mode or 'all').lower()
    if mode == 'all':
        return allowed
    if mode not in {'selected', 'current'}:
        raise ValueError('Modo de escopo inválido.')
    try:
        requested = {int(x) for x in (requested_project_ids or [])}
    except (TypeError, ValueError):
        raise ValueError('Lista de projetos inválida.')
    if not requested:
        raise ValueError('Selecione pelo menos um sistema.')
    if not requested.issubset(allowed):
        unauthorized = requested - allowed
    else:
        unauthorized = set()
    if unauthorized:
        raise PermissionError('Um ou mais sistemas não estão autorizados para este usuário.')
    return requested


async def allowed_project_ids(user):
    return await sync_to_async(allowed_project_ids_sync)(user)


async def authorized_projects(user):
    return await sync_to_async(authorized_projects_sync)(user)


async def resolve_query_scope(user, mode='all', requested_project_ids=None):
    return await sync_to_async(resolve_query_scope_sync)(user, mode, requested_project_ids)
