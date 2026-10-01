from pyagi_bench.env.tools import Param, ToolError, tool
from pyagi_bench.env.util import matches_query
from pyagi_bench.env.world import World


@tool(
    "docs_list", "documents", "List document paths, optionally under a folder (e.g. 'work/').",
    folder=Param("string", "Folder prefix", required=False),
)
def docs_list(world: World, folder: str = ""):
    return sorted(p for p in world.collection("documents") if p.startswith(folder))


@tool(
    "docs_read", "documents", "Read a document's full content.",
    path=Param("string", "Document path, as returned by docs_list"),
)
def docs_read(world: World, path: str):
    doc = world.collection("documents").get(path)
    if doc is None:
        raise ToolError(f"No document at '{path}'")
    return doc["content"]


@tool(
    "docs_search", "documents",
    "Find documents whose path or content contains every word of the query. Returns paths with the first matching line.",
    query=Param("string", "Words to search for"),
)
def docs_search(world: World, query: str):
    results = []
    for path, doc in sorted(world.collection("documents").items()):
        if not matches_query(query, path, doc["content"]):
            continue
        words = query.lower().split()
        line = next((ln.strip() for ln in doc["content"].splitlines() if any(w in ln.lower() for w in words)), "")
        results.append({"path": path, "match": line[:160]})
    return results


@tool(
    "docs_write", "documents", "Create a document, or REPLACE the entire content of an existing one.", mutates=True,
    path=Param("string", "Document path, e.g. 'personal/notes.md'"),
    content=Param("string", "The complete new content"),
)
def docs_write(world: World, path: str, content: str):
    docs = world.collection("documents")
    status = "updated" if path in docs else "created"
    docs[path] = {"path": path, "content": content}
    return {"status": status, "path": path}
