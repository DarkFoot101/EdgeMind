# EdgeMind Technical Function & Class Reference

This document provides a comprehensive, code-verified technical reference for every module, class, and primary function in EdgeMind V2.1.

---

## 1. CLI Module (`app/cli/`)

### 1.1 [`main.py`](file:///Users/akhi/EdgeMind/app/cli/main.py)

#### Function: `app()` / `Typer` Entry Point
- **File**: [`app/cli/main.py`](file:///Users/akhi/EdgeMind/app/cli/main.py)
- **Purpose**: Typer CLI application instance defining standalone command-line commands.
- **Parameters**: `None`
- **Return Value**: `None`
- **Side Effects**: Parses CLI arguments and routes execution to specific subcommand functions.
- **Callers**: Entry point invoked via python `-m app.cli.main` or CLI invocation.
- **Callees**: `analyze`, `explain`, `debug`, `generate_docker`, `generate_requirements`, `generate_compose`, `interactive`.
- **Interactions**: CLI invocation.

#### Function: `_project_path(project_path: str) -> str`
- **File**: [`app/cli/main.py`](file:///Users/akhi/EdgeMind/app/cli/main.py)
- **Purpose**: Validates and normalizes project directory arguments.
- **Parameters**: `project_path: str` (path string, default `"."`)
- **Return Value**: `str` (canonical absolute path string)
- **Side Effects**: Raises `typer.BadParameter` if path is not an existing directory.
- **Callers**: CLI command functions (`analyze`, `generate_docker`, `generate_requirements`, `generate_compose`).
- **Callees**: `Path.expanduser()`, `Path.is_dir()`, `Path.resolve()`.
- **Interactions**: Filesystem (directory check).

#### Function: `_file_path(file_path: str) -> Path`
- **File**: [`app/cli/main.py`](file:///Users/akhi/EdgeMind/app/cli/main.py)
- **Purpose**: Validates and normalizes file path arguments.
- **Parameters**: `file_path: str`
- **Return Value**: `Path` (canonical absolute Path object)
- **Side Effects**: Raises `typer.BadParameter` if path is not an existing file.
- **Callers**: CLI command functions (`explain`, `debug`).
- **Callees**: `Path.expanduser()`, `Path.is_file()`, `Path.resolve()`.
- **Interactions**: Filesystem (file check).

#### Function: `analyze(project_path: str = ".") -> None`
- **File**: [`app/cli/main.py`](file:///Users/akhi/EdgeMind/app/cli/main.py)
- **Purpose**: CLI command to analyze an entire project directory and print a formatted report.
- **Parameters**: `project_path: str`
- **Return Value**: `None`
- **Side Effects**: Prints report output to stdout.
- **Callers**: Typer CLI router.
- **Callees**: `_project_path()`, `app.tools.project_analyzer.analyze_project()`.
- **Interactions**: Filesystem, Ollama.

#### Function: `explain(file_path: str) -> None`
- **File**: [`app/cli/main.py`](file:///Users/akhi/EdgeMind/app/cli/main.py)
- **Purpose**: CLI command to generate an LLM explanation of a source code file.
- **Parameters**: `file_path: str`
- **Return Value**: `None`
- **Side Effects**: Prints explanation text to stdout.
- **Callers**: Typer CLI router.
- **Callees**: `_file_path()`, `app.tools.code_explainer.explain_code()`.
- **Interactions**: Filesystem, Ollama.

#### Function: `debug(error_file: str) -> None`
- **File**: [`app/cli/main.py`](file:///Users/akhi/EdgeMind/app/cli/main.py)
- **Purpose**: CLI command to analyze an error log or traceback file.
- **Parameters**: `error_file: str`
- **Return Value**: `None`
- **Side Effects**: Reads error file content, prints debug analysis to stdout.
- **Callers**: Typer CLI router.
- **Callees**: `_file_path()`, `Path.read_text()`, `app.tools.debug_assistant.debug_error()`.
- **Interactions**: Filesystem, Ollama.

#### Function: `generate_docker(project_path: str = ".") -> None`
- **File**: [`app/cli/main.py`](file:///Users/akhi/EdgeMind/app/cli/main.py)
- **Purpose**: CLI command to generate and save a Dockerfile.
- **Parameters**: `project_path: str`
- **Return Value**: `None`
- **Side Effects**: Writes `Dockerfile` in project directory.
- **Callers**: Typer CLI router.
- **Callees**: `_project_path()`, `app.tools.deployment_generator.save_dockerfile()`.
- **Interactions**: Filesystem, Ollama.

#### Function: `generate_requirements(project_path: str = ".") -> None`
- **File**: [`app/cli/main.py`](file:///Users/akhi/EdgeMind/app/cli/main.py)
- **Purpose**: CLI command to discover imports and save `requirements.txt`.
- **Parameters**: `project_path: str`
- **Return Value**: `None`
- **Side Effects**: Writes `requirements.txt` in project directory.
- **Callers**: Typer CLI router.
- **Callees**: `_project_path()`, `app.tools.requirements_generator.save_requirements()`.
- **Interactions**: Filesystem.

#### Function: `generate_compose(project_path: str = ".") -> None`
- **File**: [`app/cli/main.py`](file:///Users/akhi/EdgeMind/app/cli/main.py)
- **Purpose**: CLI command to generate and save a `docker-compose.yml` file.
- **Parameters**: `project_path: str`
- **Return Value**: `None`
- **Side Effects**: Writes `docker-compose.yml` in project directory.
- **Callers**: Typer CLI router.
- **Callees**: `_project_path()`, `app.tools.docker_compose_generator.save_docker_compose()`.
- **Interactions**: Filesystem, Ollama.

#### Function: `interactive() -> None`
- **File**: [`app/cli/main.py`](file:///Users/akhi/EdgeMind/app/cli/main.py)
- **Purpose**: CLI command launching the interactive shell.
- **Parameters**: `None`
- **Return Value**: `None`
- **Side Effects**: Passes control to `app.cli.interactive.run()`.
- **Callers**: Typer CLI router, console script entrypoint `edgemind`.
- **Callees**: `app.cli.interactive.run()`.
- **Interactions**: Interactive Terminal.

---

### 1.2 [`interactive.py`](file:///Users/akhi/EdgeMind/app/cli/interactive.py)

#### Function: `format_change_review(state: dict, result_data: dict) -> str`
- **File**: [`app/cli/interactive.py`](file:///Users/akhi/EdgeMind/app/cli/interactive.py)
- **Purpose**: Formats execution results into a formatted report (Workflow Steps, Files Status, Validation & Review, Diff Output).
- **Parameters**: `state: dict`, `result_data: dict`
- **Return Value**: `str` (formatted multi-line summary string)
- **Side Effects**: None (pure string builder).
- **Callers**: `run()` in execution branch.
- **Callees**: `Path.name`.
- **Interactions**: Formatter.

#### Function: `update_session_context(session: SessionState, query: str)`
- **File**: [`app/cli/interactive.py`](file:///Users/akhi/EdgeMind/app/cli/interactive.py)
- **Purpose**: Resolves active project paths and updates `session.active_file` from user query.
- **Parameters**: `session: SessionState`, `query: str`
- **Return Value**: `None`
- **Side Effects**: Mutates `session.project_path`, `session.active_file`, and `session.active_directory`.
- **Callers**: `run()` prior to intent detection.
- **Callees**: `Path.cwd()`, `app.tools.file_discovery.resolve_best_file()`.
- **Interactions**: Filesystem.

#### Function: `create_state(session: SessionState, query: str) -> dict`
- **File**: [`app/cli/interactive.py`](file:///Users/akhi/EdgeMind/app/cli/interactive.py)
- **Purpose**: Builds an initial `EdgeMindState` TypedDict payload for graph execution.
- **Parameters**: `session: SessionState`, `query: str`
- **Return Value**: `dict` (initial state dictionary)
- **Side Effects**: None.
- **Callers**: `run()` when `intent == IntentType.EXECUTION`.
- **Callees**: None.
- **Interactions**: State Builder.

#### Function: `run() -> None`
- **File**: [`app/cli/interactive.py`](file:///Users/akhi/EdgeMind/app/cli/interactive.py)
- **Purpose**: Main interactive shell execution loop. Handles startup checks, activity streaming subscriptions, built-in commands, intent detection, and graph invocation.
- **Parameters**: `None`
- **Return Value**: `None`
- **Side Effects**: Listens for user terminal input, prints banners/events, executes graph workflows, updates SQLite memory, writes files.
- **Callers**: `app.cli.main.interactive()`, console entry point.
- **Callees**: `ModelManager`, `check_ollama`, `start_ollama`, `missing_models`, `print_banner`, `SessionState`, `ActivityStream.subscribe`, `detect_intent`, `handle_follow_up`, `handle_conversational`, `workflow.invoke`, `format_change_review`, `session.remember`, `show_help`, `show_status`, `show_memory`, `clear_terminal`, `run_setup`.
- **Interactions**: Terminal I/O, Filesystem, Ollama, LangGraph, SQLite.

---

### 1.3 [`session.py`](file:///Users/akhi/EdgeMind/app/cli/session.py)

#### Class: `SessionState`
- **File**: [`app/cli/session.py`](file:///Users/akhi/EdgeMind/app/cli/session.py)
- **Purpose**: Dataclass maintaining active shell context across user turns.
- **Fields**: `project_path`, `project_name`, `active_file`, `active_directory`, `selected_model`, `last_query`, `last_result`, `last_plan`, `last_edited_file`, `last_created_file`, `memory_enabled`, `conversation_history`.
- **Callers**: `app.cli.interactive.run()`, `app.cli.commands.show_status()`.

#### Method: `SessionState.remember(...)`
- **File**: [`app/cli/session.py`](file:///Users/akhi/EdgeMind/app/cli/session.py)
- **Purpose**: Updates session context fields and appends to `conversation_history`.
- **Parameters**: `query: str`, `result: str`, `file_path: Optional[str]`, `plan: Optional[list]`, `model: Optional[str]`, `last_edited_file: Optional[str]`, `last_created_file: Optional[str]`.
- **Return Value**: `None`
- **Side Effects**: Mutates instance fields.
- **Callers**: `interactive.run()`.

#### Method: `SessionState.clear()`
- **File**: [`app/cli/session.py`](file:///Users/akhi/EdgeMind/app/cli/session.py)
- **Purpose**: Resets active file, history, and model state to clean defaults.
- **Parameters**: `None`
- **Return Value**: `None`
- **Side Effects**: Mutates instance fields.
- **Callers**: `interactive.run()` on `clear` command.

---

### 1.4 [`commands.py`](file:///Users/akhi/EdgeMind/app/cli/commands.py)

#### Function: `show_help() -> None`
- **File**: [`app/cli/commands.py`](file:///Users/akhi/EdgeMind/app/cli/commands.py)
- **Purpose**: Prints built-in CLI shell commands and example usage prompts.
- **Parameters**: `None`
- **Return Value**: `None`
- **Side Effects**: Writes text to stdout.
- **Callers**: `interactive.run()`.

#### Function: `show_status(session: SessionState) -> None`
- **File**: [`app/cli/commands.py`](file:///Users/akhi/EdgeMind/app/cli/commands.py)
- **Purpose**: Displays system resource metrics, project info, memory entries, and connection status.
- **Parameters**: `session: SessionState`
- **Return Value**: `None`
- **Side Effects**: Queries SQLite and system monitor; writes status block to stdout.
- **Callers**: `interactive.run()`.
- **Callees**: `get_system_resources()`, `search_memory()`.
- **Interactions**: SQLite, System Monitor.

#### Function: `show_memory(session: SessionState) -> None`
- **File**: [`app/cli/commands.py`](file:///Users/akhi/EdgeMind/app/cli/commands.py)
- **Purpose**: Displays the 10 most recent execution records from SQLite for the active project.
- **Parameters**: `session: SessionState`
- **Return Value**: `None`
- **Side Effects**: Queries SQLite; writes memory history to stdout.
- **Callers**: `interactive.run()`.
- **Callees**: `search_memory()`.
- **Interactions**: SQLite.

#### Function: `clear_terminal() -> None`
- **File**: [`app/cli/commands.py`](file:///Users/akhi/EdgeMind/app/cli/commands.py)
- **Purpose**: Clears the terminal screen via ANSI escape code `\033c`.
- **Parameters**: `None`
- **Return Value**: `None`
- **Side Effects**: Resets terminal buffer.
- **Callers**: `interactive.run()`.

---

### 1.5 [`banner.py`](file:///Users/akhi/EdgeMind/app/cli/banner.py)

#### Function: `print_banner() -> None`
- **File**: [`app/cli/banner.py`](file:///Users/akhi/EdgeMind/app/cli/banner.py)
- **Purpose**: Prints the ASCII art banner and subtitle header for EdgeMind V2.1.
- **Parameters**: `None`
- **Return Value**: `None`
- **Side Effects**: Writes banner text to stdout.
- **Callers**: `interactive.run()`.

---

## 2. Intent Routing Module (`app/routing/`)

### 2.1 [`intent_router.py`](file:///Users/akhi/EdgeMind/app/routing/intent_router.py)

#### Class: `IntentType(str, Enum)`
- **File**: [`app/routing/intent_router.py`](file:///Users/akhi/EdgeMind/app/routing/intent_router.py)
- **Purpose**: Enum defining intent categories: `EXECUTION`, `FOLLOW_UP`, `CONVERSATIONAL`.

#### Function: `detect_intent(query: str, has_previous_turn: bool = False) -> Tuple[IntentType, float]`
- **File**: [`app/routing/intent_router.py`](file:///Users/akhi/EdgeMind/app/routing/intent_router.py)
- **Purpose**: Analyzes query string and turn context using regex pattern sets (`FOLLOW_UP_PATTERNS`, `EXECUTION_PATTERNS`, `CONVERSATIONAL_PATTERNS`) to return `(IntentType, confidence_score)`.
- **Parameters**: `query: str`, `has_previous_turn: bool = False`
- **Return Value**: `Tuple[IntentType, float]` (e.g. `(IntentType.EXECUTION, 0.95)`)
- **Side Effects**: None (pure matching logic).
- **Callers**: `app.cli.interactive.run()`.
- **Callees**: `re.search()`.

---

### 2.2 [`conversation_handler.py`](file:///Users/akhi/EdgeMind/app/routing/conversation_handler.py)

#### Function: `handle_follow_up(query: str, session_state: Any, memory_context: str = "") -> Dict[str, Any]`
- **File**: [`app/routing/conversation_handler.py`](file:///Users/akhi/EdgeMind/app/routing/conversation_handler.py)
- **Purpose**: Answers user follow-up questions ("what did you change?", "why?") using prior execution context and SQLite history without altering disk files.
- **Parameters**: `query: str`, `session_state: Any`, `memory_context: str = ""`
- **Return Value**: `Dict[str, Any]` (result dictionary with `result`, `execution_success`, `intent`, `selected_model`)
- **Side Effects**: Emits activity stream progress events; invokes local Ollama inference.
- **Callers**: `interactive.run()`.
- **Callees**: `ActivityStream.emit()`, `select_model()`, `generate_response()`.
- **Interactions**: Ollama.

#### Function: `handle_conversational(query: str, session_state: Any, memory_context: str = "") -> Dict[str, Any]`
- **File**: [`app/routing/conversation_handler.py`](file:///Users/akhi/EdgeMind/app/routing/conversation_handler.py)
- **Purpose**: Handles general architectural questions and chit-chat in pair-programming companion mode.
- **Parameters**: `query: str`, `session_state: Any`, `memory_context: str = ""`
- **Return Value**: `Dict[str, Any]` (result dictionary)
- **Side Effects**: Emits activity stream events; invokes local Ollama inference.
- **Callers**: `interactive.run()`.
- **Callees**: `ActivityStream.emit()`, `select_model()`, `generate_response()`.
- **Interactions**: Ollama.

---

## 3. LangGraph Orchestration Engine (`app/graph/`)

### 3.1 [`state.py`](file:///Users/akhi/EdgeMind/app/graph/state.py)

#### Class: `EdgeMindState(TypedDict)`
- **File**: [`app/graph/state.py`](file:///Users/akhi/EdgeMind/app/graph/state.py)
- **Purpose**: Defines the complete state schema passed between nodes in the LangGraph execution graph.
- **Key Fields**: `user_query`, `project_path`, `file_path`, `source_file`, `target_file`, `modified_file`, `source_language`, `target_language`, `intent`, `plan`, `current_step`, `current_task`, `task_instruction`, `operation`, `selected_model`, `retry_count`, `max_retry`, `result`, `execution_success`, `memory_context`, `analysis_result`, `edit_response`, `discovered_files`, `review_status`, `change_summary`.

---

### 3.2 [`planner_schema.py`](file:///Users/akhi/EdgeMind/app/graph/planner_schema.py)

#### Class: `Task(BaseModel)`
- **File**: [`app/graph/planner_schema.py`](file:///Users/akhi/EdgeMind/app/graph/planner_schema.py)
- **Purpose**: Pydantic schema for individual execution plan task items.
- **Fields**: `tool`, `operation`, `instruction`, `source_file`, `target_file`, `source_language`, `target_language`, `verification_requirements`.

#### Class: `Plan(BaseModel)`
- **File**: [`app/graph/planner_schema.py`](file:///Users/akhi/EdgeMind/app/graph/planner_schema.py)
- **Purpose**: Pydantic schema wrapping the list of planned tasks (`tasks: list[Task]`).

---

### 3.3 [`planner.py`](file:///Users/akhi/EdgeMind/app/graph/planner.py)

#### Function: `clean_planner_json(raw_text: str) -> str`
- **File**: [`app/graph/planner.py`](file:///Users/akhi/EdgeMind/app/graph/planner.py)
- **Purpose**: Cleans raw LLM response text by stripping markdown code blocks, comments, and trailing commas into strictly valid JSON.
- **Parameters**: `raw_text: str`
- **Return Value**: `str` (clean JSON string)
- **Side Effects**: Uses `ast.literal_eval` as fallback for single-quoted dicts.
- **Callers**: `create_plan()`.
- **Callees**: `re.sub()`, `re.search()`, `json.loads()`, `ast.literal_eval()`.

#### Function: `sanitize_plan_tasks(plan: Plan, user_query: str, active_file: str = "") -> list[dict[str, Any]]`
- **File**: [`app/graph/planner.py`](file:///Users/akhi/EdgeMind/app/graph/planner.py)
- **Purpose**: Validates tool names, maps aliases, suppresses unrequested deployment tasks, and ensures edit task inclusion for edit queries.
- **Parameters**: `plan: Plan`, `user_query: str`, `active_file: str = ""`
- **Return Value**: `list[dict[str, Any]]` (sanitized task dictionary list)
- **Side Effects**: Strips quotes from filenames; corrects task tools/operations.
- **Callers**: `create_plan()`.

#### Function: `create_plan(user_query: str, memory: str = "", active_file: str = "") -> list[dict[str, Any]]`
- **File**: [`app/graph/planner.py`](file:///Users/akhi/EdgeMind/app/graph/planner.py)
- **Purpose**: Generates and validates a structured execution plan from LLM output. Includes recovery retry logic on parse failure.
- **Parameters**: `user_query: str`, `memory: str = ""`, `active_file: str = ""`
- **Return Value**: `list[dict[str, Any]]`
- **Side Effects**: Invokes Ollama model; logs retry notices to stdout on recovery.
- **Callers**: `app.graph.nodes.planner_node()`.
- **Callees**: `select_model()`, `generate_response()`, `clean_planner_json()`, `Plan.model_validate_json()`, `sanitize_plan_tasks()`.
- **Interactions**: Ollama.

---

### 3.4 [`evaluator.py`](file:///Users/akhi/EdgeMind/app/graph/evaluator.py)

#### Function: `evaluate_execution(result: object) -> bool`
- **File**: [`app/graph/evaluator.py`](file:///Users/akhi/EdgeMind/app/graph/evaluator.py)
- **Purpose**: Determines if an execution result object is non-empty, non-null, and non-error.
- **Parameters**: `result: object`
- **Return Value**: `bool`
- **Side Effects**: None.
- **Callers**: `app.graph.nodes.evaluate_task_node()`.

---

### 3.5 [`nodes.py`](file:///Users/akhi/EdgeMind/app/graph/nodes.py)

#### Function: `memory_lookup_node(state: EdgeMindState) -> EdgeMindState`
- **File**: [`app/graph/nodes.py`](file:///Users/akhi/EdgeMind/app/graph/nodes.py)
- **Purpose**: Graph Node 1. Queries SQLite memory for the last 5 project execution records and populates `state["memory_context"]`.
- **Callers**: LangGraph workflow.
- **Callees**: `search_memory()`.
- **Interactions**: SQLite.

#### Function: `planner_node(state: EdgeMindState) -> EdgeMindState`
- **File**: [`app/graph/nodes.py`](file:///Users/akhi/EdgeMind/app/graph/nodes.py)
- **Purpose**: Graph Node 2. Invokes Planner V2 (`create_plan()`) and emits activity events.
- **Callers**: LangGraph workflow.
- **Callees**: `ActivityStream.emit()`, `create_plan()`.
- **Interactions**: Ollama.

#### Function: `file_discovery_node(state: EdgeMindState) -> EdgeMindState`
- **File**: [`app/graph/nodes.py`](file:///Users/akhi/EdgeMind/app/graph/nodes.py)
- **Purpose**: Graph Node 3. Autonomous File Discovery. Resolves best project source files and target languages.
- **Callers**: LangGraph workflow.
- **Callees**: `ActivityStream.emit()`, `resolve_best_file()`, `search_project_files()`, `detect_language()`.
- **Interactions**: Filesystem.

#### Function: `plan_refinement_node(state: EdgeMindState) -> EdgeMindState`
- **File**: [`app/graph/nodes.py`](file:///Users/akhi/EdgeMind/app/graph/nodes.py)
- **Purpose**: Graph Node 4. Refines tasks with resolved file paths, languages, create vs modify operations, and security path normalization.
- **Callers**: LangGraph workflow.
- **Callees**: `ActivityStream.emit()`, `resolve_best_file()`, `detect_language()`, `_resolve_in_project()`.
- **Interactions**: Filesystem.

#### Function: `get_current_task_node(state: EdgeMindState) -> EdgeMindState`
- **File**: [`app/graph/nodes.py`](file:///Users/akhi/EdgeMind/app/graph/nodes.py)
- **Purpose**: Graph Node 5. Loads current task attributes into active state fields.
- **Callers**: LangGraph workflow.
- **Callees**: `resolve_best_file()`, `detect_language()`.

#### Function: `route_model_node(state: EdgeMindState) -> EdgeMindState`
- **File**: [`app/graph/nodes.py`](file:///Users/akhi/EdgeMind/app/graph/nodes.py)
- **Purpose**: Graph Node 6. Selects optimal LLM for the current task using `select_model()`.
- **Callers**: LangGraph workflow.
- **Callees**: `select_model()`.

#### Function: `execute_task_node(state: EdgeMindState) -> EdgeMindState`
- **File**: [`app/graph/nodes.py`](file:///Users/akhi/EdgeMind/app/graph/nodes.py)
- **Purpose**: Graph Node 7. Executes active tool task (`search`, `analyze`, `explain`, `debug`, `edit`, `deployment`). For edits, calls `EditingService`.
- **Callers**: LangGraph workflow.
- **Callees**: `ActivityStream.emit()`, `search_project_files()`, `analyze_project()`, `explain_code()`, `debug_error()`, `EditingService`, `save_dockerfile()`, `save_docker_compose()`, `save_requirements()`.
- **Interactions**: Filesystem, Ollama.

#### Function: `reviewer_node(state: EdgeMindState) -> EdgeMindState`
- **File**: [`app/graph/nodes.py`](file:///Users/akhi/EdgeMind/app/graph/nodes.py)
- **Purpose**: Graph Node 8. Inspects physical files on disk, verifies source file preservation, target existence/non-emptiness, and validates syntax on disk.
- **Callers**: LangGraph workflow.
- **Callees**: `ActivityStream.emit()`, `_resolve_in_project()`, `validate_code()`, `Path.read_text()`.
- **Interactions**: Filesystem.

#### Function: `evaluate_task_node(state: EdgeMindState) -> EdgeMindState`
- **File**: [`app/graph/nodes.py`](file:///Users/akhi/EdgeMind/app/graph/nodes.py)
- **Purpose**: Graph Node 9. Evaluates review status and execution metrics to update `state["execution_success"]`.
- **Callers**: LangGraph workflow.
- **Callees**: `evaluate_execution()`.

#### Function: `retry_node(state: EdgeMindState) -> EdgeMindState`
- **File**: [`app/graph/nodes.py`](file:///Users/akhi/EdgeMind/app/graph/nodes.py)
- **Purpose**: Graph Node 10 (Retry branch). Increments `retry_count`.
- **Callers**: LangGraph workflow via `should_continue`.

#### Function: `memory_update_node(state: EdgeMindState) -> EdgeMindState`
- **File**: [`app/graph/nodes.py`](file:///Users/akhi/EdgeMind/app/graph/nodes.py)
- **Purpose**: Graph Node 11. Persists completed task metadata into SQLite (`save_execution`).
- **Callers**: LangGraph workflow.
- **Callees**: `save_execution()`.
- **Interactions**: SQLite.

#### Function: `advance_step_node(state: EdgeMindState) -> EdgeMindState`
- **File**: [`app/graph/nodes.py`](file:///Users/akhi/EdgeMind/app/graph/nodes.py)
- **Purpose**: Graph Node 12. Increments `current_step` and resets `retry_count = 0`.
- **Callers**: LangGraph workflow.

#### Function: `should_continue(state: EdgeMindState) -> str`
- **File**: [`app/graph/nodes.py`](file:///Users/akhi/EdgeMind/app/graph/nodes.py)
- **Purpose**: Conditional routing function after `evaluator`. Returns `"retry"`, `"continue"`, or `"finish"`.
- **Callers**: LangGraph workflow conditional edge.

#### Function: `should_continue_after_advance(state: EdgeMindState) -> str`
- **File**: [`app/graph/nodes.py`](file:///Users/akhi/EdgeMind/app/graph/nodes.py)
- **Purpose**: Conditional routing function after `advance`. Returns `"continue"` or `"finish"`.
- **Callers**: LangGraph workflow conditional edge.

---

### 3.6 [`workflow.py`](file:///Users/akhi/EdgeMind/app/graph/workflow.py)

#### Variable: `workflow`
- **File**: [`app/graph/workflow.py`](file:///Users/akhi/EdgeMind/app/graph/workflow.py)
- **Purpose**: Compiled LangGraph `CompiledStateGraph` instance ready for invocation (`workflow.invoke(state)`).
- **Nodes**: `memory_lookup`, `planner`, `file_discovery`, `plan_refinement`, `task`, `router`, `executor`, `reviewer`, `evaluator`, `retry`, `memory`, `advance`.

---

## 4. Editing Subsystem (`app/editing/`)

### 4.1 [`models.py`](file:///Users/akhi/EdgeMind/app/editing/models.py)

#### Class: `EditRequest`
- **File**: [`app/editing/models.py`](file:///Users/akhi/EdgeMind/app/editing/models.py)
- **Purpose**: Dataclass representing a request to prepare a source code edit.
- **Fields**: `file_path`, `instruction`, `source_code`, `model`, `source_language`, `target_language`, `output_file`, `preserve_formatting`, `create_backup`, `validate_output`, `generate_diff`, `metadata`, `source_file`, `target_file`, `operation`, `analysis_result`, `project_path`.

#### Class: `EditResponse`
- **File**: [`app/editing/models.py`](file:///Users/akhi/EdgeMind/app/editing/models.py)
- **Purpose**: Dataclass storing edit preview outputs.
- **Fields**: `success`, `file_path`, `original_code`, `modified_code`, `diff`, `validation_message`, `backup_path`, `error`, `operation`, `output_file`, `source_file`.

---

### 4.2 [`file_manager.py`](file:///Users/akhi/EdgeMind/app/editing/file_manager.py)

#### Function: `get_project_root(project_path: str = ".") -> Path`
- **File**: [`app/editing/file_manager.py`](file:///Users/akhi/EdgeMind/app/editing/file_manager.py)
- **Purpose**: Returns normalized absolute `Path` of project root.

#### Function: `validate_project_path(file_path: str, project_path: str = ".") -> Path`
- **File**: [`app/editing/file_manager.py`](file:///Users/akhi/EdgeMind/app/editing/file_manager.py)
- **Purpose**: Security function ensuring a path is safely inside project root and not in forbidden internal system directories (`.git`, `.venv`, `node_modules`).
- **Side Effects**: Raises `ValueError` on path traversal attempts or security violations.

#### Function: `read_file(file_path: str, project_path: str = ".") -> str`
- **File**: [`app/editing/file_manager.py`](file:///Users/akhi/EdgeMind/app/editing/file_manager.py)
- **Purpose**: Safely reads text contents of an existing project file.

#### Function: `backup_file(file_path: str, project_path: str = ".") -> str`
- **File**: [`app/editing/file_manager.py`](file:///Users/akhi/EdgeMind/app/editing/file_manager.py)
- **Purpose**: Copies source file into `.edgemind/backups/`, maintaining relative path structure. Returns backup file path.

#### Function: `write_file(file_path: str, content: str, project_path: str = ".") -> None`
- **File**: [`app/editing/file_manager.py`](file:///Users/akhi/EdgeMind/app/editing/file_manager.py)
- **Purpose**: Overwrites existing source file atomically using a temporary file in the target directory (`tempfile.NamedTemporaryFile`). Preserves file permissions mode.

#### Function: `restore_backup(file_path: str, project_path: str = ".") -> None`
- **File**: [`app/editing/file_manager.py`](file:///Users/akhi/EdgeMind/app/editing/file_manager.py)
- **Purpose**: Restores a backed up file from `.edgemind/backups/`.

#### Function: `create_file(file_path: str, content: str, project_path: str = ".", overwrite: bool = False) -> None`
- **File**: [`app/editing/file_manager.py`](file:///Users/akhi/EdgeMind/app/editing/file_manager.py)
- **Purpose**: Safely creates parent directories and writes a new file inside project root.

---

### 4.3 [`code_modifier.py`](file:///Users/akhi/EdgeMind/app/editing/code_modifier.py)

#### Function: `clean_generated_code(code: str) -> str`
- **File**: [`app/editing/code_modifier.py`](file:///Users/akhi/EdgeMind/app/editing/code_modifier.py)
- **Purpose**: Strips markdown code fences (` ``` `), introductory text, closing XML tags, and trailing conversational commentary from LLM output.
- **Return Value**: `str` (clean source code string)

#### Function: `modify_code(request: EditRequest) -> str`
- **File**: [`app/editing/code_modifier.py`](file:///Users/akhi/EdgeMind/app/editing/code_modifier.py)
- **Purpose**: Formulates prompt with analysis findings, source code, and rules; generates modified/converted code via local Ollama LLM.
- **Return Value**: `str` (cleaned code)
- **Interactions**: Ollama.

---

### 4.4 [`validator.py`](file:///Users/akhi/EdgeMind/app/editing/validator.py)

#### Function: `detect_language(file_path: str) -> str`
- **File**: [`app/editing/validator.py`](file:///Users/akhi/EdgeMind/app/editing/validator.py)
- **Purpose**: Detects programming language from file extension (`.py` -> `"python"`, `.java` -> `"java"`, `.cpp` -> `"cpp"`, etc.).

#### Function: `check_balanced_delimiters(code: str) -> tuple[bool, str]`
- **File**: [`app/editing/validator.py`](file:///Users/akhi/EdgeMind/app/editing/validator.py)
- **Purpose**: Checks string-aware delimiter balancing for `()`, `[]`, `{}` across lines.

#### Function: `validate_code(code: str, language: str) -> tuple[bool, str]`
- **File**: [`app/editing/validator.py`](file:///Users/akhi/EdgeMind/app/editing/validator.py)
- **Purpose**: Validates generated code using Python `ast.parse()`, `json.loads()`, structural delimiter checking, Java class checks, or `node -c` execution when available.
- **Return Value**: `tuple[bool, str]` (`(success, message)`)

#### Function: `validate_python(code: str) -> tuple[bool, str]`
- **File**: [`app/editing/validator.py`](file:///Users/akhi/EdgeMind/app/editing/validator.py)
- **Purpose**: Convenience wrapper checking Python syntax validity.

---

### 4.5 [`diff_generator.py`](file:///Users/akhi/EdgeMind/app/editing/diff_generator.py)

#### Function: `generate_diff(original: str, modified: str, filename: str = "file.py") -> str`
- **File**: [`app/editing/diff_generator.py`](file:///Users/akhi/EdgeMind/app/editing/diff_generator.py)
- **Purpose**: Generates human-readable unified diff output using Python's `difflib.unified_diff()`.

---

### 4.6 [`editing_service.py`](file:///Users/akhi/EdgeMind/app/editing/editing_service.py)

#### Class: `EditingService`
- **File**: [`app/editing/editing_service.py`](file:///Users/akhi/EdgeMind/app/editing/editing_service.py)
- **Purpose**: Orchestrates the editing pipeline without asking for user input.

#### Method: `EditingService.prepare_edit(request: EditRequest) -> EditResponse`
- **Purpose**: Reads source file, creates backup if modifying, generates modified code via LLM, validates output syntax, generates unified diff, and returns `EditResponse` without modifying disk target.

#### Method: `EditingService.apply_edit(response: EditResponse, file_path: str, project_path: str = ".") -> bool`
- **Purpose**: Applies an approved preview edit to disk via atomic write or new file creation.

#### Method: `EditingService.rollback(file_path: str, project_path: str = ".") -> bool`
- **Purpose**: Restores file from `.edgemind/backups/`.

#### Method: `EditingService.create_file(response: EditResponse, project_path: str = ".") -> bool`
- **Purpose**: Writes new target file from preview response.

---

## 5. Memory Module (`app/memory/`)

### 5.1 [`database.py`](file:///Users/akhi/EdgeMind/app/memory/database.py)
- **Function `get_connection()`**: Returns sqlite3 connection to `~/.edgemind/edgemind.db`.
- **Function `get_project_path(project_path=".")`**: Returns resolved absolute project path string.

### 5.2 [`schema.py`](file:///Users/akhi/EdgeMind/app/memory/schema.py)
- **Function `initialize_database()`**: Creates `task_history` table if missing and migrates missing columns (`intent`, `source_file`, `target_file`, `operation`, `plan_json`, `diff_text`).

### 5.3 [`memory_manager.py`](file:///Users/akhi/EdgeMind/app/memory/memory_manager.py)
- **Function `save_execution(state: dict[str, Any]) -> None`**: Persists task execution metadata, truncated results, plan JSON, diffs, and success status to SQLite.
- **Function `get_recent_history(limit: int = 5)`**: Retrieves most recent history records across all projects.
- **Function `search_memory(project_path: str = ".")`**: Retrieves the 5 latest history records for a specific project.
- **Function `get_last_execution(project_path: str = ".")`**: Retrieves the single most recent execution record as a dictionary.

---

## 6. Model Management Module (`app/models/`)

### 6.1 [`ollama_client.py`](file:///Users/akhi/EdgeMind/app/models/ollama_client.py)
- **Function `generate_response(prompt: str, model: str = "qwen2.5-coder:3b", system_prompt: Optional[str] = None) -> str`**: Sends system and user messages to `ollama.chat()`, measuring inference latency and returning output string.

### 6.2 [`model_manager.py`](file:///Users/akhi/EdgeMind/app/models/model_manager.py)
- **Class `ModelManager`**:
  - `is_ollama_installed() -> bool`: Checks binary in PATH.
  - `is_ollama_running() -> bool`: Probes `ollama.list()`.
  - `list_installed_models() -> List[str]`: Returns installed model tags.
  - `get_coding_models() -> List[str]`: Filters installed models matching coding patterns (`coder`, `code`, `starcoder`, `deepseek-coder`, `codellama`, `qwen2.5-coder`).
  - `get_general_models() -> List[str]`: Filters installed models matching general patterns (`phi3`, `phi`, `llama3`, `llama`, `mistral`, `gemma`, `qwen`).
  - `select_best_model(task: str) -> str`: Selects optimal model tag for task.
  - `recommend_default_model() -> Tuple[str, str]`: Returns recommended default fallback model based on RAM (`("qwen2.5-coder:3b", "~2.0 GB")`).

### 6.3 [`model_router.py`](file:///Users/akhi/EdgeMind/app/models/model_router.py)
- **Function `select_model(task: str) -> str`**: Public routing function called by graph nodes and tools. Uses `ModelManager` or deterministic fallback defaults (`qwen2.5-coder:3b` for coding, `phi3:mini` for general) when offline.

---

## 7. Event & Monitoring Modules (`app/events/`, `app/resources/`)

### 7.1 [`activity_stream.py`](file:///Users/akhi/EdgeMind/app/events/activity_stream.py)
- **Class `EventType(str, Enum)`**: `INFO`, `PROGRESS`, `SUCCESS`, `WARNING`, `ERROR`, `ACTION`.
- **Class `ActivityEvent`**: Dataclass with `message`, `event_type`, `stage`, `detail`, `icon`. Includes `formatted()` method for Claude-Code style visual indicators (`✓`, `●`, `→`, `⚠`, `✗`).
- **Class `ActivityStream`**: Pub/Sub bus with `subscribe()`, `unsubscribe()`, `emit()`, `clear_listeners()`.

### 7.2 [`system_monitor.py`](file:///Users/akhi/EdgeMind/app/resources/system_monitor.py)
- **Function `get_system_resources() -> dict[str, float]`**: Returns CPU percent and available RAM in GB via `psutil`.

---

## 8. Setup & Utility Tools (`app/setup/`, `app/tools/`)

### 8.1 [`checks.py`](file:///Users/akhi/EdgeMind/app/setup/checks.py) & [`installer.py`](file:///Users/akhi/EdgeMind/app/setup/installer.py)
- **Function `check_ram()`, `check_disk()`, `check_sqlite()`, `check_ollama()`, `start_ollama()`**: System environment verification routines.
- **Function `run_setup()`**: Interactive setup wizard walking through checks, local model detection, and pulling missing models via `ollama.pull()`.

### 8.2 Auxiliary Tools (`app/tools/`)
- **[`file_discovery.py`](file:///Users/akhi/EdgeMind/app/tools/file_discovery.py)**: `search_project_files()`, `resolve_best_file()`.
- **[`project_analyzer.py`](file:///Users/akhi/EdgeMind/app/tools/project_analyzer.py)**: `analyze_project()`.
- **[`code_scanner.py`](file:///Users/akhi/EdgeMind/app/tools/code_scanner.py)**: `scan_project()`.
- **[`code_explainer.py`](file:///Users/akhi/EdgeMind/app/tools/code_explainer.py)**: `explain_code()`.
- **[`debug_assistant.py`](file:///Users/akhi/EdgeMind/app/tools/debug_assistant.py)**: `debug_error()`.
- **[`deployment_generator.py`](file:///Users/akhi/EdgeMind/app/tools/deployment_generator.py)**: `generate_dockerfile()`, `save_dockerfile()`.
- **[`docker_compose_generator.py`](file:///Users/akhi/EdgeMind/app/tools/docker_compose_generator.py)**: `generate_docker_compose()`, `save_docker_compose()`.
- **[`requirements_generator.py`](file:///Users/akhi/EdgeMind/app/tools/requirements_generator.py)**: `extract_imports()`, `save_requirements()`.
- **[`file_reader.py`](file:///Users/akhi/EdgeMind/app/tools/file_reader.py)**: `safe_read_file()`.
