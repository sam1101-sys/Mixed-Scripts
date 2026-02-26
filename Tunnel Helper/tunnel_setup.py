#!/usr/bin/env python3
"""Tunnel/pivot tool installer, configurator, and connector."""

from __future__ import annotations

import argparse
import gzip
import json
import platform
import shlex
import shutil
import stat
import subprocess
import sys
import tarfile
import tempfile
import time
import urllib.request
import zipfile
from pathlib import Path

PROVIDERS = [
    "cloudflared",
    "ngrok",
    "localtunnel",
    "proxychains",
    "ssh-dynamic",
    "socat",
    "chisel",
    "bore",
    "rathole",
    "frp",
    "ligolo-ng",
]


def detect_platform() -> tuple[str, str]:
    os_name = platform.system().lower()
    machine = platform.machine().lower()

    arch_map = {
        "x86_64": "amd64",
        "amd64": "amd64",
        "aarch64": "arm64",
        "arm64": "arm64",
        "armv7l": "arm",
    }

    if os_name not in {"linux", "darwin", "windows"}:
        raise RuntimeError(f"Unsupported OS: {platform.system()}")

    arch = arch_map.get(machine)
    if not arch:
        raise RuntimeError(f"Unsupported CPU architecture: {platform.machine()}")

    return os_name, arch


def ensure_executable(file_path: Path) -> None:
    if platform.system().lower() == "windows":
        return
    mode = file_path.stat().st_mode
    file_path.chmod(mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def default_install_dir(os_name: str) -> Path:
    if os_name == "windows":
        return Path.home() / "bin"
    return Path.home() / ".local" / "bin"


def default_config_dir() -> Path:
    return Path.home() / ".tunnel_helper"


def download_file(url: str, output_path: Path) -> None:
    print(f"[+] Downloading: {url}")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(url, headers={"User-Agent": "tunnel-helper/1.0"})
    with urllib.request.urlopen(req) as response, output_path.open("wb") as out_file:
        shutil.copyfileobj(response, out_file)


def run_command(cmd: list[str], purpose: str) -> None:
    print(f"[+] {purpose}: {' '.join(cmd)}")
    completed = subprocess.run(cmd, check=False)
    if completed.returncode != 0:
        raise RuntimeError(f"Command failed ({completed.returncode}): {' '.join(cmd)}")


def run_connect_command(cmd: list[str], keep_connected: bool, retry_delay: int) -> int:
    if not keep_connected:
        return subprocess.run(cmd, check=False).returncode

    while True:
        print(f"[+] Starting connection command: {' '.join(cmd)}")
        rc = subprocess.run(cmd, check=False).returncode
        print(f"[!] Connection command exited with code {rc}. Restarting in {retry_delay}s...")
        time.sleep(retry_delay)


def detect_linux_package_manager() -> str | None:
    for manager in ("apt", "dnf", "yum", "pacman", "zypper", "apk"):
        if shutil.which(manager):
            return manager
    return None


def github_latest_assets(repo: str) -> list[dict[str, str]]:
    url = f"https://api.github.com/repos/{repo}/releases/latest"
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "tunnel-helper/1.0", "Accept": "application/vnd.github+json"},
    )
    with urllib.request.urlopen(req) as response:
        data = json.loads(response.read().decode("utf-8"))

    assets = data.get("assets", [])
    out: list[dict[str, str]] = []
    for asset in assets:
        name = asset.get("name")
        dl = asset.get("browser_download_url")
        if isinstance(name, str) and isinstance(dl, str):
            out.append({"name": name, "url": dl})

    if not out:
        raise RuntimeError(f"No downloadable assets found in latest release for {repo}")

    return out


def os_keywords(os_name: str) -> list[str]:
    if os_name == "linux":
        return ["linux", "gnu", "musl", "unknown-linux"]
    if os_name == "darwin":
        return ["darwin", "mac", "macos", "osx", "apple-darwin"]
    return ["windows", "win", "pc-windows", "mingw"]


def arch_keywords(arch: str) -> list[str]:
    if arch == "amd64":
        return ["amd64", "x86_64", "x64"]
    if arch == "arm64":
        return ["arm64", "aarch64"]
    return ["arm", "armv7"]


