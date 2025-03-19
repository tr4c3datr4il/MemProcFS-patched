import requests
import subprocess as sp
import zipfile
import os
import ctypes

def MessageBox(title, text, style):
    return ctypes.windll.user32.MessageBoxW(0, text, title, style)  

os_version = os.name
if os_version != "nt":
    print("This script is only supported on Windows")
    exit()

# Change this to the path where MemProcFS is installed
memproc_folder = ".\MemProcFS"
output = sp.run([".\MemProcFS\MemProcFS.exe", "-version"], shell=True, text=True, capture_output=True)
local_version = output.stdout.strip().split(" ")[-1].removesuffix(".0")
# print(f"Local version: {local_version}")

response = requests.get("https://api.github.com/repos/ufrisk/MemProcFS/releases/latest")
latest_version = response.json()["tag_name"]
# print(f"Latest version: {latest_version}")

if local_version != latest_version:
    # ret_code == 1 is Yes, ret_code == 2 is No
    if MessageBox("MemProcFS Updater", f"Update available, do you want to update?\nFound version: {latest_version}\nLocal version: {local_version}", 1) == 1:
        json_data = response.json()["assets"]
        for asset in json_data:
            # print(f"FOUND Distribution: {asset['name']}")
            if "win" in asset["name"]:
                download_url = asset["browser_download_url"]
                # print(f"Downloading from {download_url}")
                r = requests.get(download_url)
                with open("MemProcFS.zip", "wb") as f:
                    f.write(r.content)

                with zipfile.ZipFile("MemProcFS.zip", "r") as f:
                    f.extractall(memproc_folder)
                MessageBox("MemProcFS Updater", "Update completed!", 1)