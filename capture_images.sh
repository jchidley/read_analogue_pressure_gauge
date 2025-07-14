#!/bin/bash
# Make sure script is executable (chmod +x /home/jack/capture_images.sh)

# pigpiod is now started by systemd before this service

# Set frequency for PWM on GPIO 18
pigs pfs 18 800

# Change to the image storage directory
cd /home/jack/dial_images

while true; do
    # Get the current minute and second
    current_minute=$(date +"%M")
    current_second=$(date +"%S")
    
    # Remove leading zero for arithmetic
    current_minute=$((10#$current_minute))
    current_second=$((10#$current_second))
    
    # Calculate minutes until next capture time (00, 20, or 40)
    if [ $current_minute -lt 20 ]; then
        sleep_minutes=$((20 - current_minute))
    elif [ $current_minute -lt 40 ]; then
        sleep_minutes=$((40 - current_minute))
    else
        sleep_minutes=$((60 - current_minute))
    fi
    
    # Calculate total sleep seconds (subtract current seconds to be precise)
    sleep_seconds=$(( (sleep_minutes * 60) - current_second ))
    
    # Only sleep if we need to wait
    if [ $sleep_seconds -gt 0 ]; then
        echo "$(date): Sleeping for $sleep_seconds seconds until next capture time"
        sleep $sleep_seconds
    fi
    
    # Get the current date and time in the desired format
    filename=$(date +"%y%m%d_%H%M").jpg
    
    # Activate the GPIO pin 18
    pigs p 18 124
    sleep 1
    
    # Capture the image using rpicam-jpeg
    echo "$(date): Capturing image $filename"
    rpicam-jpeg -o $filename -cfx 128:128
    
    # Deactivate the GPIO pin 18
    pigs p 18 0
    
    # Sleep for 60 seconds to ensure we don't capture twice in the same minute
    sleep 60
done
