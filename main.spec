# build.spec
block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datadesc=[],
    hiddenimports=['flet', 'lunalib', 'requests', 'certifi', 'certifi.core', 'certifi.__main__', 'cupy', 'cupy.cuda', 'cupy.cuda.runtime'],
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