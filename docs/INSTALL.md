# Installing lorcana-mcp

`lorcana-mcp` is a **local MCP server**. It runs on your own machine and talks to your MCP client (Claude and others) over stdio. There is nothing to host, no account, no API key, and no per-user cost — your client already pays for its own model usage; this server only fetches and returns card data.

This guide covers every supported client. Pick your client below; they all end up running the same command, `lorcana-mcp serve`.

- [Which clients work](#which-clients-work)
- [Prerequisites](#prerequisites)
- [Claude Desktop — one-click bundle (easiest)](#claude-desktop--one-click-bundle-easiest)
- [Claude Desktop — manual config](#claude-desktop--manual-config)
- [Claude Code (CLI)](#claude-code-cli)
- [Cursor](#cursor)
- [VS Code (GitHub Copilot / MCP)](#vs-code-github-copilot--mcp)
- [Windsurf](#windsurf)
- [Cline](#cline)
- [Zed](#zed)
- [Any other stdio MCP client](#any-other-stdio-mcp-client)
- [Verify it's working](#verify-its-working)
- [Updating](#updating)
- [Uninstalling](#uninstalling)
- [Troubleshooting](#troubleshooting)
- [What this server can't do](#what-this-server-cant-do)

---

## Which clients work

| Client | Supported | How |
|---|---|---|
| **Claude Desktop** (macOS / Windows) | ✅ | One-click `.mcpb` bundle, or manual config |
| **Claude Code** (CLI) | ✅ | `claude mcp add` |
| **Cursor** | ✅ | `~/.cursor/mcp.json` |
| **VS Code** (Copilot MCP) | ✅ | `.vscode/mcp.json` or user settings |
| **Windsurf** | ✅ | `~/.codeium/windsurf/mcp_config.json` |
| **Cline** | ✅ | MCP Servers panel |
| **Zed** | ✅ | `settings.json` → `context_servers` |
| Any stdio MCP client | ✅ | Command: `lorcana-mcp serve` |
| **Claude.ai** (web) | ❌ | Web needs a hosted remote server; this one is local-only |
| **ChatGPT** (app or web) | ❌ | ChatGPT only connects to hosted remote MCP servers |

See [What this server can't do](#what-this-server-cant-do) for the reasoning on the last two.

---

## Prerequisites

You need **one** of these on your machine:

- **[uv](https://docs.astral.sh/uv/)** (recommended) — a fast Python package runner. Install with:
  ```bash
  # macOS / Linux
  curl -LsSf https://astral.sh/uv/install.sh | sh
  # Windows (PowerShell)
  powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
  ```
  With `uv` you don't have to install `lorcana-mcp` yourself — `uvx lorcana-mcp` fetches and caches it on demand.

- **or Python 3.11+** with `pip`, then:
  ```bash
  pip install lorcana-mcp
  ```

The **Claude Desktop one-click bundle** needs neither — it ships with its own bundled `uv`.

---

## Claude Desktop — one-click bundle (easiest)

1. Download **`lorcana-mcp.mcpb`** from the [latest release](https://github.com/IcaroBichir/lorcana-mcp/releases/latest).
2. Double-click it, **or** open Claude Desktop → **Settings → Extensions → Advanced settings → Install extension…** and choose the file.
3. Click **Install**, then enable it. Restart Claude Desktop if prompted.

That's it — no config file, no Python install. On first use Claude Desktop's bundled `uv` sets up an isolated environment for the server (takes a few seconds once).

---

## Claude Desktop — manual config

If you'd rather not use the bundle:

1. Install the package: `pip install lorcana-mcp` (or have `uv` installed — see [Prerequisites](#prerequisites)).
2. Open the config file:
   - **macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
   - **Windows:** `%APPDATA%\Claude\claude_desktop_config.json`
   - Or: Claude Desktop → **Settings → Developer → Edit Config**.
3. Add the server:
   ```json
   {
     "mcpServers": {
       "lorcana": {
         "command": "uvx",
         "args": ["lorcana-mcp", "serve"]
       }
     }
   }
   ```
   If you installed with `pip` instead of using `uv`, use `"command": "lorcana-mcp", "args": ["serve"]`.
4. Save and **fully quit and reopen** Claude Desktop.

---

## Claude Code (CLI)

```bash
claude mcp add lorcana -- uvx lorcana-mcp serve
```

Or, if installed with pip:

```bash
claude mcp add lorcana -- lorcana-mcp serve
```

Add `-s user` to make it available in every project, or `-s project` to share it with a repo via `.mcp.json`. Check it with `claude mcp list`.

---

## Cursor

Edit `~/.cursor/mcp.json` (global) or `.cursor/mcp.json` (per-project):

```json
{
  "mcpServers": {
    "lorcana": {
      "command": "uvx",
      "args": ["lorcana-mcp", "serve"]
    }
  }
}
```

Then enable **lorcana** in **Cursor Settings → MCP**.

---

## VS Code (GitHub Copilot / MCP)

Create `.vscode/mcp.json` in your workspace (or add to user `settings.json` under `"mcp"`):

```json
{
  "servers": {
    "lorcana": {
      "type": "stdio",
      "command": "uvx",
      "args": ["lorcana-mcp", "serve"]
    }
  }
}
```

Open the file and click **Start** on the server, or run **MCP: List Servers** from the Command Palette.

---

## Windsurf

Edit `~/.codeium/windsurf/mcp_config.json`:

```json
{
  "mcpServers": {
    "lorcana": {
      "command": "uvx",
      "args": ["lorcana-mcp", "serve"]
    }
  }
}
```

Then **Refresh** in **Windsurf Settings → Cascade → MCP Servers**.

---

## Cline

In the Cline panel: **MCP Servers → Configure MCP Servers**, then add:

```json
{
  "mcpServers": {
    "lorcana": {
      "command": "uvx",
      "args": ["lorcana-mcp", "serve"]
    }
  }
}
```

---

## Zed

In `settings.json` (**Zed → Settings**, or `~/.config/zed/settings.json`):

```json
{
  "context_servers": {
    "lorcana": {
      "command": {
        "path": "uvx",
        "args": ["lorcana-mcp", "serve"]
      }
    }
  }
}
```

---

## Any other stdio MCP client

Use whatever the client calls "command" / "executable":

```
command: uvx
args:    lorcana-mcp serve
```

or, with the package pip-installed:

```
command: lorcana-mcp
args:    serve
```

The server speaks MCP over stdio and needs no environment variables.

---

## Verify it's working

Ask your client:

> "Look up Mirage - Super Recruiter"

You should get ink color, cost, stats, keywords, full ability text, and an image URL. If you have a TCGPlayer export handy:

> "Enrich my collection at /absolute/path/to/export.csv"

> **Always give file paths as absolute paths.** The server resolves relative paths against its own working directory, not yours — a relative path fails silently or hits the wrong file.

---

## Updating

- **Bundle:** download the new `lorcana-mcp.mcpb` from [releases](https://github.com/IcaroBichir/lorcana-mcp/releases/latest) and install it over the old one.
- **`uvx` users:** `uvx` uses a cached copy. Refresh it with `uv cache clean lorcana-mcp` (or `uvx --refresh lorcana-mcp serve` once).
- **`pip` users:** `pip install -U lorcana-mcp`.

Card and price data refreshes itself every 24 hours; you don't need to update the package for new card data, only for new features or fixes.

---

## Uninstalling

- **Bundle:** Claude Desktop → **Settings → Extensions** → remove **Disney Lorcana TCG Collection**.
- **Manual config:** delete the `"lorcana"` block from the client's MCP config (or `claude mcp remove lorcana`).
- **Package:** `pip uninstall lorcana-mcp`, and optionally `rm -rf ~/.cache/lorcana-mcp` to clear cached card data.

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| Client shows the server as "failed" / it never connects | Run `uvx lorcana-mcp serve` in a terminal. If that errors, the problem is your Python/`uv` setup, not the client. If it prints nothing and waits, that's correct — it's a stdio server. |
| `command not found: uvx` (or `lorcana-mcp`) | `uv` / the package isn't on the `PATH` the client sees. Use an absolute path to the executable (`which uvx`) in the config, or install via the other method in [Prerequisites](#prerequisites). |
| "not found" for a card you know exists | Ask for it by an informal name so the server uses `resolve_card` (fuzzy) instead of `lookup_card` (exact) — e.g. "find goofy musketeer". |
| Prices or card data look stale or wrong | `lorcana-mcp cache clear`, then retry. Data is cached for 24 hours. |
| Enrich "can't find the file" | Pass an **absolute** path. `~` and relative paths don't resolve the way you expect from inside the server. |
| A brand-new set isn't resolving | [Open an issue](https://github.com/IcaroBichir/lorcana-mcp/issues) — a set-name mapping needs adding. |

CLI health checks:

```bash
lorcana-mcp --version
lorcana-mcp cache stats
```

---

## What this server can't do

**It won't work in Claude.ai (web) or ChatGPT.** Both of those only connect to *remote* MCP servers reachable at an HTTPS URL. `lorcana-mcp` is deliberately local-only:

- Its two most-used tools, `enrich_csv` and `audit_csv`, read and write CSV files on your disk. A shared remote host has no access to your files, so those tools couldn't function there anyway.
- Running it locally means no hosting bill, no auth to manage, and your collection file never leaves your machine.

If you specifically need a hosted instance for the read-only tools, the server is built on FastMCP and can be started with a streamable-HTTP transport — but you'd be standing up and paying for that yourself. That's out of scope for this project's distribution.
