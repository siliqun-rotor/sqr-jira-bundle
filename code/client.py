# Run the saved project flow through Siliqun Rotor Engine
import os
from siliqun_rotor import SiliqunRotorClient

client = SiliqunRotorClient(
    base_url=os.environ.get("SQR_BASE_URL", "https://engine.sqrengine.com"),
    api_key=os.environ["SQR_API_KEY"],
    headers={"X-SQR-Project-ID": "sqr-jira-bundle"},
)

result = client.chat(
    model="sqr",
    flow="jira_flow",
    messages=[{"role": "user", "content": os.environ["SQR_TASK"]}],
)
print(result)
