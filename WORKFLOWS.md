# EdgeMind Technical Workflows & Execution Call-Flow Documentation

This document traces the complete end-to-end call flows, state mutations, and component interactions across all primary operational workflows in EdgeMind V2.1.

---

## 1. Natural Language Coding Request Workflow

This workflow traces a natural-language request from terminal submission down to file modification, verification, and summary reporting.

```mermaid
sequenceDiagram
    autonumber
    actor User as "User Terminal"
    participant CLI as "Interactive Shell (interactive.py)"
    participant Context as "Session & Context (session.py)"
    participant Router as "Intent Router (intent_router.py)"
    participant Graph as "LangGraph Engine (workflow.py)"
    participant Disc as "File Discovery (file_discovery.py)"
    participant Plan as "Planner V2 (planner.py)"
    participant Edit as "Editing Service (editing_service.py)"
    participant Disk as "Filesystem (file_manager.py)"
    participant Rev as "Reviewer V2 (nodes.py)"
    participant Mem as "Memory Manager (memory_manager.py)"

    User->>CLI: Input prompt ("Convert bad.java to Python")
    CLI->>Context: update_session_context(session, query)
    Context->>Disc: resolve_best_file("Convert bad.java to Python")
    Disc-->>Context: Returns "bad.java"
    CLI->>Router: detect_intent(query, has_previous_turn=True)
    Router-->>CLI: Returns (IntentType.EXECUTION, 0.95)
    
    CLI->>CLI: create_state(session, query)
    CLI->>Graph: workflow.invoke(state)
    
    Graph->>Mem: memory_lookup_node(state)
    Mem-->>Graph: Injects memory_context (last 5 records)
    
    Graph->>Plan: planner_node(state) -> create_plan()
    Plan-->>Graph: Returns structured tasks [analyze, edit(create)]
    
    Graph->>Disc: file_discovery_node(state)
    Disc-->>Graph: Discovers "bad.java", target_lang="python"
    
    Graph->>Graph: plan_refinement_node() -> infers create operation, target_file="bad.py"
    
    loop For Each Step in Plan
        Graph->>Graph: get_current_task_node() -> loads task 1 (edit/create)
        Graph->>Graph: route_model_node() -> select_model("edit") -> "qwen2.5-coder:3b"
        Graph->>Edit: execute_task_node() -> prepare_edit(request)
        Edit->>Disk: read_file("bad.java")
        Edit->>Edit: modify_code() -> generates Python implementation
        Edit->>Edit: validate_code() -> Python AST check passed
        Edit->>Disk: create_file("bad.py", content)
        Edit-->>Graph: Returns EditResponse(success=True, diff=...)
        
        Graph->>Rev: reviewer_node()
        Rev->>Disk: Inspects bad.java (preserved) & bad.py (exists, non-empty, AST valid)
        Rev-->>Graph: Sets review_status(success=True)
        
        Graph->>Mem: memory_update_node() -> save_execution(state)
        Mem->>Disk: INSERT INTO task_history in edgemind.db
        Graph->>Graph: advance_step_node() -> current_step += 1
    end

    Graph-->>CLI: Returns final result_data state
    CLI->>CLI: format_change_review(state, result_data)
    CLI->>Context: session.remember(...)
    CLI->>User: Display Execution Summary & Diff Report
```

---

## 2. Autonomous Project & File Discovery Workflow

When a user submits a query referencing code or files, EdgeMind autonomously discovers candidate files without requiring absolute paths.

```mermaid
flowchart TD
    A["User Query Input"] --> B["Extract Query Tokens & Filename Patterns"]
    B --> C{"Pronoun or Continuation Reference?"}
    C -->|Yes: 'it', 'that', 'this file'| D{"Active Context File Available?"}
    D -->|Yes & Exists| E["Return session.active_file"]
    D -->|No| F["Direct Filename Search in Project"]
    C -->|No: Explicit filename| F
    
    F --> G{"Filename token in query?"}
    G -->|Yes: e.g. 'bad.java'| H["Check exact path or rglob basename"]
    H -->|Found & Not Backup| I["Return Resolved Path"]
    G -->|No| J["Search & Rank Candidate Files"]
    
    J --> K["Iterate project files excluding internal & backup dirs"]
    K --> L["Calculate Match Score: Path Name + Keyword Frequency"]
    L --> M["Sort candidates by score descending"]
    M --> N{"Candidates found?"}
    N -->|Yes| I
    N -->|No| O["Fallback: Return Primary Source File in Project Root"]
```

