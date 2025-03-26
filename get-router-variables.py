import paramiko
import re
import json

"""

*** Script has limited error checking and is for proof of concept only - not for production use ***

This script connects to a router via SSH and executes commands, and saves the extracted information to a JSON file 


"""

def subnet_mask_to_bits(subnet_mask):
    """ For SDWAN we need to convert the subnet mask into bits i.e. 255.255.255.0 -> 24 """

    # Split the subnet mask into octets
    octets = subnet_mask.split('.')
    # Convert each octet to binary and count the number of '1's
    bits = sum(bin(int(octet)).count('1') for octet in octets)
    return bits

def get_command(hostname, port, username, password, command):
    """Connect to the router, execute a command, and return the output """
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        # Connect to the router
        client.connect(hostname, port=port, username=username, password=password)

        # Execute the command
        stdin, stdout, stderr = client.exec_command(command)
        output = stdout.read().decode('utf-8')

        # Disconnect
        client.close()
        return output
    except Exception as e:
        print(f"An error occurred: {e}")
        return None

# Set the variables to access
hostname = '192.168.0.249' # hostname or IP address
port = 22
username = 'neal'
password = 'neal'

# Set default for variables
interface_ip = ""
interface_mask = ""
serial_number = ""
software_version = ""
nexthop_ip = ""

try:

    wan_int = get_command(hostname, port, username, password, "show run interface GigabitEthernet0/0/0 | inc ip add")
    wan_ip = re.search(r'ip address (\S+) (\S+)', wan_int)
    if wan_ip:
        interface_ip = wan_ip.group(1)
        interface_mask = wan_ip.group(2)

    default_route = get_command(hostname, port, username, password, "show ip route static | include Gateway")
    default_nh = re.search(r'Gateway of last resort is (\S+)', default_route)
    if default_nh:
        nexthop_ip = default_nh.group(1)

    serial = get_command(hostname, port, username, password, "show ver | inc Processor board ID")
    serial_number_match = re.search(r'Processor board ID (\S+)', serial)
    if serial_number_match:
        serial_number = serial_number_match.group(1)

    version = get_command(hostname, port, username, password, "show ver | inc Cisco IOS Software")
    software_version_match = re.search(r'Version (\S+),', version)
    if software_version_match:
        software_version = software_version_match.group(1)

except Exception as e:
    print(f"An error occurred: {e}")
    exit(1)


# Create the dictionary which will later be converted to JSON
router_data = {
    "wan": {
        "interface": "GigabitEthernet0/0/0",
        "ip": interface_ip,
        "mask": interface_mask,
        "prefix_mask": subnet_mask_to_bits(interface_mask),
    },
    "serial": serial_number,
    "software_version": software_version,
    "default-route-next-hop": nexthop_ip
}

filename = "data.json"

# Convert dictionary to JSON and save to file
with open(filename, 'w') as json_file:
    json.dump(router_data, json_file, indent=4)

print(f"Dictionary has been saved to {filename}.")

