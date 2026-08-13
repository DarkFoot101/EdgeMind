"""
Phase 17 — Complex Agentic Test Scenario for EdgeMind V2

Tests end-to-end multi-step autonomous behavior:
1. Find relevant file for Fibonacci.
2. Analyze algorithm.
3. Infer Java -> Python language conversion + optimization.
4. Generate multi-step plan.
5. Execute conversion & optimization.
6. Validate Python syntax.
7. Perform Reviewer verification (Java file preserved, Python file created & valid).
8. Persist memory & format change review.
"""

from pathlib import Path
from app.graph.workflow import workflow
from app.editing.validator import validate_code


def test_complex_agentic_fibonacci_flow(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    # 1. Setup sample Java file with unoptimized recursive Fibonacci
    java_file = tmp_path / "FibonacciSlow.java"
    java_file.write_text(
        "public class FibonacciSlow {\n"
        "    public static long fib(int n) {\n"
        "        if (n <= 1) return n;\n"
        "        return fib(n - 1) + fib(n - 2);\n"
        "    }\n"
        "}\n",
        encoding="utf-8",
    )

    query = (
        "Find the implementation responsible for Fibonacci in this project. "
        "Analyze it, identify the performance issue, fix it using dynamic programming, "
        "create a Python implementation, and test the result."
    )

    state = {
        "user_query": query,
        "project_path": str(tmp_path),
        "file_path": "",
        "source_file": None,
        "target_file": None,
        "modified_file": None,
        "source_language": None,
        "target_language": None,
        "plan": [],
        "current_step": 0,
        "current_task": "",
        "task_instruction": "",
        "operation": None,
        "selected_model": "qwen2.5-coder:3b",
        "retry_count": 0,
        "max_retry": 2,
        "result": "",
        "execution_success": False,
        "memory_context": "",
        "edit_response": None,
        "discovered_files": [],
        "review_status": None,
        "change_summary": None,
    }

    # Mock planner output & code modifier output for fast, deterministic workflow testing
    plan_json = (
        '{"tasks": ['
        '  {"tool": "edit", "operation": "create", "instruction": "Convert Java to Python DP", '
        '   "source_file": "FibonacciSlow.java", "target_file": "FibonacciSlow.py", '
        '   "source_language": "java", "target_language": "python"}'
        ']}'
    )
    monkeypatch.setattr(
        "app.graph.planner.generate_response",
        lambda prompt, model, system_prompt: plan_json,
    )

    optimized_python_code = (
        "def fib(n: int) -> int:\n"
        "    if n <= 1:\n"
        "        return n\n"
        "    dp = [0] * (n + 1)\n"
        "    dp[1] = 1\n"
        "    for i in range(2, n + 1):\n"
        "        dp[i] = dp[i - 1] + dp[i - 2]\n"
        "    return dp[n]\n"
    )
    monkeypatch.setattr(
        "app.editing.editing_service.modify_code",
        lambda request: optimized_python_code,
    )

    # 2. Invoke workflow graph
    result = workflow.invoke(state)

    # 3. Verification
    assert result.get("source_file") is not None
    assert "FibonacciSlow.java" in result["source_file"]

    # Target python file must exist
    py_target = tmp_path / "FibonacciSlow.py"
    assert py_target.exists()

    # Source Java file must remain unchanged
    assert java_file.exists()
    assert "public class FibonacciSlow" in java_file.read_text(encoding="utf-8")

    # Generated Python code must pass AST validation
    valid, msg = validate_code(py_target.read_text(encoding="utf-8"), "python")
    assert valid is True

    # Reviewer status should be successful
    review = result.get("review_status") or {}
    assert review.get("success") is True
