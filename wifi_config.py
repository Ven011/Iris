#!/usr/bin/python3

import os

from settings import settings.get_setting

# Wi-Fi configuration details
ssid = settings.get_setting("wifi_settings")["ssid"]
psk = settings.get_setting("wifi_settings")["password"]
country = "US"  # Adjust this to your country code

# Path to the wpa_supplicant configuration file
wpa_supplicant_conf = "/etc/wpa_supplicant/wpa_supplicant.conf"

# Content to write to the wpa_supplicant.conf file
wifi_config = f"""
country={country}
ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev
update_config=1
network={{
    ssid="{ssid}"
    psk="{psk}"
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