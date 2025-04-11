from dotenv import load_dotenv
from custom_config import get_my_config
from portia import Config, LogLevel, Portia, StorageClass
from custom_tool_registry import custom_tool_registry, InstagramAuthenticationTool, InstagramMessagesSummaryTool
import os

load_dotenv()

# Load your custom config
my_config = get_my_config()

# Debug: Print custom tools
print("Custom tools being registered:")
# for tool in custom_tool_registry.tools:
    # print(f"- {tool.tool_id}: {tool.description}"
        #   )

# Instantiate Portia with your custom tools 
# Explicitly pass the tools as a list for clarity
portia = Portia(
    config=my_config, 
    tools=[
        InstagramAuthenticationTool(),
        InstagramMessagesSummaryTool()
    ]
)

# Get Instagram credentials from environment variables
INSTAGRAM_USERNAME = os.environ.get("INSTAGRAM_USERNAME")
INSTAGRAM_PASSWORD = os.environ.get("INSTAGRAM_PASSWORD")

# Direct tool execution method
auth_tool = InstagramAuthenticationTool()
auth_result = auth_tool.run({"username": INSTAGRAM_USERNAME, "password": INSTAGRAM_PASSWORD})
print("Authentication result:", auth_result)

if auth_result.get("status") == "authenticated":
    msg_tool = InstagramMessagesSummaryTool()
    msg_result = msg_tool.run({})
    print("Messages summary:", msg_result)
else:
    print("Authentication failed")