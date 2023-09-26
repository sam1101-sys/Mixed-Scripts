#!/bin/bash

# Default values
port=""
filename=""

# Parse command line options
while getopts "p:f:" opt; do
  case $opt in
    p)
      port="$OPTARG"
      ;;
    f)
      filename="$OPTARG"
      ;;
    \?)
      echo "Invalid option: -$OPTARG" >&2
      exit 1
      ;;
    :)
      echo "Option -$OPTARG requires an argument." >&2
      exit 1
      ;;
  esac
done

# Check if required options are provided
if [ -z "$port" ] || [ -z "$filename" ]; then
  echo "Usage: $0 -p PORT -f FILENAME"
  exit 1
fi

# Check if the filename exists
if [ ! -f "$filename" ]; then
  echo "File '$filename' does not exist."
  exit 1
fi

# Construct the command with user inputs and execute it
command="grep \"$port/open\" \"$filename\" | cut -d \";\" -f 2 | cut -d \"(\" -f 1 | awk '{\$1=\$1}1'"
eval "$command"
