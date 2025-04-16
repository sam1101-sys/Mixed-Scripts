import sys
from smbprotocol.connection import Connection

# Function to check if anonymous login is allowed
def check_anonymous_login(host):
    try:
        with Connection(hostname=host) as conn:
            conn.connect()
            conn.login()
        return True
    except Exception as e:
        return False

# Check if the file containing hostnames is provided as an argument
if len(sys.argv) != 2:
    print("Usage: python check_anonymous.py <hosts_file>")
    sys.exit(1)

hosts_file = sys.argv[1]

try:
    with open(hosts_file, 'r') as file:
        for line in file:
            host = line.strip()
            result = check_anonymous_login(host)
            if result:
                print(f"Anonymous login allowed on {host}")
            else:
                print(f"Anonymous login not allowed on {host}")
except FileNotFoundError:
    print(f"File '{hosts_file}' not found.")
    sys.exit(1)
except Exception as e:
    print(f"An error occurred: {str(e)}")
    sys.exit(1)
