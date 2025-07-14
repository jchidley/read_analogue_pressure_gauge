#!/usr/bin/env python3
# /// script
# dependencies = []
# requires-python = ">=3.12"
# ///
"""Simple utility to find gauge records with angles > threshold and mark them as detection failures"""

import sqlite3
import argparse
import os
import shutil
from datetime import datetime

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default="gauge_data.db")
    parser.add_argument("--dir", default="dial_images", help="Image directory")
    parser.add_argument("--threshold", type=float, default=200)
    parser.add_argument("--mark-as-failures", action="store_true", help="Mark records as detection failures")
    args = parser.parse_args()
    
    if not os.path.exists(args.db):
        print(f"Database not found: {args.db}")
        return
    
    # Backup if marking as failures
    if args.mark_as_failures:
        shutil.copy2(args.db, f"{args.db}.bak")
    
    conn = sqlite3.connect(args.db)
    conn.row_factory = sqlite3.Row
    
    # Find matching records
    cursor = conn.execute(
        "SELECT image_name, angle, timestamp FROM gauge_results WHERE angle > ? ORDER BY angle DESC", 
        (args.threshold,)
    )
    results = cursor.fetchall()
    
    # Display results
    if not results:
        print(f"No records with angle > {args.threshold}°")
        conn.close()
        return
    
    print(f"Found {len(results)} records with angle > {args.threshold}°:")
    for row in results:
        print(f"{row['image_name']}: {row['angle']:.1f}° ({row['timestamp']})")
    
    # Get confirmation for marking as failures
    if args.mark_as_failures:
        confirm = input(f"Mark these {len(results)} records as detection failures? (y/n): ")
        if confirm.lower() != 'y':
            print("Operation cancelled")
            conn.close()
            return
        
        images = [row['image_name'] for row in results]
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Begin a transaction
        conn.execute("BEGIN TRANSACTION")
        
        try:
            # For each image, remove from gauge_results and add to detection_failures
            for img_name in images:
                # Remove from gauge_results
                conn.execute("DELETE FROM gauge_results WHERE image_name = ?", (img_name,))
                
                # Add to detection_failures
                conn.execute(
                    "INSERT OR REPLACE INTO detection_failures (image_name, timestamp) VALUES (?, ?)",
                    (img_name, timestamp)
                )
            
            # Commit the transaction
            conn.commit()
            print(f"Marked {len(images)} records as detection failures")
        
        except Exception as e:
            # Rollback in case of error
            conn.rollback()
            print(f"Error: {e}")
            print("Operation failed, database unchanged")
    
    conn.close()

if __name__ == "__main__":
    main()
