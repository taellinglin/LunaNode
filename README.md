![Python Version](https://img.shields.io/badge/python-3.11%2B-blue)
![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux%20%7C%20Android%20%7C%20iOS-lightgrey)
![License](https://img.shields.io/badge/license-MIT-green)
![Version](https://img.shields.io/badge/version-1.0.0-orange)
![Flet](https://img.shields.io/badge/built%20with-Flet-ff69b4)
![CUDA](https://img.shields.io/badge/CUDA-supported-success)
![Status](https://img.shields.io/badge/status-active-brightgreen)
# 🔵 Luna Node - Blockchain Mining Client

A modern, cross-platform blockchain mining client for the Luna Network with a beautiful blue-themed interface and powerful mining capabilities.

## ✨ Features

### 🎯 Core Functionality
- **Blockchain Mining**: CPU and GPU-accelerated mining with CUDA support
- **Real-time Statistics**: Live monitoring of hash rates, success rates, and performance metrics
- **Auto Mining**: Configurable automatic mining with customizable intervals
- **Network Synchronization**: Seamless blockchain synchronization with progress tracking
- **Wallet Integration**: Secure wallet management with rewards address configuration

### 🎨 User Experience
- **Modern Blue Theme**: Beautiful dark-themed interface with blue accents
- **Cross-Platform**: Native applications for Windows, macOS, Linux, Android, and iOS
- **System Tray Integration**: Minimize to system tray with background operation
- **Responsive Design**: Adapts to different screen sizes and devices
- **Real-time Updates**: Live statistics and performance monitoring

### ⚡ Performance & Optimization
- **CUDA Support**: GPU acceleration for faster mining (when available)
- **Memory Efficient**: Optimized for low memory usage and fast startup
- **Data Persistence**: Automatic saving of settings, history, and logs
- **Performance Modes**: Power saver, balanced, and high-performance modes
- **Batch Processing**: Efficient batch mining operations

## 🚀 Quick Start

### Prerequisites
- Python 3.11 or higher
- Git

### Installation

1. **Clone the repository**
```
git clone https://github.com/yourusername/luna-node.git
cd luna-node
```


2. **Install dependencies**
```
pip install -r requirements.txt
```


3. **Run the application**
```
python main.py
```


### Using Pre-built Binaries

Download the latest release for your platform:
- **Windows**: `luna-node-windows.zip`
- **macOS**: `luna-node-macos.dmg` (Intel) or `luna-node-macos-arm64.dmg` (Apple Silicon)
- **Linux**: `luna-node-linux.tar.gz` (x64) or `luna-node-linux-arm64.tar.gz` (ARM64)
- **Android**: `luna-node-android.apk`
- **iOS**: `luna-node-ios.ipa`

## 📋 System Requirements

### Minimum Requirements
- **CPU**: Dual-core processor
- **RAM**: 2GB
- **Storage**: 100MB free space
- **OS**: Windows 10, macOS 10.14, Ubuntu 18.04, Android 8.0, iOS 12

### Recommended Requirements
- **CPU**: Quad-core processor or better
- **RAM**: 4GB or more
- **GPU**: NVIDIA GPU with CUDA support (for GPU acceleration)
- **Storage**: 500MB SSD free space
- **Internet**: Broadband connection

## 🛠️ Building from Source

### Automated Builds (GitHub Actions)
The project includes GitHub Actions workflows that automatically build for all platforms when you create a release tag:
```
git tag v1.0.0
git push origin v1.0.0
```


### Manual Building

1. **Install Flet build dependencies**
```
pip install flet[all]
```


2. **Build for specific platform**
```
Windows

flet build windows --include-packages lunalib
macOS

flet build macos --include-packages lunalib
Linux

flet build linux --include-packages lunalib
Android

flet build apk --include-packages lunalib
iOS

flet build ios --include-packages lunalib
```


## 📁 Project Structure
```
luna-node/
├── main.py # Main application entry point
├── utils.py # Core node and mining logic
├── requirements.txt # Python dependencies
├── pyproject.toml # Build configuration
├── build_config.py # Build hooks and configuration
├── .github/
│ └── workflows/
│ └── build.yml # CI/CD automation
├── gui/
│ ├── sidebar.py # Navigation sidebar
│ ├── main_page.py # Mining dashboard
│ ├── mining_history.py # Statistics and performance
│ ├── bills.py # Transactions and rewards
│ ├── settings.py # Configuration management
│ └── log.py # Application logging
└── data/ # Persistent data storage
├── settings.json
├── mining_history.json
├── blockchain_cache.json
└── logs.json
```

## ⚙️ Configuration

### Settings Categories

1. **⛏️ Mining Settings**
   - Auto Mining toggle
   - Mining difficulty (1-10)
   - Mining interval (seconds)
   - GPU acceleration

2. **🌐 Network Settings**
   - Node URL configuration
   - Network timeout
   - Auto-sync interval

3. **⚡ Performance Settings**
   - Mining threads
   - Batch size
   - Cache size
   - Performance modes

4. **💰 Wallet Settings**
   - Miner address
   - Rewards address
   - Wallet encryption
   - Auto-backup

5. **🔧 Advanced Settings**
   - Log levels
   - Data retention
   - Statistics reset

##  Dashboard Features

### Mining Tab
- Real-time mining controls (Start/Stop/Single Block/Sync)
- Live status indicator
- Comprehensive statistics display:
  - Network height and difficulty
  - Blocks mined and total rewards
  - Current hash rate and success rate
  - Average mining time and uptime
  - Connection status and mempool size

### Statistics Tab
- Session performance metrics
- Interactive charts for:
  - Hash rate trends
  - Success rate history
  - Mining time patterns
- System performance monitoring:
  - CPU, memory, and GPU usage
  - Network latency
- Compact mining history table

### Bills Tab
- Transaction history and mining rewards
- Bill details with timestamps
- Status tracking (confirmed/pending)
- Total rewards summary
- Export capabilities

### Settings Tab
- Categorized configuration options
- Real-time setting validation
- Import/export functionality
- Reset to defaults

### Log Tab
- Real-time application logging
- Color-coded message types (info/success/warning/error)
- Timestamp tracking
- Clear log functionality

## 🔧 Advanced Features

### GPU Acceleration
Luna Node supports CUDA-enabled GPUs for accelerated mining:
- Automatic detection of CUDA-capable devices
- Fallback to CPU mining if GPU unavailable
- Configurable batch sizes for optimal performance

### Data Management
- Automatic persistence in `./data/` directory
- Settings, history, cache, and logs storage
- Configurable data retention periods
- Export/import functionality for backup

### Network Integration
- Multiple node URL support
- Automatic network discovery
- Connection status monitoring
- Offline operation with local block storage

## 🐛 Troubleshooting

### Common Issues

1. **Node fails to start**
   - Check Python version (requires 3.11+)
   - Verify all dependencies are installed
   - Ensure data directory has write permissions

2. **Mining not working**
   - Verify network connection
   - Check node URL configuration
   - Confirm wallet address is valid

3. **Performance issues**
   - Adjust mining difficulty
   - Enable GPU acceleration if available
   - Increase mining interval for slower systems

### Getting Help

- Check the application logs in Settings → Log tab
- Review mining history for patterns
- Ensure your system meets minimum requirements
- Verify network connectivity to the blockchain node

## 🤝 Contributing

We welcome contributions! Please see our contributing guidelines for details on:
- Code style and standards
- Testing requirements
- Pull request process
- Feature requests and bug reports

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- Ling Country; Ling and Sanny Lin
- Flet team for the excellent cross-platform GUI framework
- Contributors and testers who help improve Luna Node

---

**Luna Node** - Mining the future, one block at a time. 🔵