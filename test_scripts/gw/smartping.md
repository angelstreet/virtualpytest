# SmartPing - Network Quality Monitoring

## Overview

**SmartPing** is a comprehensive network quality monitoring tool for VirtualPyTest that performs path analysis and measures Quality of Service (QoS) metrics to target endpoints. It combines ping tests with traceroute to provide a complete picture of network performance and reachability.

## What SmartPing Tests

SmartPing performs two main network diagnostics:

### 1. **Ping Test**
Measures the round-trip time (RTT) and packet loss to a target by sending multiple probe packets and analyzing the responses.

### 2. **Traceroute**
Maps the complete network path from the device to the target, showing every intermediate hop (router/gateway) along the route with delay measurements.

## Protocols Supported

SmartPing supports three different network protocols:

- **ICMP** (Internet Control Message Protocol)
  - Standard ping protocol
  - Best for general network testing
  - Requires no port specification
  - May be blocked by some firewalls

- **TCP** (Transmission Control Protocol)
  - Tests actual TCP connection establishment
  - Best for testing service availability (web servers, APIs)
  - Uses specified port (default: 443 for HTTPS)
  - More likely to pass through firewalls

- **UDP** (User Datagram Protocol)
  - Tests UDP packet delivery
  - Useful for streaming services testing
  - Connectionless protocol
  - Good for detecting specific network policies

## Parameters

### Command Line Arguments

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `--target` | string | `google.com` | Target URL or IP address (can include :port) |
| `--protocol` | string | `icmp` | Protocol to use: `icmp`, `tcp`, or `udp` |
| `--count` | integer | `5` | Number of ping attempts to send |
| `--max_hops` | integer | `30` | Maximum number of hops for traceroute |
| `--host` | string | *(auto)* | Specific host to run test from |
| `--device` | string | *(auto)* | Specific device to run test on |

### Parameter Details

#### `--target`
The destination to test connectivity to. Can be:
- Hostname: `google.com`
- Hostname with port: `youtube.com:443`
- IP address: `8.8.8.8`
- IP with port: `142.250.190.78:443`

#### `--protocol`
Determines how network probes are sent:
- `icmp` - Classic ping (default, works without port)
- `tcp` - TCP connection test (specify port in target)
- `udp` - UDP packet test

#### `--count`
Number of ping attempts. More attempts = more accurate statistics but longer execution time.
- Minimum: `1`
- Recommended: `5-10`
- For detailed analysis: `20+`

#### `--max_hops`
Maximum number of network hops to trace. Limits how deep the traceroute goes.
- Typical internet paths: `10-20` hops
- Default: `30` (covers most scenarios)
- Increase for complex routing scenarios

## Metrics Collected

SmartPing measures and records comprehensive network quality metrics:

### Overall Metrics

| Metric | Unit | Description |
|--------|------|-------------|
| **SmartPing Score** | 0-100 | Overall network quality score (100 = excellent, 0 = failure) |
| **Service Reachability** | boolean | Whether the target is reachable |
| **Status** | string | Network status: `EXCELLENT`, `GOOD`, `DEGRADED`, `POOR`, `DOWN` |

### RTT (Round Trip Time) Metrics

| Metric | Unit | Description |
|--------|------|-------------|
| **RTT Min** | milliseconds | Fastest response time |
| **RTT Avg** | milliseconds | Average response time |
| **RTT Max** | milliseconds | Slowest response time |
| **Jitter** | milliseconds | Variation in RTT (standard deviation) |

### Packet Statistics

| Metric | Unit | Description |
|--------|------|-------------|
| **Packets Transmitted** | count | Total packets sent |
| **Packets Received** | count | Total packets received |
| **Packet Loss %** | percentage | Percentage of lost packets |

### Path Metrics

| Metric | Unit | Description |
|--------|------|-------------|
| **Hop Count** | count | Number of network hops to target |
| **Hops** | array | Detailed hop-by-hop data (TTL, IP, hostname, delay) |

### Performance Metrics

| Metric | Unit | Description |
|--------|------|-------------|
| **Ping Duration** | seconds | Time taken for ping test |
| **Trace Duration** | seconds | Time taken for traceroute |
| **Total Duration** | seconds | Total test execution time |

