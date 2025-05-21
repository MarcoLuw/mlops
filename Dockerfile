FROM python:3.11

RUN apt-get update && apt-get install -y git && apt-get clean
RUN pip install --upgrade pip setuptools wheel

ADD requirements.txt .
RUN pip install -r requirements.txt

# FROM python:3.11-slim

# # Install build dependencies
# RUN apt-get update && \
#     apt-get install -y \
#         build-essential \
#         python3-dev \
#         libssl-dev \
#         libffi-dev \
#         libbz2-dev \
#         zlib1g-dev \
#         liblzma-dev \
#         libgrpc-dev \
#         git && \
#     rm -rf /var/lib/apt/lists/*

# # Copy requirements and install wheel + dependencies in one step
# ADD requirements.txt .
# RUN pip install wheel && pip install -r requirements.txt