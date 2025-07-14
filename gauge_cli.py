#!/usr/bin/env python3
# /// script
# dependencies = [
#   "opencv-python",
#   "numpy",
#   "toml",
#   "matplotlib",
# ]
# requires-python = ">=3.12"
# ///
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

from gauge_lib import GaugeDetector, GaugeResult
from gauge_config import get_config
from gauge_plot import generate_plot, MATPLOTLIB_AVAILABLE


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
    # Arguments for time averaging (now enabled by default)
    parser.add_argument("--no-average", action="store_true",
                       help="Disable time-based averaging of results (averaging is enabled by default)")
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
        # Averaging is now enabled by default, disabled with --no-average
        average_enabled = not args.no_average
        generate_plot(
            detector.history, 
            args.plot_output, 
            args.time_window, 
            args.all_time,
            average_enabled,
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


if __name__ == "__main__":
    main()