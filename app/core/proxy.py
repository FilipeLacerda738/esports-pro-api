import ipaddress
import os
from pathlib import Path
from app.core.config import settings


def trusted_proxy_networks():
    configured = settings.TRUSTED_PROXY_CIDRS
    if not configured and os.environ.get('RENDER') == 'true':
        cloudflare = (Path(__file__).resolve().parents[2] / 'security/cloudflare-proxies.txt').read_text().splitlines()
        configured = ','.join(['10.0.0.0/8', '172.16.0.0/12', '192.168.0.0/16', *cloudflare])
    return tuple(ipaddress.ip_network(value.strip()) for value in configured.split(',') if value.strip())


def client_identity(scope, trusted):
    client = scope.get('client')
    if not client:
        return 'unknown'
    try:
        peer = ipaddress.ip_address(client[0])
        if not any(peer in network for network in trusted):
            return str(peer)
        headers = [value for key, value in scope.get('headers', []) if key.lower() == b'x-forwarded-for']
        if len(headers) != 1 or len(headers[0]) > 1024:
            return str(peer)
        chain = [ipaddress.ip_address(value.strip()) for value in headers[0].decode('ascii').split(',')]
        if len(chain) > 20:
            return str(peer)
        for address in reversed(chain):
            if not any(address in network for network in trusted):
                return str(address)
        return str(peer)
    except (ValueError, UnicodeError):
        return client[0]
