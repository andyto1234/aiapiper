# AIAPiper

AIAPiper is a Python package that provides an alternative solution for downloading SDO/AIA data when the  JSOC server is unavailable. This tool was developed in response to the water damage incident affecting the standard SDO/AIA JSOC server access.

## Installation

You can install AIAPiper using pip:
```bash
git clone https://github.com/yourusername/aiapiper.git
cd aiapiper
pip install -e .
```

## Usage
Here's a simple example of how to use AIAPiper to download AIA data:

```python
from aiapiper.core import PipeFix
import astropy.units as u
```

```python
downloader = PipeFix()

downloader.fetch(
    start_date="2023-02-05T00:00:00.000",
    end_date="2023-02-05T02:00:00.000",
    wavelength=193,
    cadence=1*u.day, # Can also use u.hour or u.min
    output_dir="/path/to/output/directory" # optional
    )
```

## Requirements

- Python >= 3.8
- requests >= 2.25.0
- astropy >= 5.0.0
- tqdm >= 4.65.0


## Why AIAPiper?

The standard method for downloading SDO/AIA data through JSOC has been affected by water damage to the server infrastructure. AIAPiper provides an alternative solution to ensure continued access to vital solar physics data for research and analysis.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## Author

Andy To (European Space Agency)

## Acknowledgments

- Solar Dynamics Observatory (SDO) team
- Atmospheric Imaging Assembly (AIA) team