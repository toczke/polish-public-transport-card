FROM myoung34/github-runner:latest

# Pre-install Python + Node for CI
RUN sudo apt-get update && sudo apt-get install -y python3 python3-pip nodejs npm \
    && sudo rm -rf /var/lib/apt/lists/*
