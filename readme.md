# Gauge Image Processing System

## System Overview

The Gauge Image Processing System is designed to automatically detect and measure the angle of gauge needles in images. The system processes images of analog gauges, detects circular gauge faces, identifies needle positions, and measures angles. It stores processing results in a SQLite database and provides time-series plotting capabilities with time-based filtering and averaging options. The system also converts angle readings to pressure units (PSI/BAR) for pressure gauge monitoring.

The system consists of two main parts:
1. **Image Capture** - Runs on a Raspberry Pi to capture gauge images every 20 minutes
2. **Image Processing** - Analyzes captured images to extract gauge readings

Both components can run on the same Raspberry Pi or separately (capture on Pi, processing on a more powerful machine).

## Core Components

### 1. GaugeDetector Class

The `GaugeDetector` class is the core component responsible for processing images and detecting gauge needles.

Key capabilities:
- Detect circular gauge faces in images using Hough Circle detection
- Identify gauge needle position through image processing techniques
- Calculate needle angle in degrees
- Convert angles to pressure values (PSI/BAR) using linear interpolation
- Maintain a history of gauge readings
- Support debug mode for troubleshooting

### 2. GaugeResult Class

This class represents the result of a gauge detection operation, containing:
- Measured angle (in degrees)
- Gauge center coordinates (x, y)
- Gauge radius (in pixels)
- Path to the source image
- Timestamp of the detection
- Pressure values in PSI and BAR (derived from angle)

## Command-Line Tools

### 1. Main CLI Tool (`gauge_cli.py`)

The primary interface for processing gauge images and storing results in a SQLite database.

Features:
- Process multiple gauge images in batch
- Configure detection parameters
- Store successful detections and failures in a SQLite database
- Skip previously processed images for efficiency
- Plot angle changes over time with configurable time windows
- Plot pressure values (PSI/BAR) derived from angles
- Time-based averaging of results for trend analysis
- Detect significant angle changes based on a threshold

Command-line arguments:
- `--dir`: Directory containing gauge images (default: "dial_images")
- `--pattern`: File pattern to match (default: "*.jpg")
- `--debug`: Enable debug mode
- `--debug-dir`: Directory for debug images (default: "debug")
- `--db`: SQLite database file (default: "gauge_data.db")
- `--plot`: Generate plots (requires matplotlib)
- `--plot-output`: Plot output path (default: "gauge_plots.png")
- `--threshold`: Binary threshold value (default: 140)
- `--min-radius`: Minimum gauge radius in pixels (default: 100)
- `--max-radius`: Maximum gauge radius in pixels (default: 1000)
- `--change-threshold`: Minimum significant angle change (default: 5.0)
- `--force`: Force processing all images
- `--retry-failures`: Retry failed detections
- `--new-only`: Plot only new results instead of all results
- `--time-window`: Number of days to include in plots (default: 7)
- `--all-time`: Plot all data regardless of time window
- `--average`: Enable time-based averaging of results
- `--average-period`: Period for averaging: 'minute', 'hour', 'day' (default: hour)
- `--average-value`: Number of periods to average (default: 1)
- `--pressure-unit`: Unit for plotting: 'angle', 'psi', 'bar' (default: angle)

### 2. Database Repair Tool (`repair_script.py`)

A utility to repair potentially corrupted entries in the gauge results database.

Features:
- Check for invalid or corrupt field values
- Replace invalid values with sensible defaults
- Create database backups before making changes
- Transaction-based processing for safety

Command-line arguments:
- `--db`: Database file path (default: "gauge_data.db")
- `--backup`: Create a backup before repairing
- `--verbose`: Show detailed information about repairs

### 3. Angle Filter Tool (`filter_large_angles.py`)

A utility to find and optionally mark as failures any gauge records with angles exceeding a specified threshold.

Features:
- Query database for records with excessive angles
- Mark identified records as detection failures
- Backup database before modification

Command-line arguments:
- `--db`: Database file (default: "gauge_data.db")
- `--dir`: Image directory (default: "dial_images")
- `--threshold`: Angle threshold (default: 200)
- `--mark-as-failures`: Mark records as detection failures

