#!/bin/bash
# summarize_links.sh - A script to summarize links from a file
# 
# Usage: ./summarize_links.sh <path_to_file_with_links> [api] [output_file]
#
# Example: ./summarize_links.sh ~/OneDrive/history_logs/open_tabs.md claude summaries.md

# Set default values
API="${2:-basic}"  # Default to basic summarization
OUTPUT="${3:-}"     # Default to automatic naming

# Check if file path is provided
if [ -z "$1" ]; then
    echo "Error: Please provide a path to the file containing links."
    echo "Usage: ./summarize_links.sh <path_to_file_with_links> [api] [output_file]"
    exit 1
fi

# Check if file exists
if [ ! -f "$1" ]; then
    echo "Error: File not found at $1"
    exit 1
fi

# Check if API is valid
if [ "$API" != "basic" ]; then
    echo "Error: API must be 'basic'."
    echo "Usage: ./summarize_links.sh <path_to_file_with_links> [api] [output_file]"
    exit 1
fi

# Build the command
CMD="python link_summarizer.py \"$1\" --api $API"

# Add output file if specified
if [ -n "$OUTPUT" ]; then
    CMD="$CMD --output \"$OUTPUT\""
fi

# Print the command being executed
echo "Executing: $CMD"

# Execute the command
eval "$CMD"