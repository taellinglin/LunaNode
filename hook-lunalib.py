# hook-lunalib.py
# PyInstaller hook for lunalib with CUDA mining support
from PyInstaller.utils.hooks import collect_all, collect_data_files, collect_submodules

# Collect all submodules of lunalib
hiddenimports = collect_submodules('lunalib')

# Collect all data files
datas, binaries, hiddenimports_more = collect_all('lunalib')
hiddenimports.extend(hiddenimports_more)

# Add specific modules for mining with CUDA
hiddenimports.extend([
    # Core modules
    'lunalib.core',
    'lunalib.core.blockchain',
    'lunalib.core.mempool',
    'lunalib.core.p2p',
    'lunalib.core.sm3_cuda',
    'lunalib.core.wallet',
    
    # Mining modules (critical for CUDA)
    'lunalib.mining',
    'lunalib.mining.miner',
    'lunalib.mining.difficulty',
    'lunalib.mining.cuda_manager',
    'lunalib.mining.gpu_miner',
    
    # Transaction modules
    'lunalib.transactions',
    'lunalib.transactions.transactions',
    
    # Storage modules
    'lunalib.storage',
    'lunalib.storage.cache',
    'lunalib.storage.database',
    
    # Utility modules
    'lunalib.utils',
    'lunalib.nodes',
    'lunalib.gtx',
])

print(f"[hook-lunalib] Hidden imports: {len(hiddenimports)}")
print(f"[hook-lunalib] Datas: {len(datas)}")
print(f"[hook-lunalib] Binaries: {len(binaries)}")