### Discovery Verification Rules
1. **Security Isolation**: Files inside `.git`, `.edgemind`, `backups`, `__pycache__`, `.venv`, `venv`, `node_modules`, `build`, `dist`, `.pytest_cache` are strictly excluded.
2. **Backup Protection**: Files with `.bak` extensions are never selected for discovery.
3. **Pronoun Priority**: Pronouns (`"fix it"`, `"explain that"`) preserve the working `active_file` across turn boundaries.

---

## 3. Planner V2 → LangGraph Execution Call Flow

The Planner converts unstructured prompts into strict multi-step execution plans.

```mermaid
sequenceDiagram
    autonumber
    participant Node as "planner_node (nodes.py)"
    participant PlanFunc as "create_plan() (planner.py)"
    participant Model as "select_model('planner')"
    participant LLM as "Ollama Client"
    participant Clean as "clean_planner_json()"
    participant Pydantic as "Plan.model_validate_json()"
    participant Sanitize as "sanitize_plan_tasks()"

    Node->>PlanFunc: create_plan(user_query, memory_context, active_file)
    PlanFunc->>Model: select_model("planner") -> "phi3:mini"
    PlanFunc->>LLM: generate_response(prompt, system_prompt=PLANNER_SYSTEM_PROMPT)
    LLM-->>PlanFunc: Returns raw JSON string

    PlanFunc->>Clean: clean_planner_json(raw_response)
    Note over Clean: Strips markdown fences ```json, inline comments //, trailing commas
    Clean-->>PlanFunc: Returns cleaned JSON string

    alt Primary Parsing Succeeds
        PlanFunc->>Pydantic: Plan.model_validate_json(cleaned)
        Pydantic-->>PlanFunc: Returns Plan Pydantic object
    else Primary Parsing Fails (SyntaxError / ValidationError)
        PlanFunc->>LLM: Correction Retry Request with Exception details
        LLM-->>PlanFunc: Returns corrected raw response
        PlanFunc->>Clean: clean_planner_json(retry_raw)
        PlanFunc->>Pydantic: Plan.model_validate_json(retry_cleaned)
    end

    PlanFunc->>Sanitize: sanitize_plan_tasks(plan, user_query, active_file)
    Note over Sanitize: Corrects tool names, removes unrequested deployment tasks, injects edit tasks if needed
    Sanitize-->>PlanFunc: Returns list of sanitized task dicts
    PlanFunc-->>Node: Updates state["plan"] and state["current_step"] = 0
```

---

## 4. Analyze → Edit/Create → Validate → Review Pipeline

This workflow illustrates the complete editing and file creation lifecycle within the graph executor and reviewer nodes.

```mermaid
flowchart TD
    A["get_current_task_node"] --> B["route_model_node: Select Model"]
    B --> C["execute_task_node"]
    C --> D{"Task Tool Type?"}
    
    D -->|search| E["search_project_files -> Populate analysis_result"]
    D -->|analyze| F["analyze_project -> Populate analysis_result"]
    D -->|debug| G["debug_error -> Populate analysis_result"]
    D -->|explain| H["explain_code -> Return explanation"]
    D -->|deployment| I["Generate Docker/Compose/Requirements"]
    
    D -->|edit| J{"Operation Mode?"}
    J -->|modify| K["Read source file & Backup to .edgemind/backups/"]
    J -->|create| L["Check target_file does not exist & Verify project root path"]
    
    K --> M["modify_code: LLM generates code with analysis context"]
    L --> M
    
    M --> N["clean_generated_code: Strip markdown, introductory text, XML tags"]
    N --> O["validate_code: AST parse / Delimiter balance check"]
    
    O -->|Validation Failed| P["Return EditResponse success=False"]
    O -->|Validation Passed| Q["generate_diff: Build unified diff"]
    
    Q --> R{"Operation Mode?"}
    R -->|modify| S["FileManager.write_file: Atomic write via temporary file"]
    R -->|create| T["FileManager.create_file: Write new target file"]
    
    S --> U["reviewer_node: Inspect Filesystem"]
    T --> U
    
    U --> V{"Check Physical File State"}
    V -->|Source missing OR Target empty OR Syntax fail| W["review_status.success = False -> Trigger Retry"]
    V -->|Source preserved AND Target written AND Syntax pass| X["review_status.success = True -> Save Memory & Advance"]
