#!/bin/bash
# Script to check how capture_images.sh is being run on Raspberry Pi
# Run this on the Raspberry Pi: bash check_capture_service.sh

echo "=== Checking for capture_images.sh in various startup locations ==="
echo ""

echo "1. Checking crontab for current user:"
crontab -l 2>/dev/null | grep -E "capture_images|dial_images" || echo "   Not found in user crontab"
echo ""

echo "2. Checking system crontab:"
sudo grep -E "capture_images|dial_images" /etc/crontab 2>/dev/null || echo "   Not found in system crontab"
echo ""

echo "3. Checking /etc/cron.d/:"
sudo grep -r "capture_images" /etc/cron.d/ 2>/dev/null || echo "   Not found in /etc/cron.d/"
echo ""

echo "4. Checking systemd services:"
systemctl list-units --type=service --all | grep -E "capture|gauge|dial" || echo "   No matching systemd services"
echo ""

echo "5. Checking for systemd service files:"
sudo find /etc/systemd/system /lib/systemd/system -name "*capture*" -o -name "*gauge*" -o -name "*dial*" 2>/dev/null || echo "   No matching service files"
echo ""

echo "6. Checking if capture_images.sh is currently running:"
ps aux | grep "[c]apture_images.sh" || echo "   capture_images.sh is not currently running"
echo ""

echo "7. Checking rc.local:"
sudo grep "capture_images" /etc/rc.local 2>/dev/null || echo "   Not found in rc.local"
echo ""

echo "8. Checking user's systemd services:"
systemctl --user list-units --type=service --all | grep -E "capture|gauge|dial" || echo "   No matching user services"
echo ""

echo "9. Checking for @reboot in crontab:"
crontab -l 2>/dev/null | grep "@reboot" || echo "   No @reboot entries in user crontab"
echo ""

echo "10. Checking supervisor (if installed):"
if command -v supervisorctl &> /dev/null; then
    sudo supervisorctl status | grep -E "capture|gauge|dial" || echo "   No matching supervisor processes"
else
    echo "   Supervisor not installed"
fi