## SmartPing Score Calculation

The SmartPing Score (0-100) is calculated based on multiple network quality factors:

```
Starting Score: 100

Deductions:
- Packet Loss:  up to -40 points  (0.4 points per 1% loss)
- High RTT:     up to -30 points  (>200ms = -30, >100ms = -20, >50ms = -10)
- High Jitter:  up to -20 points  (>50ms = -20, >20ms = -10, >10ms = -5)
- Long Path:    up to -10 points  (>20 hops = -10, >15 hops = -5)
```

### Score Interpretation

| Score Range | Status | Description |
|-------------|--------|-------------|
| **80-100** | 🟢 EXCELLENT | Optimal network quality |
| **60-79** | 🟡 GOOD | Good network quality, minor issues |
| **40-59** | 🟠 DEGRADED | Network degradation detected |
| **0-39** | 🔴 POOR | Severe network issues |
| **N/A** | ⚫ DOWN | Service unreachable |

## Usage Examples

### Basic Examples

```bash
# Test connectivity to Google (ICMP)
python test_scripts/gw/smartping.py

# Test YouTube HTTPS connectivity (TCP)
python test_scripts/gw/smartping.py --target youtube.com:443 --protocol tcp

# Test DNS server (ICMP)
python test_scripts/gw/smartping.py --target 8.8.8.8 --protocol icmp

# Test with more samples for accuracy
python test_scripts/gw/smartping.py --target google.com --count 20
```

### Advanced Examples

```bash
# Test EPG service from specific host/device
python test_scripts/gw/smartping.py \
  --target epg.prod.ch.dmdsdp.com:443 \
  --protocol tcp \
  --host sunri-pi1 \
  --device device1

# Test with detailed traceroute (more hops)
python test_scripts/gw/smartping.py \
  --target youtube.com:443 \
  --protocol tcp \
  --count 10 \
  --max_hops 50

# Quick UDP test
python test_scripts/gw/smartping.py \
  --target 8.8.8.8 \
  --protocol udp \
  --count 3
```

### Protocol Selection Guide

**Use ICMP when:**
- Testing general network connectivity
- Measuring pure network latency
- Testing internal network infrastructure
- No specific service port needed

**Use TCP when:**
- Testing web services (HTTP/HTTPS)
- Testing API endpoints
- Verifying service availability
- Testing through firewalls (TCP more likely to pass)

**Use UDP when:**
- Testing streaming services
- Testing UDP-based protocols (DNS, VoIP)
- Detecting UDP-specific network policies
- Testing packet loss on connectionless protocol

## Output

### Console Output

SmartPing provides real-time formatted output during execution:

```
🌐 [smartping] Target: youtube.com:443
📡 [smartping] Protocol: TCP
📱 [smartping] Device: sunri-pi1 (Raspberry Pi)
🖥️  [smartping] Host: sunri-pi1
🔍 [smartping] Resolved: youtube.com -> 142.250.190.78:443

================================================================================
🏓 PING TEST (TCP)
================================================================================
TCP connect to 142.250.190.78:443 - 5/5 successful

📊 RTT Statistics:
   Min:    23.45 ms
   Avg:    25.67 ms
   Max:    28.90 ms
   Jitter: 2.12 ms
📦 Packets: 5/5 received
📉 Loss: 0.0%
================================================================================

================================================================================
🗺️  TRACEROUTE (TCP)
================================================================================
traceroute to 142.250.190.78 (142.250.190.78), 30 hops max
 1  192.168.1.1 (192.168.1.1)  1.234 ms
 2  10.0.0.1 (10.0.0.1)  5.678 ms
 ...
 12  142.250.190.78 (142.250.190.78)  25.67 ms

🛤️  Path: 12 hops
================================================================================

================================================================================
🎯 SMARTPING SUMMARY
================================================================================
🌐 Target: youtube.com (142.250.190.78:443)
📡 Protocol: TCP
📱 Device: sunri-pi1
🖥️  Host: sunri-pi1

🏆 SmartPing Score: 87.3/100
📊 Status: ✅ Excellent network quality

⏱️  RTT: 25.67 ms (min: 23.45, max: 28.90)
📶 Jitter: 2.12 ms
📦 Packets: 5/5 received (100.0% success)
🛤️  Hops: 12
⏱️  Total Time: 3.45s
================================================================================
```

