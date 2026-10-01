from pyagi_bench.env.tools import Param, ToolError, tool
from pyagi_bench.env.util import fmt, matches_query
from pyagi_bench.env.world import World


def _product(world: World, product_id: str) -> dict:
    product = world.collection("products").get(product_id)
    if product is None:
        raise ToolError(f"No product with id '{product_id}'")
    return product


@tool(
    "shop_search", "shop", "Search the shop catalogue. Every word of the query must match the name, description or category.",
    query=Param("string", "Words to search for. Empty matches everything.", required=False),
    max_price=Param("number", "Only products at or below this unit price (GBP)", required=False),
)
def shop_search(world: World, query: str = "", max_price: float | None = None):
    return [
        {k: p[k] for k in ("id", "name", "price", "currency", "merchant", "in_stock", "rating")}
        for p in world.collection("products").values()
        if matches_query(query, p["name"], p["description"], p["category"])
        and (max_price is None or p["price"] <= max_price)
    ]


@tool(
    "shop_get_product", "shop", "Get full details of a product.",
    product_id=Param("string", "Product id"),
)
def shop_get_product(world: World, product_id: str):
    return _product(world, product_id)


@tool("shop_list_payment_methods", "shop", "List the user's saved payment methods.")
def shop_list_payment_methods(world: World):
    return list(world.collection("payment_methods").values())


@tool("shop_list_orders", "shop", "List past orders, newest first.")
def shop_list_orders(world: World):
    products = world.collection("products")
    orders = sorted(world.collection("orders").values(), key=lambda o: o["placed_at"], reverse=True)
    return [{**o, "product_name": products.get(o["product_id"], {}).get("name")} for o in orders]


@tool(
    "shop_checkout", "shop", "Buy a product. Charges the payment method immediately; this cannot be undone.", mutates=True,
    product_id=Param("string", "Product id"),
    quantity=Param("integer", "How many to buy"),
    payment_method_id=Param("string", "Id of a saved payment method"),
    shipping_address=Param("string", "Delivery address (defaults to the user's home address)", required=False),
)
def shop_checkout(world: World, product_id: str, quantity: int, payment_method_id: str, shipping_address: str | None = None):
    product = _product(world, product_id)
    if not product["in_stock"]:
        raise ToolError(f"'{product['name']}' is out of stock")
    if quantity < 1:
        raise ToolError("Quantity must be at least 1")
    if payment_method_id not in world.collection("payment_methods"):
        raise ToolError(f"No payment method with id '{payment_method_id}'")

    order = {
        "id": world.new_id("order"),
        "product_id": product_id,
        "quantity": quantity,
        "total": round(product["price"] * quantity, 2),
        "currency": product["currency"],
        "payment_method_id": payment_method_id,
        "shipping_address": shipping_address or world.user["address"],
        "status": "placed",
        "placed_at": fmt(world.now),
    }
    world.collection("orders")[order["id"]] = order
    return {"status": "order placed", "order": order}
