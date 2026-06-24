from pathlib import Path

p = Path('/opt/caddy-proxy/Caddyfile')
s = p.read_text()
insert = '''hitchpinlabs.com {
    handle_path /ecosystem-map/admin* {
        respond "Admin is not public. Use the private Tailnet instance until authentication is added." 403
    }
    handle_path /ecosystem-map/submit* {
        respond "Public submissions are disabled on the internet deployment. Use the private Tailnet instance." 403
    }
    handle_path /ecosystem-map/* {
        reverse_proxy localhost:3057
    }
    redir /ecosystem-map /ecosystem-map/ 308
'''
if 'handle_path /ecosystem-map/*' in s:
    print('Caddy route already present')
else:
    marker = 'hitchpinlabs.com {\n'
    if marker not in s:
        raise SystemExit('hitchpinlabs.com block not found')
    p.write_text(s.replace(marker, insert, 1))
    print('Inserted ecosystem map route')
