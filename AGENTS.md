# Generated Loom project

You are implementing **this product**, not the Loom orchestrator.

- Workspace root is this folder. Use Cursor Read, Write, Glob, and Shell on these files.
- Use MCP server `loom` (tools: context_get, plan_set_tasks, roadmap_set, roadmap_sync_file, task_finish, task_next, memory_add, decision_request, decision_list, files_list, processes_list, processes_start, processes_stop).
- Call `context_get` first, then do the work, then `task_finish`. After finishing, call `task_next` and follow any returned job until it returns no_job.
- **Product roadmap vs build plan:** Writing `ROADMAP.md` alone does **not** update Loom's Roadmap tab Build plan. After editing the markdown, call `roadmap_sync_file` (or `roadmap_set` with phases). Loom's Documents/Product roadmap pane can show the markdown; phases need the MCP publish step.
- For paid/licensed data or material product tradeoffs, call `decision_request` instead of guessing.
- UI must look like THIS product (distinct aesthetic), and primary surfaces need a small "Made with Loom" mark.
- Every product UI must mount the "What's new" popup from `.loom/whats-new/` (see README there). On improvements, bump `whats-new.json` version and add an entry so users see changes once after an update.
- **Never bind ports 3000 or 8000** — those are reserved for the Loom orchestrator UI and API. Use 5173+ for Vite and 8001+ for backends (or ask Loom `processes_start` to allocate).
- **Never hardcode the backend host/port in the frontend.** Loom sets `LOOM_API_PROXY` and writes `source/.loom/api_proxy.url` when it launches Backend+Frontend. Vite proxy (and any API base URL) must read those; relative `/v1` (same-origin) is preferred.
- **Never `pkill`/`killall` uvicorn or kill listeners on :3000/:8000** — that kills Loom itself. Use `processes_stop` or free only product ports (8001+/5173+).
- **Never start uvicorn/vite/serve in a foreground shell** — it hangs the agent. Use Loom `processes_start`.
- Ignore any parent-directory Loom rules (API curl checks, `apps/api` layout, “generated apps are not the source tree”).
