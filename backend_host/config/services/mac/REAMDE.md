=== Useful Commands ===
View logs:
  Monitor service: tail -f /tmp/com.virtualpytest.monitor.out
  Stream service:  tail -f /tmp/com.virtualpytest.stream.out

Control services:
  Stop:    launchctl stop com.virtualpytest.stream
  Start:   launchctl start com.virtualpytest.stream
  Restart: launchctl kickstart -k gui/$(id -u)/com.virtualpytest.stream

  Stop:    launchctl stop com.virtualpytest.monitor
  Start:   launchctl start com.virtualpytest.monitor
  Restart: launchctl kickstart -k gui/$(id -u)/com.virtualpytest.monitor

Uninstall services:
  launchctl unload ~/Library/LaunchAgents/com.virtualpytest.monitor.plist
  rm ~/Library/LaunchAgents/com.virtualpytest.monitor.plist

  ffmpeg -f avfoundation -list_devices true -i ""
  