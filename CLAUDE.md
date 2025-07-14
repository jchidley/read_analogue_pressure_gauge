# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Purpose

This repository contains a system for automatically detecting and measuring angles from analogue pressure gauges in images. The system processes images, detects circular gauge faces, identifies needle positions, measures angles, and converts these to pressure values (PSI/BAR). Results are stored in a SQLite database with visualization capabilities.

## Architecture

The system is implemented in Python with the following main files:
1. `gauge_lib.py`: Core detection functionality
2. `gauge_cli.py`: Command-line interface
3. `gauge_config.py`: Configuration management
4. `filter_large_angles.py`: Utility for filtering outliers

### Core Components

- **GaugeDetector**: Processes images to find gauges and measure needle angles
- **Database**: SQLite storage for detection results and failures
- **Configuration**: TOML-based configuration for detection parameters
- **Visualization**: Time-series plotting (Python version only)

## Command Reference

### Python Implementation

```bash
# Basic usage - process images in default directory
python gauge_cli.py

# Process images in specific directory
python gauge_cli.py --dir /path/to/images

# Process images and generate plots
python gauge_cli.py --plot

# Show pressure in PSI units
python gauge_cli.py --plot --pressure-unit psi

# Process with time windowing and averaging
python gauge_cli.py --plot --time-window 7 --average --average-period hour

# Force reprocessing of all images
python gauge_cli.py --force

# Enable debug mode with visualization
python gauge_cli.py --debug
```

### Database Utilities

```bash
# Filter large angles
python filter_large_angles.py --db gauge_data.db --threshold 200 --mark-as-failures
```

## Configuration

The system uses a TOML configuration file (`gauge_config.toml`) with sections for:

- **Gauge parameters**: Circle detection settings
- **Needle characteristics**: For detection
- **Pressure conversion**: Mapping angles to PSI/BAR
- **Debug settings**: Output options

Important parameters that may need tuning:
- `min_radius`, `max_radius`: Define size range for gauge detection
- `binary_threshold`: Controls image binarization
- `min_angle`, `max_angle`: Define the gauge scale range
- `max_psi`, `max_bar`: Define the maximum pressure values

## Development Guidelines

1. When modifying image processing parameters, carefully test across multiple sample images

2. After code changes, validate results by:
   - Checking gauge angle detection
   - Verifying pressure conversion
   - Testing database storage
   - Examining plot generation (for Python version)

3. For debugging:
   - Enable debug mode to generate visualization images
   - Check debug directory for processing artifacts
   - Use SQLite tooling to inspect database contents

4. When adding features, respect the existing architecture:
   - Image processing → detection → result → database → visualization
   - Use the configuration system for new parameters