// Requires @siliqun-rotor/sdk >= 0.1.5; runs the installed project flow
import { SiliqunRotorClient } from '@siliqun-rotor/sdk';

const client = new SiliqunRotorClient({
  baseUrl: process.env.SQR_BASE_URL!,
  apiKey: process.env.SQR_API_KEY!,
  headers: { 'X-SQR-Project-ID': process.env.SQR_PROJECT_ID! },
});

async function main() {
  const response = await client.runProjectFlow(
    process.env.SQR_PROJECT_ID!,
    process.env.SQR_TASK || 'Help',
  );
  console.log(response);
}

main().catch(console.error);
