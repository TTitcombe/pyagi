# Shared environment for every task: the starting state of the world.
# Tasks reference it by name in task.toml ([environment] docker_image), so after
# changing anything here, rebuild:
#
#   docker build -t pyagi-evals-base:local evals/base
FROM ubuntu:24.04

WORKDIR /app
COPY files/ /app/
