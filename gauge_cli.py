#!/usr/bin/env python3
"""
Command-line tool for gauge image processing using SQLite for storage
"""

import os
import sys
import glob
import argparse
import sqlite3
import shutil
from datetime import datetime, timedelta
import math

# Make matplotlib optional
try:
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False

from gauge_lib import GaugeDetector, GaugeResult
from gauge_config import get_config


def main():
    """Main entry point for the tool"""
    # Get configuration
    config = get_config()
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Process gauge images and detect angle changes")
    parser.add_argument("--dir", default=config.get_path("default_image_dir"), 
                        help=f"Directory containing gauge images (default: {config.get_path('default_image_dir')})")
    parser.add_argument("--pattern", default=config.get_path("default_image_pattern"), 
                        help=f"File pattern to match (default: {config.get_path('default_image_pattern')})")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    parser.add_argument("--debug-dir", default=config.get_path("default_debug_dir"), 
                        help=f"Directory for debug images (default: {config.get_path('default_debug_dir')})")
    parser.add_argument("--db", default=config.get_path("default_db_file"), 
                        help=f"SQLite database file (default: {config.get_path('default_db_file')})")
    parser.add_argument("--plot", action="store_true", help="Generate plots (requires matplotlib)")
    parser.add_argument("--plot-output", default=config.get_path("default_plot_output"), 
                        help=f"Plot output path (default: {config.get_path('default_plot_output')})")
    parser.add_argument("--threshold", type=int, default=config.get_detection("binary_threshold"), 
                        help=f"Binary threshold value (default: {config.get_detection('binary_threshold')})")
    parser.add_argument("--min-radius", type=int, default=config.get_detection("min_radius"), 
                        help=f"Minimum gauge radius in pixels (default: {config.get_detection('min_radius')})")
    parser.add_argument("--max-radius", type=int, default=config.get_detection("max_radius"), 
                        help=f"Maximum gauge radius in pixels (default: {config.get_detection('max_radius')})")
    parser.add_argument("--change-threshold", type=float, default=config.get_detection("change_threshold"), 
                        help=f"Minimum significant angle change (default: {config.get_detection('change_threshold')})")
    parser.add_argument("--force", action="store_true", help="Force processing all images")
    parser.add_argument("--retry-failures", action="store_true", help="Retry failed detections")
    parser.add_argument("--new-only", action="store_true", 
                       help="Plot only new results instead of all results (default: all results)")
    # New arguments for time window
    parser.add_argument("--time-window", type=int, default=config.get_plotting("default_time_window"), 
                       help=f"Number of days to include in plots (default: {config.get_plotting('default_time_window')} days)")
    parser.add_argument("--all-time", action="store_true",
                       help="Plot all data regardless of time window")
    # Arguments for time averaging
    parser.add_argument("--average", action="store_true",
                       help="Enable time-based averaging of results")
    parser.add_argument("--average-period", type=str, default=config.get_plotting("default_average_period"),
                       help=f"Period for averaging: 'minute', 'hour', 'day' (default: {config.get_plotting('default_average_period')})")
    parser.add_argument("--average-value", type=int, default=config.get_plotting("default_average_value"),
                       help=f"Number of periods to average (default: {config.get_plotting('default_average_value')})")
    parser.add_argument("--pressure-unit", type=str, default=config.get_plotting("default_pressure_unit"), 
                       choices=["angle", "psi", "bar"],
                       help=f"Unit for plotting: 'angle', 'psi', 'bar' (default: {config.get_plotting('default_pressure_unit')})")
    # Add config path argument
    parser.add_argument("--config", type=str, default=None,
                       help="Path to configuration file")
    args = parser.parse_args()

    # Create database if it doesn't exist
    db_conn = get_db_connection(args.db)
    
    # Get list of image files
    image_pattern = os.path.join(args.dir, args.pattern)
    image_files = sorted(glob.glob(image_pattern))
    if not image_files:
        print(f"No images found matching pattern '{image_pattern}'")
        db_conn.close()
        sys.exit(1)

    # Read successful detections and failures
    existing_results = get_existing_results(db_conn, args.force)
    failed_images = get_failures(db_conn, args.force)

    # Determine which images to process
    images_to_process = []
    if args.force:
        images_to_process = image_files
        print(f"Forcing processing of all {len(image_files)} images")
    else:
        # Skip images that are successfully processed or failed (if not retrying)
        images_to_skip = set(existing_results.keys())
        if not args.retry_failures:
            images_to_skip.update(failed_images)
        else:
            print(f"Will retry {len(failed_images)} previously failed detections")

        images_to_process = [img for img in image_files if os.path.basename(img) not in images_to_skip]
        print(f"Found {len(image_files)} total images, {len(images_to_process)} need processing, "
              f"{len(image_files) - len(images_to_process)} skipped")

    # Create and configure detector
    detector = GaugeDetector(debug_mode=args.debug, debug_dir=args.debug_dir, config_path=args.config)
    detector.binary_threshold = args.threshold
    detector.circle_params["minRadius"] = args.min_radius
    detector.circle_params["maxRadius"] = args.max_radius

    # Process images
    new_results = []
    new_failures = []

    for i, img_path in enumerate(images_to_process):
        img_name = os.path.basename(img_path)
        print(f"Processing {i + 1}/{len(images_to_process)}: {img_name}")

        result = detector.detect_gauge(img_path)
        if result:
            new_results.append(result)

            # If previously failed but now successful, remove from failures
            if img_name in failed_images:
                failed_images.remove(img_name)
                db_conn.execute("DELETE FROM detection_failures WHERE image_name = ?", (img_name,))

            # Print angle and calculate changes if there's history
            if len(detector.history) > 1:
                change = detector.get_angle_change(-2, -1)
                rate = detector.get_angle_change_rate(-2, -1)
                significant = abs(change) >= args.change_threshold if change else False
                marker = "* " if significant else "  "
                print(f"  Angle: {result.angle:.1f}°, Change: {marker}{change:.2f}°, Rate: {rate:.2f}°/min")
            else:
                print(f"  Angle: {result.angle:.1f}°")
        else:
            print(f"  Failed to detect gauge in {img_name}")
            new_failures.append(img_name)

    # Save results to database
    if new_results:
        save_results(db_conn, new_results)
    
    # Update failure records
    if new_failures:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        for img_name in new_failures:
            db_conn.execute("INSERT OR REPLACE INTO detection_failures (image_name, timestamp) VALUES (?, ?)",
                           (img_name, timestamp))
        db_conn.commit()
        print(f"Updated {len(new_failures)} failure records")

    # Load results for visualization
    if args.plot:
        # Determine what to load based on flags
        if args.new_only and detector.history:
            print(f"Using only new results for visualization ({len(detector.history)} results)")
        else:
            # Clear history and load data with time window if needed
            detector.history = []
            if args.all_time:
                print("Loading all results for visualization")
                load_results_for_visualization(detector, db_conn, args.dir)
            else:
                print(f"Loading results from the past {args.time_window} days for visualization")
                cutoff_date = datetime.now() - timedelta(days=args.time_window)
                load_results_for_visualization(detector, db_conn, args.dir, cutoff_date)
            
            print(f"Loaded {len(detector.history)} results for visualization")

    # Generate plots if requested
    if args.plot and detector.history and MATPLOTLIB_AVAILABLE:
        generate_plot(
            detector.history, 
            args.plot_output, 
            args.time_window, 
            args.all_time,
            args.average,
            args.average_period,
            args.average_value,
            args.pressure_unit
        )
    elif args.plot and not MATPLOTLIB_AVAILABLE:
        print("Warning: Plotting requires matplotlib library")

    # Print summary
    count = db_conn.execute("SELECT COUNT(*) FROM gauge_results").fetchone()[0]
    print(f"\nProcessing summary:")
    print(f"  Total images: {len(image_files)}")
    print(f"  Processed this run: {len(images_to_process)}")
    print(f"  Successfully processed: {len(new_results)}")
    print(f"  Failed detections: {len(new_failures)}")
    print(f"  Total successful detections: {count}")
    
    # Close the database connection
    db_conn.close()


