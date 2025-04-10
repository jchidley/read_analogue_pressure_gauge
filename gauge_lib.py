#!/usr/bin/env python3
"""
Simplified Gauge Detection Library - Core functionality only
"""

import cv2
import numpy as np
import os
from datetime import datetime
from typing import Optional, Tuple, NamedTuple, Union

# Import configuration
from gauge_config import get_config


class GaugeResult(NamedTuple):
    """Stores essential gauge detection results"""

    angle: float
    center: Tuple[int, int]
    radius: int
    image_path: str
    timestamp: datetime
    pressure_psi: Union[float, None] = None
    pressure_bar: Union[float, None] = None


def angle_to_psi(angle, min_angle=None, max_angle=None, max_psi=None):
    """Convert angle to PSI"""
    config = get_config()
    
    # Use config values as defaults
    if min_angle is None:
        min_angle = config.get_pressure("min_angle")
    if max_angle is None:
        max_angle = config.get_pressure("max_angle")
    if max_psi is None:
        max_psi = config.get_pressure("max_psi")
    
    if angle < min_angle:
        return 0.0
    if angle > max_angle:
        return max_psi
    return round((angle - min_angle) * max_psi / (max_angle - min_angle), 2)


def angle_to_bar(angle, min_angle=None, max_angle=None, max_bar=None):
    """Convert angle to BAR"""
    config = get_config()
    
    # Use config values as defaults
    if min_angle is None:
        min_angle = config.get_pressure("min_angle")
    if max_angle is None:
        max_angle = config.get_pressure("max_angle")
    if max_bar is None:
        max_bar = config.get_pressure("max_bar")
    
    if angle < min_angle:
        return 0.0
    if angle > max_angle:
        return max_bar
    return round((angle - min_angle) * max_bar / (max_angle - min_angle), 2)


