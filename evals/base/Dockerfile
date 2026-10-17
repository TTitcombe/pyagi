# Shared environment for every task: the starting state of the world plus the mock services.
# Tasks reference it by name in task.toml ([environment] docker_image), so after
# changing anything here, rebuild:
#
#   docker build -t pyagi-evals-base:local evals/base
#
#   /app             the user's files (files/); the agent's file tools work here
#   /var/lib/world   live service state (seed/), changed only through the service CLIs
#   /opt/world/seed  untouched copy of the starting state, for checkers to diff against
#   /opt/world/bin   service CLIs the agent's tools call (cal, ...)
#   /opt/world/lib   world.py (shared state access) and check.py (checker library)
FROM python:3.13-slim

COPY world/ /opt/world/
COPY seed/ /var/lib/world/
COPY seed/ /opt/world/seed/
COPY files/ /app/

ENV PATH="/opt/world/bin:$PATH" \
    PYTHONPATH="/opt/world/lib" \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app
