import ast
from pathlib import Path


TARGET = Path(__file__).resolve().parent / "scripts" / "langsmith_client.py"


def _call_names() -> set[str]:
    tree = ast.parse(TARGET.read_text())
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Attribute):
                names.add(func.attr)
            elif isinstance(func, ast.Name):
                names.add(func.id)
    return names


def test_legacy_langsmith_thread_and_project_apis_are_not_used():
    calls = _call_names()
    assert "read_thread" not in calls
    assert "list_projects" not in calls
