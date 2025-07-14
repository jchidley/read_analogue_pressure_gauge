# Gauge Image Processing System

A computer vision system that automatically reads analog pressure gauges using a Raspberry Pi camera. It captures images of physical gauges, detects the needle position, converts the angle to pressure values (PSI/BAR), and tracks readings over time with graphical analysis.

## What It Does

1. **Captures** gauge images every 20 minutes using a Pi camera with LED lighting
2. **Detects** the circular gauge face and needle position using OpenCV
3. **Calculates** the needle angle and converts it to pressure (PSI/BAR)
4. **Stores** readings in a SQLite database with timestamps
5. **Plots** time-series graphs showing pressure trends over time
6. **Filters** outlier readings automatically

Perfect for monitoring pressure systems, boilers, compressors, or any analog gauge that needs logging.

## Quick Start

### One-Command Deployment to Raspberry Pi

```bash
# Clone this repo, then deploy everything:
./deploy_to_pi.sh

# Or specify custom host:
PI_HOST=pi@raspberrypi.local ./deploy_to_pi.sh
```

This script automatically:
- Installs all dependencies (uv, sqlite3, pigpio, libcamera)
- Copies all required files
- Configures and starts both services
- Verifies the deployment

### Manual Processing

```bash
# Process captured images and generate plots
uv run gauge_cli.py --plot --pressure-unit bar --average --all-time

# Remove outlier readings
uv run filter_large_angles.py --mark-as-failures
```

## How It Works

### System Architecture

Two systemd services work together:

1. **dial_capture.service** - Image capture
   - Runs continuously, sleeps until next capture time
   - Captures at :00, :20, :40 minutes past each hour
   - Controls LED via GPIO for consistent lighting
   - Saves JPEGs to `/home/jack/dial_images/`

2. **gauge_processor.service** - Image processing
   - Checks for new images every 5 minutes
   - Processes images (10-20 min per image on Pi)
   - Deletes processed images to save space
   - Updates database and plots

### Image Processing Pipeline

1. Load image and convert to grayscale
2. Detect circular gauge using Hough circles
3. Extract gauge region and apply threshold
4. Detect needle using line detection
5. Calculate angle from vertical (0-360°)
6. Convert angle to pressure using calibration
7. Store results in database

### Data Storage

SQLite database (`gauge_data.db`) with two tables:
- `gauge_results` - Successful readings (angle, pressure, timestamp)
- `detection_failures` - Failed detection attempts

## Configuration

Edit `gauge_config.toml` to adjust:

```toml
[gauge.detection]
binary_threshold = 140      # Image threshold for needle detection
min_radius = 100           # Minimum gauge size in pixels
max_radius = 1000          # Maximum gauge size in pixels

[gauge.pressure]
min_angle = 31             # Angle at 0 pressure
max_angle = 265            # Angle at max pressure
max_psi = 58              
max_bar = 4.0
```

## Monitoring & Management

```bash
# Check service status
ssh jack@pi4light "sudo systemctl status dial_capture.service gauge_processor.service"

# Watch live processing logs
ssh jack@pi4light "sudo journalctl -u gauge_processor.service -f"

# View recent readings
ssh jack@pi4light "sqlite3 gauge_data.db 'SELECT datetime(timestamp), angle, pressure_bar FROM gauge_results ORDER BY timestamp DESC LIMIT 10;'"

# Check disk space
ssh jack@pi4light "df -h /home/jack"
```

## Command-Line Options

### gauge_cli.py
Main processing tool with options:
- `--plot` - Generate time-series plots
- `--pressure-unit [angle|psi|bar]` - Display units
- `--time-window N` - Days to include (default: 7)
- `--all-time` - Plot all historical data
- `--average` - Enable time-based averaging
- `--average-period [minute|hour|day]` - Averaging granularity
- `--force` - Reprocess all images

### filter_large_angles.py
Outlier detection:
- `--threshold` - Maximum valid angle (default: 200°)
- `--mark-as-failures` - Move outliers to failures table

## Alternative: Local Processing

For faster processing on a more powerful machine:

```bash
# Windows
.\read_it.ps1

# Linux/Mac
scp jack@pi4light:./dial_images/*.jpg ./dial_images/
uv run gauge_cli.py --plot --pressure-unit bar --average --all-time
```

## File Locations

**On Raspberry Pi:**
- Images: `/home/jack/dial_images/`
- Database: `/home/jack/gauge_data.db`
- Plots: `/home/jack/gauge_plots.png`
- Scripts: `/home/jack/`
- Services: `/etc/systemd/system/`

## Troubleshooting

**Processing seems stuck:**
```bash
# Check if actively processing (high CPU usage is normal)
ssh jack@pi4light "ps aux | grep gauge_cli"

# Restart if needed
ssh jack@pi4light "sudo systemctl restart gauge_processor.service"
```

**No images being captured:**
```bash
# Check capture service
ssh jack@pi4light "sudo systemctl status dial_capture.service"
ssh jack@pi4light "sudo journalctl -u dial_capture.service -n 50"
```

**Database errors:**
```bash
# Install sqlite3 if missing
ssh jack@pi4light "sudo apt-get install -y sqlite3"
```

## Performance Notes

- Image processing takes 10-20 minutes per image on Raspberry Pi
- CPU usage can reach 300%+ during processing (normal)
- Each image is ~1MB, processed images are deleted automatically
- Database and plots are retained indefinitely

## Repository Contents

- `deploy_to_pi.sh` - Automated deployment script
- `capture_images.sh` - Camera capture with LED control
- `continuous_gauge_processor.sh` - Processing loop
- `gauge_cli.py` - Main image processing tool
- `gauge_lib.py` - Core detection algorithms
- `gauge_config.py` - Configuration loader
- `gauge_config.toml` - User settings
- `filter_large_angles.py` - Outlier detection
- Service files and installation scripts