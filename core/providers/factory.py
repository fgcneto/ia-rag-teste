from django.conf import settings

from .github import GitHubProvider


def get_source_provider(provider_name=None):
    selected = str(
        provider_name or settings.SOURCE_PROVIDER
    ).strip().lower()

    if selected == "github":
        return GitHubProvider()

    if selected == "gitlab":
        from .gitlab import GitLabProvider

        return GitLabProvider()

    raise ValueError(
        f"Provider não suportado: {selected}"
    )
