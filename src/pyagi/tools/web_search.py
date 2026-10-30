from typing import TypedDict
from pyagi.tools.base import Toolset

class SearchResult(TypedDict):
    url: str


class Websearch(Toolset):
    def search(self, search_term: str, top_n_results: int = 20) -> list[str]:
        items: list[str] = []

        return items

    def get_webpage(self, webpage: str) -> str:
        return ""
