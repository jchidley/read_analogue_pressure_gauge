# Reading
scp jack@pi4light.local:./dial_images/*.jpg .\dial_images
uv run gauge_cli.py --plot --pressure-unit bar --average --all-time
uv run filter_large_angles.py --mark-as-failures
uv run gauge_cli.py --plot --pressure-unit bar --average --all-time
lightningview.exe .\gauge_plots.png
