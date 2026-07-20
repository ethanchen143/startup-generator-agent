import os
from google.adk.agents import LlmAgent
from google.adk.runners import InMemoryRunner
import asyncio

async def test_run():
    print("Testing ADK agent...")
    agent = LlmAgent(
        name="TestDiscovery",
        model="gemini-2.5-flash",
        instruction="You are a discovery agent."
    )
    print("Agent created:", agent.name)

if __name__ == "__main__":
    asyncio.run(test_run())
