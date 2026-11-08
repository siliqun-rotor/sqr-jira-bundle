// Run the saved project flow through Siliqun Rotor Engine
import { SiliqunRotorClient } from '@siliqun-rotor/sdk';

const client = new SiliqunRotorClient({
  baseUrl: process.env.SQR_BASE_URL!,
  apiKey: process.env.SQR_API_KEY!,
  headers: { 'X-SQR-Project-ID': process.env.SQR_PROJECT_ID! },
});

async function main() {
  const response = await client.chat({
    model: 'sqr',
    flow: 'jira-real-read',
    messages: [{ role: 'user', content: process.env.SQR_TASK || 'Help' }],
  });
  console.log(response);
}

main().catch(console.error);
