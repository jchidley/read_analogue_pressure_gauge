# Gauge Image Processing System - Configuration Update

## Overview

This update refactors the Gauge Image Processing System to use a centralized TOML configuration file instead of hardcoded magic numbers. This significantly improves maintainability, flexibility, and makes the system more configurable without having to modify code.

## Files Modified

1. **gauge_config.toml** - New file containing all configuration values
2. **gauge_config.py** - New utility module to load and access configuration
3. **gauge_lib.py** → **gauge_lib_modified.py** - Updated to use configuration system
4. **gauge_cli.py** → **gauge_cli_modified.py** - Updated to use configuration system
5. **repair_script.py** → **repair_script_modified.py** - Updated to use configuration system
6. **filter_large_angles.py** → **filter_large_angles_modified.py** - Updated to use configuration system

## Configuration Structure

The configuration is organized into the following sections:

1. **paths** - Default paths and file patterns
2. **detection** - Image processing parameters for gauge detection
3. **line_detection** - Parameters for detecting lines in images
4. **pressure** - Pressure conversion parameters for mapping angles to PSI/BAR
5. **plotting** - Time-series plot parameters and defaults
6. **repair** - Default values to use when repairing corrupted database entries
7. **filtering** - Parameters for filtering outlier angle measurements

## How to Use

### Basic Usage

The system will automatically look for a configuration file in these locations:
- `./gauge_config.toml` (Current directory)
- `~/.config/gauge/config.toml` (User config directory)
- `/etc/gauge/config.toml` (System config directory)

If no configuration file is found, it will use hardcoded defaults.

### Specifying a Custom Configuration File

All tools now support a `--config` parameter to specify a custom configuration file:

```bash
python gauge_cli_modified.py --config /path/to/my/config.toml
python repair_script_modified.py --config /path/to/my/config.toml
python filter_large_angles_modified.py --config /path/to/my/config.toml
```

### Overriding Configuration Values

Command-line arguments still take precedence over configuration file values, allowing you to override specific settings when needed:

```bash
python gauge_cli_modified.py --threshold 150 --min-radius 120
```

## Migration Guide

1. Copy the `gauge_config.toml` file to your project directory
2. Copy the `gauge_config.py` file to your project directory
3. Replace the existing scripts with the modified versions
4. Modify the configuration values in `gauge_config.toml` as needed

## Benefits

- **Centralized Configuration**: All parameters in one place
- **Flexibility**: Easy to adjust parameters without code changes
- **Maintainability**: Clearer code with reduced magic numbers
- **Modularity**: Configuration system is reusable across components
- **Documentation**: Configuration file serves as documentation for parameters
- **Multiple Environments**: Support for different configurations (development, production, etc.)

## Example: Customizing for Different Gauges

You can create multiple configuration files for different types of gauges:

```bash
# For a pressure gauge
python gauge_cli_modified.py --config pressure_gauge.toml

# For a temperature gauge
python gauge_cli_modified.py --config temperature_gauge.toml
```

## Configuration Parameters Reference

### Image Processing Parameters

- **binary_threshold**: Threshold for binary image conversion (default: 140)
- **min_radius**: Minimum radius of gauge circle in pixels (default: 100)
- **max_radius**: Maximum radius of gauge circle in pixels (default: 1000)
- **change_threshold**: Minimum angle change considered significant (default: 5.0)

### Pressure Conversion Parameters

- **min_angle**: Angle corresponding to zero pressure (default: 30)
- **max_angle**: Angle corresponding to maximum pressure (default: 295)
- **max_psi**: Maximum pressure value in PSI (default: 58)
- **max_bar**: Maximum pressure value in BAR (default: 4.0)

For a complete list of parameters, refer to the comments in the `gauge_config.toml` file.
