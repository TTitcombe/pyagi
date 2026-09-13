from pyagi.loop import agent_chat
import argparse
from pyagi import generate


def main(model: str) -> None:
    agent_chat(model)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="agent-from-scratch")
    parser.add_argument('--model', required=False, type=str, default='deepseek-r1:14b')
    args = parser.parse_args()

    main(args.model)
