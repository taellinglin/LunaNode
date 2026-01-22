import os
import sys
import platform
import traceback


def _print_section(title: str):
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80)


def main():
    _print_section("Environment")
    print("Python:", sys.version)
    print("Executable:", sys.executable)
    print("Platform:", platform.platform())
    print("CUDA_VISIBLE_DEVICES:", os.getenv("CUDA_VISIBLE_DEVICES"))

    _print_section("LunaLib")
    try:
        import lunalib
        print("lunalib.__version__:", getattr(lunalib, "__version__", "(missing)"))
    except Exception as e:
        print("Failed to import lunalib:", e)
        traceback.print_exc()
        return

    _print_section("LunaLib SM3")
    try:
        from lunalib.core import sm3 as lsm3
        print("sm3_hex exists:", hasattr(lsm3, "sm3_hex"))
        print("sm3_batch exists:", hasattr(lsm3, "sm3_batch"))
    except Exception as e:
        print("Failed to import lunalib.core.sm3:", e)
        traceback.print_exc()

    _print_section("CUDA / CuPy")
    try:
        import cupy as cp
        print("cupy version:", cp.__version__)
        device_count = cp.cuda.runtime.getDeviceCount()
        print("CUDA device count:", device_count)
        if device_count > 0:
            with cp.cuda.Device(0):
                print("Device 0 name:", cp.cuda.runtime.getDeviceProperties(0)["name"])
                # simple kernel test
                a = cp.arange(10, dtype=cp.int32)
                b = cp.arange(10, dtype=cp.int32)
                c = a + b
                cp.cuda.runtime.deviceSynchronize()
                print("CuPy add OK. sum:", int(cp.sum(c).get()))
    except Exception as e:
        print("CuPy CUDA check failed:", e)
        traceback.print_exc()

    _print_section("LunaLib Miner CUDA")
    try:
        from lunalib.mining.miner import Miner
        from utils import DataManager, NodeConfig
        dm = DataManager()
        cfg = NodeConfig(dm)
        cfg.use_gpu = True
        miner = Miner(cfg, dm)
        cm = getattr(miner, "cuda_manager", None)
        print("cuda_manager exists:", bool(cm))
        if cm:
            print("cuda_available:", getattr(cm, "cuda_available", None))
            print("device_name:", getattr(cm, "device_name", None))
    except Exception as e:
        print("LunaLib Miner CUDA init failed:", e)
        traceback.print_exc()


if __name__ == "__main__":
    main()