def get_db_connection(db_file):
    """Connect to SQLite database and create tables if needed"""
    # Create backup of existing database
    if os.path.exists(db_file):
        try:
            shutil.copy2(db_file, f"{db_file}.bak")
        except Exception as e:
            print(f"Warning: Could not create backup: {e}")
    
    conn = sqlite3.connect(db_file)
    conn.row_factory = sqlite3.Row
    
    # Create tables if they don't exist
    conn.executescript('''
    CREATE TABLE IF NOT EXISTS gauge_results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        image_name TEXT UNIQUE,
        angle REAL,
        center_x INTEGER,
        center_y INTEGER,
        radius INTEGER,
        timestamp TEXT,
        pressure_psi REAL,
        pressure_bar REAL
    );
    
    CREATE TABLE IF NOT EXISTS detection_failures (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        image_name TEXT UNIQUE,
        timestamp TEXT
    );
    ''')
    
    return conn


def get_existing_results(conn, force=False):
    """Read existing successful detections from database"""
    results = {}
    if not force:
        for row in conn.execute("SELECT * FROM gauge_results"):
            results[row['image_name']] = {
                'Image': row['image_name'],
                'Angle': row['angle'],
                'Center_X': row['center_x'],
                'Center_Y': row['center_y'],
                'Radius': row['radius'],
                'Timestamp': row['timestamp']
            }
        print(f"Found {len(results)} successful detections in database")
    return results


