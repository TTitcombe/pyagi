from pyagi.types import Tool
import os

from tavily.tavily import TavilyClient
from typing import TypedDict, Callable
from pyagi.tools.base import Toolset

class SearchResult(TypedDict):
    url: str
    title: str
    content: str
    score: float


class Websearch(Toolset):
    def __init__(self):
        super().__init__()
        key = os.getenv("TAVILY_API_KEY")
        self.client = TavilyClient(key)

    def search(self, search_term: str, top_n_results: int = 20) -> list[SearchResult]:
        response = self.client.search(search_term, max_results=top_n_results)

        return response["results"]

    @property
    def tools(self) -> list[Tool]:
        return [
            {
                "tool_name": "search_web",
                "description": "Make a web search using the Tavily API, returning URL, page title, and content for top, relevant results.",
                "parameters": {"search_term": "str", "max_results": "int, default 20"}
            },
        ]

    @property
    def tool_mapping(self) -> dict[str, Callable]:
        return {
            "search_web": self.search
        }
