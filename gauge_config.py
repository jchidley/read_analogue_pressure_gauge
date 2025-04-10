#!/usr/bin/env python3
"""
Configuration utilities for the gauge image processing system
"""

import os
import sys
import toml
from pathlib import Path

# Default locations to look for config file
DEFAULT_CONFIG_LOCATIONS = [
    "./gauge_config.toml",  # Current directory
    "~/.config/gauge/config.toml",  # User config directory
    "/etc/gauge/config.toml",  # System config directory
]

# Hard-coded defaults as fallback
DEFAULT_CONFIG = {
    "paths": {
        "default_image_dir": "dial_images",
        "default_image_pattern": "*.jpg",
        "default_debug_dir": "debug",
        "default_db_file": "gauge_data.db",
        "default_plot_output": "gauge_plots.png",
    },
    "detection": {
        "binary_threshold": 140,
        "min_radius": 100,
        "max_radius": 1000,
        "change_threshold": 5.0,
        "param1": 60,
        "param2": 30,
    },
    "line_detection": {
        "canny_low": 50,
        "canny_high": 150,
        "hough_threshold": 25,
        "min_line_length_factor": 0.25,
        "max_line_gap": 20,
        "line_center_distance_factor": 0.125,
        "angle_grouping_threshold": 10,
    },
    "pressure": {
        "min_angle": 30,
        "max_angle": 295,
        "max_psi": 58,
        "max_bar": 4.0,
    },
    "plotting": {
        "default_time_window": 7,
        "default_average_period": "hour",
        "default_average_value": 1,
        "default_pressure_unit": "psi",
    },
    "repair": {
        "default_center_x": 320,
        "default_center_y": 240,
        "default_radius": 200,
        "default_angle": 0.0,
    },
    "filtering": {
        "large_angle_threshold": 200,
    },
}


class GaugeConfig:
    """
    Configuration manager for gauge image processing system
    """

    def __init__(self, config_path=None):
        """
        Initialize configuration from TOML file
        
        Args:
            config_path: Optional path to configuration file
        """
        self.config = DEFAULT_CONFIG.copy()
        self.config_path = None
        
        # Try to load config file
        if config_path and os.path.exists(config_path):
            self.load_config(config_path)
        else:
            # Try default locations
            for location in DEFAULT_CONFIG_LOCATIONS:
                path = os.path.expanduser(location)
                if os.path.exists(path):
                    self.load_config(path)
                    break
            else:
                print(f"Warning: No configuration file found, using defaults.", file=sys.stderr)
    
    def load_config(self, config_path):
        """Load configuration from a TOML file"""
        try:
            config = toml.load(config_path)
            self.config.update(config)
            self.config_path = config_path
            print(f"Loaded configuration from {config_path}")
        except Exception as e:
            print(f"Error loading configuration from {config_path}: {e}", file=sys.stderr)
    
    def get(self, section, key=None, default=None):
        """
        Get a configuration value
        
        Args:
            section: Configuration section
            key: Configuration key within section
            default: Default value if not found
            
        Returns:
            Configuration value or default
        """
        if key is None:
            return self.config.get(section, default)
        
        section_data = self.config.get(section, {})
        return section_data.get(key, default)
    
    def get_path(self, key, default=None):
        """Get a path from the paths section"""
        return self.get("paths", key, default)
    
    def get_detection(self, key, default=None):
        """Get a value from the detection section"""
        return self.get("detection", key, default)
    
    def get_line_detection(self, key, default=None):
        """Get a value from the line_detection section"""
        return self.get("line_detection", key, default)
    
    def get_pressure(self, key, default=None):
        """Get a value from the pressure section"""
        return self.get("pressure", key, default)
    
    def get_plotting(self, key, default=None):
        """Get a value from the plotting section"""
        return self.get("plotting", key, default)
    
    def get_repair(self, key, default=None):
        """Get a value from the repair section"""
        return self.get("repair", key, default)
    
    def get_filtering(self, key, default=None):
        """Get a value from the filtering section"""
        return self.get("filtering", key, default)


# Create a singleton instance
_config = None


def get_config(config_path=None):
    """Get the global configuration instance"""
    global _config
    if _config is None:
        _config = GaugeConfig(config_path)
    return _config


if __name__ == "__main__":
    # Print default configuration when run directly
    config = get_config()
    
    # If a path is provided, load and print that configuration
    if len(sys.argv) > 1:
        config = GaugeConfig(sys.argv[1])
    
    import json
    print(json.dumps(config.config, indent=2))
