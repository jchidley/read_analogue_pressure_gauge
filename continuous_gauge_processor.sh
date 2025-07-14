#!/bin/bash
# Continuous gauge image processor for Raspberry Pi
# Runs as a service and processes images as they appear

# Change to the home directory where scripts are located
cd /home/jack

# Create a function to process new images
process_new_images() {
    echo "$(date): Checking for new images to process..."
    
    # Get list of images in dial_images directory
    new_images=$(find dial_images -name "*.jpg" -type f 2>/dev/null)
    
    if [ -n "$new_images" ]; then
        image_count=$(echo "$new_images" | wc -l)
        echo "$(date): Found $image_count images to process"
        
        # Process gauge images with plotting, using BAR units and averaging
        echo "$(date): Processing gauge images..."
        uv run gauge_cli.py --dir dial_images --plot --pressure-unit bar --average --all-time
        
        # Filter out large angles and mark as failures
        echo "$(date): Filtering large angles..."
        uv run filter_large_angles.py --dir dial_images --mark-as-failures
        
        # Re-process to update plots after filtering
        echo "$(date): Re-processing after filtering..."
        uv run gauge_cli.py --dir dial_images --plot --pressure-unit bar --average --all-time
        
        # Delete only successfully processed images
        echo "$(date): Cleaning up successfully processed images..."
        processed_images=$(sqlite3 gauge_data.db "SELECT image_name FROM gauge_results" 2>/dev/null | grep -E "^[0-9]{6}_[0-9]{4}\.jpg$")
        
        if [ -n "$processed_images" ]; then
            deleted_count=0
            for image in $processed_images; do
                if [ -f "dial_images/$image" ]; then
                    rm "dial_images/$image"
                    ((deleted_count++))
                fi
            done
            echo "$(date): Deleted $deleted_count processed images"
        fi
        
        # Show remaining images
        remaining=$(find dial_images -name "*.jpg" -type f 2>/dev/null | wc -l)
        echo "$(date): $remaining images remain (unprocessed or failed)"
    else
        echo "$(date): No new images found"
    fi
}

# Main loop
echo "$(date): Starting continuous gauge processor"

while true; do
    # Process any new images
    process_new_images
    
    # Sleep for 5 minutes before checking again
    # This gives enough time for processing but checks frequently enough
    # to catch new images (which arrive every 20 minutes)
    echo "$(date): Sleeping for 5 minutes before next check..."
    sleep 300
done