def select_release_asset(
    assets: list[dict[str, str]],
    os_name: str,
    arch: str,
    name_hints: list[str],
) -> dict[str, str]:
    os_keys = os_keywords(os_name)
    arch_keys = arch_keywords(arch)

    ranked: list[tuple[int, dict[str, str]]] = []
    for asset in assets:
        name = asset["name"].lower()
        score = 0

        if any(k in name for k in os_keys):
            score += 4
        if any(k in name for k in arch_keys):
            score += 4
        if any(h in name for h in name_hints):
            score += 3

        if name.endswith((".tar.gz", ".tgz", ".zip")):
            score += 2
        elif name.endswith((".gz", ".exe")):
            score += 1

        if "sha" in name or "checksum" in name or name.endswith((".txt", ".sig")):
            score -= 10

        ranked.append((score, asset))

    ranked.sort(key=lambda item: item[0], reverse=True)
    best_score, best_asset = ranked[0]
    if best_score < 4:
        sample = ", ".join(a["name"] for a in assets[:8])
        raise RuntimeError(f"Could not confidently select release asset. Seen: {sample}")

    return best_asset


def extract_asset(archive_path: Path, extract_dir: Path) -> None:
    name = archive_path.name.lower()

    if name.endswith(".zip"):
        with zipfile.ZipFile(archive_path, "r") as zf:
            zf.extractall(extract_dir)
        return

    if name.endswith((".tar.gz", ".tgz", ".tar")):
        with tarfile.open(archive_path, "r:*") as tf:
            tf.extractall(extract_dir)
        return

    if name.endswith(".gz") and not name.endswith((".tar.gz", ".tgz")):
        out_file = extract_dir / archive_path.name[:-3]
        with gzip.open(archive_path, "rb") as src, out_file.open("wb") as dst:
            shutil.copyfileobj(src, dst)
        return

    shutil.copy2(archive_path, extract_dir / archive_path.name)


def normalize_bin_name(path: Path) -> str:
    name = path.name.lower()
    if name.endswith(".exe"):
        name = name[:-4]
    return name


def collect_candidate_binaries(extract_dir: Path, expected_bins: list[str]) -> list[Path]:
    expected = {name.lower() for name in expected_bins}
    candidates: list[Path] = []

    for file_path in extract_dir.rglob("*"):
        if not file_path.is_file():
            continue
        norm = normalize_bin_name(file_path)
        if expected and (norm in expected or any(norm.startswith(name) for name in expected)):
            candidates.append(file_path)

    if candidates:
        return sorted(candidates)

    for file_path in extract_dir.rglob("*"):
        if not file_path.is_file():
            continue
        lname = file_path.name.lower()
        if lname.endswith((".md", ".txt", ".yaml", ".yml", ".json", ".toml", ".sig")):
            continue
        if file_path.stat().st_size < 50_000:
            continue
        candidates.append(file_path)

    return sorted(candidates)


def install_binaries_from_paths(binary_paths: list[Path], install_dir: Path, os_name: str) -> list[Path]:
    install_dir.mkdir(parents=True, exist_ok=True)
    installed: list[Path] = []

    for src in binary_paths:
        target_name = src.name
        if os_name != "windows" and target_name.endswith(".exe"):
            target_name = target_name[:-4]
        dst = install_dir / target_name
        shutil.copy2(src, dst)
        ensure_executable(dst)
        installed.append(dst)

    if not installed:
        raise RuntimeError("No binaries were installed from selected release asset")

    return installed


def install_from_github_release(
    os_name: str,
    arch: str,
    install_dir: Path,
    repo: str,
    name_hints: list[str],
    expected_bins: list[str],
) -> list[Path]:
    assets = github_latest_assets(repo)
    asset = select_release_asset(assets, os_name, arch, name_hints)

    with tempfile.TemporaryDirectory() as td:
        tmp_dir = Path(td)
        archive_path = tmp_dir / asset["name"]
        extract_dir = tmp_dir / "extract"
        extract_dir.mkdir(parents=True, exist_ok=True)

        download_file(asset["url"], archive_path)
        extract_asset(archive_path, extract_dir)

        binaries = collect_candidate_binaries(extract_dir, expected_bins)
        if not binaries:
            raise RuntimeError(f"No executable candidates found in asset {asset['name']}")

        return install_binaries_from_paths(binaries, install_dir, os_name)


