import os
from dotenv import load_dotenv
from agno.agent import Agent
from agno.models.openai.like import OpenAILike
from tools.recommend_tool import recommend_food
from tools.reserve_tool import reserve_food

load_dotenv()

model = OpenAILike(
    id="openai/gpt-4o-mini",
    api_key=os.getenv("OPENROUTER_API_KEY"),
    base_url="https://openrouter.ai/api/v1",
)

agent = Agent(
    name="Food Agent",
    model=model,
    add_history_to_context=True,
    instructions="""
    You are a food ordering assistant.

    Your job is to:
    - Recommend food based on user preferences
    - Filter food by budget, calories, and preferences
    - Create food orders when requested
    - Use tools to provide accurate results

    Always respond in Persian (Farsi).
    """,
    tools=[recommend_food, reserve_food],
)