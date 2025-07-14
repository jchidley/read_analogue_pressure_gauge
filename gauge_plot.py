#!/usr/bin/env python3
"""
Plotting utilities for gauge data visualization
"""

from datetime import datetime, timedelta

# Make matplotlib optional
try:
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False

from gauge_config import get_config


def average_results(history, period='hour', value=1):
    """
    Calculate min, max, and average results over specified time periods
    
    Args:
        history: List of GaugeResult objects
        period: 'minute', 'hour', or 'day'
        value: Number of periods to average
        
    Returns:
        Tuple of (timestamps, min_angles, max_angles, avg_angles) with statistics
    """
    if not history:
        return [], [], [], []
    
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
    
    # Calculate statistics for each period
    timestamps = []
    min_angles = []
    max_angles = []
    avg_angles = []
    
    for period_start, results in sorted(periods.items()):
        angles = [r.angle for r in results]
        min_angle = min(angles)
        max_angle = max(angles)
        avg_angle = sum(angles) / len(angles)
        
        # Use the middle of the period as the timestamp for better visualization
        if period == 'minute':
            mid_timestamp = period_start + timedelta(minutes=value/2)
        elif period == 'hour':
            mid_timestamp = period_start + timedelta(hours=value/2)
        elif period == 'day':
            mid_timestamp = period_start + timedelta(days=value/2)
        else:
            mid_timestamp = period_start
            
        timestamps.append(mid_timestamp)
        min_angles.append(min_angle)
        max_angles.append(max_angle)
        avg_angles.append(avg_angle)
    
    return timestamps, min_angles, max_angles, avg_angles


def plot_unit_data(ax, history, average, avg_period, avg_value, pressure_unit, 
                   raw_timestamps, raw_values, y_label, conversion_func=None):
    """
    Common plotting logic for all units
    
    Args:
        ax: matplotlib axis object
        history: List of GaugeResult objects
        average: Whether to use averaging
        avg_period: Period for averaging ('hour', 'day', etc.)
        avg_value: Number of periods to average
        pressure_unit: Unit type ('angle', 'psi', 'bar')
        raw_timestamps: Raw timestamp data
        raw_values: Raw value data (already converted to target unit)
        y_label: Y-axis label
        conversion_func: Optional function to convert angles to target unit
        
    Returns:
        tuple: (timestamps, max_values) for statistics and y-axis limits
    """
    if average and history:
        # Get min, max, avg angles
        timestamps, min_angles, max_angles, avg_angles = average_results(history, avg_period, avg_value)
        
        # Convert angles to target unit if needed
        if conversion_func:
            max_values = [conversion_func(a) for a in max_angles]
        else:
            max_values = max_angles
        
        # Plot only maximum line
        period_label = f"Maximum (per {avg_value} {avg_period}{'s' if avg_value > 1 else ''})"
        ax.plot(timestamps, max_values, 'r-', linewidth=2, label=period_label)
        
        # Also plot the raw data with lighter style
        ax.plot(raw_timestamps, raw_values, "b.", markersize=3, alpha=0.5, label="Raw data")
        
        return timestamps, max_values
    else:
        # No averaging - just plot raw data
        ax.plot(raw_timestamps, raw_values, "b-", marker="o", markersize=4, label=f"{y_label.replace(' (', ' readings (')}")
        return raw_timestamps, raw_values


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
            y_label = "Angle (degrees)"
            timestamps, values = plot_unit_data(
                ax, history, average, avg_period, avg_value, pressure_unit,
                raw_timestamps, raw_angles, y_label
            )
            
        elif pressure_unit == 'psi':
            # Use the angle_to_psi function to convert angles to PSI
            from gauge_lib import angle_to_psi
            raw_values = [angle_to_psi(angle) for angle in raw_angles]
            y_label = "Pressure (PSI)"
            
            timestamps, values = plot_unit_data(
                ax, history, average, avg_period, avg_value, pressure_unit,
                raw_timestamps, raw_values, y_label, angle_to_psi
            )
            
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
            
            timestamps, values = plot_unit_data(
                ax, history, average, avg_period, avg_value, pressure_unit,
                raw_timestamps, raw_values, y_label, angle_to_bar
            )
            
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
        ax.set_ylabel(y_label, fontsize=12)
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
            # Add appropriate unit suffix
            if pressure_unit == 'angle':
                unit_suffix = "°"
                raw_data = raw_angles
            elif pressure_unit == 'psi':
                unit_suffix = " PSI"
                raw_data = raw_values
            elif pressure_unit == 'bar':
                unit_suffix = " BAR"
                raw_data = raw_values
            
            stats_parts = []
            
            if average:
                # When averaging is enabled
                overall_max = max(values)
                raw_min = min(raw_data)
                raw_max = max(raw_data)
                stats_parts.append(f"Data points: {len(raw_timestamps)} raw, {len(timestamps)} time periods")
                stats_parts.append(f"Raw Range: {raw_min:.2f} - {raw_max:.2f}{unit_suffix}  |  Max per period: {overall_max:.2f}{unit_suffix}")
            else:
                # Original statistics for non-averaged data
                min_value = min(values)
                max_value = max(values)
                avg_value = sum(values) / len(values)
                
                stats_parts.append(f"Data points: {len(values)}")
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