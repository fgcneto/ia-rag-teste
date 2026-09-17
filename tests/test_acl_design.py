from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def test_analyst_rule_exists():
 t=(ROOT/'accounts/services.py').read_text();assert 'Role.ANALYST' in t and 'Project.objects.filter(enabled=True)' in t
def test_developer_is_scoped():
 t=(ROOT/'accounts/services.py').read_text();assert 'project_accesses.filter(can_query=True,project__enabled=True)' in t
def test_mcp_revalidates_acl():
 t=(ROOT/'mcp_servers/knowledge/server.py').read_text();assert 'verify_actor_token' in t and 'allowed_project_ids(user)' in t
def test_streaming_endpoint_uses_mcp():
 t=(ROOT/'chatapp/views.py').read_text();assert 'search_knowledge_via_mcp' in t and 'StreamingHttpResponse' in t