def install_cloudflared(os_name: str, arch: str, install_dir: Path) -> list[Path]:
    suffix = ".exe" if os_name == "windows" else ""
    combos = {
        ("linux", "amd64"): "cloudflared-linux-amd64",
        ("linux", "arm64"): "cloudflared-linux-arm64",
        ("darwin", "amd64"): "cloudflared-darwin-amd64",
        ("darwin", "arm64"): "cloudflared-darwin-arm64",
        ("windows", "amd64"): "cloudflared-windows-amd64.exe",
        ("windows", "arm64"): "cloudflared-windows-arm64.exe",
    }
    target = combos.get((os_name, arch))
    if not target:
        raise RuntimeError(f"cloudflared does not support {os_name}/{arch}")

    install_dir.mkdir(parents=True, exist_ok=True)
    destination = install_dir / f"cloudflared{suffix}"
    download_file(f"https://github.com/cloudflare/cloudflared/releases/latest/download/{target}", destination)
    ensure_executable(destination)
    return [destination]


def install_ngrok(os_name: str, arch: str, install_dir: Path) -> list[Path]:
    combos = {
        ("linux", "amd64"): "linux-amd64",
        ("linux", "arm64"): "linux-arm64",
        ("darwin", "amd64"): "darwin-amd64",
        ("darwin", "arm64"): "darwin-arm64",
        ("windows", "amd64"): "windows-amd64",
        ("windows", "arm64"): "windows-arm64",
    }
    target = combos.get((os_name, arch))
    if not target:
        raise RuntimeError(f"ngrok does not support {os_name}/{arch}")

    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        z = tmp / "ngrok.zip"
        e = tmp / "extract"
        e.mkdir(parents=True, exist_ok=True)
        download_file(f"https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-{target}.zip", z)
        extract_asset(z, e)
        name = "ngrok.exe" if os_name == "windows" else "ngrok"
        candidate = e / name
        if not candidate.exists():
            raise RuntimeError("Downloaded ngrok archive did not include expected binary")
        return install_binaries_from_paths([candidate], install_dir, os_name)


def install_localtunnel() -> str:
    npm = shutil.which("npm")
    if not npm:
        raise RuntimeError("npm is required for localtunnel")
    run_command([npm, "install", "-g", "localtunnel"], "Installing localtunnel")
    return "lt"


def install_socat(os_name: str) -> str:
    if shutil.which("socat"):
        return "socat"
    if os_name == "windows":
        raise RuntimeError("socat is not supported natively on Windows")
    if os_name == "darwin":
        brew = shutil.which("brew")
        if not brew:
            raise RuntimeError("Homebrew is required to install socat")
        run_command([brew, "install", "socat"], "Installing socat")
        return "socat"

    manager = detect_linux_package_manager()
    if not manager:
        raise RuntimeError("No supported Linux package manager found for socat")
    if manager == "apt":
        run_command(["sudo", "apt", "update"], "Updating apt")
        run_command(["sudo", "apt", "install", "-y", "socat"], "Installing socat")
    elif manager == "dnf":
        run_command(["sudo", "dnf", "install", "-y", "socat"], "Installing socat")
    elif manager == "yum":
        run_command(["sudo", "yum", "install", "-y", "socat"], "Installing socat")
    elif manager == "pacman":
        run_command(["sudo", "pacman", "-Sy", "--noconfirm", "socat"], "Installing socat")
    elif manager == "zypper":
        run_command(["sudo", "zypper", "install", "-y", "socat"], "Installing socat")
    elif manager == "apk":
        run_command(["sudo", "apk", "add", "socat"], "Installing socat")

    if not shutil.which("socat"):
        raise RuntimeError("socat installation completed but command not found")
    return "socat"


