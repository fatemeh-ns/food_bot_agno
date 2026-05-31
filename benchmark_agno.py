import os
import time
import warnings
from dotenv import load_dotenv
from agno.agent import Agent
from agno.models.openai.like import OpenAILike
from agno.models.message import Message
from tools.recommend_tool import recommend_food
from tools.reserve_tool import reserve_food

warnings.filterwarnings("ignore")
load_dotenv()

model = OpenAILike(
    id="openai/gpt-4o-mini",
    api_key=os.getenv("OPENROUTER_API_KEY"),
    base_url="https://openrouter.ai/api/v1",
)

SYSTEM_INSTRUCTIONS = """
You are a food ordering assistant.
- Recommend food based on user preferences
- Filter food by budget, calories, and preferences
- Create food orders when requested
- Use tools to provide accurate results
Always respond in Persian (Farsi).
"""

# ─────
agent_with_tools = Agent(
    name="Food Agent With Tools",
    model=model,
    instructions=SYSTEM_INSTRUCTIONS,
    tools=[recommend_food, reserve_food],
)

agent_no_tools = Agent(
    name="Food Agent No Tools",
    model=model,
    instructions=SYSTEM_INSTRUCTIONS,
    tools=[],
)

# ──────
TEST_INPUT = "غذای گیاهی میخوام، بودجه‌ام ۲۵۰ هزار تومنه"

NUM_RUNS = 5


def run_benchmark(agent, label: str):
    print(f"\n{'='*55}")
    print(f"  {label}")
    print(f"{'='*55}")

    latencies = []

    for i in range(NUM_RUNS):
        messages = [Message(role="user", content=TEST_INPUT)]
        start = time.time()
        result = agent.run(messages)
        elapsed = round(time.time() - start, 2)
        latencies.append(elapsed)

        answer = result.content[:80].replace("\n", " ")
        print(f"  Run {i+1}: {elapsed}s  →  {answer}...")

    avg = round(sum(latencies) / len(latencies), 2)
    mn = round(min(latencies), 2)
    mx = round(max(latencies), 2)

    print(f"\nمیانگین : {avg}s")
    print(f"کمترین  : {mn}s")
    print(f"بیشترین : {mx}s")

    return {"label": label, "avg": avg, "min": mn, "max": mx}


if __name__ == "__main__":
    print("\nشروع بنچمارک Agno Food Agent")
    print(f"تسک: {TEST_INPUT}")
    print(f"تعداد اجرا: {NUM_RUNS}")

    r1 = run_benchmark(agent_with_tools, "با Tool Calling")
    r2 = run_benchmark(agent_no_tools,   "بدون Tool Calling")

    print(f"\n{'='*55}")
    print("نتیجه نهایی مقایسه")
    print(f"{'='*55}")
    print(f"  با Tool    → میانگین: {r1['avg']}s")
    print(f"  بدون Tool  → میانگین: {r2['avg']}s")
    diff = round(r1['avg'] - r2['avg'], 2)
    if diff > 0:
        print(f"\nTool calling  {diff}s کندتر بود (به خاطر اجرای tool)")
    else:
        print(f"\nبدون tool  {abs(diff)}s کندتر بود")
