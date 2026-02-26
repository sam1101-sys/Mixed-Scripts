#!/usr/bin/env python3
"""Tunnel/pivot tool installer based on OS and provider."""

from __future__ import annotations

import argparse
import gzip
import json
import platform
import shutil
import stat
import subprocess
import sys
import tarfile
import tempfile
import urllib.request
import zipfile
from pathlib import Path


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


def detect_linux_package_manager() -> str | None:
    for manager in ("apt", "dnf", "yum", "pacman", "zypper", "apk"):
        if shutil.which(manager):
            return manager
    return None


def github_latest_assets(repo: str) -> list[dict[str, str]]:
    url = f"https://api.github.com/repos/{repo}/releases/latest"
    req = urllib.request.Request(url, headers={"User-Agent": "tunnel-helper/1.0", "Accept": "application/vnd.github+json"})
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
        output_name = archive_path.name[:-3]
        out_file = extract_dir / output_name
        with gzip.open(archive_path, "rb") as src, out_file.open("wb") as dst:
            shutil.copyfileobj(src, dst)
        return

    copied = extract_dir / archive_path.name
    shutil.copy2(archive_path, copied)


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
        raise RuntimeError("No binaries were installed from the selected release asset")

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
    filename = f"cloudflared{suffix}"

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
        raise RuntimeError(f"cloudflared does not support {os_name}/{arch} in this installer")

    url = f"https://github.com/cloudflare/cloudflared/releases/latest/download/{target}"
    install_dir.mkdir(parents=True, exist_ok=True)
    destination = install_dir / filename
    download_file(url, destination)
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
        raise RuntimeError(f"ngrok does not support {os_name}/{arch} in this installer")

    url = f"https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-{target}.zip"

    with tempfile.TemporaryDirectory() as td:
        tmp_dir = Path(td)
        zip_path = tmp_dir / "ngrok.zip"
        extract_dir = tmp_dir / "extract"
        extract_dir.mkdir(parents=True, exist_ok=True)

        download_file(url, zip_path)
        extract_asset(zip_path, extract_dir)

        binary_name = "ngrok.exe" if os_name == "windows" else "ngrok"
        candidate = extract_dir / binary_name
        if not candidate.exists():
            raise RuntimeError("Downloaded ngrok archive did not include expected binary")

        return install_binaries_from_paths([candidate], install_dir, os_name)


def install_localtunnel() -> str:
    npm = shutil.which("npm")
    if not npm:
        raise RuntimeError("npm is required for localtunnel installation but was not found in PATH")
    run_command([npm, "install", "-g", "localtunnel"], "Installing localtunnel")
    return "lt"


def install_socat(os_name: str) -> str:
    existing = shutil.which("socat")
    if existing:
        return "socat"

    if os_name == "windows":
        raise RuntimeError("socat is not supported natively on Windows in this installer")

    if os_name == "darwin":
        brew = shutil.which("brew")
        if not brew:
            raise RuntimeError("Homebrew is required to install socat on macOS")
        run_command([brew, "install", "socat"], "Installing socat")
        return "socat"

    manager = detect_linux_package_manager()
    if not manager:
        raise RuntimeError("No supported Linux package manager found for socat install")

    if manager == "apt":
        run_command(["sudo", "apt", "update"], "Updating apt repositories")
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
        raise RuntimeError("socat installation completed but command was not found in PATH")

    return "socat"


def install_or_detect_proxychains(os_name: str) -> str:
    existing = shutil.which("proxychains4") or shutil.which("proxychains")
    if existing:
        return Path(existing).name

    if os_name == "windows":
        raise RuntimeError("proxychains is not supported natively on Windows in this installer")

    if os_name == "darwin":
        brew = shutil.which("brew")
        if not brew:
            raise RuntimeError("Homebrew is required to install proxychains-ng on macOS")
        run_command([brew, "install", "proxychains-ng"], "Installing proxychains-ng")
    else:
        manager = detect_linux_package_manager()
        if not manager:
            raise RuntimeError("No supported Linux package manager found for proxychains install")

        if manager == "apt":
            run_command(["sudo", "apt", "update"], "Updating apt repositories")
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
        raise RuntimeError("proxychains installation completed but command was not found in PATH")
    return Path(installed).name


def install_or_detect_ssh_client(os_name: str) -> str:
    existing = shutil.which("ssh")
    if existing:
        return existing

    if os_name == "windows":
        raise RuntimeError("OpenSSH client not found. Enable Windows OpenSSH Client feature first")

    if os_name == "darwin":
        raise RuntimeError("ssh not found on macOS; install Xcode Command Line Tools")

    manager = detect_linux_package_manager()
    if not manager:
        raise RuntimeError("No supported Linux package manager found for OpenSSH install")

    if manager == "apt":
        run_command(["sudo", "apt", "update"], "Updating apt repositories")
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
        raise RuntimeError("SSH client installation completed but ssh command was not found in PATH")
    return installed


