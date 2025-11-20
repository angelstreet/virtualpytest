#!/usr/bin/env python3
"""
SmartPing Script for VirtualPyTest

Performs network path analysis with ping, traceroute, and QoS metrics.
Measures RTT, jitter, packet loss, and maps the complete path to target.

Usage:
    python test_scripts/gw/smartping.py [--target <url:port>] [--protocol <icmp|tcp|udp>] [--count <n>] [--userinterface <ui>] [--host <host>] [--device <device>]
    
Examples:
    python test_scripts/gw/smartping.py                                              # Default: ICMP to google.com
    python test_scripts/gw/smartping.py --target youtube.com:443 --protocol tcp      # TCP to YouTube
    python test_scripts/gw/smartping.py --target 8.8.8.8 --protocol icmp --count 10  # 10 ICMP pings to Google DNS
    python test_scripts/gw/smartping.py --target epg.prod.ch.dmdsdp.com:443 --protocol tcp --host sunri-pi1
    python test_scripts/gw/smartping.py --target google.com --userinterface web_test
    
"""

import sys
import os
import socket
import subprocess
import time
import re
import statistics
from datetime import datetime
from typing import List, Dict, Optional, Tuple

# Add project root to path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from shared.src.lib.executors.script_decorators import script, get_context, get_args, get_device

# Script arguments
_script_args = [
    '--userinterface:str:web_test',   # Ignored (framework passes it, but we don't need it)
    '--target:str:google.com',        # Target URL or IP (can include :port)
    '--protocol:str:icmp',            # Protocol: icmp, tcp, udp
    '--count:int:5',                  # Number of ping attempts
    '--max_hops:int:30',              # Maximum hops for traceroute
]


def resolve_target(target: str) -> Tuple[str, str, int]:
    """
    Resolve target to (hostname, ip, port).
    Examples: 'youtube.com:443' -> ('youtube.com', '142.250.x.x', 443)
              'google.com' -> ('google.com', '172.217.x.x', 80)
    """
    if ':' in target:
        host, port_str = target.rsplit(':', 1)
        try:
            port = int(port_str)
        except ValueError:
            host = target
            port = 443  # Default
    else:
        host = target
        port = 443  # Default HTTPS
    
    try:
        ip = socket.gethostbyname(host)
        return host, ip, port
    except socket.gaierror as e:
        raise ValueError(f"Cannot resolve hostname '{host}': {e}")


def run_icmp_ping(host: str, count: int, timeout: int = 3) -> Dict:
    """Run ICMP ping using system ping command and parse results"""
    try:
        # Use platform-appropriate ping command
        if sys.platform == 'darwin':  # macOS
            cmd = ['ping', '-c', str(count), '-W', str(timeout * 1000), host]
        else:  # Linux
            cmd = ['ping', '-c', str(count), '-W', str(timeout), host]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout * count + 5)
        output = result.stdout + result.stderr
        
        # Parse ping statistics
        rtts = []
        packets_transmitted = 0
        packets_received = 0
        
        for line in output.split('\n'):
            # Parse RTT lines: "64 bytes from...: icmp_seq=1 ttl=117 time=25.4 ms"
            time_match = re.search(r'time[=:]?\s*(\d+\.?\d*)\s*ms', line)
            if time_match:
                rtts.append(float(time_match.group(1)))
            
            # Parse packet statistics
            stats_match = re.search(r'(\d+)\s+packets transmitted,\s+(\d+)\s+(?:packets\s+)?received', line)
            if stats_match:
                packets_transmitted = int(stats_match.group(1))
                packets_received = int(stats_match.group(2))
        
        # Parse summary statistics if available
        rtt_stats = {}
        stats_line_match = re.search(r'min/avg/max/(?:stddev|mdev)\s*=\s*(\d+\.?\d*)/(\d+\.?\d*)/(\d+\.?\d*)/(\d+\.?\d*)', output)
        if stats_line_match:
            rtt_stats = {
                'min': float(stats_line_match.group(1)),
                'avg': float(stats_line_match.group(2)),
                'max': float(stats_line_match.group(3)),
                'stddev': float(stats_line_match.group(4)),
            }
        elif rtts:
            rtt_stats = {
                'min': min(rtts),
                'avg': statistics.mean(rtts),
                'max': max(rtts),
                'stddev': statistics.stdev(rtts) if len(rtts) > 1 else 0,
            }
        
        packet_loss = ((packets_transmitted - packets_received) / packets_transmitted * 100) if packets_transmitted > 0 else 100
        
        return {
            'success': result.returncode == 0 and packets_received > 0,
            'rtts': rtts,
            'rtt_stats': rtt_stats,
            'packets_transmitted': packets_transmitted,
            'packets_received': packets_received,
            'packet_loss_percent': packet_loss,
            'raw_output': output
        }
    except subprocess.TimeoutExpired:
        return {
            'success': False,
            'error': 'Ping timeout',
            'rtts': [],
            'rtt_stats': {},
            'packet_loss_percent': 100
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'rtts': [],
            'rtt_stats': {},
            'packet_loss_percent': 100
        }


