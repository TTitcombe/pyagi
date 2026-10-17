# Food-shop tasks (food-shop-a to -d): the base world plus this layer. Build after the base:
#
#   docker build -t pyagi-evals-food-shop:local evals/overlays/food-shop
#
# seed/ records are added to (or replace, by id) the base world's services; files/ lands in /app.
FROM pyagi-evals-base:local

COPY seed/ /tmp/overlay/
COPY files/ /app/
RUN python3 /opt/world/lib/overlay.py /tmp/overlay && rm -rf /tmp/overlay
