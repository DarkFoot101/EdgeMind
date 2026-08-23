"""
Regression tests for EdgeMind Planner V2 robustness.
Tests cover:
- tool = explain + operation = explain mapping
- tool = explain + valid operation
- malformed planner JSON recovery and cleaning
- invalid operation normalization
- valid multi-step plan processing
- planner recovery path
"""

import pytest
from app.graph.planner import (
    clean_planner_json,
    create_plan,
    normalize_planner_dict,
    parse_and_validate_plan,
    sanitize_plan_tasks,
)
from app.graph.planner_schema import Plan, Task


def test_explain_tool_with_explain_operation_copied():
    """
    Test Qwen LLM mistake: tool = explain, operation = explain.
    Must normalize operation to 'inspect' (or another valid op) without failing Pydantic validation.
    """
    raw_json = '''
    {
      "tasks": [
        {
          "tool": "explain",
          "operation": "explain",
          "instruction": "Explain the authentication flow in auth.py",
          "source_file": "auth.py"
        }
      ]
    }
    '''
    plan = parse_and_validate_plan(raw_json)
    assert isinstance(plan, Plan)
    assert len(plan.tasks) == 1
    assert plan.tasks[0].tool == "explain"
    assert plan.tasks[0].operation in {"inspect", "analyze"}

    sanitized = sanitize_plan_tasks(plan, "Explain the authentication flow in auth.py")
    assert sanitized[0]["tool"] == "explain"
    assert sanitized[0]["operation"] in {"inspect", "analyze"}


def test_explain_tool_with_valid_operation():
    """Test tool = explain with valid operation = analyze."""
    raw_json = '''
    {
      "tasks": [
        {
          "tool": "explain",
          "operation": "analyze",
          "instruction": "Explain memory manager design"
        }
      ]
    }
    '''
    plan = parse_and_validate_plan(raw_json)
    assert plan.tasks[0].tool == "explain"
    assert plan.tasks[0].operation == "analyze"


def test_invalid_operation_normalization():
    """Test invalid operation values (e.g. 'custom_op', 'updating') normalize gracefully."""
    raw_json = '''
    {
      "tasks": [
        {
          "tool": "edit",
          "operation": "updating",
          "instruction": "Update function",
          "target_file": null
        },
        {
          "tool": "search",
          "operation": "searching_files",
          "instruction": "Search for usages"
        }
      ]
    }
    '''
    plan = parse_and_validate_plan(raw_json)
    assert plan.tasks[0].operation == "modify"
    assert plan.tasks[1].operation == "search"


def test_malformed_planner_json():
    """Test malformed JSON with single quotes, trailing commas, and markdown fences."""
    raw_malformed = '''```json
    {
      'tasks': [
        {
          'tool': 'edit',
          'operation': 'create',
          'instruction': 'Create test',
          'target_file': 'output.py\'',
        },
      ]
    }
    ```'''
    plan = parse_and_validate_plan(raw_malformed)
    assert len(plan.tasks) == 1
    assert plan.tasks[0].tool == "edit"
    assert plan.tasks[0].target_file == "output.py"


def test_valid_multistep_plan():
    """Test a realistic 5-step plan covering analyze, search, explain, edit, test."""
    raw_multistep = '''
    {
      "tasks": [
        {
          "tool": "analyze",
          "operation": "inspect",
          "instruction": "Analyze the codebase structure"
        },
        {
          "tool": "search",
          "operation": "search",
          "instruction": "Find authentication bug"
        },
        {
          "tool": "explain",
          "operation": "explain",
          "instruction": "Explain why auth is failing"
        },
        {
          "tool": "edit",
          "operation": "modify",
          "instruction": "Fix auth logic in auth.py"
        },
        {
          "tool": "test",
          "operation": "test",
          "instruction": "Validate fixed auth"
        }
      ]
    }
    '''
    plan = parse_and_validate_plan(raw_multistep)
    assert len(plan.tasks) == 5
    assert plan.tasks[2].tool == "explain"
    assert plan.tasks[2].operation == "inspect"

    sanitized = sanitize_plan_tasks(plan, "Analyze project, explain what is wrong, fix the issue, validate")
    assert len(sanitized) == 5
    assert sanitized[2]["tool"] == "explain"
    assert sanitized[2]["operation"] == "inspect"
    assert sanitized[4]["tool"] == "debug"


def test_planner_recovery_fallback(monkeypatch):
    """Test recovery path when first LLM generation is completely invalid and second attempt succeeds."""
    attempt_count = 0

    def mock_generate_response(prompt, model, system_prompt):
        nonlocal attempt_count
        attempt_count += 1
        if attempt_count == 1:
            return "This is not JSON at all, sorry!"
        return '''
        {
          "tasks": [
            {
              "tool": "explain",
              "operation": "explain",
              "instruction": "Recovered plan"
            }
          ]
        }
        '''

    monkeypatch.setattr("app.graph.planner.generate_response", mock_generate_response)

    plan = create_plan("Explain the architecture")
    assert attempt_count == 2
    assert len(plan) == 1
    assert plan[0]["tool"] == "explain"
    assert plan[0]["operation"] == "inspect"
