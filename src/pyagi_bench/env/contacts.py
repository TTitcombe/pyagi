from pyagi_bench.env.tools import Param, tool
from pyagi_bench.env.util import matches_query
from pyagi_bench.env.world import World


@tool(
    "contacts_search", "contacts",
    "Search contacts by name, email, relationship or notes. Every word of the query must match.",
    query=Param("string", "Words to search for. Empty lists all contacts."),
)
def contacts_search(world: World, query: str):
    return [
        c for c in world.collection("contacts").values()
        if matches_query(query, c["name"], c["email"], c.get("relationship"), c.get("notes"))
    ]
