# Claude Desktop bundle (`.mcpb`)

This directory builds `lorcana-mcp.mcpb` — a single-file [MCP Bundle](https://github.com/modelcontextprotocol/mcpb) that installs the server into Claude Desktop with one click, no terminal and no `claude_desktop_config.json` editing.

## What's here

| File | Purpose |
|---|---|
| `manifest.json` | MCP Bundle manifest (spec v0.4). Declares the 11 tools, runtime, and how to launch. |
| `pyproject.toml` | Dependency spec — pins `lorcana-mcp==<version>`. Bump with the package version. |
| `server/main.py` | One-line launcher: imports `lorcana_mcp.server.mcp` and runs it. |
| `.mcpbignore` | Files excluded from the packed bundle. |

The bundle is a **thin launcher**, not a copy of the source. Claude Desktop's bundled `uv` reads `pyproject.toml`, installs `lorcana-mcp` from PyPI into an isolated environment on first launch, then runs `server/main.py` — so the bundle always executes the same code as `pip install lorcana-mcp`.

## Build it locally

```bash
npm install -g @anthropic-ai/mcpb
cd packaging/mcpb
mcpb validate manifest.json
mcpb pack . ../../dist/lorcana-mcp.mcpb
```

`mcpb pack` validates the manifest against the schema and zips the directory. The result is `dist/lorcana-mcp.mcpb`.

## Release it

`mcpb pack` runs automatically in CI on every `v*` tag (`.github/workflows/bundle.yml`) and uploads `lorcana-mcp.mcpb` to that GitHub Release. The manual release checklist:

1. Bump `version` in `manifest.json` **and** `version` + the `lorcana-mcp==` pin in `pyproject.toml` to match the package release.
2. Cut the PyPI release first (the bundle installs `lorcana-mcp` from PyPI at runtime — the pinned version must exist there).
3. Push the `vX.Y.Z` tag. CI packs the bundle and attaches it to the release.

## Test the packed bundle

Double-click `lorcana-mcp.mcpb`, or in Claude Desktop go to **Settings → Extensions → Advanced settings → Install extension…** and pick the file. Then ask Claude "look up Mirage - Super Recruiter" to confirm the tools are live.
