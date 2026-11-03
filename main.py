from dotenv import load_dotenv
from pyagi.tools.manager import create_tools
from pyagi.agent.basic import BasicLoopAgent
from pyagi.models.ollama import OllamaDirect
import argparse


def main(model_name: str) -> None:
    load_dotenv()
    model = OllamaDirect(model_name)
    tools = create_tools(file_io=True)
    agent = BasicLoopAgent(model, tools)
    agent.run()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="agent-from-scratch")
    parser.add_argument('--model', required=False, type=str, default='deepseek-r1:14b')
    args = parser.parse_args()

    main(args.model)