def install_or_detect_proxychains(os_name: str) -> str:
    existing = shutil.which("proxychains4") or shutil.which("proxychains")
    if existing:
        return Path(existing).name

    if os_name == "windows":
        raise RuntimeError("proxychains is not supported natively on Windows")

    if os_name == "darwin":
        brew = shutil.which("brew")
        if not brew:
            raise RuntimeError("Homebrew is required to install proxychains-ng")
        run_command([brew, "install", "proxychains-ng"], "Installing proxychains-ng")
    else:
        manager = detect_linux_package_manager()
        if not manager:
            raise RuntimeError("No supported Linux package manager found for proxychains")
        if manager == "apt":
            run_command(["sudo", "apt", "update"], "Updating apt")
            run_command(["sudo", "apt", "install", "-y", "proxychains4"], "Installing proxychains4")
        elif manager == "dnf":
            run_command(["sudo", "dnf", "install", "-y", "proxychains-ng"], "Installing proxychains-ng")
        elif manager == "yum":
            run_command(["sudo", "yum", "install", "-y", "proxychains-ng"], "Installing proxychains-ng")
        elif manager == "pacman":
            run_command(["sudo", "pacman", "-Sy", "--noconfirm", "proxychains-ng"], "Installing proxychains-ng")
        elif manager == "zypper":
            run_command(["sudo", "zypper", "install", "-y", "proxychains-ng"], "Installing proxychains-ng")
        elif manager == "apk":
            run_command(["sudo", "apk", "add", "proxychains-ng"], "Installing proxychains-ng")

    installed = shutil.which("proxychains4") or shutil.which("proxychains")
    if not installed:
        raise RuntimeError("proxychains installation completed but command not found")
    return Path(installed).name


def install_or_detect_ssh_client(os_name: str) -> str:
    existing = shutil.which("ssh")
    if existing:
        return existing

    if os_name == "windows":
        raise RuntimeError("OpenSSH client not found. Enable Windows OpenSSH Client feature")
    if os_name == "darwin":
        raise RuntimeError("ssh not found on macOS; install Xcode Command Line Tools")

    manager = detect_linux_package_manager()
    if not manager:
        raise RuntimeError("No supported Linux package manager found for openssh")
    if manager == "apt":
        run_command(["sudo", "apt", "update"], "Updating apt")
        run_command(["sudo", "apt", "install", "-y", "openssh-client"], "Installing openssh-client")
    elif manager == "dnf":
        run_command(["sudo", "dnf", "install", "-y", "openssh-clients"], "Installing openssh-clients")
    elif manager == "yum":
        run_command(["sudo", "yum", "install", "-y", "openssh-clients"], "Installing openssh-clients")
    elif manager == "pacman":
        run_command(["sudo", "pacman", "-Sy", "--noconfirm", "openssh"], "Installing openssh")
    elif manager == "zypper":
        run_command(["sudo", "zypper", "install", "-y", "openssh"], "Installing openssh")
    elif manager == "apk":
        run_command(["sudo", "apk", "add", "openssh-client"], "Installing openssh-client")

    installed = shutil.which("ssh")
    if not installed:
        raise RuntimeError("ssh installation completed but command not found")
    return installed


def build_ssh_dynamic_command(args: argparse.Namespace) -> list[str]:
    if not args.ssh_host or not args.ssh_user:
        raise RuntimeError("ssh-dynamic connect requires --ssh-host and --ssh-user")
    cmd = ["ssh", "-N", "-D", f"127.0.0.1:{args.socks_port}", "-p", str(args.ssh_port)]
    if args.ssh_key:
        cmd.extend(["-i", args.ssh_key])
    cmd.append(f"{args.ssh_user}@{args.ssh_host}")
    return cmd


def choose_provider(arg_provider: str | None) -> str:
    if arg_provider:
        provider = arg_provider.lower().strip()
        if provider not in PROVIDERS:
            raise RuntimeError(f"Unknown provider: {arg_provider}. Supported: {', '.join(PROVIDERS)}")
        return provider

    print("Select provider:")
    for idx, provider in enumerate(PROVIDERS, start=1):
        print(f"  {idx}. {provider}")
    selection = input(f"Enter choice (1-{len(PROVIDERS)}): ").strip()
    if not selection.isdigit() or not (1 <= int(selection) <= len(PROVIDERS)):
        raise RuntimeError("Invalid selection")
    return PROVIDERS[int(selection) - 1]


def configure_proxychains(args: argparse.Namespace, config_dir: Path) -> Path:
    path = Path(args.proxychains_config).expanduser() if args.proxychains_config else (config_dir / "proxychains.conf")
    path.parent.mkdir(parents=True, exist_ok=True)
    content = (
        "strict_chain\n"
        "proxy_dns\n"
        "[ProxyList]\n"
        f"{args.proxy_type} {args.proxy_host} {args.proxy_port}\n"
    )
    path.write_text(content, encoding="utf-8")
    return path


