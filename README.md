# Speech-Resilient-Alexa

## MCP Server

### 1. Install dependencies

From the project root:

```bash
uv sync
```

### 2. Run the MCP server

Run:

```bash
uv run python mcp-server/server.py
```

The server will start at:

```text
http://127.0.0.1:8000/mcp
```

Keep this terminal running.

### 3. Open MCP Inspector

Open a **new terminal** and run:

```bash
npx -y @modelcontextprotocol/inspector
```

This will open the **MCP Inspector** in your browser.

### 4. Add the local MCP server

In MCP Inspector:

1. Click **Add Server**.
2. Set the **Server ID** to:

```text
speech-resilient-alexa
```

3. Select:

```text
HTTP → Streamable HTTP
```

4. Set the server URL to:

```text
http://127.0.0.1:8000/mcp
```

5. Click **Connect**.

You should see:

```text
speech-resilient-alexa
Connected
HTTP
Streamable HTTP
MCP 2025-11-25
```

### 5. Test the MCP server

Open **Tools**.

You should see:

```text
hello_world
```

Run the tool.

Expected result:

```text
Hello from Speech-Resilient Alexa!
```

If you get this result, the MCP server is working correctly.

## Current MCP Tools

| Tool                   | Status  | Purpose                        |
| ---------------------- | ------- | ------------------------------ |
| `hello_world`          | Done    | Verify MCP server connectivity |
| `understand_speech`    | Next    | Understand fragmented speech   |
| `do_confirmed_request` | Planned | Execute a confirmed request    |
| `cancel_request`       | Planned | Cancel a pending request       |
| `resume_unfinished`    | Planned | Resume an unfinished request   |
| `remember_word`        | Later   | Store personal shortcuts       |

## Development Flow

The current development order is:

```text
MCP Server
    ↓
hello_world
    ↓
understand_speech
    ↓
Fake Brain
    ↓
Bedrock Brain
    ↓
Actions + Confirmation
    ↓
Memory
    ↓
Agent + Simulator
```

### Important

Keep the MCP server terminal running while using MCP Inspector.

To stop the server:

```text
Ctrl + C
```
