This script is to assist in the automated migration of an autonomous Cisco router to running in controller-mode for Catalyst SDWAN that requires static IP addressing for ZTP.

There are 4 files.

1) get-router-variables.py - Get existing configuration elements
2) bootstrap.py - Code to extend the Viptela SDK
3) SDWAN_static_ip_ZTP_helper.py - Code to do the SDWAN manager interaction and upload file to router
4) requirements.txt - Python packages required
