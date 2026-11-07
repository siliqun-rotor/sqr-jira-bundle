// Run the saved project flow through Siliqun Rotor Engine
import { SiliqunRotorClient } from "@siliqun-rotor/sdk";

const client = new SiliqunRotorClient({
  baseUrl: process.env.SQR_BASE_URL || "https://engine.sqrengine.com",
  apiKey: process.env.SQR_API_KEY!,
  projectId: "sqr-jira-bundle",
});

async function main() {
  const response = await client.chat({
    model: "sqr",
    flow: "jira_flow",
    messages: [{ role: "user", content: process.env.SQR_TASK || "Execute task" }],
  });
  console.log(response);
}

main().catch(console.error);
