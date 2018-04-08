# Description
This script will ping a subnet specified by the user using CIDR notation. Example: 10.0.1.0/24. 'ping_results.csv' will be generated
in the same directory with the ip and status (up/down) of each host in the specified range. 

# Compatibility
- Linux, Mac, Windows
- Python 3.4+

# Arguments
--hosts = network to ping (CIDR Notation)

# Example Usage:

### Ping all usuable host IPs within the range 10.0.1.0/24
python ping.py --hosts 10.0.1.0/24