def run_tcp_ping(host: str, port: int, count: int, timeout: int = 3) -> Dict:
    """Run TCP connect test (TCP ping equivalent)"""
    rtts = []
    successful = 0
    
    for i in range(count):
        start = time.time()
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        
        try:
            result = sock.connect_ex((host, port))
            elapsed = (time.time() - start) * 1000  # Convert to ms
            
            if result == 0:
                rtts.append(elapsed)
                successful += 1
        except Exception as e:
            pass
        finally:
            sock.close()
        
        # Small delay between attempts
        if i < count - 1:
            time.sleep(0.5)
    
    rtt_stats = {}
    if rtts:
        rtt_stats = {
            'min': min(rtts),
            'avg': statistics.mean(rtts),
            'max': max(rtts),
            'stddev': statistics.stdev(rtts) if len(rtts) > 1 else 0,
        }
    
    packet_loss = ((count - successful) / count * 100) if count > 0 else 100
    
    return {
        'success': successful > 0,
        'rtts': rtts,
        'rtt_stats': rtt_stats,
        'packets_transmitted': count,
        'packets_received': successful,
        'packet_loss_percent': packet_loss,
        'raw_output': f'TCP connect to {host}:{port} - {successful}/{count} successful'
    }


def run_udp_ping(host: str, port: int, count: int, timeout: int = 3) -> Dict:
    """Run UDP probe test"""
    rtts = []
    successful = 0
    
    # Use common UDP ports if not specified
    test_port = port if port != 443 else 53  # Use DNS port for UDP
    
    for i in range(count):
        start = time.time()
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(timeout)
        
        try:
            # Send UDP packet
            sock.sendto(b'\x00' * 32, (host, test_port))
            
            # Try to receive (may timeout, which is normal for UDP)
            try:
                data, addr = sock.recvfrom(1024)
                elapsed = (time.time() - start) * 1000
                rtts.append(elapsed)
                successful += 1
            except socket.timeout:
                # For UDP, timeout doesn't mean failure - we just don't get a response
                elapsed = (time.time() - start) * 1000
                rtts.append(elapsed)
                successful += 1
        except Exception as e:
            pass
        finally:
            sock.close()
        
        if i < count - 1:
            time.sleep(0.5)
    
    rtt_stats = {}
    if rtts:
        rtt_stats = {
            'min': min(rtts),
            'avg': statistics.mean(rtts),
            'max': max(rtts),
            'stddev': statistics.stdev(rtts) if len(rtts) > 1 else 0,
        }
    
    packet_loss = ((count - successful) / count * 100) if count > 0 else 100
    
    return {
        'success': successful > 0,
        'rtts': rtts,
        'rtt_stats': rtt_stats,
        'packets_transmitted': count,
        'packets_received': successful,
        'packet_loss_percent': packet_loss,
        'raw_output': f'UDP probe to {host}:{test_port} - {successful}/{count} successful'
    }


