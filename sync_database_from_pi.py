#!/usr/bin/env python3
# /// script
# dependencies = []
# requires-python = ">=3.12"
# ///
"""Sync gauge data from Raspberry Pi to local database without duplicates"""

import sqlite3
import subprocess
import os
import sys
from datetime import datetime

def sync_database(pi_host="jack@pi4light", local_db="gauge_data.db", remote_db="gauge_data.db"):
    """Sync data from Pi database to local database"""
    
    # Download Pi database to temp file
    temp_db = "gauge_data_pi_temp.db"
    print(f"Downloading database from {pi_host}...")
    
    try:
        subprocess.run(["scp", f"{pi_host}:~/{remote_db}", temp_db], check=True)
    except subprocess.CalledProcessError:
        print(f"Error: Could not download database from {pi_host}")
        return False
    
    if not os.path.exists(temp_db):
        print("Error: Downloaded database not found")
        return False
    
    # Connect to both databases
    print(f"Connecting to databases...")
    local_conn = sqlite3.connect(local_db)
    pi_conn = sqlite3.connect(temp_db)
    
    try:
        # Get counts before sync
        local_before = local_conn.execute("SELECT COUNT(*) FROM gauge_results").fetchone()[0]
        pi_total = pi_conn.execute("SELECT COUNT(*) FROM gauge_results").fetchone()[0]
        
        print(f"Local database: {local_before} records")
        print(f"Pi database: {pi_total} records")
        
        # Copy new gauge_results records
        print("Syncing gauge_results...")
        new_results = pi_conn.execute("""
            SELECT * FROM gauge_results 
            WHERE image_name NOT IN (
                SELECT image_name FROM main.gauge_results
            )
        """)
        
        records_added = 0
        for row in new_results:
            local_conn.execute("""
                INSERT INTO gauge_results 
                (image_name, angle, center_x, center_y, radius, timestamp, pressure_psi, pressure_bar)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, row[1:])  # Skip the id column
            records_added += 1
        
        # Copy new detection_failures records
        print("Syncing detection_failures...")
        new_failures = pi_conn.execute("""
            SELECT * FROM detection_failures 
            WHERE image_name NOT IN (
                SELECT image_name FROM main.detection_failures
            )
        """)
        
        failures_added = 0
        for row in new_failures:
            local_conn.execute("""
                INSERT INTO detection_failures (image_name, timestamp)
                VALUES (?, ?)
            """, row[1:])  # Skip the id column
            failures_added += 1
        
        # Commit changes
        local_conn.commit()
        
        # Get final count
        local_after = local_conn.execute("SELECT COUNT(*) FROM gauge_results").fetchone()[0]
        
        print(f"\nSync complete:")
        print(f"  - Added {records_added} new gauge readings")
        print(f"  - Added {failures_added} new failure records")
        print(f"  - Local database now has {local_after} total records")
        
        # Show recent synced records
        if records_added > 0:
            print(f"\nMost recent synced readings:")
            recent = local_conn.execute("""
                SELECT datetime(timestamp), image_name, angle, pressure_bar 
                FROM gauge_results 
                ORDER BY timestamp DESC 
                LIMIT 5
            """).fetchall()
            
            for row in recent:
                print(f"  {row[0]} - {row[1]} - {row[2]:.1f}° - {row[3]:.2f} bar")
        
    finally:
        local_conn.close()
        pi_conn.close()
        
        # Clean up temp file
        if os.path.exists(temp_db):
            os.remove(temp_db)
    
    return True

if __name__ == "__main__":
    # Check if local database exists
    if not os.path.exists("gauge_data.db"):
        print("Error: Local gauge_data.db not found")
        print("Run gauge processing locally first to create the database")
        sys.exit(1)
    
    if sync_database():
        print("\nYou can now run gauge_cli.py --plot to visualize all data")
    else:
        sys.exit(1)