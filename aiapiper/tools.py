import requests
import json
from datetime import datetime
from typing import Optional
import os
import re
from tqdm import tqdm
from astropy import units as u
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

class PipeFix:
    def __init__(self, max_workers: int = 8):
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
        self.max_workers = max_workers
        # Create a session for connection pooling
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        
        # Thread-safe progress tracking
        self.progress_lock = threading.Lock()
        self.downloaded_count = 0
    
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
            "_dc": str(int(datetime.now().timestamp() * 1000)),
            "nocount": "false",
            "p[0]": f"DATE_BETWEEN|date__obs|{start_date}|{end_date}",
            "p[1]": f"CADENCE|mask_cadence|{cadence_str}",
            "p[2]": f"LISTBOXMULTIPLE|wavelnth|{wavelength}",
            "page": "1",
            "start": "0",
            "limit": "300"
        }

        try:
            print("Fetching file list...")
            response = self.session.get(
                self.base_url,
                params=params,
                timeout=15  # Reduced timeout for initial request
            )
            response.raise_for_status()
            data = response.json()
            
            if not data.get("success"):
                print("API request was not successful")
                return
            
            total_files = len(data["data"])
            print(f"Found {total_files} files to download")
            
            # Reset progress counter
            self.downloaded_count = 0
            
            # Use ThreadPoolExecutor for concurrent downloads
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                # Create progress bar
                with tqdm(total=total_files, desc="Downloading SDO files") as pbar:
                    # Submit all download tasks
                    future_to_url = {
                        executor.submit(self._download_file, record["get"], output_dir): record["get"]
                        for record in data["data"]
                    }
                    
                    # Process completed downloads
                    for future in as_completed(future_to_url):
                        url = future_to_url[future]
                        try:
                            result = future.result()
                            if result:  # Successfully downloaded
                                with self.progress_lock:
                                    self.downloaded_count += 1
                            pbar.update(1)
                        except Exception as e:
                            print(f"Error downloading {url}: {e}")
                            pbar.update(1)
            
            print(f"Download complete! Successfully downloaded {self.downloaded_count}/{total_files} files")
                
        except requests.RequestException as e:
            print(f"Error during request: {e}")
        except json.JSONDecodeError:
            print("Error: Response is not valid JSON")
    
    def _download_file(self, file_url: str, output_dir: str) -> bool:
        """Download a single file from the given URL. Returns True if successful."""
        try:
            response = self.session.get(
                file_url, 
                stream=True, 
                timeout=(10, 30)  # Reduced timeout: (connect, read)
            )
            response.raise_for_status()
            
            # Get filename from Content-Disposition header
            content_disposition = response.headers.get('Content-Disposition', '')
            filename_match = re.search(r'filename="?([^"]+)"?', content_disposition)
            
            if filename_match:
                filename = filename_match.group(1).replace(':', '-')
            else:
                filename = file_url.split('/')[-1]
            
            filepath = os.path.join(output_dir, filename)

            # Skip if file already exists
            if os.path.exists(filepath):
                return True
            
            # Use larger chunk size for better performance
            with open(filepath, "wb") as f:
                for chunk in response.iter_content(chunk_size=65536):  # 64KB chunks
                    if chunk:
                        f.write(chunk)
            
            return True
            
        except requests.Timeout:
            print(f"Timeout reached while downloading {file_url} - skipping")
            return False
        except requests.RequestException as e:
            print(f"Failed to download {file_url}: {e}")
            return False
        except Exception as e:
            print(f"Unexpected error downloading {file_url}: {e}")
            return False

    def __del__(self):
        """Clean up session when object is destroyed."""
        if hasattr(self, 'session'):
            self.session.close()

# Example usage
if __name__ == "__main__":
    # You can adjust max_workers based on your needs and server limits
    downloader = PipeFix(max_workers=6)  # Start with 6 concurrent downloads
    downloader.fetch(
        start_date="2023-02-05T00:00:00.000",
        end_date="2023-02-05T02:00:00.000",
        wavelength=193,
        cadence=1*u.min,
        output_dir="/Users/andysh.to/Downloads/aia_test"
    )