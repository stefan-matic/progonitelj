# VIOLATION: ubuntu is explicitly blocked - policy requires alpine
FROM ubuntu:22.04 AS base

RUN apt-get update && apt-get install -y python3 curl

# VIOLATION: centos is explicitly blocked (EOL)
FROM centos:7 AS legacy

RUN yum install -y wget

# VIOLATION: nginx without alpine tag - policy only allows 1.27-alpine
FROM nginx:latest

COPY --from=base /app /usr/share/nginx/html

# VIOLATION: python tag not in pinned list - policy allows 3.11-slim, 3.12-slim, 3.13-slim only
FROM python:3.10

WORKDIR /app
COPY . .
CMD ["python", "main.py"]
