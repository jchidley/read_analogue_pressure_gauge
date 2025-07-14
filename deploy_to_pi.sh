#!/bin/bash
# Complete deployment script for Raspberry Pi gauge monitoring system

# Configuration
PI_HOST="${PI_HOST:-jack@pi4light}"
PI_USER=$(echo $PI_HOST | cut -d@ -f1)

echo "Deploying Gauge Monitoring System to $PI_HOST..."

# Check SSH connection
if ! ssh -o ConnectTimeout=5 $PI_HOST "echo 'SSH connection successful'" &>/dev/null; then
    echo "Error: Cannot connect to $PI_HOST"
    echo "Please check your SSH connection and try again"
    exit 1
fi

# Copy all required files
echo "Copying files to Raspberry Pi..."
scp -q capture_images.sh \
    continuous_gauge_processor.sh \
    gauge_processor.service \
    install_gauge_processor_service.sh \
    gauge_cli.py \
    gauge_lib.py \
    gauge_config.py \
    gauge_plot.py \
    filter_large_angles.py \
    gauge_config.toml \
    $PI_HOST:~/

# Execute deployment on Pi
ssh $PI_HOST 'bash -s' << 'EOF'
set -e

echo "Installing system dependencies..."
# Check if dependencies are installed
DEPS_NEEDED=""
command -v sqlite3 >/dev/null 2>&1 || DEPS_NEEDED="$DEPS_NEEDED sqlite3"
command -v pigpiod >/dev/null 2>&1 || DEPS_NEEDED="$DEPS_NEEDED pigpio python3-pigpio"
command -v rpicam-jpeg >/dev/null 2>&1 || DEPS_NEEDED="$DEPS_NEEDED libcamera-apps"

if [ -n "$DEPS_NEEDED" ]; then
    echo "Installing: $DEPS_NEEDED"
    sudo apt-get update -qq
    sudo apt-get install -y -qq $DEPS_NEEDED
fi

# Install uv if not present
if ! command -v uv >/dev/null 2>&1; then
    echo "Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    source ~/.bashrc
fi

# Create required directories
mkdir -p ~/dial_images

# Make scripts executable
chmod +x capture_images.sh continuous_gauge_processor.sh install_gauge_processor_service.sh

# Update capture service if it exists
if systemctl is-enabled dial_capture.service &>/dev/null; then
    echo "Updating capture service..."
    sudo systemctl restart dial_capture.service
    echo "Capture service restarted"
else
    echo "Warning: dial_capture.service not found - you may need to set it up manually"
fi

# Install/update processor service
echo "Installing processor service..."
sudo bash install_gauge_processor_service.sh

# Show status
echo ""
echo "=== Deployment Complete ==="
echo ""
echo "Service Status:"
sudo systemctl status dial_capture.service gauge_processor.service --no-pager | grep -E "(●|Active:|Main PID:)"

echo ""
echo "Recent images:"
ls -lt dial_images/*.jpg 2>/dev/null | head -3 || echo "No images found yet"

echo ""
echo "Database status:"
if [ -f gauge_data.db ]; then
    sqlite3 gauge_data.db "SELECT COUNT(*) || ' images processed' FROM gauge_results;"
else
    echo "Database not yet created"
fi

echo ""
echo "Useful commands:"
echo "  Watch logs:     sudo journalctl -u gauge_processor.service -f"
echo "  Check status:   sudo systemctl status gauge_processor.service"
echo "  View results:   sqlite3 gauge_data.db 'SELECT * FROM gauge_results ORDER BY timestamp DESC LIMIT 5;'"
EOF

echo ""
echo "Deployment completed successfully!"
echo "You can monitor the services with:"
echo "  ssh $PI_HOST 'sudo journalctl -u gauge_processor.service -f'"