## Database Schema

### 1. gauge_results Table

Stores successful gauge detections:
- `id`: INTEGER PRIMARY KEY AUTOINCREMENT
- `image_name`: TEXT UNIQUE - Filename of the processed image
- `angle`: REAL - Detected angle in degrees
- `center_x`: INTEGER - X-coordinate of gauge center
- `center_y`: INTEGER - Y-coordinate of gauge center
- `radius`: INTEGER - Radius of gauge in pixels
- `timestamp`: TEXT - Timestamp of detection
- `pressure_psi`: REAL - Pressure value in PSI
- `pressure_bar`: REAL - Pressure value in BAR

### 2. detection_failures Table

Stores records of images where gauge detection failed:
- `id`: INTEGER PRIMARY KEY AUTOINCREMENT
- `image_name`: TEXT UNIQUE - Filename of the failed image
- `timestamp`: TEXT - Timestamp of detection attempt

## Input/Output

### Input
- Directory of gauge images (default: "dial_images")
- Image file pattern (default: "*.jpg")

### Output
- SQLite database with detection results including angle and pressure values
- Time-series plots of angle or pressure changes with configurable time windows
- Time-averaged plots for trend analysis
- Debug images showing detection process (optional)

## Error Handling and Recovery

- Database backup creation before modifications
- Transaction-based database operations
- Robust error handling during image processing
- Data validation before database storage
- Tools to identify and fix corrupt database entries
- Tools to mark false detections as failures

## Image Processing Parameters

- Binary threshold: Controls image binarization (default: 140)
- Minimum radius: Lower bound for gauge detection (default: 100 pixels)
- Maximum radius: Upper bound for gauge detection (default: 1000 pixels)
- Change threshold: Minimum angle change to consider significant (default: 5.0 degrees)

## Pressure Conversion Parameters

- Minimum angle: Angle corresponding to 0 PSI/BAR (default: 31 degrees)
- Maximum angle: Angle corresponding to maximum pressure (default: 265 degrees)
- Maximum PSI: Maximum pressure value in PSI (default: 58 PSI)
- Maximum BAR: Maximum pressure value in BAR (default: 4.0 BAR)

## Data Analysis Features

### Time Window Filtering
- Filter data based on time periods (default: 7 days)
- Option to view all historical data
- Adaptive tick formatting based on data range

### Time-Based Averaging
- Average readings over configurable time periods
- Support for minute, hour, and day-based averaging
- Configurable number of periods to average
- Visual display of both raw and averaged data
- Statistical summaries including standard deviation

### Pressure Unit Display
- Option to display angles in original degrees
- Option to display pressure in PSI units
- Option to display pressure in BAR units
- Automatic scaling of pressure values on plots

## Performance Considerations

- Skip previously processed images for efficiency
- Option to process only new images
- Separate tracking of successful and failed detections
- Command to force reprocessing when needed

## Dependencies

Primary dependencies:
- Python 3.x
- OpenCV (for image processing)
- SQLite3 (for data storage)
- Optional: Matplotlib (for plotting)

## Typical Workflow

1. Collect gauge images in a designated directory
2. Run the main CLI tool to process images and store results
3. Generate plots with appropriate time window, averaging options, and pressure units
4. Use repair and filter tools as needed for data maintenance
5. Track gauge readings over time to detect significant changes and trends

## Common Use Cases

### Basic Gauge Monitoring
```bash
python gauge_cli.py --dir my_gauges --plot
```

### Pressure Gauge Monitoring with PSI Units
```bash
python gauge_cli.py --dir my_gauges --plot --pressure-unit psi
```

### Analyzing Long-Term Pressure Trends
```bash
python gauge_cli.py --plot --all-time --average --average-period day --pressure-unit bar
```

### Comparing Recent Data with Higher Resolution
```bash
python gauge_cli.py --plot --time-window 3 --average --average-period hour --average-value 2
```

### Detecting Rapid Changes
```bash
python gauge_cli.py --plot --time-window 1 --change-threshold 2.0
```

## Security and Data Integrity

- Database backups before modifications
- Transaction-based operations to prevent partial updates
- Validation of data during loading and processing
- Error handling to prevent database corruption