def configure_rathole(args: argparse.Namespace, config_dir: Path) -> Path:
    path = config_dir / f"rathole-{args.role}.toml"
    path.parent.mkdir(parents=True, exist_ok=True)
    if args.role == "server":
        listen = f"{args.listen_host}:{args.listen_port}"
        content = (
            "[server]\n"
            f"bind_addr = \"{listen}\"\n\n"
            "[server.services.pivot]\n"
            f"bind_addr = \"{args.listen_host}:{args.remote_port}\"\n"
            f"token = \"{args.shared_secret}\"\n"
        )
    else:
        server_addr = f"{args.target_host}:{args.target_port}"
        content = (
            "[client]\n"
            f"remote_addr = \"{server_addr}\"\n\n"
            "[client.services.pivot]\n"
            f"local_addr = \"{args.remote_host}:{args.remote_port}\"\n"
            f"token = \"{args.shared_secret}\"\n"
        )
    path.write_text(content, encoding="utf-8")
    return path


def configure_frp(args: argparse.Namespace, config_dir: Path) -> Path:
    path = config_dir / ("frps.toml" if args.role == "server" else "frpc.toml")
    path.parent.mkdir(parents=True, exist_ok=True)
    if args.role == "server":
        content = (
            f"bindPort = {args.listen_port}\n"
            f"auth.token = \"{args.shared_secret}\"\n"
        )
    else:
        content = (
            f"serverAddr = \"{args.target_host}\"\n"
            f"serverPort = {args.target_port}\n"
            f"auth.token = \"{args.shared_secret}\"\n\n"
            "[[proxies]]\n"
            "name = \"pivot\"\n"
            "type = \"tcp\"\n"
            f"localIP = \"{args.remote_host}\"\n"
            f"localPort = {args.remote_port}\n"
            f"remotePort = {args.listen_port}\n"
        )
    path.write_text(content, encoding="utf-8")
    return path


def configure_provider(provider: str, args: argparse.Namespace, config_dir: Path) -> dict[str, Path]:
    output: dict[str, Path] = {}
    config_dir.mkdir(parents=True, exist_ok=True)

    if provider == "proxychains":
        path = configure_proxychains(args, config_dir)
        output["proxychains"] = path
        print(f"[+] Wrote proxychains config: {path}")

    if provider == "rathole":
        path = configure_rathole(args, config_dir)
        output["rathole"] = path
        print(f"[+] Wrote rathole config: {path}")

    if provider == "frp":
        path = configure_frp(args, config_dir)
        output["frp"] = path
        print(f"[+] Wrote frp config: {path}")

    if provider == "ngrok" and args.ngrok_authtoken:
        run_command(["ngrok", "config", "add-authtoken", args.ngrok_authtoken], "Configuring ngrok authtoken")

    if provider == "ligolo-ng":
        hint = config_dir / "ligolo-commands.txt"
        hint.write_text(
            "proxy -selfcert\nagent -connect <c2-ip>:11601 -ignore-cert\n",
            encoding="utf-8",
        )
        output["ligolo"] = hint
        print(f"[+] Wrote ligolo command hints: {hint}")

    return output


