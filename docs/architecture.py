"""Draws docs/architecture.png with the official AWS icons.

    uv run --no-project --with diagrams python docs/architecture.py

Needs Graphviz: sudo apt install graphviz
"""

from pathlib import Path

from diagrams import Cluster, Diagram, Edge
from diagrams.aws.business import AlexaForBusiness
from diagrams.aws.general import General
from diagrams.aws.ml import Bedrock, Polly, Transcribe
from diagrams.aws.security import IAM
from diagrams.generic.compute import Rack
from diagrams.generic.database import SQL
from diagrams.generic.device import Mobile
from diagrams.onprem.client import Client, User
from diagrams.onprem.network import Internet
from diagrams.programming.flowchart import Decision
from diagrams.programming.language import Python
from diagrams.saas.chat import Telegram

OUTPUT = Path(__file__).with_name("architecture")
# Planned, not built yet.
NEXT = {"style": "dashed", "color": "#8a8f98", "fontcolor": "#5f6670"}
# Curved edges keep each label next to its arrow; Graphviz misplaces labels on square ones.
GRAPH = {"pad": "0.6", "nodesep": "1.0", "ranksep": "1.3", "fontsize": "28", "labelloc": "t", "splines": "spline"}
EDGE = {"fontsize": "13", "color": "#5f6670"}


def below(label: str) -> str:
    """Graphviz draws the first line of a label over the icon; a blank first line moves the text below it."""
    return "\n" + label


with Diagram(
    "Speech-Resilient Alexa",
    filename=str(OUTPUT),
    outformat="png",
    show=False,
    direction="TB",
    graph_attr=GRAPH,
    edge_attr=EDGE,
):
    person = User(below("Person with\nbroken speech"))

    with Cluster("Clients"):
        alexa = AlexaForBusiness(below("Alexa+\n(the AI host)"))
        page = Client(below("Browser page\nweb/"))

    with Cluster("MCP server · mcp-server/ · FastMCP over Streamable HTTP"):
        voice = Rack(below("Voice routes\n/transcribe · /speak"))
        tools = Python(
            below(
                "MCP tools at /mcp\nunderstand_speech · do_confirmed_request\ncancel_request · resume_unfinished\nemergency_sos"
            )
        )
        brain = Decision(below("Brain\nfixed words first, then the LLM"))

    memory = SQL(below("SQLite memory\nturns · requests · summaries\nprofiles · helpers · alerts"))

    with Cluster("AWS Cloud · us-east-1"):
        transcribe = Transcribe(below("Amazon Transcribe\nspeech to text"))
        polly = Polly(below("Amazon Polly\nneural voice"))
        bedrock = Bedrock(below("Amazon Bedrock\n(optional brain)"))
        location = General(below("Amazon Location\n(next)"))
        IAM(below("IAM user\nspeech-resilient-alexa"))

    with Cluster("Hosted LLMs"):
        openrouter = Internet(below("OpenRouter"))
        groq = Internet(below("Groq"))

    telegram = Telegram(below("Telegram Bot API\n(next)"))
    phone = Mobile(below("Helper's phone"))

    person >> Edge(label="talks") >> alexa
    person >> Edge(label="speaks · types") >> page
    alexa >> Edge(label="tool calls") >> tools
    page >> Edge(label="tool calls") >> tools
    page >> Edge(label="mic audio · reply text") >> voice
    voice >> Edge(label="audio → text") >> transcribe
    voice >> Edge(label="text → voice") >> polly
    tools >> Edge(label="every piece") >> brain
    brain >> bedrock
    brain >> openrouter
    brain >> groq
    tools - Edge(label="every turn") - memory
    tools >> Edge(label="emergency_sos: address", **NEXT) >> location
    tools >> Edge(label="emergency_sos: notify()", **NEXT) >> telegram
    telegram >> Edge(label="alert + map pin", **NEXT) >> phone
