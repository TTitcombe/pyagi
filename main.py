import argparse
from pyagi import generate


def main(message: str) -> None:
    output = generate(message)
    print(output)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
                        prog='PyAgi',
                        description='the power of chatgpt, in the palm of my hand.')
    parser.add_argument('message')
    args = parser.parse_args()

    main(args.message)