def connect_command_for_provider(
    provider: str,
    args: argparse.Namespace,
    config_paths: dict[str, Path],
) -> list[str]:
    if args.connect_command:
        return shlex.split(args.connect_command)

    if provider == "cloudflared":
        return ["cloudflared", "tunnel", "--url", args.cloudflared_url]

    if provider == "ngrok":
        return ["ngrok", args.ngrok_proto, str(args.target_port)]

    if provider == "localtunnel":
        return ["lt", "--port", str(args.target_port)]

    if provider == "proxychains":
        runner = shutil.which("proxychains4") or "proxychains"
        proxied = shlex.split(args.proxychains_command)
        return [runner, *proxied]

    if provider == "ssh-dynamic":
        return build_ssh_dynamic_command(args)

    if provider == "socat":
        return [
            "socat",
            f"TCP-LISTEN:{args.listen_port},fork,reuseaddr",
            f"TCP:{args.remote_host}:{args.remote_port}",
        ]

    if provider == "chisel":
        if args.role == "server":
            return ["chisel", "server", "--reverse", "-p", str(args.listen_port)]
        endpoint = f"{args.target_host}:{args.target_port}"
        return ["chisel", "client", endpoint, args.chisel_remote]

    if provider == "bore":
        return ["bore", "local", str(args.target_port), "--to", args.bore_server]

    if provider == "rathole":
        path = args.config_path or str(config_paths.get("rathole", default_config_dir() / f"rathole-{args.role}.toml"))
        return ["rathole", path]

    if provider == "frp":
        path = args.config_path or str(config_paths.get("frp", default_config_dir() / ("frps.toml" if args.role == "server" else "frpc.toml")))
        return (["frps", "-c", path] if args.role == "server" else ["frpc", "-c", path])

    if provider == "ligolo-ng":
        if args.role == "server":
            return ["proxy", "-selfcert"]
        if not args.target_host:
            raise RuntimeError("ligolo-ng client connect requires --target-host")
        return ["agent", "-connect", f"{args.target_host}:{args.target_port}", "-ignore-cert"]

    raise RuntimeError(f"No connect command template defined for provider: {provider}")


def install_provider(provider: str, os_name: str, arch: str, install_dir: Path) -> str | list[Path]:
    if provider == "cloudflared":
        return install_cloudflared(os_name, arch, install_dir)
    if provider == "ngrok":
        return install_ngrok(os_name, arch, install_dir)
    if provider == "localtunnel":
        return install_localtunnel()
    if provider == "proxychains":
        return install_or_detect_proxychains(os_name)
    if provider == "ssh-dynamic":
        return install_or_detect_ssh_client(os_name)
    if provider == "socat":
        return install_socat(os_name)
    if provider == "chisel":
        return install_from_github_release(os_name, arch, install_dir, "jpillora/chisel", ["chisel"], ["chisel"])
    if provider == "bore":
        return install_from_github_release(os_name, arch, install_dir, "ekzhang/bore", ["bore"], ["bore"])
    if provider == "rathole":
        return install_from_github_release(os_name, arch, install_dir, "rapiz1/rathole", ["rathole"], ["rathole"])
    if provider == "frp":
        return install_from_github_release(os_name, arch, install_dir, "fatedier/frp", ["frp", "frpc", "frps"], ["frpc", "frps"])
    if provider == "ligolo-ng":
        return install_from_github_release(
            os_name,
            arch,
            install_dir,
            "nicocha30/ligolo-ng",
            ["ligolo", "proxy", "agent"],
            ["proxy", "agent", "ligolo-proxy", "ligolo-agent"],
        )
    raise RuntimeError(f"Unsupported provider: {provider}")


