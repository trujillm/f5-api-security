#!/bin/bash

cd "$(dirname "$0")"

# Set default VERSION if not provided
VERSION=${VERSION:-0.2.22}

# Replace __LLAMASTACK_VERSION__ with actual version in pyproject.toml
echo "Replacing __LLAMASTACK_VERSION__ with $VERSION in pyproject.toml"
sed -i.bak "s/__LLAMASTACK_VERSION__/$VERSION/g" pyproject.toml
rm -f pyproject.toml.bak

# Export TAVILY_SEARCH_API_KEY if it's set
if [ -n "$TAVILY_SEARCH_API_KEY" ]; then
    export TAVILY_SEARCH_API_KEY
fi

uv sync && \
uv run streamlit run llama_stack_ui/distribution/ui/app.py --server.runOnSave true --server.fileWatcherType auto