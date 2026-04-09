import os
import urllib.request

EPHE_DIR = "ephe"
FILES = [
    "seas_18.se1",  # Core ephemeris data
    "sweph.zip",    # Optional full bundle
]
BASE_URL = "https://www.astro.com/ftp/swisseph/ephe/"

def download_ephe():
    if not os.path.exists(EPHE_DIR):
        os.makedirs(EPHE_DIR)
        print(f"Created {EPHE_DIR} directory.")

    print(f"Downloading ephemeris data to {EPHE_DIR}...")
    for filename in FILES:
        url = BASE_URL + filename
        target = os.path.join(EPHE_DIR, filename)
        
        if os.path.exists(target):
            print(f"File {filename} already exists. Skipping.")
            continue
            
        try:
            print(f"Fetching {url}...")
            urllib.request.urlretrieve(url, target)
            print(f"Successfully downloaded {filename}")
        except Exception as e:
            print(f"Failed to download {filename}: {e}")

if __name__ == "__main__":
    download_ephe()
