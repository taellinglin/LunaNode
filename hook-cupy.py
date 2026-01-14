# hook-cupy.py
# PyInstaller hook for cupy and CUDA support
from PyInstaller.utils.hooks import collect_all, collect_submodules, collect_dynamic_libs
import os

# Collect all cupy submodules
hiddenimports = collect_submodules('cupy')

# Add explicit CUDA-related imports
hiddenimports.extend([
    'cupy',
    'cupy.cuda',
    'cupy.cuda.runtime',
    'cupy.cuda.memory',
    'cupy.cuda.device',
    'cupy.cuda.compiler',
    'cupy.cuda.stream',
    'cupy.cuda.function',
    'cupy.cuda.driver',
    'cupy.cuda.pinned_memory',
    'cupy.cuda.texture',
    'cupy.cuda.graph',
    'cupy._core',
    'cupy._core.core',
    'cupy._core._dtype',
    'cupy._core._kernel',
    'cupy._core._routines_manipulation',
    'cupy._core._routines_math',
    'cupy._core._scalar',
    'cupy.fft',
    'cupy.linalg',
    'cupy.random',
])

# Try to collect cupy-cuda12x (or other versions)
for cuda_ver in ['cupy_cuda12x', 'cupy_cuda11x', 'cupy_cuda102']:
    try:
        hiddenimports.extend(collect_submodules(cuda_ver))
    except:
        pass

# Collect data files and binaries
datas = []
binaries = []

try:
    d, b, h = collect_all('cupy')
    datas.extend(d)
    binaries.extend(b)
    hiddenimports.extend(h)
except:
    pass

# Try to collect CUDA-specific cupy packages
for cuda_pkg in ['cupy_cuda12x', 'cupy_cuda11x', 'cupy_cuda102']:
    try:
        d, b, h = collect_all(cuda_pkg)
        datas.extend(d)
        binaries.extend(b)
        hiddenimports.extend(h)
    except:
        pass

print(f"[hook-cupy] Hidden imports: {len(hiddenimports)}")
print(f"[hook-cupy] Binaries: {len(binaries)}")
