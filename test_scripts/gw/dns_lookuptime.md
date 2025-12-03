# dns_lookuptime

Performs DNS lookup and measures response time.

## Usage

```bash
python test_scripts/gw/dns_lookuptime.py                           # Default domain
python test_scripts/gw/dns_lookuptime.py --dns google.com          # Custom domain
python test_scripts/gw/dns_lookuptime.py --dns api.example.com --host sunri-pi1
```

## Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `--dns` | string | `epg.prod.ch.dmdsdp.com` | Domain to lookup |

## Output

Stores in metadata:
- `lookup_time_ms` - DNS resolution time
- `dns_server` - DNS server used
- `ipv4_addresses` - Resolved IPv4 addresses
- `ipv6_addresses` - Resolved IPv6 addresses
- `canonical_name` - CNAME if present

