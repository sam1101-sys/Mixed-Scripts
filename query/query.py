#!/usr/bin/env python3
# Copyright (c) 2025 Shamya
# Licensed under the MIT License. See LICENSE file in the repository.

import ipaddress
import argparse

def cidr_to_query(file_path, output_path=None):
    """Convert CIDR ranges to query format."""
    try:
        with open(file_path, 'r') as file:
            cidr_list = [line.strip() for line in file if line.strip()]

        query_parts = []
        for cidr in cidr_list:
            try:
                network = ipaddress.ip_network(cidr, strict=False)
                start_ip = network[0]
                end_ip = network[-1]
                query_parts.append(f"asset.ipv{network.version} BETWEEN {start_ip} AND {end_ip}")
            except ValueError as e:
                print(f"Invalid CIDR format: {cidr} ({e})")

        query = " || ".join(query_parts) if query_parts else ""
        if query and output_path:
            try:
                with open(output_path, 'w') as f:
                    f.write(query)
                print(f"Query saved to {output_path}")
            except IOError as e:
                print(f"Error writing to output file: {e}")
        return query

    except FileNotFoundError:
        print(f"File not found: {file_path}")
        return ""

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Convert CIDR ranges to a query format.")
    parser.add_argument("-f", "--file", required=True, help="File containing CIDR ranges.")
    parser.add_argument("-o", "--output", help="Output file for query.")
    args = parser.parse_args()

    query = cidr_to_query(args.file, args.output)
    if query and not args.output:
        print("Generated Query:")
        print(query)
    elif not query:
        print("No valid queries generated.")
