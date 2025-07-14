#!/bin/bash
# Deploy updated capture_images.sh to Raspberry Pi

echo "Deploying updated capture_images.sh to pi4light..."

# Copy the updated script
scp capture_images.sh jack@pi4light.local:~/capture_images.sh

# Execute commands on the Pi
ssh jack@pi4light.local << 'EOF'
    echo "Checking current service status..."
    sudo systemctl status dial_capture.service --no-pager
    
    echo -e "\nRestarting dial_capture service..."
    sudo systemctl restart dial_capture.service
    
    echo -e "\nWaiting for service to start..."
    sleep 3
    
    echo -e "\nChecking new service status..."
    sudo systemctl status dial_capture.service --no-pager
    
    echo -e "\nShowing recent logs..."
    sudo journalctl -u dial_capture.service -n 20 --no-pager
EOF

echo -e "\nDeployment complete!"