### Database Storage

All results are automatically stored in the `script_results` table with:

**Standard Fields:**
- `script_name`: `"smartping"`
- `script_type`: `"network"`
- `host_name`: Source host
- `device_name`: Source device
- `success`: Boolean (true if reachable)
- `execution_time_ms`: Total execution time
- `completed_at`: Timestamp

**Metadata (JSONB):**
```json
{
  "target": "youtube.com:443",
  "hostname": "youtube.com",
  "ip": "142.250.190.78",
  "port": 443,
  "protocol": "tcp",
  "smartping_score": 87.3,
  "service_reachability": true,
  "status": "EXCELLENT",
  "status_label": "✅ Excellent network quality",
  "rtt_min_ms": 23.45,
  "rtt_avg_ms": 25.67,
  "rtt_max_ms": 28.90,
  "jitter_ms": 2.12,
  "packets_transmitted": 5,
  "packets_received": 5,
  "packet_loss_percent": 0.0,
  "hop_count": 12,
  "hops": [
    {
      "idx": 0,
      "ttl": 1,
      "hostname": "gateway",
      "ip": "192.168.1.1",
      "delay_ms": 1.234
    },
    ...
  ],
  "ping_duration_seconds": 2.5,
  "trace_duration_seconds": 0.95,
  "total_duration_seconds": 3.45
}
```

## Grafana Dashboard

SmartPing includes a dedicated Grafana dashboard for visualization and monitoring.

**Dashboard UID:** `smartping-dashboard`

**URL:** `/grafana/d/smartping-dashboard/smartping-network-quality`

### Dashboard Panels

1. **Current Network Metrics** - Latest RTT, jitter, packet loss, and score
2. **RTT Trends** - Time series of Min/Avg/Max RTT
3. **SmartPing Score & Packet Loss** - Network quality over time
4. **Recent Tests Table** - Detailed view of last 50 tests

### Dashboard Variables

- **Host Filter** - Filter by source host
- **Device Filter** - Filter by source device
- **Target Filter** - Filter by destination target

## Use Cases

### 1. Service Availability Monitoring
Monitor critical services (APIs, websites) for availability and performance:
```bash
python test_scripts/gw/smartping.py --target api.example.com:443 --protocol tcp
```

### 2. Network Troubleshooting
Diagnose network issues by analyzing the complete path:
```bash
python test_scripts/gw/smartping.py --target slow-service.com --count 20 --max_hops 50
```

### 3. Performance Baseline
Establish network performance baselines for comparison:
```bash
python test_scripts/gw/smartping.py --target internal-server.local --count 100
```

### 4. Multi-Protocol Testing
Compare different protocols to the same target:
```bash
python test_scripts/gw/smartping.py --target example.com --protocol icmp
python test_scripts/gw/smartping.py --target example.com:443 --protocol tcp
python test_scripts/gw/smartping.py --target example.com:53 --protocol udp
```

### 5. Geographic Network Analysis
Test network paths to different geographic locations:
```bash
python test_scripts/gw/smartping.py --target us-server.example.com
python test_scripts/gw/smartping.py --target eu-server.example.com
python test_scripts/gw/smartping.py --target asia-server.example.com
```

## Interpretation Guide

### Good Network Health Indicators
- ✅ SmartPing Score > 80
- ✅ Packet Loss < 1%
- ✅ RTT Average < 50ms
- ✅ Jitter < 10ms
- ✅ Consistent hop count

### Warning Signs
- ⚠️ Score 60-80: Minor degradation
- ⚠️ Packet Loss 1-5%: Network congestion possible
- ⚠️ RTT 50-100ms: Increased latency
- ⚠️ Jitter 10-20ms: Network instability
- ⚠️ Hop count increasing: Route changes

### Critical Issues
- 🔴 Score < 60: Significant problems
- 🔴 Packet Loss > 5%: Serious network issues
- 🔴 RTT > 200ms: Severe latency
- 🔴 Jitter > 50ms: Major instability
- 🔴 Service unreachable: Complete failure

## Troubleshooting

### "traceroute command not found"
If you see this error, traceroute is not installed. 

