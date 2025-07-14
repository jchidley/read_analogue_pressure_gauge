# Reading - Local processing
scp jack@pi4light.local:./dial_images/*.jpg .\dial_images
uv run gauge_cli.py --plot --pressure-unit bar --all-time
uv run filter_large_angles.py --mark-as-failures
uv run gauge_cli.py --plot --pressure-unit bar --all-time
lightningview.exe .\gauge_plots.png

# Or to view the plot from Pi directly:
# scp jack@pi4light:~/gauge_plots.png . && lightningview.exe .\gauge_plots.png

# Or to sync Pi database with local and regenerate plots:
# uv run sync_database_from_pi.py
# uv run gauge_cli.py --plot --pressure-unit bar --all-time
# lightningview.exe .\gauge_plots.png
