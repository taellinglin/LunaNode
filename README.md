![Python Version](https://img.shields.io/badge/python-3.11%2B-blue)
![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux%20%7C%20Android%20%7C%20iOS-lightgrey)
![License](https://img.shields.io/badge/license-MIT-green)
![Version](https://img.shields.io/badge/version-1.0.0-orange)
![Flet](https://img.shields.io/badge/built%20with-Flet-ff69b4)
![CUDA](https://img.shields.io/badge/CUDA-supported-success)
![Status](https://img.shields.io/badge/status-active-brightgreen)

# Luna Node

A modern, cross-platform mining client for the Luna Network with a clean blue UI and robust CPU/GPU mining support.

## Highlights

- CPU and GPU mining (CUDA when available)
- Real-time stats (hash rate, success rate, performance)
- Auto-mining with configurable intervals
- Network sync with progress feedback
- Wallet address management for rewards

## Quick Start

### Requirements

- Python 3.11+
- Git

### Install & Run

1) Clone the repo
```
git clone https://github.com/yourusername/luna-node.git
cd luna-node
```

2) Install dependencies
```
pip install -r requirements.txt
```

3) Run
```
python main.py
```

## Prebuilt Binaries

Download the latest release for your platform:

- Windows: luna-node-windows.zip
- macOS: luna-node-macos.dmg (Intel) or luna-node-macos-arm64.dmg (Apple Silicon)
- Linux: luna-node-linux.tar.gz (x64) or luna-node-linux-arm64.tar.gz (ARM64)
- Android: luna-node-android.apk
- iOS: luna-node-ios.ipa

## System Requirements

Minimum:
- CPU: Dual-core
- RAM: 2 GB
- Storage: 100 MB
- OS: Windows 10, macOS 10.14, Ubuntu 18.04, Android 8.0, iOS 12

Recommended:
- CPU: Quad-core or better
- RAM: 4 GB+
- GPU: NVIDIA CUDA-capable (for GPU mining)
- Storage: 500 MB SSD
- Internet: Broadband connection

## Build from Source

Install build dependencies:
```
pip install flet[all]
```

Build examples:
```
# Windows
flet build windows --include-packages lunalib

# macOS
flet build macos --include-packages lunalib

# Linux
flet build linux --include-packages lunalib

# Android
flet build apk --include-packages lunalib

# iOS
flet build ios --include-packages lunalib
```

## Project Structure

```
luna-node/
├── main.py
├── utils.py
├── requirements.txt
├── pyproject.toml
├── gui/
│   ├── sidebar.py
│   ├── main_page.py
│   ├── mining_history.py
│   ├── bills.py
│   ├── settings.py
│   └── log.py
└── data/
    ├── settings.json
    ├── mining_history.json
    ├── blockchain_cache.json
    └── logs.json
```

## Troubleshooting

- Check the Log tab in the app for errors.
- Verify the node URL and network connectivity.
- Confirm your wallet address is valid before mining.

## License

MIT License. See LICENSE for details.