```

---

## 5. Conversational & Follow-Up Workflows (Read-Only)

Conversational inquiries bypass graph execution completely, eliminating unwanted file edits.

```mermaid
sequenceDiagram
    autonumber
    actor User as "User Terminal"
    participant Shell as "Interactive Shell"
    participant Router as "Intent Router"
    participant FollowUp as "handle_follow_up()"
    participant Conv as "handle_conversational()"
    participant State as "SessionState"
    participant LLM as "Ollama Client"

    User->>Shell: "What did you change?"
    Shell->>Router: detect_intent("What did you change?", has_previous_turn=True)
    Router-->>Shell: Returns (IntentType.FOLLOW_UP, 0.95)

    Shell->>FollowUp: handle_follow_up(query, session_state)
    FollowUp->>State: Extract last_query, last_edited_file, last_result diff
    FollowUp->>LLM: generate_response(context_prompt, system_prompt=FOLLOW_UP_SYSTEM_PROMPT)
    LLM-->>FollowUp: Returns technical summary of changes
    FollowUp-->>Shell: Returns result string ("EdgeMind: ... No additional files were modified.")
    Shell->>State: remember(query, result)
    Shell->>User: Display Follow-Up Response

    User->>Shell: "What do you think about microservices?"
    Shell->>Router: detect_intent("What do you think about microservices?")
    Router-->>Shell: Returns (IntentType.CONVERSATIONAL, 0.90)

    Shell->>Conv: handle_conversational(query, session_state)
    Conv->>LLM: generate_response(prompt, system_prompt=CONVERSATIONAL_SYSTEM_PROMPT)
    LLM-->>Conv: Returns conversational advice
    Conv-->>Shell: Returns result string
    Shell->>User: Display Companion Response
```

---

## 6. Resource-Aware Model Detection & Model Selection Workflow

EdgeMind dynamically selects installed local Ollama models based on task requirements and system hardware.

```mermaid
flowchart TD
    A["Task Requested: task_name"] --> B["ModelManager.list_installed_models"]
    B --> C{"Any models installed?"}
    
    C -->|No Installed Models| D{"Task Category?"}
    D -->|edit / create / debug / deployment| E["Fallback Default: qwen2.5-coder:3b"]
    D -->|planner / search / explain / conversational| F["Fallback Default: phi3:mini"]
    
    C -->|Models Detected| G["Filter Installed Models"]
    G --> H["get_coding_models: match 'coder', 'code', 'starcoder', 'deepseek-coder', 'codellama'"]
    G --> I["get_general_models: match 'phi3', 'phi', 'llama3', 'llama', 'mistral', 'gemma'"]
    
    H --> J{"Task Category?"}
    J -->|edit / modify / create / debug / deployment| K{"Explicit 'coder' model present?"}
    K -->|Yes| L["Return Preferred Coding Model tag"]
    K -->|No| M["Return First Available Coding Model tag"]
    
    I --> N{"Task Category?"}
    N -->|planner / search / explain / conversational| O{"Explicit 'phi3' or 'mini' present?"}
    O -->|Yes| P["Return Preferred General Model tag"]
    O -->|No| Q["Return First Available General Model tag"]
