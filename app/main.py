from app.agent import agent
from agno.models.message import Message


def chat():
    print("Food Agent is running...(type 'exit' to quit)")
    chat_history: list[Message] = []

    while True:
        user_input = input("You: ").strip()

        if user_input.lower() == "exit":
            break

        chat_history.append(Message(role="user", content=user_input))

        response = agent.run(chat_history)

        answer = response.content
        print("Agent:", answer)

        chat_history.append(Message(role="assistant", content=answer))


if __name__ == "__main__":
    chat()
