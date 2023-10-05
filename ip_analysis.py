import argparse
import csv

# Define a function to parse command-line arguments
def parse_args():
    parser = argparse.ArgumentParser(description="IP Analysis Script")
    parser.add_argument('-f', '--files', nargs='+', help='List of input files for each server', required=True)
    parser.add_argument('-o', '--output', help='Output format (default: txt)', choices=['txt', 'csv'], default='txt')
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
        accessible_from.sort()  # Sort the server names to get consistent combinations
        common_ips[ip] = accessible_from

# Calculate total IPs from input files
total_ips = sum(len(ips) for ips in server_ips.values())

# Calculate total unique IPs with duplicates removed
all_ips = set(ip for ips in server_ips.values() for ip in ips)
total_unique_ips = len(all_ips)

# Output results in the specified format
if args.output == 'csv':
    with open('ip_analysis.csv', 'w', newline='') as csvfile:
        fieldnames = ['Server', 'IP']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()

        for server, ips in unique_ips.items():
            for ip in ips:
                writer.writerow({'Server': server, 'IP': ip})

    # Save common IPs to a CSV file
    with open('common_ips.csv', 'w', newline='') as csvfile:
        fieldnames = ['IP', 'Servers']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()

        for ip, servers in common_ips.items():
            writer.writerow({'IP': ip, 'Servers': ', '.join(servers)})

else:
    # Save results to separate output files in text format
    for server, ips in unique_ips.items():
        with open(f'{server}_unique_ips.txt', 'w') as file:
            file.write('\n'.join(ips))

    # Save common IPs to separate text files
    for ip, servers in common_ips.items():
        common_servers = ' & '.join(s for s in servers)
        with open(f'common_{common_servers}_ips.txt', 'w') as file:
            file.write(f"{ip}\n")

# Print the results...
print("Total IPs from input files:", total_ips)
print("Total Unique IPs (with duplicates removed):", total_unique_ips)
for server, ips in unique_ips.items():
    print(f"Server {server} IPs saved to {server}_unique_ips.txt:", len(ips))
