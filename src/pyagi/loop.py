from pyagi.tools.tools import tool_prompt, process_tools
from pyagi import generate
from pyagi.types import Message

SYSTEM = f"You are an agent helping with personal tasks.\n\n{tool_prompt()}"

def agent_chat(model: str):
    messages: list[Message] = [{ "role": "system", "content": SYSTEM }]

    while True:
        user_msg = input("> ")

        if user_msg == "exit":
            break

        messages.append({ "role": "user", "content": user_msg })

        call_model = True
        tool_iteration = 0
        while call_model:
            output, new_messages, call_model = model_iteration(model, messages)
            print(output + "\n\n")
            messages.extend(new_messages)
            tool_iteration += 1

            # backstop to stop an infinite loop. To be removed when this is less buggy.
            if tool_iteration > 5:
                break


def model_iteration(model: str, messages: list[Message]):
    new_messages: list[Message] = []
    output = generate(messages, model)
    new_messages.append({ "role": "assistant", "content": output })

    tool_use = process_tools(output)
    for tool in tool_use:
        # user not "tool" - ollama / deepseek drops "tool" roles silently when constructing
        # the prompt, so the model never sees the tool output
        new_messages.append({ "role": "user", "content": f"{tool["tool_name"]} output: {tool["output"]}" })

    return output, new_messages, len(tool_use) > 0
