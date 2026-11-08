# Run the saved project flow through Siliqun Rotor Engine
import os
from siliqun_rotor import SiliqunRotorClient

client = SiliqunRotorClient(
    base_url=os.environ["SQR_BASE_URL"],
    api_key=os.environ["SQR_API_KEY"],
    headers={"X-SQR-Project-ID": os.environ["SQR_PROJECT_ID"]},
)

result = client.chat(
    model="sqr",
    flow="jira-real-read",
    messages=[{"role": "user", "content": os.environ["SQR_TASK"]}],
)
print(result)
