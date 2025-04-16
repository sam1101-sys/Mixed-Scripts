#!/bin/bash
# Copyright (c) 2025 Shamya
# Licensed under the MIT License. See LICENSE file in the repository.

# Check dependencies
if ! command -v psql >/dev/null 2>&1; then
    echo "Error: 'psql' not found. Install postgresql-client (e.g., sudo apt install postgresql-client)."
    exit 1
fi

# Default values
INPUT_FILE=""
USERNAME="postgres"
PORT=5432
OUTPUT_FILE=""

# Function to display usage
usage() {
    echo "Usage: $0 -h <input_file> [-u <username>] [-p <port>] [-o <output_file>]"
    echo "  -h <input_file>    Input file with IP addresses"
    echo "  -u <username>      PostgreSQL username (default: postgres)"
    echo "  -p <port>          PostgreSQL port (default: 5432)"
    echo "  -o <output_file>   Output file for results"
    exit 1
}

# Parse command-line options
while getopts ":h:u:p:o:" opt; do
    case ${opt} in
        h ) INPUT_FILE="$OPTARG" ;;
        u ) USERNAME="$OPTARG" ;;
        p ) PORT="$OPTARG" ;;
        o ) OUTPUT_FILE="$OPTARG" ;;
        \? ) echo "❌ Invalid option: -$OPTARG" >&2; usage ;;
        : ) echo "❌ Option -$OPTARG requires an argument." >&2; usage ;;
    esac
done

# Check input file
if [ -z "$INPUT_FILE" ]; then
    echo "❌ Input file not specified."
    usage
fi
if [ ! -f "$INPUT_FILE" ]; then
    echo "❌ Input file '$INPUT_FILE' not found."
    exit 1
fi

# Check output file overwrite
if [ -n "$OUTPUT_FILE" ] && [ -f "$OUTPUT_FILE" ]; then
    read -p "Output file '$OUTPUT_FILE' exists. Overwrite? (y/n): " confirm
    if [ "$confirm" != "y" ]; then
        echo "Aborted."
        exit 1
    fi
fi

# Read IPs
while IFS= read -r IP; do
    if [[ -z "$IP" || "$IP" == \#* ]]; then
        continue
    fi
    if ! [[ "$IP" =~ ^[0-9a-zA-Z.:]+$ ]]; then
        echo "❌ Skipping invalid IP: $IP"
        [ -n "$OUTPUT_FILE" ] && echo "Skipping invalid IP: $IP" >> "$OUTPUT_FILE"
        continue
    fi

    echo "➡  Checking PostgreSQL connection to $IP:$PORT..."
    OUTPUT=$(timeout 5 psql -h "$IP" -p "$PORT" -U "$USERNAME" -w -q -c '\q' 2>&1)
    if [ $? -eq 0 ]; then
        echo "✅ Connection to $IP:$PORT successful."
        [ -n "$OUTPUT_FILE" ] && echo "Connection to $IP:$PORT successful." >> "$OUTPUT_FILE"
    else
        echo "❌ Connection to $IP:$PORT failed."
        echo "   Error: $OUTPUT"
        [ -n "$OUTPUT_FILE" ] && {
            echo "Connection to $IP:$PORT failed." >> "$OUTPUT_FILE"
            echo "Error: $OUTPUT" >> "$OUTPUT_FILE"
        }
    fi
    echo "----------------------------------------"
    [ -n "$OUTPUT_FILE" ] && echo "----------------------------------------" >> "$OUTPUT_FILE"
done < "$INPUT_FILE"
