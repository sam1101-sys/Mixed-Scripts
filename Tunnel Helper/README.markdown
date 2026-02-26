# Tunnel Helper

Cross-platform installer, configurator, and connector for pivot/tunneling tools.

## Main Goal

The script is now centered on **operational workflow** instead of just install:

- `install`: get the tool
- `configure`: generate config / set auth
- `connect`: run the tunnel/pivot command
- `all`: do install + configure + connect in one command

It can also auto-reconnect when a connection drops.

## Providers

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

## Quick Help

```bash
python3 tunnel_setup.py --help
python3 tunnel_setup.py --help-examples
```

## Core Flags

- `--provider <name>`
- `--action install|configure|connect|all` (default `all`)
- `--keep-connected` (restart on disconnect)
- `--retry-delay <seconds>` (default `5`)
- `--connect-command "..."` (override generated connect command)

Shared pivot params:

- `--role server|client`
- `--target-host`, `--target-port`
- `--listen-host`, `--listen-port`
- `--remote-host`, `--remote-port`
- `--shared-secret`

## Examples

### Chisel reverse SOCKS (kept connected)

Server:

```bash
python3 tunnel_setup.py \
  --provider chisel \
  --action all \
  --role server \
  --listen-port 8001 \
  --keep-connected
```

Client:

```bash
python3 tunnel_setup.py \
  --provider chisel \
  --action all \
  --role client \
  --target-host <server-ip> \
  --target-port 8001 \
  --chisel-remote R:1080:socks \
  --keep-connected
```

### SSH dynamic SOCKS with auto-reconnect

```bash
python3 tunnel_setup.py \
  --provider ssh-dynamic \
  --action connect \
  --ssh-user alice \
  --ssh-host jump.example.com \
  --socks-port 1080 \
  --keep-connected
```

### Proxychains config + usage

```bash
python3 tunnel_setup.py --provider proxychains --action configure --proxy-port 1080
python3 tunnel_setup.py --provider proxychains --action connect --proxychains-command "nmap -sT 10.10.10.0/24"
```

### FRP server/client with generated configs

Server:

```bash
python3 tunnel_setup.py \
  --provider frp \
  --action all \
  --role server \
  --listen-port 7000 \
  --shared-secret change-me
```

Client:

```bash
python3 tunnel_setup.py \
  --provider frp \
  --action all \
  --role client \
  --target-host <frps-ip> \
  --target-port 7000 \
  --remote-host 127.0.0.1 \
  --remote-port 22 \
  --listen-port 6000 \
  --shared-secret change-me
```

### Rathole server/client with generated configs

Server:

```bash
python3 tunnel_setup.py --provider rathole --action all --role server --listen-port 7000 --remote-port 6000 --shared-secret change-me
```

Client:

```bash
python3 tunnel_setup.py --provider rathole --action all --role client --target-host <server-ip> --target-port 7000 --remote-host 127.0.0.1 --remote-port 22 --shared-secret change-me
```

### Ligolo-ng

Server side:

```bash
python3 tunnel_setup.py --provider ligolo-ng --action connect --role server --keep-connected
```

Agent side:

```bash
python3 tunnel_setup.py --provider ligolo-ng --action connect --role client --target-host <c2-ip> --target-port 11601 --keep-connected
```

## Config Output

Generated configs are stored under:

- Default: `~/.tunnel_helper`
- Override: `--config-dir <path>`

## Notes

- For `ngrok`, pass authtoken in configure/all mode: `--ngrok-authtoken <token>`.
- If command names differ in your distro/path, use `--connect-command`.
- `--keep-connected` is best for unstable links/pivots.
