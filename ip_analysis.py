import argparse
from collections import defaultdict

# Define a function to parse command-line arguments
def parse_args():
    parser = argparse.ArgumentParser(description="IP Analysis Script")
    parser.add_argument('-f', '--files', nargs='+', help='List of input files for each server', required=True)
    return parser.parse_args()

# Get the command-line arguments
args = parse_args()

# Define dictionaries to store IPs for each server
server_ips = {}

# Read IP lists from files for each server and populate the dictionaries
for file_name in args.files:
    with open(file_name, 'r') as file:
        server_name = file_name.split('.')[0]  # Extract server name from file name
        server_ips[server_name] = file.read().splitlines()

# Identify IPs only reachable from a specific server
unique_ips = {}
for server, ips in server_ips.items():
    other_servers = [s for s in server_ips.keys() if s != server]
    unique_ips[server] = list(set(ips) - set().union(*[server_ips[s] for s in other_servers]))

# Find common IPs and the servers they are accessible from
common_ips = {}
for ip in set().union(*server_ips.values()):
    accessible_from = [server for server, ips in server_ips.items() if ip in ips]
    if len(accessible_from) > 1:
        common_ips[ip] = accessible_from

# Calculate total IPs from input files
total_ips = sum(len(ips) for ips in server_ips.values())

# Calculate total unique IPs with duplicates removed
all_ips = set(ip for ips in server_ips.values() for ip in ips)
total_unique_ips = len(all_ips)

# Create a dictionary to categorize common IPs by the combination of servers
categorized_common_ips = defaultdict(list)
for ip, accessible_from in common_ips.items():
    categorized_common_ips[' & '.join(sorted(accessible_from))].append(ip)

# Save results to separate output files
for server, ips in unique_ips.items():
    with open(f'{server}_unique_ips.txt', 'w') as file:
        file.write('\n'.join(ips))

# Create separate files for common IPs categorized by server combinations
for server_combination, ips in categorized_common_ips.items():
    with open(f'CommonIn{server_combination}.txt', 'w') as file:
        for ip in ips:
            file.write(f"IP {ip} is accessible from servers: {server_combination}\n")

# Print the results...
print("Total IPs from input files:", total_ips)
print("Total Unique IPs (with duplicates removed):", total_unique_ips)
for server, ips in unique_ips.items():
    print(f"Server {server} IPs saved to {server}_unique_ips.txt:", len(ips))

print("Common IPs count:", len(common_ips))
