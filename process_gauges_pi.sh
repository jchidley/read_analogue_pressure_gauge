#!/bin/bash
# Process gauge images on Raspberry Pi locally
# Run this script on the Pi where images are captured

# Change to the directory where the script is located
cd /home/jack

# Process gauge images with plotting, using BAR units and averaging
echo "Processing gauge images (first pass)..."
uv run gauge_cli.py --dir dial_images --plot --pressure-unit bar --all-time

# Filter out large angles and mark as failures
echo "Filtering large angles..."
uv run filter_large_angles.py --dir dial_images --mark-as-failures

# Re-process to update plots after filtering
echo "Processing gauge images (second pass after filtering)..."
uv run gauge_cli.py --dir dial_images --plot --pressure-unit bar --all-time

echo "Processing complete. Plot saved as gauge_plots.png"

# Optional: Display plot information
if [ -f gauge_plots.png ]; then
    echo "Plot file size: $(ls -lh gauge_plots.png | awk '{print $5}')"
    echo "Plot timestamp: $(ls -l gauge_plots.png | awk '{print $6, $7, $8}')"
fi

# Delete only images that have been successfully processed and recorded in the database
echo "Cleaning up successfully processed images..."
# Get list of images that were successfully processed from the database
processed_images=$(sqlite3 gauge_data.db "SELECT image_name FROM gauge_results" 2>/dev/null | grep -E "^[0-9]{6}_[0-9]{4}\.jpg$")

if [ -n "$processed_images" ]; then
    deleted_count=0
    for image in $processed_images; do
        if [ -f "dial_images/$image" ]; then
            rm "dial_images/$image"
            ((deleted_count++))
        fi
    done
    echo "Deleted $deleted_count processed images from dial_images/"
    
    # Show remaining images (these might be failures or new unprocessed images)
    remaining=$(find dial_images -name "*.jpg" -type f | wc -l)
    echo "$remaining images remain in dial_images/ (unprocessed or failed)"
else
    echo "No successfully processed images found in database to delete"
fi