def print_help_examples() -> None:
    print("Quick usage examples:")
    print("  python3 tunnel_setup.py --provider chisel --action all --role server --listen-port 8001 --keep-connected")
    print("  python3 tunnel_setup.py --provider chisel --action all --role client --target-host 1.2.3.4 --target-port 8001 --chisel-remote R:1080:socks --keep-connected")
    print("  python3 tunnel_setup.py --provider ssh-dynamic --action connect --ssh-user alice --ssh-host jump.example.com --keep-connected")
    print("  python3 tunnel_setup.py --provider proxychains --action configure --proxy-port 1080")
    print("  python3 tunnel_setup.py --provider frp --action all --role server --listen-port 7000 --shared-secret change-me")
    print("  python3 tunnel_setup.py --provider frp --action all --role client --target-host 1.2.3.4 --target-port 7000 --remote-host 127.0.0.1 --remote-port 22 --shared-secret change-me")
    print("  python3 tunnel_setup.py --provider ligolo-ng --action connect --role server --keep-connected")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Install, configure, and keep pivot/tunnel tools connected")
    parser.add_argument("--help-examples", action="store_true", help="Show quick usage examples and exit")
    parser.add_argument("--provider", help=f"Provider: {', '.join(PROVIDERS)}")
    parser.add_argument("--action", choices=["install", "configure", "connect", "all"], default="all")
    parser.add_argument("--install-dir", help="Binary install dir (default: ~/.local/bin on Linux/macOS, ~/bin on Windows)")
    parser.add_argument("--config-dir", help="Config directory (default: ~/.tunnel_helper)")

    parser.add_argument("--keep-connected", action="store_true", help="Restart connect command automatically on exit")
    parser.add_argument("--retry-delay", type=int, default=5, help="Reconnect delay seconds when --keep-connected is enabled")
    parser.add_argument("--connect-command", help="Override generated connect command")

    parser.add_argument("--role", choices=["server", "client"], default="client")
    parser.add_argument("--target-host", default="127.0.0.1", help="Server/C2 host for client role")
    parser.add_argument("--target-port", type=int, default=8080, help="Server/C2/local service port")
    parser.add_argument("--listen-host", default="0.0.0.0", help="Local listen host")
    parser.add_argument("--listen-port", type=int, default=7000, help="Local listen port")
    parser.add_argument("--remote-host", default="127.0.0.1", help="Internal target host")
    parser.add_argument("--remote-port", type=int, default=22, help="Internal target port")
    parser.add_argument("--shared-secret", default="change-me", help="Shared token for tools that require one")

    parser.add_argument("--ssh-host", help="SSH jump host for ssh-dynamic")
    parser.add_argument("--ssh-user", help="SSH username for ssh-dynamic")
    parser.add_argument("--ssh-port", type=int, default=22, help="SSH port")
    parser.add_argument("--ssh-key", help="SSH private key path")
    parser.add_argument("--socks-port", type=int, default=1080, help="SOCKS port for ssh-dynamic")

    parser.add_argument("--proxy-type", choices=["socks5", "socks4", "http"], default="socks5")
    parser.add_argument("--proxy-host", default="127.0.0.1", help="Proxy host for proxychains config")
    parser.add_argument("--proxy-port", type=int, default=1080, help="Proxy port for proxychains config")
    parser.add_argument("--proxychains-config", help="Proxychains config path")
    parser.add_argument("--proxychains-command", default="curl https://ifconfig.me", help="Command to run via proxychains in connect mode")

    parser.add_argument("--cloudflared-url", default="http://localhost:8080", help="URL for cloudflared tunnel")
    parser.add_argument("--ngrok-proto", choices=["http", "tcp"], default="http")
    parser.add_argument("--ngrok-authtoken", help="Ngrok authtoken for configure step")

    parser.add_argument("--chisel-remote", default="R:1080:socks", help="Chisel remote spec for client role")
    parser.add_argument("--bore-server", default="bore.pub", help="Bore relay server")
    parser.add_argument("--config-path", help="Explicit config path for rathole/frp connect step")

    return parser.parse_args()


def main() -> int:
    args = parse_args()

    try:
        if args.help_examples:
            print_help_examples()
            return 0

        os_name, arch = detect_platform()
        provider = choose_provider(args.provider)
        install_dir = Path(args.install_dir).expanduser() if args.install_dir else default_install_dir(os_name)
        config_dir = Path(args.config_dir).expanduser() if args.config_dir else default_config_dir()

        print(f"[+] Platform: {os_name}/{arch}")
        print(f"[+] Provider: {provider}")
        print(f"[+] Action: {args.action}")

        do_install = args.action in {"install", "all"}
        do_configure = args.action in {"configure", "all"}
        do_connect = args.action in {"connect", "all"}

        if do_install:
            result = install_provider(provider, os_name, arch, install_dir)
            if isinstance(result, list):
                print("[+] Installed binaries:")
                for item in result:
                    print(f"  - {item}")
                print(f"[+] Add to PATH if needed: {install_dir}")
            else:
                print(f"[+] Tool ready: {result}")

        config_paths: dict[str, Path] = {}
        if do_configure:
            config_paths = configure_provider(provider, args, config_dir)
            if not config_paths:
                print("[+] No explicit config file required for this provider/flags")

        if do_connect:
            cmd = connect_command_for_provider(provider, args, config_paths)
            print(f"[+] Connect command: {' '.join(cmd)}")
            rc = run_connect_command(cmd, args.keep_connected, args.retry_delay)
            return rc

        print("[+] Completed")
        return 0

    except KeyboardInterrupt:
        print("\n[!] Cancelled by user")
        return 130
    except Exception as exc:
        print(f"[!] Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
