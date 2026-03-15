# Spendsy MCP: Claude Desktop Configuration

To use the Spendsy Financial Assistant in Claude Desktop, add the following to your `config.json`.

### Config File Location
- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
- **Linux**: `~/.config/Claude/claude_desktop_config.json`

### Configuration Snippet

```json
{
  "mcpServers": {
    "spendsy": {
      "command": "/home/rohinvengatesh04/Spendsy/Spendsy/venv/bin/python",
      "args": [
        "/home/rohinvengatesh04/Spendsy/Spendsy/spendsy-mcp/server.py"
      ],
      "env": {
        "FINANCE_SERVICE_URL": "http://localhost:8002",
        "PARSER_SERVICE_URL": "http://localhost:8003",
        "INTERNAL_API_KEY": "internal-dev-key"
      }
    }
  }
}
```

### Steps
1. Open the file.
2. Paste the snippet above inside the `mcpServers` object.
3. Restart Claude Desktop.
4. You should see a 🔌 icon in Claude, indicating the Spendsy tools are available.
