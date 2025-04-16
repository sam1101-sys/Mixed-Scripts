#!/bin/bash

# Filename: check_psql_connections.sh

# Default values
INPUT_FILE=""

# PostgreSQL username
USERNAME="postgres"

# Function to display usage
usage() {
    echo "Usage: $0 -h <input_file>"
    echo "  -h <input_file>    Specify the input file containing IP addresses"
    exit 1
}

# Parse command-line options
while getopts ":h:" opt; do
    case ${opt} in
        h )
            INPUT_FILE="$OPTARG"
            ;;
        \? )
            echo "❌ Invalid option: -$OPTARG" >&2
            usage
            ;;
        : )
            echo "❌ Option -$OPTARG requires an argument." >&2
            usage
            ;;
    esac
done

# Check if the input file was provided
if [ -z "$INPUT_FILE" ]; then
    echo "❌ Input file not specified."
    usage
fi

# Check if the input file exists
if [ ! -f "$INPUT_FILE" ]; then
    echo "❌ Input file '$INPUT_FILE' not found."
    exit 1
fi

# Read each IP address from the input file
while IFS= read -r IP; do
    # Skip empty lines or lines starting with '#'
    if [[ -z "$IP" || "$IP" == \#* ]]; then
        continue
    fi

    echo "➡️  Checking PostgreSQL connection to $IP..."

    # Attempt to connect to the PostgreSQL server
    # The -q option suppresses the psql welcome message
    # The -c '\q' option runs the quit command immediately after connecting
    OUTPUT=$(psql -h "$IP" -U "$USERNAME" -w -q -c '\q' 2>&1)

    # Check the exit status of the psql command
    if [ $? -eq 0 ]; then
        echo "✅ Connection to $IP successful."
    else
        echo "❌ Connection to $IP failed."
        echo "   Error: $OUTPUT"
    fi
    echo "----------------------------------------"
done < "$INPUT_FILE"