def run_traceroute(host: str, protocol: str, max_hops: int = 30) -> Dict:
    """Run traceroute to map network path"""
    try:
        # Find traceroute command (may be in /usr/sbin or /usr/bin)
        traceroute_cmd = None
        for path in ['/usr/sbin/traceroute', '/usr/bin/traceroute', 'traceroute']:
            try:
                result = subprocess.run(['which', path] if path == 'traceroute' else ['test', '-f', path], 
                                       capture_output=True, timeout=1)
                if result.returncode == 0 or os.path.exists(path):
                    traceroute_cmd = path
                    break
            except:
                continue
        
        if not traceroute_cmd:
            return {
                'success': False,
                'error': 'traceroute command not found. Install with: sudo apt-get install traceroute',
                'hops': [],
                'hop_count': 0
            }
        
        # Build traceroute command based on protocol
        if protocol == 'tcp':
            cmd = [traceroute_cmd, '-T', '-m', str(max_hops), '-q', '1', host]
        elif protocol == 'udp':
            cmd = [traceroute_cmd, '-U', '-m', str(max_hops), '-q', '1', host]
        else:  # icmp (default)
            cmd = [traceroute_cmd, '-I', '-m', str(max_hops), '-q', '1', host]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=max_hops * 2 + 10)
        output = result.stdout
        
        # Parse traceroute output
        hops = []
        hop_idx = 0
        
        for line in output.split('\n'):
            line = line.strip()
            if not line or line.startswith('traceroute'):
                continue
            
            # Parse hop line: " 1  gateway (192.168.1.1)  1.234 ms"
            hop_match = re.match(r'\s*(\d+)\s+(.+?)(?:\s+\(([^\)]+)\))?\s+(\d+\.?\d*)\s*ms', line)
            if hop_match:
                ttl = int(hop_match.group(1))
                hostname = hop_match.group(2).strip()
                ip = hop_match.group(3) if hop_match.group(3) else hostname
                delay = float(hop_match.group(4))
                
                hops.append({
                    'idx': hop_idx,
                    'ttl': ttl,
                    'hostname': hostname,
                    'ip': ip,
                    'delay_ms': delay,
                })
                hop_idx += 1
            # Handle * * * (no response)
            elif re.match(r'\s*(\d+)\s+\*', line):
                ttl_match = re.match(r'\s*(\d+)', line)
                if ttl_match:
                    ttl = int(ttl_match.group(1))
                    hops.append({
                        'idx': hop_idx,
                        'ttl': ttl,
                        'hostname': '*',
                        'ip': '*',
                        'delay_ms': None,
                    })
                    hop_idx += 1
        
        return {
            'success': len(hops) > 0,
            'hops': hops,
            'hop_count': len(hops),
            'raw_output': output
        }
    except subprocess.TimeoutExpired:
        return {
            'success': False,
            'error': 'Traceroute timeout',
            'hops': [],
            'hop_count': 0
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'hops': [],
            'hop_count': 0
        }


def calculate_smartping_score(ping_data: Dict, trace_data: Dict) -> float:
    """
    Calculate SmartPing score (0-100) based on network quality.
    Higher score = better network performance.
    """
    score = 100.0
    
    # Penalty for packet loss (0-40 points)
    packet_loss = ping_data.get('packet_loss_percent', 100)
    score -= min(40, packet_loss * 0.4)
    
    # Penalty for high RTT (0-30 points)
    rtt_stats = ping_data.get('rtt_stats', {})
    avg_rtt = rtt_stats.get('avg', 0)
    if avg_rtt > 200:
        score -= 30
    elif avg_rtt > 100:
        score -= 20
    elif avg_rtt > 50:
        score -= 10
    
    # Penalty for high jitter (0-20 points)
    jitter = rtt_stats.get('stddev', 0)
    if jitter > 50:
        score -= 20
    elif jitter > 20:
        score -= 10
    elif jitter > 10:
        score -= 5
    
    # Penalty for long path (0-10 points)
    hop_count = trace_data.get('hop_count', 0)
    if hop_count > 20:
        score -= 10
    elif hop_count > 15:
        score -= 5
    
    return max(0, min(100, score))


def determine_status(score: float, reachable: bool) -> Tuple[str, str]:
    """Determine network status and label based on score"""
    if not reachable:
        return 'DOWN', '❌ Service unreachable'
    elif score >= 80:
        return 'EXCELLENT', '✅ Excellent network quality'
    elif score >= 60:
        return 'GOOD', '✅ Good network quality'
    elif score >= 40:
        return 'DEGRADED', '⚠️  Degraded network quality'
    else:
        return 'POOR', '⚠️  Poor network quality'


