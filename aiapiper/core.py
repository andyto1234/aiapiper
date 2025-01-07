import requests
import json
from datetime import datetime
from typing import Optional
import os
import re
from tqdm import tqdm
from astropy import units as u

class PipeFix:
    def __init__(self):
        self.base_url = "https://idoc-medoc.ias.u-psud.fr/webs_IAS_SDO_AIA_dataset/records"
        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/131.0.0 Safari/537.36"
            ),
            "Accept": "application/json",
            "Accept-Encoding": "gzip, deflate, br",
            "X-Requested-With": "XMLHttpRequest"
        }
    
    def fetch(self, start_date: str, end_date: str, wavelength: int,
                      cadence: u.Quantity, output_dir: Optional[str] = None) -> None:
        """
        Download SDO files for given parameters.
        
        Args:
            start_date: Start date in format "YYYY-MM-DDTHH:MM:SS.000"
            end_date: End date in format "YYYY-MM-DDTHH:MM:SS.000"
            wavelength: Wavelength value (e.g., 1600)
            cadence: Time cadence as astropy Quantity (e.g., 1*u.min, 1*u.hour, 1*u.day)
            output_dir: Optional directory to save files (default: creates 'sdo_downloads')
        """
        # Validate dates
        try:
            datetime.strptime(start_date, "%Y-%m-%dT%H:%M:%S.%f")
            datetime.strptime(end_date, "%Y-%m-%dT%H:%M:%S.%f")
        except ValueError:
            raise ValueError("Dates must be in format: YYYY-MM-DDTHH:MM:SS.000")

        # Convert cadence to appropriate string format
        if cadence.unit == u.min:
            cadence_str = f"{int(cadence.value)} min"
        elif cadence.unit == u.hour:
            cadence_str = f"{int(cadence.value)} h"
        elif cadence.unit == u.day:
            cadence_str = f"{int(cadence.value)} day"
        else:
            raise ValueError("Cadence must be in minutes, hours, or days")

        # Create output directory
        if output_dir is None:
            output_dir = "sdo_downloads"
        os.makedirs(output_dir, exist_ok=True)

        params = {
            "_dc": "1736181211408",
            "nocount": "false",
            "p[0]": f"DATE_BETWEEN|date__obs|{start_date}|{end_date}",
            "p[1]": f"CADENCE|mask_cadence|{cadence_str}",
            "p[2]": f"LISTBOXMULTIPLE|wavelnth|{wavelength}",
            "page": "1",
            "start": "0",
            "limit": "300"
        }

        try:
            response = requests.get(
                self.base_url,
                params=params,
                headers=self.headers,
                timeout=20
            )
            response.raise_for_status()
            data = response.json()
            
            if not data.get("success"):
                print("API request was not successful")
                return
            
            total_files = len(data["data"])
            print(f"Found {total_files} files to download")
            
            for i, record in tqdm(enumerate(data["data"], 1), desc="Downloading SDO files", total=total_files):
                file_url = record["get"]
                # print(f"Downloading file {i}/{total_files}")
                self._download_file(file_url, output_dir)
                
        except requests.RequestException as e:
            print(f"Error during request: {e}")
        except json.JSONDecodeError:
            print("Error: Response is not valid JSON")
            
    def _download_file(self, file_url: str, output_dir: str) -> None:
        """Download a single file from the given URL."""
        try:
            response = requests.get(file_url, headers=self.headers, stream=True)
            response.raise_for_status()
            
            # Get filename from Content-Disposition header
            content_disposition = response.headers.get('Content-Disposition', '')
            filename_match = re.search(r'filename="?([^"]+)"?', content_disposition)
            
            if filename_match:
                filename = filename_match.group(1).replace(':', '-')
            else:
                print("Could not extract filename from headers, using default name")
                filename = file_url.split('/')[-1]
            
            filepath = os.path.join(output_dir, filename)
            
            with open(filepath, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            # print(f"Successfully downloaded: {filepath}")
            
        except requests.RequestException as e:
            print(f"Failed to download {file_url}: {e}")

# Example usage
if __name__ == "__main__":
    downloader = PipeFix()
    downloader.fetch(
        start_date="2023-02-05T00:00:00.000",
        end_date="2023-02-05T02:00:00.000",
        wavelength=193,
        cadence=1*u.min,  # Can also use u.hour or u.day
        output_dir="/Users/andysh.to/Downloads/aia_test"  # optional
    )