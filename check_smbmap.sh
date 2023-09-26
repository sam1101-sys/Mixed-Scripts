#!/bin/bash

# Check if the file containing hostnames is provided as an argument
if [ $# -ne 1 ]; then
  echo "Usage: $0 <hosts_file>"
  exit 1
fi

hosts_file="$1"

# Loop through each host in the file
while IFS= read -r host; do
  echo "Checking $host with smbmap..."
  smbmap -H $host
  echo "----"
done < "$hosts_file"
