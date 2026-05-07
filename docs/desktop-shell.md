# Desktop shell plan

Status: desktop-shell packaging work is deferred until operator review accepts packaging scope.

The desktop shell should be a thin local wrapper around the existing web console and `shyftr serve`. It must not replace the CLI, HTTP API, or web console.

## Recommended approach

- Target Tauri v2 when this work slice starts.
- Keep the React/Vite console standalone-capable.
- Use the desktop wrapper for native folder selection, local service lifecycle, tray/status UI, and first-run checks only.
- Do not bundle Python in the alpha shell; require Python 3.11+ and show clear install instructions.
- Prefer an OS-assigned local port or explicit conflict handling over a hardcoded port.

## Start gate before implementation

Do not begin desktop-shell implementation until:

1. operator review has accepted the packaging scope;
2. the web console has no UI-blocking alpha issues;
3. service start/stop, health polling, port conflict handling, and orphan cleanup are specified;
4. at least two OS families have clone/install/gate evidence or the operator explicitly narrows desktop support;
5. a public/private review confirms the shell will not ship private-core logic or real local memory data.
