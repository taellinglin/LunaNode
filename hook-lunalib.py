# hook-lunalib.py
from PyInstaller.utils.hooks import collect_all, collect_data_files, collect_submodules

# Collect all submodules of lunalib
hiddenimports = collect_submodules('lunalib')

# Collect all data files
datas, binaries, hiddenimports_more = collect_all('lunalib')
hiddenimports.extend(hiddenimports_more)

# Add specific modules you're using
hiddenimports.extend([
    'lunalib.core.blockchain',
    'lunalib.core',
    'lunalib.nodes', 
    'lunalib.utils',
])

print(f"LunaLib hidden imports: {hiddenimports}")
print(f"LunaLib datas: {datas}")