class GaugeDetector:
    """Simplified gauge detector that focuses on core functionality"""

    def __init__(self, debug_mode: bool = False, debug_dir: str = None, config_path: str = None):
        """Initialize the gauge detector with minimal parameters"""
        self.config = get_config(config_path)
        
        # Set defaults from config
        if debug_dir is None:
            debug_dir = self.config.get_path("default_debug_dir")
            
        self.debug_mode = debug_mode
        self.debug_dir = debug_dir
        if debug_mode and not os.path.exists(debug_dir):
            os.makedirs(debug_dir)

        # Core detection parameters from config
        self.binary_threshold = self.config.get_detection("binary_threshold")
        self.circle_params = {
            "param1": self.config.get_detection("param1"),
            "param2": self.config.get_detection("param2"),
            "minRadius": self.config.get_detection("min_radius"),
            "maxRadius": self.config.get_detection("max_radius"),
        }

        # Store results for tracking changes
        self.history = []

    def detect_gauge(self, image_path: str) -> Optional[GaugeResult]:
        """
        Detect gauge and needle angle in an image

        Args:
            image_path: Path to the image file

        Returns:
            GaugeResult object or None if detection failed
        """
        # Read image
        image = cv2.imread(str(image_path))
        if image is None:
            print(f"Error: Could not read image {image_path}")
            return None

        # Find gauge circle
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (9, 9), 0)
        circles = cv2.HoughCircles(
            blurred,
            cv2.HOUGH_GRADIENT,
            1,
            100,
            param1=self.circle_params["param1"],
            param2=self.circle_params["param2"],
            minRadius=self.circle_params["minRadius"],
            maxRadius=self.circle_params["maxRadius"],
        )

        if circles is None:
            print(f"No gauge found in {image_path}")
            return None

        # Get circle parameters
        x, y, radius = np.round(circles[0][0]).astype(int)
        center = (x, y)

        # Create binary image
        mask = np.zeros(gray.shape, dtype=np.uint8)
        cv2.circle(mask, center, radius, 255, -1)
        masked = cv2.bitwise_and(gray, gray, mask=mask)
        _, binary = cv2.threshold(
            masked, self.binary_threshold, 255, cv2.THRESH_BINARY_INV
        )

        if self.debug_mode:
            debug_path = os.path.join(
                self.debug_dir, f"{os.path.basename(image_path)}_1_binary.jpg"
            )
            cv2.imwrite(debug_path, binary)

        # Line detection parameters from config
        canny_low = self.config.get_line_detection("canny_low")
        canny_high = self.config.get_line_detection("canny_high")
        hough_threshold = self.config.get_line_detection("hough_threshold")
        min_line_length = radius * self.config.get_line_detection("min_line_length_factor")
        max_line_gap = self.config.get_line_detection("max_line_gap")
        
        # Find lines
        edges = cv2.Canny(binary, canny_low, canny_high)
        lines = cv2.HoughLinesP(
            edges, 1, np.pi / 180, hough_threshold, 
            minLineLength=min_line_length, maxLineGap=max_line_gap
        )

        if lines is None or len(lines) == 0:
            print(f"No lines found in {image_path}")
            return None

        # Line filtering parameters from config
        line_center_distance_factor = self.config.get_line_detection("line_center_distance_factor")
        
        # Filter lines that pass near center
        good_lines = []
        for line in lines:
            x1, y1, x2, y2 = line[0]

            # Calculate distance from center to line
            line_len = np.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
            if line_len == 0:
                continue

            v1x, v1y = x - x1, y - y1
            v2x, v2y = x2 - x1, y2 - y1
            dist_to_line = abs(v1x * v2y - v1y * v2x) / line_len

            # Calculate direction from center to endpoints
            dist1 = np.sqrt((x1 - x) ** 2 + (y1 - y) ** 2)
            dist2 = np.sqrt((x2 - x) ** 2 + (y2 - y) ** 2)
            angle = np.degrees(np.arctan2(y2 - y1, x2 - x1)) % 180

            # Determine direction
            if dist1 > dist2:
                direction = np.degrees(np.arctan2(y1 - y, x1 - x))
            else:
                direction = np.degrees(np.arctan2(y2 - y, x2 - x))
            if direction < 0:
                direction += 360

            if dist_to_line < radius * line_center_distance_factor:
                good_lines.append(
                    {"line": line[0], "angle": angle, "direction": direction}
                )

        if not good_lines:
            print(f"No valid lines found in {image_path}")
            return None

        if self.debug_mode:
            # Draw all valid lines
            all_lines = image.copy()
            cv2.circle(all_lines, center, radius, (0, 255, 0), 2)
            for line_data in good_lines:
                line = line_data["line"]
                cv2.line(
                    all_lines, (line[0], line[1]), (line[2], line[3]), (0, 0, 255), 1
                )
            debug_path = os.path.join(
                self.debug_dir, f"{os.path.basename(image_path)}_2_all_lines.jpg"
            )
            cv2.imwrite(debug_path, all_lines)

        # Angle grouping threshold from config
        angle_grouping_threshold = self.config.get_line_detection("angle_grouping_threshold")
        
        # Group lines by angle
        good_lines.sort(key=lambda x: x["angle"])
        groups = []
        current_group = [good_lines[0]]

        for i in range(1, len(good_lines)):
            if abs(good_lines[i]["angle"] - current_group[0]["angle"]) < angle_grouping_threshold:
                current_group.append(good_lines[i])
            else:
                groups.append(current_group)
                current_group = [good_lines[i]]

        groups.append(current_group)
        groups.sort(key=lambda g: len(g), reverse=True)

        # Find direction quadrant
        directions = [line_data["direction"] for line_data in groups[0]]
        quadrants = [0, 0, 0, 0]
        for dir_angle in directions:
            quadrant = int(dir_angle // 90)
            quadrants[quadrant] += 1

        most_common_quadrant = quadrants.index(max(quadrants))
        likely_direction = most_common_quadrant * 90 + 45

        # Calculate bisector
        best_group = groups[0]
        avg_angle = sum(line_data["angle"] for line_data in best_group) / len(
            best_group
        )
        angle_rad = np.radians(avg_angle)

        # Unit vectors
        unit_x, unit_y = np.cos(angle_rad), np.sin(angle_rad)

        # Create bisector line
        b1_x = int(x - radius * unit_x)
        b1_y = int(y - radius * unit_y)
        b2_x = int(x + radius * unit_x)
        b2_y = int(y + radius * unit_y)

        # Get correct direction
        dir1 = np.degrees(np.arctan2(b1_y - y, b1_x - x)) % 360
        dir2 = np.degrees(np.arctan2(b2_y - y, b2_x - x)) % 360

        # Choose direction closer to likely direction
        diff1 = min(
            abs(dir1 - likely_direction),
            abs(dir1 - likely_direction + 360),
            abs(dir1 - likely_direction - 360),
        )
        diff2 = min(
            abs(dir2 - likely_direction),
            abs(dir2 - likely_direction + 360),
            abs(dir2 - likely_direction - 360),
        )

        if diff1 < diff2:
            needle_angle = dir1
            needle_end = (b1_x, b1_y)
        else:
            needle_angle = dir2
            needle_end = (b2_x, b2_y)

        # Try to parse timestamp from filename, otherwise use current time
        try:
            filename = os.path.basename(image_path)
            import re

            match = re.search(r"(\d{6})_(\d{4})", filename)
            if match:
                date_str, time_str = match.groups()
                year = 2000 + int(date_str[0:2])
                month = int(date_str[2:4])
                day = int(date_str[4:6])
                hour = int(time_str[0:2])
                minute = int(time_str[2:4])
                timestamp = datetime(year, month, day, hour, minute)
            else:
                timestamp = datetime.now()
        except:
            timestamp = datetime.now()

        # Calculate pressure values using config values
        pressure_psi = angle_to_psi(needle_angle)
        pressure_bar = angle_to_bar(needle_angle)

        # Create result object
        result = GaugeResult(
            angle=needle_angle,
            center=center,
            radius=radius,
            image_path=str(image_path),
            timestamp=timestamp,
            pressure_psi=pressure_psi,
            pressure_bar=pressure_bar
        )

        # Store in history
        self.history.append(result)

        if self.debug_mode:
            # Create final result image
            result_img = image.copy()
            cv2.circle(result_img, center, radius, (0, 255, 0), 2)

            # Draw group lines
            for line_data in best_group:
                line = line_data["line"]
                cv2.line(
                    result_img, (line[0], line[1]), (line[2], line[3]), (0, 0, 255), 1
                )

            # Draw needle direction
            cv2.arrowedLine(
                result_img, center, needle_end, (255, 0, 0), 2, tipLength=0.1
            )

            # Add text
            cv2.putText(
                result_img,
                f"Angle: {needle_angle:.1f}° (PSI: {pressure_psi:.1f}, BAR: {pressure_bar:.2f})",
                (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (255, 255, 255),
                2,
            )

            debug_path = os.path.join(
                self.debug_dir, f"{os.path.basename(image_path)}_result.jpg"
            )
            cv2.imwrite(debug_path, result_img)

        return result

    def get_angle_change(self, first_idx=-2, second_idx=-1):
        """Calculate angle change between two detections"""
        if len(self.history) < 2:
            return None

        try:
            first = self.history[first_idx]
            second = self.history[second_idx]

            # Calculate smallest angle between the two readings
            change = (second.angle - first.angle) % 360
            if change > 180:
                change -= 360

            return change
        except IndexError:
            return None

    def get_angle_change_rate(self, first_idx=-2, second_idx=-1):
        """Calculate rate of angle change in degrees per minute"""
        if len(self.history) < 2:
            return None

        try:
            first = self.history[first_idx]
            second = self.history[second_idx]

            # Calculate time difference in minutes
            time_diff = (second.timestamp - first.timestamp).total_seconds() / 60

            if time_diff == 0:
                return 0

            # Calculate angle change
            change = self.get_angle_change(first_idx, second_idx)
            if change is None:
                return None

            return change / time_diff
        except IndexError:
            return None

# Simple function for backward compatibility with minimal-gauge-detector.py
def detect_gauge(image_path, debug=False):
    """Simple wrapper function to match original interface"""
    detector = GaugeDetector(debug_mode=debug)
    result = detector.detect_gauge(image_path)
    return result.angle if result else None


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python gauge_lib.py <image_path>")
        sys.exit(1)

    angle = detect_gauge(sys.argv[1], debug=True)
    if angle is not None:
        print(f"Needle angle: {angle:.1f}°")