```

---

## 7. Ollama Startup & Model Setup Workflow

During interactive shell launch (`edgemind`), EdgeMind verifies local environment prerequisites.

```mermaid
sequenceDiagram
    autonumber
    participant CLI as "interactive.run()"
    participant Mgr as "ModelManager"
    participant Checks as "checks.py"
    participant Subproc as "subprocess"
    participant Ollama as "Ollama Client / Daemon"

    CLI->>Mgr: is_ollama_installed()
    alt Ollama binary missing
        Mgr-->>CLI: False
        CLI-->>CLI: Print error & exit ("Install Ollama from https://ollama.com")
    end

    CLI->>Checks: check_ollama() -> ModelManager.is_ollama_running()
    alt Ollama not running
        Checks-->>CLI: False
        CLI->>CLI: Prompt user: "Start it now? (Y/N)"
        alt User confirms 'Y'
            CLI->>Checks: start_ollama()
            Checks->>Subproc: Popen(["ollama", "serve"])
            loop Poll check_ollama() up to 10 seconds
                CLI->>Checks: check_ollama()
            end
        end
    end

    CLI->>Checks: missing_models()
    alt No compatible models installed
        Checks->>Mgr: recommend_default_model()
        Mgr->>Mgr: get_system_resources() -> evaluate RAM
        Mgr-->>Checks: Returns ("qwen2.5-coder:3b", "~2.0 GB")
        CLI->>CLI: Prompt user: "Download model? [Y/n]"
        alt User confirms 'Y'
            CLI->>Ollama: ollama.pull("qwen2.5-coder:3b")
            Ollama-->>CLI: Pull complete
        end
    end

    CLI->>CLI: Launch Interactive Shell Prompt (EdgeMind > )
```

---

## 8. File Creation vs In-Place Modification Workflow

EdgeMind distinguishes between modifying existing files in-place and creating new files (e.g. converting Java to Python).

```mermaid
flowchart TD
    A["Task: edit"] --> B{"Operation Mode?"}
    
    B -->|create| C["Read Source File Content"]
    C --> D["Verify target_file Path is inside Project Root"]
    D --> E{"Target File already exists on Disk?"}
    E -->|Yes| F["Switch Operation to 'modify' & set source_file = target_file"]
    E -->|No| G["Keep operation = 'create' & original_code = ''"]
    
    B -->|modify| H["Verify Source File exists on Disk"]
    H --> I["Read Source File Content"]
    I --> J["FileManager.backup_file: Copy to .edgemind/backups/"]
    
    G --> K["code_modifier.modify_code: LLM generates target implementation"]
    J --> K
    
    K --> L["validator.validate_code: Check target syntax"]
    L --> M["diff_generator.generate_diff: Build preview diff"]
    
    M --> N{"Operation Mode?"}
    N -->|create| O["FileManager.create_file: Write new target file"]
    N -->|modify| P["FileManager.write_file: Atomic replacement via temp file"]
    
    O --> Q["Reviewer Verification: Source file UNTOUCHED, Target file CREATED & VALID"]
    P --> Q2["Reviewer Verification: Target file MODIFIED & VALID"]
```

---

## 9. Validation, Rollback & Recovery Workflow

If syntax validation or disk inspection fails, EdgeMind automatically executes recovery loops.

```mermaid
sequenceDiagram
    autonumber
    participant Graph as "LangGraph Engine"
    participant Exec as "execute_task_node"
    participant Val as "validate_code()"
    participant Rev as "reviewer_node"
    participant Eval as "evaluate_task_node"
    participant Cond as "should_continue"
    participant Retry as "retry_node"
    participant Service as "EditingService"

    Graph->>Exec: execute_task_node()
    Exec->>Val: validate_code(modified_code, "python")
    
    alt AST Syntax Error Detected
        Val-->>Exec: Returns (False, "Python SyntaxError line 12: invalid syntax")
        Exec-->>Graph: State edit_response success=False
        Graph->>Rev: reviewer_node()
        Rev-->>Graph: review_status success=False
        Graph->>Eval: evaluate_task_node() -> execution_success=False
        Graph->>Cond: should_continue(state)
        
        alt retry_count < max_retry (2)
            Cond-->>Graph: Returns "retry"
            Graph->>Retry: retry_node() -> retry_count += 1
            Graph->>Graph: Loop back to route_model_node & executor
        else retry_count >= max_retry
            Cond-->>Graph: Returns "finish"
            Graph->>Service: Optional rollback(file_path)
            Service->>Service: restore_backup() from .edgemind/backups/
        end
    end
```
