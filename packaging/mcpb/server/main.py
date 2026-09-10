#!/usr/bin/env python3
"""Entry point for the lorcana-mcp Claude Desktop bundle (.mcpb).

This is intentionally a one-line launcher. It runs the exact same stdio server as
`lorcana-mcp serve` from the published PyPI package — the bundle only exists to
install that package into an isolated environment and start it without the user
touching a terminal or a JSON config file.
"""
from lorcana_mcp.server import main

if __name__ == "__main__":
    main()
