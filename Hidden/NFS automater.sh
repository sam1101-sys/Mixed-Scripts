#!/bin/bash

# Check if an input file was provided as an argument
if [ $# -lt 1 ]; then
    echo "Usage: $0 <input_file>"
    exit 1
fi

input_file="$1"

# Name of the output file for NFS share results
output_file="nfs_share_results.txt"

# Name of the output file for IP addresses with NFS shares
nfs_found_file="nfs_found_ips.txt"

# Check if the input file exists
if [ ! -e "$input_file" ]; then
    echo "Input file $input_file not found."
    exit 1
fi

# Initialize a variable to track whether NFS shares were found
shares_found=false

# Initialize an array to store IPs with NFS shares
nfs_ips=()

# Loop through the list of IP addresses or hostnames, check NFS shares, and append the results to the output file
while IFS= read -r host; do
    shares=$(showmount -e "$host")
    if [ -n "$shares" ]; then
        shares_found=true
        nfs_ips+=("$host")
        echo "NFS shares found on $host:"
        echo "$shares"
        echo "----------------------"
        echo "NFS shares found on $host:" >> "$output_file"
        echo "$shares" >> "$output_file"
        echo "----------------------" >> "$output_file"
    fi
done < "$input_file"

# Write the list of IPs with NFS shares to a separate file
if [ "$shares_found" = true ]; then
    echo "Results have been saved to $output_file"
    printf "%s\n" "${nfs_ips[@]}" > "$nfs_found_file"
    echo "List of IPs with NFS shares saved to $nfs_found_file"
else
    echo "No NFS shares found among the specified hosts."
fi
