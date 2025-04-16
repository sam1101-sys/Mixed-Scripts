#!/bin/bash
# Copyright (c) 2025 Shamya
# Licensed under the MIT License. See LICENSE file in the repository.

# Function to show usage
usage() {
    echo "Usage: $0 -f <file> [-r <width>,<height>]"
    echo "  -f <file>          File with IP:port entries"
    echo "  -r <width>,<height> Resolution (default: 1280,1024)"
    exit 1
}

# Default values
RESOLUTION="1280,1024"

# Parse arguments
while getopts "f:r:" opt; do
    case "${opt}" in
        f) URL_FILE="${OPTARG}" ;;
        r) RESOLUTION="${OPTARG}" ;;
        *) usage ;;
    esac
done

# Check file
if [[ -z "$URL_FILE" ]]; then
    usage
fi
if [[ ! -f "$URL_FILE" ]]; then
    echo "Error: File '$URL_FILE' not found!"
    exit 1
fi

# Check Chrome
if ! command -v google-chrome &> /dev/null; then
    echo "Error: Google Chrome not installed. Install with 'sudo apt install google-chrome-stable'."
    exit 1
fi

# Create output directory
OUTPUT_DIR="screenshots_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$OUTPUT_DIR"

# Read IP:port
while read -r IP_PORT; do
    if [[ -z "$IP_PORT" ]]; then
        continue
    fi
    if ! [[ "$IP_PORT" =~ ^[0-9.]+:[0-9]+$ ]]; then
        echo "Skipping invalid IP:port: $IP_PORT"
        continue
    fi

    IP=$(echo "$IP_PORT" | awk -F: '{print $1}')
    PORT=$(echo "$IP_PORT" | awk -F: '{print $2}')
    IP_FORMATTED=$(echo "$IP" | tr '.' '_')

    # Protocol detection
    if [[ "$PORT" == "443" ]]; then
        SERVICE="https"
        URL="https://${IP}:${PORT}"
    else
        SERVICE="http"
        URL="http://${IP}:${PORT}"
    fi

    FILENAME="${SERVICE}_${IP_FORMATTED}_${PORT}.png"

    # Capture screenshot
    echo "Capturing screenshot for $URL..."
    if timeout 10 google-chrome --headless --disable-gpu --screenshot="$OUTPUT_DIR/$FILENAME" --window-size="$RESOLUTION" "$URL" 2>/dev/null; then
        echo "Screenshot saved: $OUTPUT_DIR/$FILENAME"
    else
        echo "Failed to capture screenshot for $URL"
    fi
done < "$URL_FILE"

echo "All screenshots saved in $OUTPUT_DIR"
