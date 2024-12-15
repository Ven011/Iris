#!/usr/bin/python3

import os

from settings import settings

# Wi-Fi configuration details
ssid = None
psk = None

# Path to the wpa_supplicant configuration file
wpa_supplicant_conf = "/etc/wpa_supplicant/wpa_supplicant.conf"

def update_wifi_settings():
    # get network settings
    ns = settings.network_settings

    # Content to write to the wpa_supplicant.conf file
    wifi_config = f"""
    country={"US"}
    ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev
    update_config=1
    network={{
        ssid="{ns["wifi_ssid"]}"
        psk="{ns["wifi_password"]}"
    }}
    """

    try:
        # Check if the script is being run as root
        if os.geteuid() != 0:
            raise PermissionError("You need to run this script as root!")

        # Backup the existing configuration
        os.system(f"sudo cp {wpa_supplicant_conf} {wpa_supplicant_conf}.bak")

        # Write the new Wi-Fi configuration
        with open(wpa_supplicant_conf, 'w') as file:
            file.write(wifi_config)
        
        print("Wi-Fi configuration updated successfully!")
        
        # Restart the Wi-Fi service to apply changes
        os.system("sudo systemctl restart dhcpcd")
        print("Wi-Fi service restarted. Connecting to the new network...")

    except Exception as e:
        print(f"Error: {e}")