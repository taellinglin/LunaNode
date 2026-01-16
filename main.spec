# build.spec
import os
import subprocess

block_cipher = None

# Detect CUDA version
def get_cuda_version():
    """Detect installed CUDA version"""
    try:
        # Try nvcc first
        result = subprocess.run(['nvcc', '--version'], capture_output=True, text=True)
        if result.returncode == 0:
            output = result.stdout
            if 'release 12' in output or 'V12' in output:
                return '12x'
            elif 'release 11' in output or 'V11' in output:
                return '11x'
            elif 'release 10' in output or 'V10' in output:
                return '102'
    except FileNotFoundError:
        pass
    
    # Check environment variable
    cuda_path = os.environ.get('CUDA_PATH', '')
    if '12.' in cuda_path or 'v12' in cuda_path.lower():
        return '12x'
    elif '11.' in cuda_path or 'v11' in cuda_path.lower():
        return '11x'
    elif '10.' in cuda_path or 'v10' in cuda_path.lower():
        return '102'
    
    # Default to 12x (most common for RTX 40 series)
    return '12x'

cuda_version = get_cuda_version()
print(f"[BUILD] Detected CUDA version: {cuda_version}")

# Base hidden imports
hidden_imports = [
    'flet', 'lunalib', 'requests', 
    'certifi', 'certifi.core', 'certifi.__main__',
    'tqdm',
    'tqdm.auto',
    'tqdm.std',
]

# Add cupy imports based on CUDA version
cupy_imports = [
    'cupy', 'cupy.cuda', 'cupy.cuda.runtime',
    'cupy.cuda.memory', 'cupy.cuda.device',
    'cupy.cuda.compiler', 'cupy.cuda.stream',
    f'cupy_cuda{cuda_version}',
]
hidden_imports.extend(cupy_imports)

print(f"[BUILD] Hidden imports: {hidden_imports}")

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datadesc=[],
    hiddenimports=hidden_imports,
    hookspath=['.'],
    hooksconfig={},
    runtime_hooks=['encoding_hook.py'],
    excludes=['pystray', '_ctypes', 'ctypes', 'infi.systray'],  # ADD sqlite3 HERE
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# Force remove any sqlite3 modules
for module in list(a.scripts):
    if any(x in str(module).lower() for x in ['pystray', 'systray']):
        a.scripts.remove(module)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],  # NO BINARIES
    exclude_binaries=True,
    name='LunaNode',
    debug=False,
    bootloader_ignore_signals=False,
    strip=True,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='node_icon.png'
)