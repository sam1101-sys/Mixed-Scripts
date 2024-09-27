#!/bin/bash

# Filename: check_snmp_connections.sh

# Default values
INPUT_FILE=""
COMMUNITY="public"        # SNMP community string for SNMP v1/v2c
SNMP_VERSION="2c"         # SNMP version: 1, 2c, or 3
OID="1.3.6.1.2.1.1.1.0"   # Default OID to query (sysDescr)

# Function to display usage
usage() {
    echo "Usage: $0 -h <input_file> [-c <community>] [-v <version>] [-o <oid>]"
    echo "  -h <input_file>    Specify the input file containing IP addresses"
    echo "  -c <community>     Specify the SNMP community string (default: public)"
    echo "  -v <version>       Specify the SNMP version (1, 2c, 3) (default: 2c)"
    echo "  -o <oid>           Specify the OID to query (default: sysDescr OID)"
    exit 1
}

# Parse command-line options
while getopts ":h:c:v:o:" opt; do
    case ${opt} in
        h )
            INPUT_FILE="$OPTARG"
            ;;
        c )
            COMMUNITY="$OPTARG"
            ;;
        v )
            SNMP_VERSION="$OPTARG"
            ;;
        o )
            OID="$OPTARG"
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

    echo "➡️  Checking SNMP connectivity to $IP..."

    # Attempt to query the OID using snmpget
    if [[ "$SNMP_VERSION" == "1" || "$SNMP_VERSION" == "2c" ]]; then
        # SNMP v1 or v2c
        OUTPUT=$(snmpget -v "$SNMP_VERSION" -c "$COMMUNITY" "$IP" "$OID" 2>&1)
        STATUS=$?
    elif [[ "$SNMP_VERSION" == "3" ]]; then
        # SNMP v3 (this example uses noAuthNoPriv security level)
        # You can modify this section to include authentication and privacy options
        OUTPUT=$(snmpget -v 3 -l noAuthNoPriv "$IP" "$OID" 2>&1)
        STATUS=$?
    else
        echo "❌ Unsupported SNMP version: $SNMP_VERSION"
        exit 1
    fi

    # Check the exit status of the snmpget command
    if [ $STATUS -eq 0 ]; then
        echo "✅ SNMP connectivity to $IP successful."
        echo "   Response: $OUTPUT"
    else
        echo "❌ SNMP connectivity to $IP failed."
        echo "   Error: $OUTPUT"
    fi
    echo "----------------------------------------"
done < "$INPUT_FILE"
