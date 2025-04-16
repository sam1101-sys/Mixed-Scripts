#!/bin/bash
# Copyright (c) 2025 Shamya
# Licensed under the MIT License. See LICENSE file in the repository.

# Check if showmount is installed
if ! command -v showmount >/dev/null 2>&1; then
    echo "Error: 'showmount' command not found. Install nfs-common (e.g., sudo apt install nfs-common)."
    exit 1
fi

# Check if an input file was provided
if [ $# -lt 1 ]; then
    echo "Usage: $0 <input_file>"
    exit 1
fi

input_file="$1"
output_file="nfs_share_results.txt"
nfs_found_file="nfs_found_ips.txt"

# Check if the input file exists
if [ ! -e "$input_file" ]; then
    echo "Input file $input_file not found."
    exit 1
fi

# Check if output files exist
for file in "$output_file" "$nfs_found_file"; do
    if [ -e "$file" ]; then
        read -p "Output file $file exists. Overwrite? (y/n): " confirm
        if [ "$confirm" != "y" ]; then
            echo "Aborted."
            exit 1
        fi
    fi
done

# Initialize variables
shares_found=false
nfs_ips=()

# Loop through hosts
while IFS= read -r host; do
    if [ -z "$host" ]; then
        continue
    fi
    if ! [[ "$host" =~ ^[0-9a-zA-Z.-]+$ ]]; then
        echo "Skipping invalid host: $host"
        continue
    fi
    shares=$(timeout 5 showmount -e "$host" 2>/tmp/nfs_error)
    if [ $? -eq 0 ] && [ -n "$shares" ]; then
        shares_found=true
        nfs_ips+=("$host")
        echo "NFS shares found on $host:"
        echo "$shares"
        echo "----------------------"
        echo "NFS shares found on $host:" >> "$output_file"
        echo "$shares" >> "$output_file"
        echo "----------------------" >> "$output_file"
    else
        echo "No NFS shares found on $host" >> "$output_file"
        echo "----------------------" >> "$output_file"
        if [ -s /tmp/nfs_error ]; then
            echo "Error querying $host: $(cat /tmp/nfs_error)"
        fi
    fi
    rm -f /tmp/nfs_error
done < "$input_file"

# Write results
if [ "$shares_found" = true ]; then
    echo "Results have been saved to $output_file"
    printf "%s\n" "${nfs_ips[@]}" > "$nfs_found_file"
    echo "List of IPs with NFS shares saved to $nfs_found_file"
else
    echo "No NFS shares found among the specified hosts."
fi
