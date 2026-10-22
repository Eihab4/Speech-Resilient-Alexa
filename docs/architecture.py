"""Draws docs/architecture.png with the official AWS icons, and docs/architecture-logos.png, the same picture
with the Groq and OpenRouter logos from docs/icons (keep that one out of the demo video: they're trademarks).

    uv run --no-project --with diagrams python docs/architecture.py

Needs Graphviz: sudo apt install graphviz
"""

import sys
from pathlib import Path

from diagrams import Cluster, Diagram, Edge

# One icon family: AWS service icons for AWS, and AWS "General" icons for everything else.
from diagrams.aws.business import AlexaForBusiness
from diagrams.aws.general import (
    Client,
    Forums,
    General,
    GenericDatabase,
    InternetAlt1,
    MobileClient,
    Multimedia,
    TraditionalServer,
    User,
)
from diagrams.aws.integration import (
    EventbridgeScheduler,
    SimpleNotificationServiceSns,
    SimpleNotificationServiceSnsEmailNotification,
)
from diagrams.aws.ml import Bedrock, MachineLearning, Polly, Transcribe
from diagrams.aws.security import IAM
from diagrams.custom import Custom

ICONS = Path(__file__).with_name("icons")
# Curved edges keep each label next to its arrow; Graphviz misplaces labels on square ones.
GRAPH = {"pad": "0.6", "nodesep": "1.4", "ranksep": "1.6", "fontsize": "28", "labelloc": "t", "splines": "spline"}
EDGE = {"fontsize": "13", "color": "#5f6670"}


def below(label: str) -> str:
    """Graphviz draws the first line of a label over the icon; a blank first line moves the text below it."""
    return "\n" + label


def draw(output: Path, logos: bool) -> None:
    with Diagram(
        "Speech-Resilient Alexa",
        filename=str(output),
        outformat="png",
        show=False,
        direction="TB",
        graph_attr=GRAPH,
        edge_attr=EDGE,
    ):
        person = User(below("Person with\nbroken speech"))

        with Cluster("Clients"):
            alexa = AlexaForBusiness(below("Alexa+"))
            page = Client(below("Browser page"))

        with Cluster("MCP server (FastMCP, Streamable HTTP)"):
            voice = Multimedia(below("Voice routes"))
            tools = TraditionalServer(below("MCP tools"))
            brain = MachineLearning(below("Brain"))

        memory = GenericDatabase(below("SQLite memory"))

        with Cluster("AWS Cloud"):
            transcribe = Transcribe(below("Amazon Transcribe"))
            polly = Polly(below("Amazon Polly"))
            bedrock = Bedrock(below("Amazon Bedrock"))
            location = General(below("Amazon Location"))
            scheduler = EventbridgeScheduler(below("EventBridge Scheduler"))
            reminder_topic = SimpleNotificationServiceSns(below("Reminder SNS topic"))
            email_delivery = SimpleNotificationServiceSnsEmailNotification(below("SNS email delivery"))
            scheduler_role = IAM(below("Scheduler publish role"))
            IAM(below("IAM permissions"))

        reminder_email = User(below("Verified email inbox"))

        with Cluster("Hosted LLMs"):
            openrouter = (
                Custom(below("OpenRouter"), str(ICONS / "openrouter.png"))
                if logos
                else InternetAlt1(below("OpenRouter"))
            )
            groq = Custom(below("Groq"), str(ICONS / "groq.png")) if logos else InternetAlt1(below("Groq"))

        telegram = Forums(below("Telegram bot"))
        phone = MobileClient(below("Helper's phone"))

        person >> alexa
        person >> page
        alexa >> Edge(label="tool calls") >> tools
        page >> Edge(label="tool calls") >> tools
        page >> Edge(label="audio") >> voice
        voice >> Edge(label="speech to text") >> transcribe
        voice >> Edge(label="text to speech") >> polly
        tools >> brain
        brain >> bedrock
        brain >> openrouter
        brain >> groq
        tools - memory
        tools >> Edge(label="address") >> location
        tools >> Edge(label="SOS alert") >> telegram
        telegram >> phone
        tools >> Edge(label="create one-time schedule") >> scheduler
        scheduler >> Edge(label="assume role") >> scheduler_role
        scheduler_role >> Edge(label="sns:Publish") >> reminder_topic
        reminder_topic >> email_delivery >> reminder_email


if __name__ == "__main__":
    here = Path(sys.argv[0]).resolve().parent
    draw(here / "architecture", logos=False)
    draw(here / "architecture-logos", logos=True)