def get_failures(conn, force=False):
    """Read detection failures from database"""
    failed_images = set()
    if not force:
        for row in conn.execute("SELECT image_name FROM detection_failures"):
            failed_images.add(row['image_name'])
        print(f"Found {len(failed_images)} known detection failures")
    return failed_images

def save_results(conn, results):
    """Save gauge detection results to database with data validation and pressure values"""
    from gauge_lib import angle_to_psi, angle_to_bar
    
    valid_results = 0
    invalid_results = 0
    
    # Get configuration for pressure conversion
    config = get_config()
    min_angle = config.get_pressure("min_angle")
    max_angle = config.get_pressure("max_angle")
    max_psi = config.get_pressure("max_psi")
    max_bar = config.get_pressure("max_bar")
    
    for result in results:
        img_name = os.path.basename(result.image_path)
        timestamp_str = result.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        
        # Validate data before storing
        try:
            # Validate angle
            angle = float(result.angle)
            
            # Validate center coordinates
            if not isinstance(result.center, tuple) or len(result.center) != 2:
                print(f"Warning: Invalid center format for {img_name} - skipping")
                invalid_results += 1
                continue
                
            center_x = int(result.center[0])
            center_y = int(result.center[1])
            
            # Validate radius
            radius = int(result.radius)
            
            # Additional sanity checks
            if center_x <= 0 or center_y <= 0 or radius <= 0:
                print(f"Warning: Invalid geometry values for {img_name} - skipping")
                invalid_results += 1
                continue
            
            # Calculate pressure values with config values
            pressure_psi = angle_to_psi(angle, min_angle, max_angle, max_psi)
            pressure_bar = angle_to_bar(angle, min_angle, max_angle, max_bar)
                
            # All validations passed, store to database
            conn.execute('''
            INSERT OR REPLACE INTO gauge_results 
            (image_name, angle, center_x, center_y, radius, timestamp, pressure_psi, pressure_bar) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (img_name, angle, center_x, center_y, radius, timestamp_str, pressure_psi, pressure_bar))
            
            valid_results += 1
            
        except (ValueError, TypeError) as e:
            print(f"Warning: Invalid data for {img_name}: {e} - skipping")
            invalid_results += 1
            continue
    
    conn.commit()
    print(f"Saved {valid_results} valid results to database ({invalid_results} skipped due to validation errors)")

def load_results_for_visualization(detector, conn, image_dir, cutoff_date=None):
    """Load existing results for visualization with improved error handling and pressure value loading"""
    from gauge_lib import angle_to_psi, angle_to_bar
    config = get_config()
    
    all_results = []
    skipped_results = 0
    
    # Build query based on whether we have a cutoff date
    query = "SELECT * FROM gauge_results ORDER BY timestamp"
    params = ()
    
    if cutoff_date:
        query = "SELECT * FROM gauge_results WHERE timestamp >= ? ORDER BY timestamp"
        params = (cutoff_date.strftime("%Y-%m-%d %H:%M:%S"),)
    
    # Get default repair values from config
    default_center_x = config.get_repair("default_center_x")
    default_center_y = config.get_repair("default_center_y")
    default_radius = config.get_repair("default_radius")
    default_angle = config.get_repair("default_angle")
    
    for row in conn.execute(query, params):
        try:
            # Handle potential binary data more robustly
            timestamp = datetime.strptime(row['timestamp'], "%Y-%m-%d %H:%M:%S")
            path = os.path.join(image_dir, row['image_name'])
            
            # Handle angle values
            try:
                angle = float(row['angle'])
            except (ValueError, TypeError):
                print(f"Warning: Skipping {row['image_name']}: Invalid angle value '{row['angle']}'")
                skipped_results += 1
                continue
                
            # Handle center_x binary data
            try:
                if isinstance(row['center_x'], bytes):
                    # Try to interpret binary data as little-endian integer
                    # The [:4] takes first 4 bytes for a 32-bit integer
                    center_x = int.from_bytes(row['center_x'][:4], byteorder='little')
                    print(f"Note: Converted binary center_x for {row['image_name']}: {row['center_x']} -> {center_x}")
                else:
                    center_x = int(row['center_x'])
            except (ValueError, TypeError):
                print(f"Warning: Using default for {row['image_name']}: Cannot interpret center_x '{row['center_x']}'")
                center_x = default_center_x
                
            # Handle center_y binary data
            try:
                if isinstance(row['center_y'], bytes):
                    # Try to interpret binary data as little-endian integer
                    center_y = int.from_bytes(row['center_y'][:4], byteorder='little')
                    print(f"Note: Converted binary center_y for {row['image_name']}: {row['center_y']} -> {center_y}")
                else:
                    center_y = int(row['center_y'])
            except (ValueError, TypeError):
                print(f"Warning: Using default for {row['image_name']}: Cannot interpret center_y '{row['center_y']}'")
                center_y = default_center_y
                    
            # Handle radius values
            try:
                if isinstance(row['radius'], bytes):
                    # Try to interpret binary data as little-endian integer
                    radius = int.from_bytes(row['radius'][:4], byteorder='little')
                    print(f"Note: Converted binary radius for {row['image_name']}: {row['radius']} -> {radius}")
                else:
                    radius = int(row['radius'])
            except (ValueError, TypeError):
                print(f"Warning: Using default for {row['image_name']}: Invalid radius value '{row['radius']}'")
                radius = default_radius
            
            # Additional validation check
            if center_x <= 0 or center_y <= 0 or radius <= 0:
                print(f"Warning: Using defaults for {row['image_name']}: Center or radius values out of range")
                if center_x <= 0:
                    center_x = default_center_x
                if center_y <= 0:
                    center_y = default_center_y
                if radius <= 0:
                    radius = default_radius
            
            # Handle pressure values
            try:
                # Try to get pressure values from the database
                if 'pressure_psi' in row.keys() and row['pressure_psi'] is not None:
                    pressure_psi = float(row['pressure_psi'])
                else:
                    # Calculate if not in database
                    pressure_psi = angle_to_psi(angle)
                    
                if 'pressure_bar' in row.keys() and row['pressure_bar'] is not None:
                    pressure_bar = float(row['pressure_bar'])
                else:
                    # Calculate if not in database
                    pressure_bar = angle_to_bar(angle)
            except (ValueError, TypeError):
                # If we can't parse the values from the database, calculate them
                pressure_psi = angle_to_psi(angle)
                pressure_bar = angle_to_bar(angle)
            
            result = GaugeResult(
                angle=angle,
                center=(center_x, center_y),
                radius=radius,
                image_path=path,
                timestamp=timestamp,
                pressure_psi=pressure_psi,
                pressure_bar=pressure_bar
            )
            all_results.append(result)
        except Exception as e:
            print(f"Warning: Could not load result for {row['image_name']}: {e}")
            skipped_results += 1
    
    # Sort and add to detector history
    all_results.sort(key=lambda r: r.timestamp)
    detector.history.extend(all_results)
    
    print(f"Loaded {len(all_results)} results for visualization ({skipped_results} skipped due to data issues)")
    return len(all_results)

def average_results(history, period='hour', value=1):
    """
    Average results over specified time periods
    
    Args:
        history: List of GaugeResult objects
        period: 'minute', 'hour', or 'day'
        value: Number of periods to average
        
    Returns:
        Tuple of (timestamps, angles) with averaged data
    """
    if not history:
        return [], []
    
    # Sort history by timestamp (should already be sorted)
    sorted_history = sorted(history, key=lambda r: r.timestamp)
    
    # Function to get the period start time
    def get_period_start(dt):
        if period == 'minute':
            # Round to nearest X minutes
            minute_group = (dt.minute // value) * value
            return dt.replace(minute=minute_group, second=0, microsecond=0)
        elif period == 'hour':
            # Round to nearest X hours
            hour_group = (dt.hour // value) * value
            return dt.replace(hour=hour_group, minute=0, second=0, microsecond=0)
        elif period == 'day':
            # Round to X days
            day_offset = dt.day % value
            if day_offset == 0:
                day_offset = value
            new_day = dt.day - day_offset + 1
            return dt.replace(day=new_day, hour=0, minute=0, second=0, microsecond=0)
        else:
            # Default fallback - no averaging
            return dt
    
    # Group by time period
    periods = {}
    for result in sorted_history:
        period_start = get_period_start(result.timestamp)
        if period_start not in periods:
            periods[period_start] = []
        periods[period_start].append(result)
    
    # Calculate averages for each period
    avg_timestamps = []
    avg_angles = []
    
    for period_start, results in sorted(periods.items()):
        avg_angle = sum(r.angle for r in results) / len(results)
        # Use the middle of the period as the timestamp for better visualization
        if period == 'minute':
            mid_timestamp = period_start + timedelta(minutes=value/2)
        elif period == 'hour':
            mid_timestamp = period_start + timedelta(hours=value/2)
        elif period == 'day':
            mid_timestamp = period_start + timedelta(days=value/2)
        else:
            mid_timestamp = period_start
            
        avg_timestamps.append(mid_timestamp)
        avg_angles.append(avg_angle)
    
    return avg_timestamps, avg_angles


def generate_plot(history, output_path, time_window=7, all_time=False, average=False, avg_period='hour', avg_value=1, pressure_unit='angle'):
    """Generate time-series plot using matplotlib with time window options and averaging"""
    config = get_config()
    
    try:
        fig, ax = plt.subplots(figsize=(12, 7))
        
        # Get raw data points
        raw_timestamps = [r.timestamp for r in history]
        raw_angles = [r.angle for r in history]
        
        # Default to PSI if no unit specified
        if pressure_unit == 'angle':
            # When displaying angle
            y_values = raw_angles
            y_label = "Angle (degrees)"
            plot_color = 'b'
            
            # Apply averaging if requested
            if average and history:
                timestamps, values = average_results(history, avg_period, avg_value)
                # Use different style for averaged data
                line_style = f"{plot_color}-"
                marker = "o"
                markersize = 6
                label = f"Averaged (per {avg_value} {avg_period}{'s' if avg_value > 1 else ''})"
                # Also plot the raw data with lighter style
                ax.plot(raw_timestamps, y_values, "c.", markersize=3, alpha=0.3, label="Raw data")
            else:
                timestamps = raw_timestamps
                values = y_values
                line_style = f"{plot_color}-"
                marker = "o"
                markersize = 4
                label = "Gauge readings"
                
            # Plot the data
            ax.plot(timestamps, values, line_style, marker=marker, markersize=markersize, label=label)
            
        elif pressure_unit == 'psi':
            # Use the angle_to_psi function to convert angles to PSI
            from gauge_lib import angle_to_psi
            raw_values = [angle_to_psi(angle) for angle in raw_angles]
            y_label = "Pressure (PSI)"
            plot_color = 'r'
            
            # Apply averaging if requested
            if average and history:
                # First convert angles to pressure values
                for r in history:
                    if not hasattr(r, 'pressure_psi') or r.pressure_psi is None:
                        r = r._replace(pressure_psi=angle_to_psi(r.angle))
                
                # Then average the pressure values
                timestamps, angles = average_results(history, avg_period, avg_value)
                values = [angle_to_psi(a) for a in angles]
                
                # Use different style for averaged data
                line_style = f"{plot_color}-"
                marker = "o"
                markersize = 6
                label = f"Averaged (per {avg_value} {avg_period}{'s' if avg_value > 1 else ''})"
                # Also plot the raw data with lighter style
                ax.plot(raw_timestamps, raw_values, "salmon", markersize=3, alpha=0.3, label="Raw data")
            else:
                timestamps = raw_timestamps
                values = raw_values
                line_style = f"{plot_color}-"
                marker = "o"
                markersize = 4
                label = "Pressure (PSI)"
            
            # Plot the data
            ax.plot(timestamps, values, line_style, marker=marker, markersize=markersize, label=label)
            
            # Set appropriate y-tick intervals based on range
            if values:
                max_psi = max(values)
                if max_psi > 30:
                    # For larger ranges, use divisions of 10
                    ax.yaxis.set_major_locator(plt.MultipleLocator(10))
                else:
                    # For smaller ranges, use divisions of 2
                    ax.yaxis.set_major_locator(plt.MultipleLocator(2))
                
                # Set reasonable y limits starting from 0
                min_pressure = 0
                max_pressure = max_psi * 1.1  # Add 10% padding
                ax.set_ylim(min_pressure, max_pressure)
            
        elif pressure_unit == 'bar':
            # Use the angle_to_bar function to convert angles to BAR
            from gauge_lib import angle_to_bar
            raw_values = [angle_to_bar(angle) for angle in raw_angles]
            y_label = "Pressure (BAR)"
            plot_color = 'g'
            
            # Apply averaging if requested
            if average and history:
                # First convert angles to pressure values
                for r in history:
                    if not hasattr(r, 'pressure_bar') or r.pressure_bar is None:
                        r = r._replace(pressure_bar=angle_to_bar(r.angle))
                
                # Then average the pressure values
                timestamps, angles = average_results(history, avg_period, avg_value)
                values = [angle_to_bar(a) for a in angles]
                
                # Use different style for averaged data
                line_style = f"{plot_color}-"
                marker = "o"
                markersize = 6
                label = f"Averaged (per {avg_value} {avg_period}{'s' if avg_value > 1 else ''})"
                # Also plot the raw data with lighter style
                ax.plot(raw_timestamps, raw_values, "lightgreen", markersize=3, alpha=0.3, label="Raw data")
            else:
                timestamps = raw_timestamps
                values = raw_values
                line_style = f"{plot_color}-"
                marker = "o"
                markersize = 4
                label = "Pressure (BAR)"
            
            # Plot the data
            ax.plot(timestamps, values, line_style, marker=marker, markersize=markersize, label=label)
            
            # Set y-tick intervals to 0.2 for BAR
            ax.yaxis.set_major_locator(plt.MultipleLocator(0.2))
            
            # Set reasonable y limits starting from 0
            if values:
                min_pressure = 0
                max_pressure = max(values) * 1.1  # Add 10% padding
                ax.set_ylim(min_pressure, max_pressure)
        
        # Set title based on the time window and averaging
        title_parts = []
        if all_time:
            title_parts.append(f"Gauge {pressure_unit.upper() if pressure_unit != 'angle' else 'Angle'} Over All Time")
        else:
            title_parts.append(f"Gauge {pressure_unit.upper() if pressure_unit != 'angle' else 'Angle'} Over Past {time_window} Days")
            
        if average:
            title_parts.append(f"Averaged Every {avg_value} {avg_period}{'s' if avg_value > 1 else ''}")
            
        ax.set_title(" - ".join(title_parts), fontsize=14)
        
        # Set axis labels
        ax.set_ylabel(y_label, fontsize=12, color=plot_color)
        ax.set_xlabel("Time", fontsize=12)
        ax.grid(True, linestyle='--', alpha=0.7)
        
        # Format x-axis dates
        if len(timestamps) > 20:
            # For many points, use a more compact date format
            date_format = "%m/%d\n%H:%M"
        else:
            # For fewer points, use a more detailed format
            date_format = "%Y-%m-%d\n%H:%M"
            
        ax.xaxis.set_major_formatter(mdates.DateFormatter(date_format))
        
        # Adjust number of ticks based on data range
        if len(timestamps) > 1:
            time_range = max(timestamps) - min(timestamps)
            if time_range.days > 14:
                # For longer periods, show fewer ticks
                ax.xaxis.set_major_locator(mdates.DayLocator(interval=max(1, time_range.days // 10)))
            elif time_range.days > 2:
                # For medium periods, show daily ticks
                ax.xaxis.set_major_locator(mdates.DayLocator())
            else:
                # For short periods, show hourly ticks
                ax.xaxis.set_major_locator(mdates.HourLocator(interval=4))
        
        plt.xticks(rotation=45, ha="right")
        
        # Add summary statistics
        if values:
            min_value = min(values)
            max_value = max(values)
            avg_value = sum(values) / len(values)
            
            stats_parts = []
            if average:
                stats_parts.append(f"Data points: {len(raw_timestamps)} raw, {len(timestamps)} averaged")
            else:
                stats_parts.append(f"Data points: {len(values)}")
                
            # Add appropriate unit suffix
            if pressure_unit == 'angle':
                unit_suffix = "°"
            elif pressure_unit == 'psi':
                unit_suffix = " PSI"
            elif pressure_unit == 'bar':
                unit_suffix = " BAR"
            
            stats_parts.append(f"Min: {min_value:.2f}{unit_suffix}  Max: {max_value:.2f}{unit_suffix}  Avg: {avg_value:.2f}{unit_suffix}")
            
            # Calculate standard deviation
            if len(values) > 1:
                std_dev = (sum((v - avg_value) ** 2 for v in values) / len(values)) ** 0.5
                stats_parts.append(f"Std Dev: {std_dev:.2f}{unit_suffix}")
                
            fig.text(0.5, 0.01, "  |  ".join(stats_parts), ha='center', fontsize=10)
        
        if average:
            plt.legend(loc='best')
            
        plt.tight_layout()
        plt.savefig(output_path, dpi=100)
        plt.close(fig)
        
        print(f"Generated plot: {output_path}")
    except Exception as e:
        print(f"Error generating plot: {e}")

if __name__ == "__main__":
    main()