@script("smartping", "Network path analysis with QoS metrics (ping, traceroute, jitter)")
def main():
    """Execute SmartPing analysis and store results in metadata"""
    args = get_args()
    context = get_context()
    device = get_device()
    
    target = args.target
    protocol = args.protocol.lower()
    count = args.count
    max_hops = args.max_hops
    
    # Validate protocol
    if protocol not in ['icmp', 'tcp', 'udp']:
        context.error_message = f"Invalid protocol '{protocol}'. Must be icmp, tcp, or udp"
        context.overall_success = False
        return False
    
    print(f"🌐 [smartping] Target: {target}")
    print(f"📡 [smartping] Protocol: {protocol.upper()}")
    print(f"📱 [smartping] Device: {device.device_name} ({device.device_model})")
    print(f"🖥️  [smartping] Host: {context.host.host_name}")
    
    # Resolve target
    try:
        hostname, ip, port = resolve_target(target)
        print(f"🔍 [smartping] Resolved: {hostname} -> {ip}:{port}")
    except ValueError as e:
        context.error_message = str(e)
        context.overall_success = False
        return False
    
    # Run ping based on protocol
    print(f"\n{'='*80}")
    print(f"🏓 PING TEST ({protocol.upper()})")
    print(f"{'='*80}")
    
    start_time = time.time()
    
    if protocol == 'icmp':
        ping_data = run_icmp_ping(ip, count)
    elif protocol == 'tcp':
        ping_data = run_tcp_ping(ip, port, count)
    else:  # udp
        ping_data = run_udp_ping(ip, port, count)
    
    ping_duration = time.time() - start_time
    
    if not ping_data.get('success'):
        error = ping_data.get('error', 'Ping failed')
        context.error_message = f"Ping failed: {error}"
        context.overall_success = False
        return False
    
    # Print ping results
    print(ping_data.get('raw_output', ''))
    rtt_stats = ping_data.get('rtt_stats', {})
    if rtt_stats:
        print(f"\n📊 RTT Statistics:")
        print(f"   Min:    {rtt_stats.get('min', 0):.2f} ms")
        print(f"   Avg:    {rtt_stats.get('avg', 0):.2f} ms")
        print(f"   Max:    {rtt_stats.get('max', 0):.2f} ms")
        print(f"   Jitter: {rtt_stats.get('stddev', 0):.2f} ms")
    print(f"📦 Packets: {ping_data.get('packets_received', 0)}/{ping_data.get('packets_transmitted', 0)} received")
    print(f"📉 Loss: {ping_data.get('packet_loss_percent', 0):.1f}%")
    print(f"{'='*80}\n")
    
    # Run traceroute
    print(f"{'='*80}")
    print(f"🗺️  TRACEROUTE ({protocol.upper()})")
    print(f"{'='*80}")
    
    trace_start = time.time()
    trace_data = run_traceroute(ip, protocol, max_hops)
    trace_duration = time.time() - trace_start
    
    if trace_data.get('success'):
        print(trace_data.get('raw_output', ''))
        print(f"\n🛤️  Path: {trace_data.get('hop_count', 0)} hops")
        
        # Show hop summary
        for hop in trace_data.get('hops', [])[:5]:  # Show first 5 hops
            delay = hop.get('delay_ms')
            delay_str = f"{delay:.2f} ms" if delay is not None else "* * *"
            print(f"   {hop['ttl']:2d}. {hop['hostname']:30s} {delay_str}")
        
        if trace_data.get('hop_count', 0) > 5:
            print(f"   ... ({trace_data.get('hop_count', 0) - 5} more hops)")
    else:
        print(f"⚠️  Traceroute failed: {trace_data.get('error', 'Unknown error')}")
    
    print(f"{'='*80}\n")
    
    # Calculate SmartPing score
    score = calculate_smartping_score(ping_data, trace_data)
    reachable = ping_data.get('success', False)
    status, status_label = determine_status(score, reachable)
    
    # Build metadata
    context.metadata = {
        'target': target,
        'hostname': hostname,
        'ip': ip,
        'port': port,
        'protocol': protocol,
        'timestamp': datetime.now().isoformat(),
        'device_name': device.device_name,
        'device_model': device.device_model,
        'host_name': context.host.host_name,
        
        # SmartPing metrics
        'smartping_score': round(score, 1),
        'service_reachability': reachable,
        'status': status,
        'status_label': status_label,
        
        # Ping metrics
        'rtt_min_ms': rtt_stats.get('min', 0),
        'rtt_avg_ms': rtt_stats.get('avg', 0),
        'rtt_max_ms': rtt_stats.get('max', 0),
        'jitter_ms': rtt_stats.get('stddev', 0),
        'packets_transmitted': ping_data.get('packets_transmitted', 0),
        'packets_received': ping_data.get('packets_received', 0),
        'packet_loss_percent': ping_data.get('packet_loss_percent', 0),
        
        # Traceroute metrics
        'hop_count': trace_data.get('hop_count', 0),
        'hops': trace_data.get('hops', []),
        
        # Timing
        'ping_duration_seconds': round(ping_duration, 2),
        'trace_duration_seconds': round(trace_duration, 2),
        'total_duration_seconds': round(ping_duration + trace_duration, 2),
    }
    
    # Print summary
    print(f"{'='*80}")
    print(f"🎯 SMARTPING SUMMARY")
    print(f"{'='*80}")
    print(f"🌐 Target: {hostname} ({ip}:{port})")
    print(f"📡 Protocol: {protocol.upper()}")
    print(f"📱 Device: {device.device_name}")
    print(f"🖥️  Host: {context.host.host_name}")
    print(f"")
    print(f"🏆 SmartPing Score: {score:.1f}/100")
    print(f"📊 Status: {status_label}")
    print(f"")
    print(f"⏱️  RTT: {rtt_stats.get('avg', 0):.2f} ms (min: {rtt_stats.get('min', 0):.2f}, max: {rtt_stats.get('max', 0):.2f})")
    print(f"📶 Jitter: {rtt_stats.get('stddev', 0):.2f} ms")
    print(f"📦 Packets: {ping_data.get('packets_received', 0)}/{ping_data.get('packets_transmitted', 0)} received ({100 - ping_data.get('packet_loss_percent', 0):.1f}% success)")
    print(f"🛤️  Hops: {trace_data.get('hop_count', 0)}")
    print(f"⏱️  Total Time: {ping_duration + trace_duration:.2f}s")
    print(f"{'='*80}\n")
    
    # Build traceroute path summary for execution summary
    path_summary = ""
    hops = trace_data.get('hops', [])
    if hops and len(hops) > 0:
        path_summary = "\n🛤️  Network Path:\n"
        
        # Show first hop (gateway)
        if len(hops) > 0:
            first_hop = hops[0]
            delay_str = f"{first_hop.get('delay_ms', 0):.1f}ms" if first_hop.get('delay_ms') else "* ms"
            path_summary += f"   1. {first_hop.get('hostname', 'unknown'):20s} {delay_str:>8s}\n"
        
        # Show middle hops if path is long (condensed)
        if len(hops) > 3:
            path_summary += f"   ... ({len(hops) - 2} intermediate hops)\n"
        elif len(hops) == 3:
            # Show middle hop for 3-hop paths
            mid_hop = hops[1]
            delay_str = f"{mid_hop.get('delay_ms', 0):.1f}ms" if mid_hop.get('delay_ms') else "* ms"
            path_summary += f"   {mid_hop.get('ttl', 2)}. {mid_hop.get('hostname', 'unknown'):20s} {delay_str:>8s}\n"
        
        # Show last hop (destination)
        if len(hops) > 1:
            last_hop = hops[-1]
            delay_str = f"{last_hop.get('delay_ms', 0):.1f}ms" if last_hop.get('delay_ms') else "* ms"
            path_summary += f"   {last_hop.get('ttl', len(hops))}. {last_hop.get('hostname', 'unknown'):20s} {delay_str:>8s}\n"
    else:
        path_summary = f"\n🛤️  Network Path: {trace_data.get('hop_count', 0)} hops\n"
    
    # Set execution summary
    context.execution_summary = f"""🌐 SMARTPING ANALYSIS SUMMARY
📱 Device: {device.device_name} ({device.device_model})
🖥️  Host: {context.host.host_name}
🎯 Target: {hostname} ({ip}:{port})
📡 Protocol: {protocol.upper()}

🏆 SmartPing Score: {score:.1f}/100
📊 Status: {status_label}

⏱️  RTT: {rtt_stats.get('avg', 0):.2f} ms (±{rtt_stats.get('stddev', 0):.2f} ms jitter)
📦 Packets: {ping_data.get('packets_received', 0)}/{ping_data.get('packets_transmitted', 0)} ({100 - ping_data.get('packet_loss_percent', 0):.1f}% success){path_summary}
🎯 Result: {status}"""
    
    context.overall_success = True
    return True


main._script_args = _script_args

if __name__ == "__main__":
    main()

