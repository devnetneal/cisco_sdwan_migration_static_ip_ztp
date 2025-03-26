from ensurepip import bootstrap

from vmanage.api.authentication import Authentication
from vmanage.api.device import Device
from vmanage.api.device_templates import DeviceTemplates
import json
import os
from bootstrap import Bootstrap
import paramiko
from scp import SCPClient

"""

*** Script has limited error checking and is for proof of concept only - not for production use ***

 This script is to assist in the automated migration of an autonomous Cisco router to running in controller-mode
 for Catalyst SDWAN that requires static IP addressing for ZTP.
 
 # Pre-requisites
 1. Target device is added to WAN edge list on SDWAN Manager.
 2. You have a template built already
 
 
 Overview of process
 1. Load variable file created by get-router-variables.py
 2. Query SDWAN Manager to check serial number of device is added to the WAN Edge list
 3. Create payload for device template attachment
 4. Attach the template
 5. Download bootstrap file
 6. Upload bootstrap file via SCP as ciscosdwan.cfg
 
 To complete the migration you can execute "controller-mode enable" on the device manually

"""

def print_task_status(task_name, total_width=50):
    # Print messages nicely!
    message_length = len(task_name)
    dots_needed = total_width - message_length

    if dots_needed < 0:
        dots_needed = 0 # prevent negative dots

    dots = "." * dots_needed

    return print("{}{}".format(task_name, dots), end="", flush=True)


def load_json_file():
    print_task_status("Loading JSON file")
    while True:
        # Specify the initial filename
        filename = "data.json"

        # Check if the file exists
        if not os.path.isfile(filename):
            print(f"File '{filename}' not found.")
            choice = input("Enter a new filename or type 'exit' to quit: ").strip()

            if choice.lower() == 'exit':
                print("Exiting the program.")
                return None

            filename = choice

        try:
            # Open the JSON file and load its contents into a dictionary
            with open(filename, 'r') as json_file:
                data = json.load(json_file)
            print("Completed")
            return data

        except Exception as e:
            print(f"An error occurred: {e}")
            exit()


def create_ssh_client(server, user, ssh_password):
    # Create an SSH client instance
    client = paramiko.SSHClient()
    client.load_system_host_keys()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(server, username=user, password=ssh_password)
    return client


def get_env(my_env):
    # Function to get envs for example for credentials.
    retrieved_env = os.getenv(my_env)

    if retrieved_env is None:
        raise ValueError("Environment variables {} is not set".format(my_env))

    return retrieved_env

# Credentials
manager_host = "" # IP or DNS name of SDWAN Manager
manager_username = get_env("MANAGER_USERNAME")
manager_password = get_env("MANAGER_PASSWORD")

# Try to Open JSON file - will prompt if unable to find
router_details = load_json_file()

# Authenticate
auth = Authentication(host=manager_host, user=manager_username, password=manager_password).login()

# Create Device Object
manager_device = Device(auth, manager_host)

# Find UUID by serial number
print_task_status("Confirming {} is in WAN edge list".format(router_details['serial']))
device_config_list = manager_device.get_device_config_list('all')
target_serial = router_details['serial']
target_uuid = ''

for d in device_config_list:
    if d['subjectSerialNumber'] == target_serial:
        target_uuid = d['uuid']

if target_uuid == '':
    print("Error: Unable to find target serial number - please check")
    print("Exiting the program.")
    exit(1)
else:
    uuid_list = [target_uuid]
    print("Completed")

print_task_status("Building payload for attachment")
# Build variable dictionary - some are static in the script - can be changed for requirements
device_variables = {

    'host_name': 'SDWAN-CPE-{}'.format(target_serial),
    'site_id': '55',
    'system_ip': '10.255.255.55',
    'variables': {
        'wan_interface': router_details['wan']['interface'],
        'wan_interface_ip_add': '{}/{}'.format(router_details['wan']['ip'],router_details['wan']['prefix_mask']),
        'vpn_dns_primary': '8.8.8.8',
        'vpn_next_hop_ip_address_0': router_details['default-route-next-hop'],
        'system_latitude': '10',
        'system_longitude': '10',
        'system_host_name': 'SDWAN-CPE-{}'.format(target_serial),
        'system_system_ip': '10.255.255.55',
        'system_site_id': '55',

    },
}

# In order to use the "attach template", need a dictionary with UUID + variables. Can attach multiple devices at a time.
uuid_dict = {
    target_uuid: device_variables,
}

print("Completed")

# Useful link for template API - https://community.cisco.com/t5/sd-wan-and-cloud-networking/api-template/td-p/3857741

# Attach template to device - template ID can be found by looking at GUI URL: configuration > templates > view (selected)
# https://x.x.x.x/#/app/config/template/device/feature/view/7ee1aae3-c8c0-4430-b783-6f3fe5c10105
my_template = '7ee1aae3-c8c0-4430-b783-6f3fe5c10105'
manager_templates = DeviceTemplates(auth, manager_host)
print_task_status("Attempting to attach template to device")
action_id = manager_templates.attach_to_template(my_template, 'template', uuid_dict)
print("Completed: {}".format(action_id))

# Download the bootstrap configuration
print_task_status("Downloading Bootstrap file")
b = Bootstrap(auth, manager_host)
b_cfg = b.get_bootstrap_config(target_uuid)
if b_cfg['status_code'] != 200:
    print("Unable to download bootstrap file - Exiting the program.")
bootstrap_config_content = b_cfg['json']['bootstrapConfig']

# Save Bootstrap file to disk
file_name = "{}_bootstrap.cfg".format(target_uuid)
with open(file_name, 'w', encoding='ascii') as file:
    file.write(bootstrap_config_content)
print(f"Completed: Saved to {file_name}")

# Router credentials for SSH / SCP
print_task_status("Uploading bootstrap file")
router_ip = "192.168.0.1"
ssh_username = get_env("SSH_USERNAME")
ssh_password = get_env("SSH_PASSWORD")
local_file_path = file_name
remote_file_path = "bootflash:/ciscosdwan.cfg" # Required filename for ZTP

# Uploading the bootstrap to router via SCP
try:
    # Establish SSH connection
    ssh = create_ssh_client(router_ip, ssh_username, ssh_password)

    # Initialize SCP client and transfer the file
    with SCPClient(ssh.get_transport()) as scp:
        scp.put(local_file_path, remote_file_path)

    print("Completed.")

except Exception as e:
    print(f"An error occurred: {e}")

finally:
    # Close the SSH connection
    if ssh:
        ssh.close()