# Requires siliqun-rotor >= 0.1.5; runs the installed project flow
import os
from siliqun_rotor import SiliqunRotorClient

client = SiliqunRotorClient(
    base_url=os.environ["SQR_BASE_URL"],
    api_key=os.environ["SQR_API_KEY"],
    headers={"X-SQR-Project-ID": os.environ["SQR_PROJECT_ID"]},
)

result = client.run_project_flow(
    os.environ["SQR_PROJECT_ID"],
    os.environ["SQR_TASK"],
)
print(result)
