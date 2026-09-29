from fastmcp import FastMCP

mcp = FastMCP("speech-resilient-alexa")


@mcp.tool()
def hello_world() -> str:
    return "Hello from Speech-Resilient Alexa!"


if __name__ == "__main__":
    mcp.run(transport="streamable-http")