**Quick Fix (Automatic):**
```bash
bash test_scripts/gw/install_traceroute.sh
```

**Or install manually:**

**Ubuntu/Debian/Raspberry Pi:**
```bash
sudo apt-get update && sudo apt-get install traceroute
```

**CentOS/RHEL:**
```bash
sudo yum install traceroute
```

After installation, SmartPing will automatically detect traceroute in `/usr/sbin/traceroute` or `/usr/bin/traceroute`.

### SmartPing Fails with "Permission Denied"
Some protocols (especially ICMP and TCP traceroute) may require elevated privileges:
```bash
sudo python test_scripts/gw/smartping.py --target google.com
```

### High Packet Loss on UDP
UDP packet loss doesn't always indicate problems - many services don't respond to UDP probes. Try TCP or ICMP instead.

### Traceroute Shows Many "* * *" Hops
Some routers don't respond to traceroute probes. This is normal and doesn't indicate a problem if the target is still reachable.

### Timeout Issues
Increase the count or use a closer target for testing:
```bash
python test_scripts/gw/smartping.py --target 8.8.8.8 --count 3
```

## Integration

SmartPing integrates seamlessly with VirtualPyTest:

- **Automatic Database Recording** - All results stored in `script_results` table
- **Device Context** - Runs on specified device/host
- **Grafana Integration** - Results automatically visible in dashboard
- **Script Framework** - Uses standard `@script` decorator
- **Report Generation** - Execution summary included in reports

## Technical Details

### System Commands Used
- **Linux/macOS Ping**: `ping -c <count> -W <timeout> <target>`
- **TCP Socket**: Python `socket.connect_ex()` for TCP testing
- **UDP Socket**: Python `socket.sendto()` for UDP testing
- **Traceroute**: `traceroute -T/-U/-I` depending on protocol

### Script Type
- **Type**: `network` (non-UI script)
- **Requires Device Lock**: Yes (for context tracking)
- **Requires UI Interface**: No
- **Requires Navigation**: No

### Dependencies
- Python 3.x standard library
- System `ping` command (pre-installed on most systems)
- System `traceroute` command
- VirtualPyTest shared libraries

### Installing traceroute

If you see the error `traceroute command not found`, install it:

**Quick Install (Automatic):**
```bash
bash test_scripts/gw/install_traceroute.sh
```

**Manual Install:**

**Ubuntu/Debian/Raspberry Pi:**
```bash
sudo apt-get update
sudo apt-get install traceroute
```

**CentOS/RHEL:**
```bash
sudo yum install traceroute
```

**Fedora:**
```bash
sudo dnf install traceroute
```

**macOS:**
Traceroute is pre-installed on macOS.

## Comparison with DNS Lookup

| Feature | SmartPing | DNS Lookup |
|---------|-----------|------------|
| **Purpose** | Network quality & path | DNS resolution time |
| **Protocols** | ICMP, TCP, UDP | DNS (UDP/TCP port 53) |
| **Metrics** | RTT, jitter, loss, hops | Lookup time only |
| **Path Analysis** | Yes (traceroute) | No |
| **Service Check** | Yes | No |
| **Typical Duration** | 5-15 seconds | 1-3 seconds |

## Best Practices

1. **Use TCP for Service Testing** - More accurate for actual service availability
2. **Run Regular Baselines** - Establish what "normal" looks like
3. **Test Multiple Protocols** - Different protocols may show different issues
4. **Monitor Trends** - Watch for gradual degradation over time
5. **Set Appropriate Count** - Balance accuracy vs execution time
6. **Document Targets** - Keep a list of critical endpoints to monitor
7. **Combine with DNS Tests** - Use both SmartPing and DNS lookup for complete picture

## Related Documentation

- [DNS Lookup Time](./dns_lookuptime.md) - DNS resolution performance testing
- [Script Results Dashboard](./script_results_dashboard.md) - Viewing test results
- [Grafana Integration](./architecture/GRAFANA_INTEGRATION.md) - Monitoring setup

## Support

For issues or questions:
- Check the [troubleshooting section](#troubleshooting) above
- Review test output for specific error messages
- Verify network connectivity with basic `ping` command first
- Check Grafana dashboard for historical patterns