## Future Enhancements

Potential areas for enhancement:
- Web interface for result visualization
- Real-time monitoring capabilities
- More advanced image processing techniques
- Machine learning-based needle detection
- Alert system for significant changes
- Export functionality for reports
- API for integration with other systems
- Customizable pressure conversion parameters
- Support for additional pressure units

## Implementation Notes

- The system is implemented in Python for flexibility and ease of development
- OpenCV is used for image processing operations
- SQLite is used for persistent storage
- The code has been simplified by removing debug image generation functionality
  - This was done to reduce complexity and dependencies
  - Future LLMs should not attempt to reimplement this feature
  - Debug information is still available through console output

## Usage

```bash
# Process images in the default directory
python gauge_cli.py

# Process images in a specific directory
python gauge_cli.py --dir /path/to/images

# Force reprocessing of all images
python gauge_cli.py --force

# Enable debug mode
python gauge_cli.py --debug
```

## Configuration

The system uses default parameters for:
- Circle detection (min/max radius, Hough transform parameters)
- Line detection (Canny edge detection, Hough lines)
- Pressure conversion (angle to PSI/BAR)

These can be modified in the code if needed.

## Database Schema

The system uses two tables:
1. `gauge_results` - Stores successful detections
2. `detection_failures` - Tracks failed detections

## Dependencies

### Python Dependencies
Scripts now use inline script metadata for dependency management with `uv`:
- OpenCV (Python bindings)
- SQLite3
- Matplotlib (for plotting)  
- TOML (for configuration file parsing)
- numpy

### System Dependencies (Raspberry Pi)
- `pigpiod` - For GPIO control (LED lighting)
- `rpicam-jpeg` - For camera capture (part of libcamera)
- `uv` - For Python dependency management
- `sqlite3` - For database queries in cleanup scripts

## Raspberry Pi Deployment

This section describes how to deploy the complete system on a Raspberry Pi for automated gauge monitoring.

### Prerequisites

1. **Install uv on the Raspberry Pi:**
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   source ~/.bashrc  # or restart shell
   ```

2. **Ensure pigpiod is installed:**
   ```bash
   sudo apt-get update
   sudo apt-get install pigpio python3-pigpio
   ```

3. **Ensure camera tools are installed:**
   ```bash
   # For Raspberry Pi OS with libcamera
   sudo apt-get install libcamera-apps
   ```

4. **Install sqlite3 for database operations:**
   ```bash
   sudo apt-get update
   sudo apt-get install -y sqlite3
   ```

### SSH Key Setup

To enable passwordless SSH access from your local machine to the Raspberry Pi:

1. **Check if you have an SSH key on your local machine:**
   ```bash
   ls ~/.ssh/id_*.pub
   ```

2. **If no key exists, generate one:**
   ```bash
   ssh-keygen -t ed25519 -C "your_email@example.com"
   ```

3. **Copy your public key to the Raspberry Pi:**
   ```bash
   # Method 1: Using ssh-copy-id (easiest)
   ssh-copy-id jack@pi4light.local
   
   # Method 2: Manual copy
   # First, display your public key:
   cat ~/.ssh/id_ed25519.pub
   
   # Then SSH to the Pi and add it to authorized_keys:
   ssh jack@pi4light.local
   echo "YOUR_PUBLIC_KEY_HERE" >> ~/.ssh/authorized_keys
   chmod 600 ~/.ssh/authorized_keys
   ```

### Deployment Steps

1. **Clone or copy this repository to your local machine**

2. **Deploy the capture service:**
   ```bash
   # Copy capture script to Pi
   scp capture_images.sh jack@pi4light:~/
   
   # The capture service (dial_capture.service) should already be installed
   # To check its status:
   ssh jack@pi4light "sudo systemctl status dial_capture.service"
   
   # To update the capture script:
   ssh jack@pi4light "sudo systemctl restart dial_capture.service"
   ```

3. **Deploy the processing service:**
   ```bash
   # Copy all required files
   scp continuous_gauge_processor.sh gauge_processor.service install_gauge_processor_service.sh jack@pi4light:~/
   scp gauge_cli.py gauge_lib.py gauge_config.py filter_large_angles.py gauge_config.toml jack@pi4light:~/
   
   # Install the service
   ssh jack@pi4light "sudo bash install_gauge_processor_service.sh"
   ```

### Service Management

Both services run continuously via systemd:

#### Capture Service (dial_capture.service)
- Captures images at 00, 20, and 40 minutes past each hour
- Controls LED lighting via GPIO for consistent illumination
- Saves images to `/home/jack/dial_images/`

```bash
# View status
sudo systemctl status dial_capture.service

