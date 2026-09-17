from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def test_backend_validates_requested_scope():
    text=(ROOT/'accounts/services.py').read_text()
    assert 'requested.issubset(allowed)' in text
    assert "raise PermissionError" in text

def test_chat_sends_effective_scope_to_mcp():
    text=(ROOT/'chatapp/views.py').read_text()
    assert 'resolve_query_scope' in text
    assert 'effective_project_ids' in text
    assert 'search_knowledge_via_mcp' in text

def test_mcp_revalidates_requested_scope():
    text=(ROOT/'mcp_servers/knowledge/server.py').read_text()
    assert 'requested.issubset(allowed)' in text
    assert "retrieve(question,requested)" in text

def test_frontend_has_project_selector_without_innerhtml():
    text=(ROOT/'chatapp/templates/chatapp/home.html').read_text()
    assert 'scopeMode' in text and 'projects' in text
    assert 'project_ids:ids' in text
    assert 'innerHTML' not in text
