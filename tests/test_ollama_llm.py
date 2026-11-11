"""
Verification test for Ollama + Llama 3.1 8B LLM Service.
"""

import asyncio
from models.ollama.llm_service import llm_service


async def main():
    print("=" * 60)
    print("DesktopPilot AI: Testing Ollama & Llama 3.1 8B Integration")
    print("=" * 60)

    # 1. Health & Model check
    print("\n[Step 1] Checking Ollama Health & Model Presence...")
    health = await llm_service.check_health()
    print(f"Health Status: {health.get('status')}")
    print(f"Target Model:  {health.get('target_model')}")
    print(f"Installed:     {health.get('installed_models', [])}")

    if not health.get("ready"):
        print("\n[!] WARNING: Target model is not available or Ollama is offline.")
        print(f"Message: {health.get('message', 'Please pull llama3.1:8b in Ollama.')}")
        await llm_service.close()
        return

    # 2. Test chat inference
    print("\n[Step 2] Sending test prompt to Llama 3.1 8B...")
    messages = [
        {"role": "user", "content": "You are DesktopPilot AI. State your role in 1 short sentence."}
    ]
    response = await llm_service.chat(
        messages=messages,
        system_prompt="You are DesktopPilot AI, an autonomous local desktop automation assistant."
    )
    print("\n--- Model Response ---")
    print(response.strip())
    print("----------------------")

    # 3. Test token streaming
    print("\n[Step 3] Testing real-time token streaming...")
    stream_messages = [{"role": "user", "content": "Count from 1 to 5."}]
    print("Streaming output: ", end="", flush=True)
    async for token in llm_service.stream_chat(stream_messages):
        print(token, end="", flush=True)
    print("\n\n[SUCCESS] Ollama + Llama 3.1 8B integration verified successfully!")

    await llm_service.close()


if __name__ == "__main__":
    asyncio.run(main())