# View logs
sudo journalctl -u dial_capture.service -f

# Restart service
sudo systemctl restart dial_capture.service
```

#### Processing Service (gauge_processor.service)
- Checks for new images every 5 minutes
- Processes images to extract gauge readings
- Deletes successfully processed images to save space
- Maintains failed images for troubleshooting

```bash
# View status
sudo systemctl status gauge_processor.service

# View logs
sudo journalctl -u gauge_processor.service -f

# Restart service
sudo systemctl restart gauge_processor.service
```

### File Locations on Raspberry Pi

- **Images**: `/home/jack/dial_images/`
- **Database**: `/home/jack/gauge_data.db`
- **Plots**: `/home/jack/gauge_plots.png`
- **Scripts**: `/home/jack/`
- **Service files**: `/etc/systemd/system/`

### Processing Images Locally (Alternative)

If you prefer to process images on a more powerful machine:

1. **Windows (PowerShell):**
   ```powershell
   # Use read_it.ps1 to copy images and process
   .\read_it.ps1
   ```

2. **Linux/Mac:**
   ```bash
   # Copy images from Pi
   scp jack@pi4light:./dial_images/*.jpg ./dial_images/
   
   # Process locally
   uv run gauge_cli.py --plot --pressure-unit bar --average --all-time
   uv run filter_large_angles.py --mark-as-failures
   uv run gauge_cli.py --plot --pressure-unit bar --average --all-time
   ```

### Monitoring and Verification

After deployment, you can monitor the system's operation:

1. **Check processing progress:**
   ```bash
   # View service status with CPU usage
   ssh jack@pi4light "sudo systemctl status gauge_processor.service --no-pager"
   
   # Watch live logs
   ssh jack@pi4light "sudo journalctl -u gauge_processor.service -f"
   ```

2. **Verify database entries:**
   ```bash
   # Check processed images
   ssh jack@pi4light "sqlite3 gauge_data.db 'SELECT image_name, angle, pressure_bar FROM gauge_results ORDER BY timestamp DESC LIMIT 5;'"
   
   # Count total records
   ssh jack@pi4light "sqlite3 gauge_data.db 'SELECT COUNT(*) FROM gauge_results;'"
   ```

3. **Monitor performance:**
   - Initial image processing takes 10-20 minutes on a Raspberry Pi
   - The processor service uses significant CPU (up to 300%+ on multi-core)
   - Check for completion messages in logs: "Successfully processed: X"

### Troubleshooting

1. **Check if services are running:**
   ```bash
   ssh jack@pi4light "sudo systemctl status dial_capture.service gauge_processor.service"
   ```

2. **Check for images:**
   ```bash
   ssh jack@pi4light "ls -la dial_images/"
   ```

3. **Database issues:**
   ```bash
   # If sqlite3 is not found, install it:
   ssh jack@pi4light "sudo apt-get install -y sqlite3"
   
   # Check database contents
   ssh jack@pi4light "sqlite3 gauge_data.db 'SELECT COUNT(*) FROM gauge_results;'"
   ```

4. **View recent captures:**
   ```bash
   ssh jack@pi4light "ls -lt dial_images/ | head -10"
   ```

5. **Check disk space:**
   ```bash
   ssh jack@pi4light "df -h /home/jack"
   ```

6. **If processing seems stuck:**
   ```bash
   # Check if the process is actually running
   ssh jack@pi4light "ps aux | grep gauge_cli"
   
   # Restart the service if needed
   ssh jack@pi4light "sudo systemctl restart gauge_processor.service"
   ```
