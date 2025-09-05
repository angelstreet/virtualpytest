"""
Power Controller Command Descriptions
Covers: Tapo power control, USB hub control
"""

POWER_DESCRIPTIONS = {
    # Basic Power Control Commands
    'power_on': {
        'description': 'Turn device power ON. Use to start devices or recover from power issues.',
        'example': "power_on()"
    },
    'power_off': {
        'description': 'Turn device power OFF. Use for clean shutdown or power cycling.',
        'example': "power_off()"
    },
    'power_toggle': {
        'description': 'Toggle device power state (ON->OFF or OFF->ON). Use for power state switching.',
        'example': "power_toggle()"
    },
    'power_cycle': {
        'description': 'Turn power OFF then ON with delay. Use to reset devices or clear issues.',
        'example': "power_cycle(delay=5.0)"
    },
    'soft_reset': {
        'description': 'Perform soft power reset with minimal delay. Use for quick device restart.',
        'example': "soft_reset(delay=2.0)"
    },
    'hard_reset': {
        'description': 'Perform hard power reset with extended delay. Use for complete device reset.',
        'example': "hard_reset(delay=10.0)"
    },
    
    # Power Status Commands
    'get_power_status': {
        'description': 'Check current power state. Use to verify device power status.',
        'example': "get_power_status()"
    },
    'is_power_on': {
        'description': 'Check if device power is ON. Use for power state verification.',
        'example': "is_power_on()"
    },
    'is_power_off': {
        'description': 'Check if device power is OFF. Use for power state verification.',
        'example': "is_power_off()"
    },
    'wait_for_power_on': {
        'description': 'Wait for device to power ON. Use after power commands to ensure state change.',
        'example': "wait_for_power_on(timeout=30.0)"
    },
    'wait_for_power_off': {
        'description': 'Wait for device to power OFF. Use after shutdown commands.',
        'example': "wait_for_power_off(timeout=15.0)"
    },
    
    # Tapo Smart Plug Commands
    'tapo_connect': {
        'description': 'Connect to Tapo smart plug. Use to establish control connection.',
        'example': "tapo_connect(ip_address='192.168.1.100', username='admin', password='pass')"
    },
    'tapo_disconnect': {
        'description': 'Disconnect from Tapo smart plug. Use to end control session.',
        'example': "tapo_disconnect()"
    },
    'tapo_get_device_info': {
        'description': 'Get Tapo device information and status. Use for device verification.',
        'example': "tapo_get_device_info()"
    },
    'tapo_set_alias': {
        'description': 'Set friendly name for Tapo device. Use for device identification.',
        'example': "tapo_set_alias(alias='TV Power')"
    },
    'tapo_get_energy_usage': {
        'description': 'Get power consumption data from Tapo plug. Use for energy monitoring.',
        'example': "tapo_get_energy_usage()"
    },
    
    # USB Hub Power Control Commands
    'usb_hub_power_on': {
        'description': 'Turn ON specific USB hub port. Use to power USB-connected devices.',
        'example': "usb_hub_power_on(hub_id='1-1', port=2)"
    },
    'usb_hub_power_off': {
        'description': 'Turn OFF specific USB hub port. Use to power down USB devices.',
        'example': "usb_hub_power_off(hub_id='1-1', port=2)"
    },
    'usb_hub_power_cycle': {
        'description': 'Cycle power on USB hub port. Use to reset USB-connected devices.',
        'example': "usb_hub_power_cycle(hub_id='1-1', port=2, delay=3.0)"
    },
    'usb_hub_get_status': {
        'description': 'Get USB hub port status. Use to verify USB port power state.',
        'example': "usb_hub_get_status(hub_id='1-1', port=2)"
    },
    'usb_hub_list_ports': {
        'description': 'List all USB hub ports and their status. Use for hub inventory.',
        'example': "usb_hub_list_ports(hub_id='1-1')"
    },
    'usb_hub_reset_all': {
        'description': 'Reset all ports on USB hub. Use for complete hub reset.',
        'example': "usb_hub_reset_all(hub_id='1-1')"
    },
    
    # Power Scheduling Commands
    'schedule_power_on': {
        'description': 'Schedule device to power ON at specific time. Use for automated power management.',
        'example': "schedule_power_on(time='08:00', days=['monday', 'tuesday'])"
    },
    'schedule_power_off': {
        'description': 'Schedule device to power OFF at specific time. Use for automated shutdown.',
        'example': "schedule_power_off(time='22:00', days=['daily'])"
    },
    'cancel_power_schedule': {
        'description': 'Cancel scheduled power operations. Use to remove automation.',
        'example': "cancel_power_schedule(schedule_id='morning_start')"
    },
    'get_power_schedule': {
        'description': 'Get current power schedule configuration. Use to verify automation setup.',
        'example': "get_power_schedule()"
    },
    
    # Power Monitoring Commands
    'monitor_power_consumption': {
        'description': 'Monitor real-time power consumption. Use for energy analysis.',
        'example': "monitor_power_consumption(duration=60.0)"
    },
    'get_power_history': {
        'description': 'Get historical power usage data. Use for consumption analysis.',
        'example': "get_power_history(days=7)"
    },
    'set_power_limit': {
        'description': 'Set maximum power consumption limit. Use for power management.',
        'example': "set_power_limit(watts=100)"
    },
    'get_power_statistics': {
        'description': 'Get power usage statistics (min, max, average). Use for analysis.',
        'example': "get_power_statistics(period='24h')"
    },
    
    # Safety and Protection Commands
    'enable_overload_protection': {
        'description': 'Enable power overload protection. Use for device safety.',
        'example': "enable_overload_protection(threshold_watts=150)"
    },
    'disable_overload_protection': {
        'description': 'Disable power overload protection. Use when protection interferes.',
        'example': "disable_overload_protection()"
    },
    'set_voltage_threshold': {
        'description': 'Set voltage protection thresholds. Use for electrical safety.',
        'example': "set_voltage_threshold(min_volts=110, max_volts=130)"
    },
    'emergency_power_off': {
        'description': 'Immediately cut power for emergency. Use for safety or damage prevention.',
        'example': "emergency_power_off()"
    },
    
    # Multi-Device Power Management
    'power_on_group': {
        'description': 'Power ON multiple devices in sequence. Use for coordinated startup.',
        'example': "power_on_group(devices=['tv', 'stb', 'audio'], delay=2.0)"
    },
    'power_off_group': {
        'description': 'Power OFF multiple devices in sequence. Use for coordinated shutdown.',
        'example': "power_off_group(devices=['audio', 'stb', 'tv'], delay=1.0)"
    },
    'power_cycle_group': {
        'description': 'Power cycle multiple devices. Use for system-wide reset.',
        'example': "power_cycle_group(devices=['router', 'modem'], delay=5.0)"
    },
    'get_group_status': {
        'description': 'Get power status of device group. Use for multi-device verification.',
        'example': "get_group_status(group='entertainment_system')"
    },
    
    # Advanced Power Control
    'gradual_power_on': {
        'description': 'Gradually increase power to device. Use for sensitive equipment startup.',
        'example': "gradual_power_on(ramp_time=10.0)"
    },
    'gradual_power_off': {
        'description': 'Gradually decrease power to device. Use for gentle shutdown.',
        'example': "gradual_power_off(ramp_time=5.0)"
    },
    'pulse_power': {
        'description': 'Send power pulse to device. Use for wake-on-LAN or special signaling.',
        'example': "pulse_power(duration=0.5, count=3, interval=1.0)"
    },
    'set_power_profile': {
        'description': 'Apply predefined power configuration. Use for different operating modes.',
        'example': "set_power_profile(profile='energy_saver')"
    },
    
    # Diagnostics and Testing
    'test_power_connection': {
        'description': 'Test power control connection and functionality. Use for diagnostics.',
        'example': "test_power_connection()"
    },
    'calibrate_power_meter': {
        'description': 'Calibrate power measurement accuracy. Use for precise monitoring.',
        'example': "calibrate_power_meter()"
    },
    'run_power_diagnostics': {
        'description': 'Run comprehensive power system diagnostics. Use for troubleshooting.',
        'example': "run_power_diagnostics()"
    },
    'get_power_controller_info': {
        'description': 'Get power controller hardware information. Use for system verification.',
        'example': "get_power_controller_info()"
    }
}
