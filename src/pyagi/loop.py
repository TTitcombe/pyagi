from pyagi import generate
from pyagi.types import Message

def agent_chat(model: str = "qwen2.5-coder:14b"):
    messages: list[Message] = [{ "role": "system", "content": "You are an agent helping with personal tasks." }]

    while True:
        user_msg = input("> ")

        if user_msg == "exit":
            break

        messages.append({ "role": "user", "content": user_msg })

        output = generate(messages, model)
        messages.append(output.message)

        print(output.message.content + "\n\n")
