#!/usr/bin/env python3
"""
DNS Lookup Time Script for VirtualPyTest

Performs DNS lookup and measures response time, storing results in metadata.

Usage:
    python test_scripts/gw/dns_lookuptime.py [--dns <domain>] [--userinterface <ui>] [--host <host>] [--device <device>]
    
Examples:
    python test_scripts/gw/dns_lookuptime.py                                    # Default: epg.prod.ch.dmdsdp.com
    python test_scripts/gw/dns_lookuptime.py --dns google.com                   # Custom domain
    python test_scripts/gw/dns_lookuptime.py --dns epg.prod.ch.dmdsdp.com --host sunri-pi1
    python test_scripts/gw/dns_lookuptime.py --dns google.com --userinterface web_test
    
"""

import sys
import os
import subprocess
import time
import re
from datetime import datetime

# Add project root to path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from shared.src.lib.executors.script_decorators import script, get_context, get_args, get_device

# Script arguments
_script_args = [
    '--userinterface:str:web_test',           # Ignored (framework passes it, but we don't need it)
    '--dns:str:epg.prod.ch.dmdsdp.com'        # Domain to lookup
]


def parse_nslookup_output(output: str) -> dict:
    """Parse nslookup output to extract server, addresses, and CNAME"""
    data = {
        'server': None,
        'server_port': None,
        'canonical_name': None,
        'ipv4_addresses': [],
        'ipv6_addresses': []
    }
    
    for line in output.split('\n'):
        line = line.strip()
        
        # Server address
        if line.startswith('Server:'):
            data['server'] = line.split('Server:')[1].strip()
        elif line.startswith('Address:') and '#' in line and not data['server_port']:
            match = re.search(r'(\d+\.\d+\.\d+\.\d+)#(\d+)', line)
            if match:
                data['server'] = match.group(1)
                data['server_port'] = match.group(2)
        
        # Canonical name (CNAME)
        elif 'canonical name' in line.lower():
            match = re.search(r'canonical name = (.+)', line)
            if match:
                data['canonical_name'] = match.group(1).strip().rstrip('.')
        
        # IPv4 addresses
        elif line.startswith('Address:') and '.' in line and ':' not in line.split('Address:')[1]:
            match = re.search(r'(\d+\.\d+\.\d+\.\d+)', line)
            if match:
                data['ipv4_addresses'].append(match.group(1))
        
        # IPv6 addresses
        elif line.startswith('Address:') and '::' in line:
            match = re.search(r'Address:\s*(.+)', line)
            if match:
                data['ipv6_addresses'].append(match.group(1).strip())
    
    return data


@script("dns_lookuptime", "Perform DNS lookup and measure response time")
def main():
    """Execute nslookup, measure time, and store results in metadata"""
    args = get_args()
    context = get_context()
    device = get_device()
    domain = args.dns
    
    print(f"🔍 [dns_lookuptime] Looking up: {domain}")
    print(f"📱 [dns_lookuptime] Device: {device.device_name} ({device.device_model})")
    
    # Execute nslookup and measure time
    start_time = time.time()
    try:
        result = subprocess.run(
            ['nslookup', domain],
            capture_output=True,
            text=True,
            timeout=10
        )
        elapsed_time = time.time() - start_time
        
        output = result.stdout
        success = result.returncode == 0
        
        if not success:
            context.error_message = f"nslookup failed: {result.stderr}"
            context.overall_success = False
            return False
        
        # Print raw output first
        print(f"\n{'='*80}")
        print(f"✅ DNS LOOKUP RAW OUTPUT")
        print(f"{'='*80}")
        print(output)
        print(f"{'='*80}\n")
        
        # Parse output
        parsed_data = parse_nslookup_output(output)
        
        # Store in metadata
        context.metadata = {
            'domain': domain,
            'lookup_time_seconds': round(elapsed_time, 3),
            'lookup_time_ms': round(elapsed_time * 1000, 1),
            'timestamp': datetime.now().isoformat(),
            'device_name': device.device_name,
            'host_name': context.host.host_name,
            'dns_server': parsed_data['server'],
            'dns_server_port': parsed_data['server_port'],
            'canonical_name': parsed_data['canonical_name'],
            'ipv4_addresses': parsed_data['ipv4_addresses'],
            'ipv6_addresses': parsed_data['ipv6_addresses'],
            'raw_output': output
        }
        
        # Print parsed summary
        print(f"{'='*80}")
        print(f"✅ DNS LOOKUP PARSED RESULTS")
        print(f"{'='*80}")
        print(f"🌐 Domain: {domain}")
        print(f"⏱️  Lookup Time: {elapsed_time*1000:.1f}ms ({elapsed_time:.3f}s)")
        print(f"🖥️  DNS Server: {parsed_data['server']}#{parsed_data['server_port']}")
        if parsed_data['canonical_name']:
            print(f"🔗 CNAME: {parsed_data['canonical_name']}")
        if parsed_data['ipv4_addresses']:
            print(f"📍 IPv4: {', '.join(parsed_data['ipv4_addresses'])}")
        if parsed_data['ipv6_addresses']:
            print(f"📍 IPv6: {', '.join(parsed_data['ipv6_addresses'])}")
        print(f"{'='*80}\n")
        
        # Set execution summary
        context.execution_summary = f"""🔍 DNS LOOKUP SUMMARY
📱 Device: {device.device_name} ({device.device_model})
🖥️  Host: {context.host.host_name}
🌐 Domain: {domain}
⏱️  Lookup Time: {elapsed_time*1000:.1f}ms
🖥️  DNS Server: {parsed_data['server']}
📊 IPv4 Addresses: {len(parsed_data['ipv4_addresses'])}
📊 IPv6 Addresses: {len(parsed_data['ipv6_addresses'])}

🎯 Result: SUCCESS"""
        
        context.overall_success = True
        return True
        
    except subprocess.TimeoutExpired:
        context.error_message = f"DNS lookup timeout after 10s"
        context.overall_success = False
        return False
    except Exception as e:
        context.error_message = f"DNS lookup failed: {str(e)}"
        context.overall_success = False
        return False


main._script_args = _script_args

if __name__ == "__main__":
    main()