def build_ssh_dynamic_command(args: argparse.Namespace) -> str:
    host = args.ssh_host or "<jump-host>"
    user = args.ssh_user or "<user>"
    key_part = f" -i {args.ssh_key}" if args.ssh_key else ""
    return f"ssh -N -D 127.0.0.1:{args.socks_port} -p {args.ssh_port}{key_part} {user}@{host}"


def maybe_write_proxychains_config(args: argparse.Namespace) -> Path | None:
    if not args.write_proxychains_config:
        return None

    config_path = (
        Path(args.proxychains_config).expanduser()
        if args.proxychains_config
        else Path.home() / ".proxychains" / "proxychains.conf"
    )
    config_path.parent.mkdir(parents=True, exist_ok=True)
    content = (
        "strict_chain\n"
        "proxy_dns\n"
        "[ProxyList]\n"
        f"{args.proxy_type} {args.proxy_host} {args.proxy_port}\n"
    )
    config_path.write_text(content, encoding="utf-8")
    return config_path


def choose_provider(arg_provider: str | None) -> str:
    choices = [
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
    if arg_provider:
        provider = arg_provider.lower().strip()
        if provider not in choices:
            raise RuntimeError(f"Unknown provider: {arg_provider}. Supported: {', '.join(choices)}")
        return provider

    print("Select tunneling provider:")
    for idx, provider in enumerate(choices, start=1):
        print(f"  {idx}. {provider}")

    selection = input(f"Enter choice (1-{len(choices)}): ").strip()
    if not selection.isdigit() or not (1 <= int(selection) <= len(choices)):
        raise RuntimeError("Invalid selection")
    return choices[int(selection) - 1]


def print_help_examples() -> None:
    print("Quick usage examples:")
    print("  python3 tunnel_setup.py")
    print("  python3 tunnel_setup.py --provider cloudflared")
    print("  python3 tunnel_setup.py --provider ngrok")
    print("  python3 tunnel_setup.py --provider localtunnel")
    print("  python3 tunnel_setup.py --provider ssh-dynamic --ssh-user alice --ssh-host jump.example.com --start")
    print("  python3 tunnel_setup.py --provider proxychains --write-proxychains-config")
    print("  python3 tunnel_setup.py --provider socat")
    print("  python3 tunnel_setup.py --provider chisel")
    print("  python3 tunnel_setup.py --provider bore")
    print("  python3 tunnel_setup.py --provider rathole")
    print("  python3 tunnel_setup.py --provider frp")
    print("  python3 tunnel_setup.py --provider ligolo-ng")
    print("  proxychains4 nmap -sT scanme.nmap.org")


def format_install_result(install_result: str | list[Path], install_dir: Path) -> None:
    if isinstance(install_result, list):
        print("Installed binaries:")
        for item in install_result:
            print(f"  - {item}")
        print("\nAdd install directory to PATH if needed:")
        print(f"  {install_dir}")
    else:
        print(f"Command: {install_result}")


def print_next_steps(provider: str, install_result: str | list[Path], install_dir: Path, args: argparse.Namespace) -> None:
    print("\n[+] Installation complete")
    format_install_result(install_result, install_dir)

    print("\nPivot quick-start:")
    if provider == "cloudflared":
        print("  cloudflared tunnel --url http://localhost:8080")
    elif provider == "ngrok":
        print("  ngrok config add-authtoken <YOUR_AUTHTOKEN>")
        print("  ngrok tcp 22")
    elif provider == "localtunnel":
        print("  lt --port 8080")
    elif provider == "proxychains":
        cmd = str(install_result)
        print(f"  {cmd} curl https://ifconfig.me")
        print(f"  {cmd} nmap -sT 10.10.10.0/24")
    elif provider == "ssh-dynamic":
        print(f"  {build_ssh_dynamic_command(args)}")
        print("  proxychains4 ssh internal-user@10.10.10.10")
    elif provider == "socat":
        print("  # Forward local 8443 to internal 10.10.10.5:443 via jump host")
        print("  socat TCP-LISTEN:8443,fork,reuseaddr TCP:10.10.10.5:443")
    elif provider == "chisel":
        print("  # Server (on pivot): chisel server --reverse -p 8001")
        print("  # Client: chisel client <server>:8001 R:1080:socks")
    elif provider == "bore":
        print("  # Expose local SOCKS or app port")
        print("  bore local 1080 --to bore.pub")
    elif provider == "rathole":
        print("  # Use config-driven reverse forwarding")
        print("  rathole server.toml  # on server")
        print("  rathole client.toml  # on pivot/client")
    elif provider == "frp":
        print("  # Run server on VPS and client on pivot")
        print("  frps -c frps.toml")
        print("  frpc -c frpc.toml")
    elif provider == "ligolo-ng":
        print("  # C2 side")
        print("  proxy -selfcert")
        print("  # Agent side")
        print("  agent -connect <c2-ip>:11601 -ignore-cert")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Install tunneling and pivot tools based on OS and provider")
    parser.add_argument("--help-examples", action="store_true", help="Show quick usage examples and exit")
    parser.add_argument(
        "--provider",
        help=(
            "Provider to install "
            "(cloudflared, ngrok, localtunnel, proxychains, ssh-dynamic, socat, chisel, bore, rathole, frp, ligolo-ng)."
        ),
    )
    parser.add_argument(
        "--install-dir",
        help="Directory to place downloaded binaries (default: ~/.local/bin on Linux/macOS, ~/bin on Windows)",
    )
    parser.add_argument("--socks-port", type=int, default=1080, help="SOCKS port for ssh -D and proxychains")
    parser.add_argument("--ssh-host", help="SSH jump host for ssh-dynamic mode")
    parser.add_argument("--ssh-user", help="SSH username for ssh-dynamic mode")
    parser.add_argument("--ssh-port", type=int, default=22, help="SSH port for ssh-dynamic mode")
    parser.add_argument("--ssh-key", help="Optional SSH private key path")
    parser.add_argument("--start", action="store_true", help="Start ssh -D immediately (ssh-dynamic only)")
    parser.add_argument("--proxy-host", default="127.0.0.1", help="Proxy host for proxychains config")
    parser.add_argument("--proxy-port", type=int, default=1080, help="Proxy port for proxychains config")
    parser.add_argument("--proxy-type", choices=["socks5", "socks4", "http"], default="socks5")
    parser.add_argument(
        "--write-proxychains-config",
        action="store_true",
        help="Write a minimal proxychains config with the provided proxy host/port/type",
    )
    parser.add_argument("--proxychains-config", help="Custom path for proxychains config output")
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

        print(f"[+] Detected platform: {os_name}/{arch}")
        print(f"[+] Selected provider: {provider}")

        if provider == "cloudflared":
            result: str | list[Path] = install_cloudflared(os_name, arch, install_dir)
        elif provider == "ngrok":
            result = install_ngrok(os_name, arch, install_dir)
        elif provider == "localtunnel":
            result = install_localtunnel()
        elif provider == "proxychains":
            result = install_or_detect_proxychains(os_name)
            config_path = maybe_write_proxychains_config(args)
            if config_path:
                print(f"[+] Wrote proxychains config: {config_path}")
        elif provider == "ssh-dynamic":
            install_or_detect_ssh_client(os_name)
            result = "ssh"
            if args.start:
                if not args.ssh_host or not args.ssh_user:
                    raise RuntimeError("--start requires both --ssh-host and --ssh-user for ssh-dynamic")
                cmd = ["ssh", "-N", "-D", f"127.0.0.1:{args.socks_port}", "-p", str(args.ssh_port)]
                if args.ssh_key:
                    cmd.extend(["-i", args.ssh_key])
                cmd.append(f"{args.ssh_user}@{args.ssh_host}")
                print("[+] Starting SSH dynamic SOCKS tunnel (Ctrl+C to stop)")
                subprocess.run(cmd, check=False)
        elif provider == "socat":
            result = install_socat(os_name)
        elif provider == "chisel":
            result = install_from_github_release(
                os_name, arch, install_dir, "jpillora/chisel", ["chisel"], ["chisel"]
            )
        elif provider == "bore":
            result = install_from_github_release(
                os_name, arch, install_dir, "ekzhang/bore", ["bore"], ["bore"]
            )
        elif provider == "rathole":
            result = install_from_github_release(
                os_name, arch, install_dir, "rapiz1/rathole", ["rathole"], ["rathole"]
            )
        elif provider == "frp":
            result = install_from_github_release(
                os_name, arch, install_dir, "fatedier/frp", ["frp", "frpc", "frps"], ["frpc", "frps"]
            )
        elif provider == "ligolo-ng":
            result = install_from_github_release(
                os_name,
                arch,
                install_dir,
                "nicocha30/ligolo-ng",
                ["ligolo", "proxy", "agent"],
                ["proxy", "agent", "ligolo-proxy", "ligolo-agent"],
            )
        else:
            raise RuntimeError(f"Unsupported provider: {provider}")

        print_next_steps(provider, result, install_dir, args)
        return 0

    except KeyboardInterrupt:
        print("\n[!] Cancelled by user")
        return 130
    except Exception as exc:
        print(f"[!] Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
