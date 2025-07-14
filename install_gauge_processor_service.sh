#!/bin/bash
# Install the gauge processor service on Raspberry Pi

echo "Installing Gauge Processor Service..."

# Check if running as root or with sudo
if [ "$EUID" -ne 0 ]; then 
    echo "Please run with sudo: sudo bash install_gauge_processor_service.sh"
    exit 1
fi

# Copy the processing script
echo "Copying processing script..."
cp continuous_gauge_processor.sh /home/jack/continuous_gauge_processor.sh
chown jack:jack /home/jack/continuous_gauge_processor.sh
chmod +x /home/jack/continuous_gauge_processor.sh

# Copy the service file
echo "Installing systemd service..."
cp gauge_processor.service /etc/systemd/system/gauge_processor.service

# Reload systemd
echo "Reloading systemd..."
systemctl daemon-reload

# Enable the service to start at boot
echo "Enabling service..."
systemctl enable gauge_processor.service

# Start the service
echo "Starting service..."
systemctl start gauge_processor.service

# Check status
echo ""
echo "Service status:"
systemctl status gauge_processor.service --no-pager

echo ""
echo "Installation complete!"
echo ""
echo "Useful commands:"
echo "  View logs:    sudo journalctl -u gauge_processor.service -f"
echo "  Stop service: sudo systemctl stop gauge_processor.service"
echo "  Start service: sudo systemctl start gauge_processor.service"
echo "  Restart service: sudo systemctl restart gauge_processor.service"
echo "  Disable service: sudo systemctl disable gauge_processor.service"