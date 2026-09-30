from pyagi.tools.manager import create_tools
from pyagi.tools.files import TOOLSET_FILES
from pyagi.agent.basic import BasicLoopAgent
from pyagi.models.ollama import OllamaDirect
from pyagi.loop import agent_chat
import argparse
from pyagi import generate


def main(model_name: str) -> None:
    model = OllamaDirect(model_name)
    tools = create_tools(file_io=True)
    agent = BasicLoopAgent(model, tools)
    agent.run()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="agent-from-scratch")
    parser.add_argument('--model', required=False, type=str, default='deepseek-r1:14b')
    args = parser.parse_args()

    main(args.model)
