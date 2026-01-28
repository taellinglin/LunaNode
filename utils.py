import os
import json
import time
import hashlib
import socket
import requests
import sys
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import threading
import re

# Force UTF-8 console to avoid charmap errors from emoji output
os.environ.setdefault("PYTHONUTF8", "1")
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

def _is_frozen_like() -> bool:
    try:
        if bool(getattr(sys, "frozen", False)):
            return True
        exe = str(getattr(sys, "executable", "") or "").lower()
        if exe.endswith("lunanode.exe"):
            return True
        return False
    except Exception:
        return False

if _is_frozen_like():
    os.environ.setdefault("LUNALIB_DISABLE_P2P", "1")

try:
    from gmssl import sm3, func
    SM3_AVAILABLE = True
except Exception:
    sm3 = None
    func = None
    SM3_AVAILABLE = False

LUNALIB_IMPORT_ERROR = None
try:
    from lunalib.core.blockchain import BlockchainManager
    from lunalib.core.mempool import MempoolManager
    from lunalib.core.p2p import HybridBlockchainClient
    try:
        from lunalib.core import sm3_cuda as LUNALIB_SM3_CUDA
    except Exception:
        LUNALIB_SM3_CUDA = None
    from lunalib.mining.difficulty import DifficultySystem
    from lunalib.mining.miner import Miner as LunaLibMiner
    from lunalib.mining.miner import GenesisMiner as LunaLibGenesisMiner
    from lunalib.mining.cuda_manager import CUDAManager
    from lunalib.transactions.transactions import TransactionManager
except ImportError as e:
    LUNALIB_IMPORT_ERROR = str(e)
    print(f"LunaLib import error: {e}")
    BlockchainManager = None
    MempoolManager = None
    HybridBlockchainClient = None
    LUNALIB_SM3_CUDA = None
    DifficultySystem = None
    LunaLibMiner = None
    LunaLibGenesisMiner = None
    CUDAManager = None
    TransactionManager = None

LUNALIB_SM3_FUNC = None
LUNALIB_SM3_BATCH = None
def _load_sm3_impl() -> bool:
    """SM3実装を遅延ロード（lunalib優先、gmsslフォールバック）"""
    global LUNALIB_SM3_FUNC, LUNALIB_SM3_BATCH
    if LUNALIB_SM3_FUNC:
        return True
    try:
        from lunalib.core.sm3 import sm3_hex as _sm3_hex
        from lunalib.core.sm3 import sm3_batch as _sm3_batch
        LUNALIB_SM3_FUNC = _sm3_hex
        LUNALIB_SM3_BATCH = _sm3_batch
        return True
    except Exception:
        try:
            from lunalib.utils.hash import sm3_hex as _sm3_hex
            LUNALIB_SM3_FUNC = _sm3_hex
            return True
        except Exception:
            pass
    if SM3_AVAILABLE and sm3 and func:
        def _gmssl_sm3_hex(data: bytes) -> str:
            return sm3.sm3_hash(func.bytes_to_list(data))
        LUNALIB_SM3_FUNC = _gmssl_sm3_hex
        return True
    return False

_load_sm3_impl()

P2P_AVAILABLE = HybridBlockchainClient is not None


class _MinerPlaceholder:
    def __init__(self):
        self.blocks_mined = 0
        self.total_reward = 0.0
        self.mining_history = []
        self.is_mining = False
        self.mining_active = False
        self.cuda_manager = None
        self.hash_rate = 0
        self.auto_submit = False

    def get_mining_stats(self):
        return {}

    def start_mining(self):
        return False

    def stop_mining(self):
        return False

# --- 安全なprintラッパー ---
def safe_print(*args, **kwargs):
    """例外を握りつぶして安全にprintする"""
    try:
        print(*args, **kwargs)
    except Exception:
        pass

# --- ハッシュアルゴリズム名の正規化 ---
def _normalize_hash_algo(algo: str) -> str:
    """ハッシュアルゴリズム名を正規化（例: 'SHA256', 'sha256', 'SM3' → 'sha256' or 'sm3'）"""
    if not isinstance(algo, str):
        return "sha256"
    a = algo.strip().lower()
    if a in ("sha256", "sha-256", "256", "default", ""):
        return "sha256"
    if a in ("sm3", "sm-3"):
        return "sm3"
    return a

def get_app_data_dir() -> str:
    if os.name == "nt":
        base_dir = os.environ.get("LOCALAPPDATA", os.path.join(os.path.expanduser("~"), "AppData", "Local"))
    else:
        base_dir = os.environ.get("XDG_DATA_HOME", os.path.join(os.path.expanduser("~"), ".local", "share"))
    return os.path.join(base_dir, "LunaNode")

def is_valid_luna_address(address: str) -> bool:
    if not address or not isinstance(address, str):
        return False
    address = address.strip()
    if not address.startswith("LUN_"):
        return False
    if len(address) < 10:
        return False
    if not re.match(r"^LUN_[A-Za-z0-9_]+$", address):
        return False
    return True

# --- ユーティリティ関数 ---
def sanitize_for_console(message: str) -> str:
    """コンソール出力用に文字列をサニタイズ"""
    if not isinstance(message, str):
        return str(message)
    # 制御文字や危険な文字を除去（必要に応じて拡張）
    return message.replace("\r", "").replace("\x1b", "").replace("\x00", "")

def compute_sm3_hexdigest(data: bytes) -> str:
    """SM3ハッシュの16進ダイジェストを計算（lunalib依存）"""
    if not LUNALIB_SM3_FUNC:
        _load_sm3_impl()
    if LUNALIB_SM3_FUNC:
        return LUNALIB_SM3_FUNC(data)
    raise RuntimeError("SM3 hash function is not available in this LunaLib version.")

def log_cpu_mining_event(event: str, data: dict = None):
    """追跡用: CPUマイニングの詳細イベントをlogs/cpu_mining.logへ追記"""
    import os
    import json
    from datetime import datetime
    log_dir = os.path.join(get_app_data_dir(), "logs")
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, "cpu_mining.log")
    try:
        entry = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "event": event,
            "data": data or {}
        }
    except Exception as e:
        print(f"[LOGGING ERROR] Could not create log entry: {e}")
    try:
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception as e:
        print(f"[LOGGING ERROR] Could not write cpu_mining.log: {e}")

def log_mining_debug_event(event: str, data: dict = None, scope: str = "mining"):
    """追跡用: CUDA/検証/送信イベントをlogs/mining_debug.logへ追記"""
    import os
    import json
    from datetime import datetime
    log_dir = os.path.join(get_app_data_dir(), "logs")
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, "mining_debug.log")
    try:
        entry = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "scope": scope,
            "event": event,
            "data": data or {},
        }
    except Exception as e:
        print(f"[LOGGING ERROR] Could not create mining debug entry: {e}")
        return
    try:
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception as e:
        print(f"[LOGGING ERROR] Could not write mining_debug.log: {e}")

class DataManager:
    """Manages data storage in ./data/ directory"""
    
    def __init__(self):
        self.data_dir = os.path.join(get_app_data_dir(), "data")
        self.settings_file = os.path.join(self.data_dir, "settings.json")
        self.mining_history_file = os.path.join(self.data_dir, "mining_history.json")
        self.blockchain_cache_file = os.path.join(self.data_dir, "blockchain_cache.json")
        self.mempool_cache_file = os.path.join(self.data_dir, "mempool_cache.json")
        self.logs_file = os.path.join(self.data_dir, "logs.json")
        self.stats_cache_file = os.path.join(self.data_dir, "stats_cache.json")
        
        self.ensure_data_directory()
    
    def ensure_data_directory(self):
        """Create data directory if it doesn't exist"""
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)
    
    def save_settings(self, settings: Dict):
        """Save settings to file"""
        try:
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(settings, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"Error saving settings: {e}")
            return False
    
    def load_settings(self) -> Dict:
        """Load settings from file"""
        try:
            if os.path.exists(self.settings_file):
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            print(f"Error loading settings: {e}")
        return {
            'miner_address': "LUN_Node_Miner_Default",
            'difficulty': 2,
            'auto_mine': False,
            'node_url': "https://bank.linglin.art",
            'mining_interval': 30,
            'performance_level': 70,
            'hash_algorithm': "sm3",
            'sm3_workers': max(1, (os.cpu_count() or 4) - 1),
            'cuda_batch_size': 100000,
            'gpu_batch_dynamic': False,
            'enable_cpu_mining': True,
            'enable_gpu_mining': False,
            'multi_gpu_enabled': False,
            'cuda_sm3_kernel': True,
            'cpu_threads': 1,
            'gpu_batch_size': 100000
        }
    
    def save_mining_history(self, history: List[Dict]):
        """Save mining history to file"""
        try:
            with open(self.mining_history_file, 'w', encoding='utf-8') as f:
                json.dump(history, f, indent=2, default=str, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"Error saving mining history: {e}")
            return False
    
    def load_mining_history(self) -> List[Dict]:
        """Load mining history from file"""
        try:
            if os.path.exists(self.mining_history_file):
                with open(self.mining_history_file, 'r', encoding='utf-8') as f:
                    history = json.load(f)
                    # Check if the loaded history contains stringified JSON
                    if isinstance(history, str):
                        history = json.loads(history)
                    print("[DEBUG] DataManager.load_mining_history: Loaded history:", history)
                    return history
        except Exception as e:
            print(f"Error loading mining history: {e}")
        return []
    
    def save_blockchain_cache(self, blockchain: List[Dict]):
        """Save blockchain cache to file"""
        try:
            with open(self.blockchain_cache_file, 'w', encoding='utf-8') as f:
                json.dump(blockchain, f, indent=2, default=str, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"Error saving blockchain cache: {e}")
            return False
    
    def load_blockchain_cache(self) -> List[Dict]:
        """Load blockchain cache from file"""
        try:
            if os.path.exists(self.blockchain_cache_file):
                with open(self.blockchain_cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            print(f"Error loading blockchain cache: {e}")
        return []

    def save_submitted_block(self, block_data: Dict) -> bool:
        """Upsert a submitted block into blockchain cache"""
        try:
            cache = self.load_blockchain_cache()
            if not isinstance(cache, list):
                cache = []
            index = block_data.get("index") if isinstance(block_data, dict) else None
            if index is not None:
                cache = [b for b in cache if not (isinstance(b, dict) and b.get("index") == index)]
            cache.append(block_data)
            return self.save_blockchain_cache(cache)
        except Exception as e:
            print(f"Error saving submitted block: {e}")
            return False
    
    def save_mempool_cache(self, mempool: List[Dict]):
        """Save mempool cache to file"""
        try:
            with open(self.mempool_cache_file, 'w', encoding='utf-8') as f:
                json.dump(mempool, f, indent=2, default=str, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"Error saving mempool cache: {e}")
            return False
    
    def load_mempool_cache(self) -> List[Dict]:
        """Load mempool cache from file"""
        try:
            if os.path.exists(self.mempool_cache_file):
                with open(self.mempool_cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            print(f"Error loading mempool cache: {e}")
        return []
    
    def save_logs(self, logs: List[Dict]):
        """Save logs to file"""
        try:
            with open(self.logs_file, 'w', encoding='utf-8') as f:
                json.dump(logs, f, indent=2, default=str, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"Error saving logs: {e}")
            return False
    
    def load_logs(self) -> List[Dict]:
        """Load logs from file, or return default messages if not found/empty"""
        default_logs = [
            {
                "timestamp": "2026-01-15 11:50:46",
                "message": "Roses are #FF0000",
                "type": "error"
            },
            {
                "timestamp": "2026-01-15 11:50:46",
                "message": "Violets are #0000FF",
                "type": "info"
            },
            {
                "timestamp": "2026-01-15 11:50:46",
                "message": "我爱你 is Chinese for I love you! Happy Mining!",
                "type": "warning"
            }
        ]
        try:
            if os.path.exists(self.logs_file):
                with open(self.logs_file, 'r', encoding='utf-8') as f:
                    logs = json.load(f)
                    print("[DEBUG] DataManager.load_logs: Loaded logs:", logs)
                    print("[DEBUG] DataManager.load_logs: Type of logs:", type(logs))
                    if logs:
                        return logs
        except Exception as e:
            print(f"Error loading logs: {e}")
        return default_logs

    def save_stats(self, stats: Dict) -> bool:
        """Save latest stats snapshot to cache"""
        try:
            with open(self.stats_cache_file, 'w', encoding='utf-8') as f:
                json.dump(stats, f, indent=2, default=str, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"Error saving stats cache: {e}")
            return False

    def load_stats(self) -> Dict:
        """Load latest stats snapshot from cache"""
        try:
            if os.path.exists(self.stats_cache_file):
                with open(self.stats_cache_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return data if isinstance(data, dict) else {}
        except Exception as e:
            print(f"Error loading stats cache: {e}")
        return {}

class NodeConfig:


    """Node configuration with data persistence"""
    
    def __init__(self, data_manager: DataManager):
        self.data_manager = data_manager
        self.load_from_storage()
    
    def load_from_storage(self):
        """Load configuration from storage"""
        settings = self.data_manager.load_settings()
        print("[DEBUG] NodeConfig.load_from_storage: Loaded settings:", settings)
        self.miner_address = settings.get('miner_address', "LUN_Node_Miner_Default")
        self.difficulty = settings.get('difficulty', 2)
        self.auto_mine = settings.get('auto_mine', False)
        self.node_url = settings.get('node_url', "https://bank.linglin.art")
        self.mining_interval = settings.get('mining_interval', 30)
        self.use_gpu = settings.get('use_gpu', False)
        self.last_scan_height = settings.get('last_scan_height', 0)
        self.setup_complete = settings.get('setup_complete', False)
        self.performance_level = settings.get('performance_level', 70)
        self.hash_algorithm = settings.get('hash_algorithm', "sm3")
        self.sm3_workers = settings.get('sm3_workers', max(1, (os.cpu_count() or 4) - 1))
        self.cuda_batch_size = settings.get('cuda_batch_size', 100000)
        self.gpu_batch_dynamic = settings.get('gpu_batch_dynamic', False)
        self.enable_cpu_mining = settings.get('enable_cpu_mining', True)
        self.enable_gpu_mining = settings.get('enable_gpu_mining', self.use_gpu)
        self.multi_gpu_enabled = settings.get('multi_gpu_enabled', False)
        self.adapt_load_balance = settings.get('adapt_load_balance', False)
        self.parallel_mining = settings.get('parallel_mining', False)
        self.cuda_sm3_kernel = settings.get('cuda_sm3_kernel', True)
        self.cpu_threads = settings.get('cpu_threads', 1)
        self.gpu_batch_size = settings.get('gpu_batch_size', 100000)
    
    def save_to_storage(self):
        """Save configuration to storage"""
        settings = {
            'miner_address': self.miner_address,
            'difficulty': self.difficulty,
            'auto_mine': self.auto_mine,
            'node_url': self.node_url,
            'mining_interval': self.mining_interval,
            'use_gpu': self.use_gpu,
            'last_scan_height': self.last_scan_height,
            'setup_complete': self.setup_complete,
            'performance_level': self.performance_level,
            'hash_algorithm': self.hash_algorithm,
            'sm3_workers': self.sm3_workers,
            'cuda_batch_size': self.cuda_batch_size,
            'gpu_batch_dynamic': getattr(self, 'gpu_batch_dynamic', False),
            'enable_cpu_mining': getattr(self, 'enable_cpu_mining', True),
            'enable_gpu_mining': getattr(self, 'enable_gpu_mining', self.use_gpu),
            'multi_gpu_enabled': getattr(self, 'multi_gpu_enabled', False),
            'adapt_load_balance': getattr(self, 'adapt_load_balance', False),
            'parallel_mining': getattr(self, 'parallel_mining', False),
            'cuda_sm3_kernel': getattr(self, 'cuda_sm3_kernel', True),
            'cpu_threads': getattr(self, 'cpu_threads', 1),
            'gpu_batch_size': getattr(self, 'gpu_batch_size', 100000),
        }
        return self.data_manager.save_settings(settings)

class LunaNode:
    """Main Luna Node class using lunalib directly"""
    
    def __init__(self, cuda_available: bool = False,
                 log_callback=None,
                 new_bill_callback=None,
                 new_reward_callback=None,
                 history_updated_callback=None,
                 mining_started_callback=None,
                 mining_completed_callback=None):
        try:
            log_mining_debug_event("init_step", {"step": "LunaNode.__init__ start"}, scope="app")
        except Exception:
            pass
        
        self.cuda_available = cuda_available
        self.data_manager = DataManager()
        print("[DEBUG] LunaNode.__init__: DataManager instance:", self.data_manager)
        
        # Store callbacks
        self.log_callback = log_callback
        self.new_bill_callback = new_bill_callback
        self.new_reward_callback = new_reward_callback
        self.history_updated_callback = history_updated_callback
        self.mining_started_callback = mining_started_callback
        self.mining_completed_callback = mining_completed_callback
        
        # Debugging DataManager instance in LunaNode constructor
        print("[DEBUG] LunaNode.__init__: Type of self.data_manager:", type(self.data_manager))
        print("[DEBUG] LunaNode.__init__: Value of self.data_manager:", self.data_manager)
        
        # Debugging self.data_manager after initialization
        print("[DEBUG] LunaNode.__init__: Type of self.data_manager after initialization:", type(self.data_manager))
        print("[DEBUG] LunaNode.__init__: Value of self.data_manager after initialization:", self.data_manager)
        
        self.logs = self.data_manager.load_logs()
        
        self.config = NodeConfig(self.data_manager)
        print("[DEBUG] LunaNode.__init__: NodeConfig instance:", self.config)
        # Align lunalib miner flags with current settings
        try:
            self.config.enable_gpu_mining = bool(getattr(self.config, "use_gpu", False))
            if not hasattr(self.config, "enable_cpu_mining"):
                self.config.enable_cpu_mining = True
            if not hasattr(self.config, "cuda_sm3_kernel"):
                self.config.cuda_sm3_kernel = True
            if not hasattr(self.config, "multi_gpu_enabled"):
                self.config.multi_gpu_enabled = False
        except Exception:
            pass

        # Environment toggles for lunalib backends
        if getattr(self.config, "cuda_sm3_kernel", True):
            os.environ.setdefault("LUNALIB_CUDA_SM3", "1")
        else:
            os.environ.setdefault("LUNALIB_CUDA_SM3", "0")
        if getattr(self.config, "multi_gpu_enabled", False):
            os.environ.setdefault("LUNALIB_MULTI_GPU", "1")
        try:
            log_mining_debug_event(
                "env_snapshot",
                {
                    "CUDA_VISIBLE_DEVICES": os.environ.get("CUDA_VISIBLE_DEVICES"),
                    "CUDA_PATH": os.environ.get("CUDA_PATH"),
                    "LUNALIB_CUDA_SM3": os.environ.get("LUNALIB_CUDA_SM3"),
                    "LUNALIB_MULTI_GPU": os.environ.get("LUNALIB_MULTI_GPU"),
                    "LUNALIB_SM2_BACKEND": os.environ.get("LUNALIB_SM2_BACKEND"),
                    "LUNALIB_MINING_HASH_MODE": os.environ.get("LUNALIB_MINING_HASH_MODE"),
                },
                scope="env",
            )
        except Exception:
            pass
        try:
            log_mining_debug_event("init_step", {"step": "env_snapshot_done"}, scope="app")
        except Exception:
            pass
        try:
            if LUNALIB_IMPORT_ERROR:
                log_mining_debug_event(
                    "lunalib_import_error",
                    {"error": LUNALIB_IMPORT_ERROR},
                    scope="p2p",
                )
        except Exception:
            pass
        self.stats = {
            'start_time': time.time(),
            'total_hash_attempts': 0,
            'successful_blocks': 0,
            'failed_attempts': 0,
            'cuda_hash_rate': 0,
            'cuda_last_nonce': 0,
            'cuda_last_hash': '',
            'last_mining_method': 'cpu'
        }
        self._cached_status = self.data_manager.load_stats()
        self._prefer_cached_stats = True
        self._gpu_batch_warmup = True
        self._startup_ts = time.time()
        self._last_mined_ts = 0.0

        # Prevent repeated submissions of the same block
        self._last_submitted_hash = None
        self._last_submitted_index = None
        self._last_submitted_ts = 0.0
        self._last_submitted_success = False
        
        self.is_running = True
        self._stop_mining_event = threading.Event()
        self._submit_lock = threading.Lock()
        self._sync_stop_event = threading.Event()
        self._sync_thread = None

        # Network polling throttling
        self.net_poll_interval = float(os.getenv("LUNANODE_NET_POLL_INTERVAL", "20"))
        self._net_cache_ts = 0.0
        self._net_cache = {
            "height": 0,
            "latest_block": None,
            "mempool": [],
        }
        
        # Peer list for P2P networking (disabled unless using lunalib P2P)
        self.peers = []
        
        # Use LunaLib managers for blockchain management
        try:
            log_mining_debug_event("init_step", {"step": "blockchain_manager_init"}, scope="app")
        except Exception:
            pass
        self.blockchain_manager = BlockchainManager(endpoint_url=self.config.node_url)
        try:
            log_mining_debug_event("init_step", {"step": "blockchain_manager_ready"}, scope="app")
        except Exception:
            pass
        try:
            log_mining_debug_event("init_step", {"step": "mempool_manager_init"}, scope="app")
        except Exception:
            pass
        self.mempool_manager = MempoolManager([self.config.node_url])
        try:
            log_mining_debug_event("init_step", {"step": "mempool_manager_ready"}, scope="app")
        except Exception:
            pass

        # Tolerate incomplete mempool txs from remote nodes
        try:
            if self.mempool_manager and hasattr(self.mempool_manager, "_validate_transaction_basic"):
                def _validate_transaction_basic_safe(transaction):
                    if not isinstance(transaction, dict):
                        return False
                    transaction.setdefault("type", "transaction")
                    transaction.setdefault("from", "unknown")
                    transaction.setdefault("to", "unknown")
                    transaction.setdefault("amount", 0)
                    transaction.setdefault("timestamp", time.time())
                    transaction.setdefault("hash", "0" * 64)
                    return True
                self.mempool_manager._validate_transaction_basic = _validate_transaction_basic_safe
        except Exception:
            pass

        # Override LunaLib submission to use plain JSON (server rejects gzip)
        try:
            def _submit_mined_block_plain(block_data):
                ok, _msg = self._submit_block_plain_json(block_data)
                return bool(ok)

            self.blockchain_manager.submit_mined_block = _submit_mined_block_plain
        except Exception:
            pass

        # Patch get_latest_block to include retries + range fallback (quiet)
        try:
            def _get_latest_block_quiet():
                # Retry a couple times to reduce transient disconnects
                for _ in range(2):
                    try:
                        resp = self.blockchain_manager._session.get(
                            f"{self.config.node_url}/blockchain/blocks",
                            timeout=10,
                        )
                        if resp.status_code == 200:
                            data = resp.json()
                            blocks = data.get("blocks", [])
                            if blocks:
                                return blocks[-1]
                    except Exception:
                        time.sleep(0.5)
                # Fallback to range by height
                try:
                    height = self.blockchain_manager.get_blockchain_height()
                    if height > 0:
                        blocks = self.blockchain_manager.get_blocks_range(height, height)
                        if blocks:
                            return blocks[0]
                except Exception:
                    pass
                return None

            self.blockchain_manager.get_latest_block = _get_latest_block_quiet
        except Exception:
            pass

        # Transaction manager (lunalib 2.x)
        self.tx_manager = None
        if TransactionManager:
            try:
                self.tx_manager = TransactionManager([self.config.node_url])
            except Exception:
                self.tx_manager = None

        # Initialize DifficultySystem for reward calculation
        self.difficulty_system = DifficultySystem()
        
        # Optionally defer GPU init to avoid startup hangs in packaged builds
        self._gpu_init_deferred = False
        if os.getenv("LUNANODE_DISABLE_GPU_INIT", "0") == "1":
            try:
                self._gpu_init_deferred = True
                self.config.enable_gpu_mining = False
                self.config.use_gpu = False
                self.config.save_to_storage()
                log_mining_debug_event("gpu_init_deferred", {}, scope="cuda")
            except Exception:
                pass

        # Miner init guard + placeholder to avoid startup hangs in frozen builds
        self._miner_init_lock = threading.Lock()
        self.miner = _MinerPlaceholder()
        self.cpu_miner = self.miner
        self.gpu_miner = None
        self.cpu_mining_thread = None
        self.gpu_mining_thread = None

        if LunaLibMiner:
            if _is_frozen_like():
                try:
                    log_mining_debug_event("init_step", {"step": "miner_init_async"}, scope="app")
                except Exception:
                    pass
                threading.Thread(target=self._init_miner_sync, daemon=True).start()
            else:
                self._init_miner_sync()

        # Initialize LunaLib GenesisMiner for GTX Genesis bills (optional)
        self.genesis_miner = None
        if LunaLibGenesisMiner:
            try:
                self.genesis_miner = LunaLibGenesisMiner([self.config.node_url])
            except Exception:
                self.genesis_miner = None

        raw_algo = getattr(self.config, "hash_algorithm", "sha256")
        normalized_algo = _normalize_hash_algo(str(raw_algo))
        self.hash_algorithm = str(raw_algo).lower().strip()
        if normalized_algo in ("", "sha256"):
            self.hash_algorithm = "sm3"
            self.config.hash_algorithm = "sm3"
            try:
                self.config.save_to_storage()
            except Exception:
                pass
        self._apply_hash_algorithm()
        self._configure_cuda_sm3()
        try:
            log_mining_debug_event("cuda_probe_invoked", {}, scope="cuda")
        except Exception:
            pass
        self._probe_cuda_runtime()
        try:
            log_mining_debug_event("init_step", {"step": "cuda_probe_done"}, scope="app")
        except Exception:
            pass

        # Override CUDA batch size if configured
        try:
            if hasattr(self.miner, "_cuda_mine") and self.miner.cuda_manager:
                original_cuda_mine = self.miner._cuda_mine

                def _cuda_mine_with_batch(block_data: Dict, difficulty: int):
                    batch_size = self._resolve_cuda_batch_size()
                    try:
                        result = self.miner.cuda_manager.cuda_mine_batch(block_data, difficulty, batch_size=batch_size)
                        if isinstance(result, dict):
                            if result.get("success") and result.get("hash") is not None:
                                block_data["hash"] = result.get("hash")
                                if result.get("nonce") is not None:
                                    block_data["nonce"] = result.get("nonce")
                                return block_data
                            if "hash" in result or "nonce" in result:
                                block_data["hash"] = result.get("hash", block_data.get("hash", ""))
                                if result.get("nonce") is not None:
                                    block_data["nonce"] = result.get("nonce")
                                return block_data
                        return result
                    except Exception:
                        return original_cuda_mine(block_data, difficulty)

                self.miner._cuda_mine = _cuda_mine_with_batch
        except Exception:
            pass

        # Load cached mining history and compute reward stats on startup
        if self.miner and not isinstance(self.miner, _MinerPlaceholder):
            try:
                cached_history = self.data_manager.load_mining_history()
                if isinstance(cached_history, list) and cached_history:
                    self.miner.mining_history = cached_history
                if self.gpu_miner is None and LunaLibMiner is not None:
                    try:
                        self.gpu_miner = LunaLibMiner(
                            self.config,
                            self.data_manager,
                            mining_started_callback=self.mining_started_callback,
                            mining_completed_callback=self.mining_completed_callback,
                            block_mined_callback=self._on_block_mined_ui,
                            block_added_callback=self._post_submit_refresh,
                        )
                    except Exception:
                        self.gpu_miner = None
                if self.gpu_miner is not None:
                    self._register_miner_callbacks(self.gpu_miner, "gpu")
                    self.gpu_miner.mining_history = getattr(self.miner, "mining_history", cached_history if isinstance(cached_history, list) else [])
                    self._apply_parallel_mining(self.gpu_miner)
                self._recalculate_reward_stats()
            except Exception:
                pass
        
        # Link managers to miner
        self.miner.blockchain_manager = self.blockchain_manager
        self.miner.mempool_manager = self.mempool_manager
        # Configure CPU mining backend/workers
        self._configure_cpu_backend(self.miner)
        if self.gpu_miner is not None:
            self.gpu_miner.blockchain_manager = self.blockchain_manager
            self.gpu_miner.mempool_manager = self.mempool_manager
            try:
                if hasattr(self.gpu_miner, "set_cpu_workers"):
                    self.gpu_miner.set_cpu_workers(1)
            except Exception:
                pass
            self.gpu_miner.use_cuda = True
            if hasattr(self.gpu_miner, "use_cpu"):
                self.gpu_miner.use_cpu = False
            self._configure_cuda_sm3(self.gpu_miner)
        
        # Disable auto-submission so we can handle it ourselves
        if hasattr(self.miner, 'auto_submit'):
            self.miner.auto_submit = False
        
        # Initialize HybridBlockchainClient for P2P networking (always enabled if available)
        try:
            log_mining_debug_event("init_step", {"step": "p2p_init"}, scope="app")
        except Exception:
            pass
        self._init_p2p_client()
        try:
            log_mining_debug_event("init_step", {"step": "p2p_init_done"}, scope="app")
        except Exception:
            pass
        
        # Set CUDA availability based on config and miner's CUDA status
        cuda_available = self.miner.cuda_manager.cuda_available if self.miner.cuda_manager else False
        if self.config.use_gpu and cuda_available:
            self.cuda_available = True
            print("[DEBUG] CUDA enabled and available")
        else:
            self.cuda_available = False
            if self.config.use_gpu:
                print("[DEBUG] CUDA requested but not available, falling back to CPU")

        if self.config.auto_mine:
            self.start_auto_mining()

        self._start_sync_loop()
        
        # Debugging DataManager and NodeConfig initialization
        print("[DEBUG] DataManager initialized:", self.data_manager)
        print("[DEBUG] NodeConfig initialized:", self.config)

        # Use LunaLib CPU mining implementation without overrides

    def _init_p2p_client(self):
        """Initialize LunaLib P2P client with compatible constructor + callbacks."""
        self.p2p_client = None
        if os.getenv("LUNALIB_DISABLE_P2P", "0") == "1":
            try:
                log_mining_debug_event("p2p_disabled", {"env": "LUNALIB_DISABLE_P2P"}, scope="p2p")
            except Exception:
                pass
            return
        if not P2P_AVAILABLE or HybridBlockchainClient is None:
            try:
                log_mining_debug_event(
                    "p2p_unavailable",
                    {"p2p_available": False, "hybrid_client": bool(HybridBlockchainClient)},
                    scope="p2p",
                )
            except Exception:
                pass
            return

        try:
            def on_peer_update(peers):
                self.peers = peers or []
                self._log_message(f"P2P peers updated: {len(self.peers)} peers", "info")

            def on_block(block):
                self._log_message(f"P2P new block received: {block.get('index', '?')}", "info")

            def on_transaction(tx):
                self._log_message("P2P new transaction received", "info")

            peer_url = os.getenv("LUNALIB_PEER_URL") or None
            try:
                self.p2p_client = HybridBlockchainClient(
                    self.config.node_url,
                    self.blockchain_manager,
                    self.mempool_manager,
                    peer_url=peer_url,
                )
            except TypeError:
                try:
                    self.p2p_client = HybridBlockchainClient(
                        self.config.node_url,
                        self.blockchain_manager,
                    )
                except TypeError:
                    self.p2p_client = HybridBlockchainClient(self.config.node_url)

            if hasattr(self.p2p_client, "p2p") and hasattr(self.p2p_client.p2p, "set_callbacks"):
                self.p2p_client.p2p.set_callbacks(
                    on_new_block=on_block,
                    on_new_transaction=on_transaction,
                    on_peer_update=on_peer_update,
                )
            elif hasattr(self.p2p_client, "set_callbacks"):
                self.p2p_client.set_callbacks(
                    on_new_block=on_block,
                    on_new_transaction=on_transaction,
                    on_peer_update=on_peer_update,
                )

            def _start_p2p_async():
                try:
                    if hasattr(self.p2p_client, "start"):
                        self.p2p_client.start()
                    self._log_message("P2P client started", "success")
                    try:
                        log_mining_debug_event(
                            "p2p_started",
                            {
                                "node_url": self.config.node_url,
                                "peer_url": peer_url,
                                "connected": self._resolve_p2p_connected(),
                                "peers": len(self.peers),
                            },
                            scope="p2p",
                        )
                    except Exception:
                        pass
                except Exception as e:
                    self._log_message(f"P2P client start failed: {e}", "error")
                    try:
                        log_mining_debug_event("p2p_start_failed", {"error": str(e)}, scope="p2p")
                    except Exception:
                        pass

            threading.Thread(target=_start_p2p_async, daemon=True).start()
            self._log_message("P2P client initializing", "info")
        except Exception as e:
            self._log_message(f"P2P client init failed: {e}", "error")
            try:
                log_mining_debug_event("p2p_init_failed", {"error": str(e)}, scope="p2p")
            except Exception:
                pass

    def _init_miner_sync(self) -> bool:
        """Initialize LunaLib CPU miner with guard to avoid duplicate init."""
        if not LunaLibMiner:
            return False
        if not self._miner_init_lock.acquire(blocking=False):
            return False
        try:
            if not isinstance(self.miner, _MinerPlaceholder) and self.miner:
                return True
            try:
                log_mining_debug_event("init_step", {"step": "miner_init"}, scope="app")
            except Exception:
                pass
            miner = LunaLibMiner(
                self.config,
                self.data_manager,
                mining_started_callback=self.mining_started_callback,
                mining_completed_callback=self.mining_completed_callback,
                block_mined_callback=self._on_block_mined_ui,
                block_added_callback=self._post_submit_refresh,
            )
            self.miner = miner
            self.cpu_miner = miner
            try:
                log_mining_debug_event("init_step", {"step": "miner_ready", "miner": True}, scope="app")
            except Exception:
                pass
            try:
                self._register_miner_callbacks(self.miner, "cpu")
                self._apply_parallel_mining(self.miner)
            except Exception:
                pass
            try:
                cached_history = self.data_manager.load_mining_history()
                if isinstance(cached_history, list) and cached_history:
                    self.miner.mining_history = cached_history
                self._recalculate_reward_stats()
            except Exception:
                pass
            try:
                self.miner.blockchain_manager = self.blockchain_manager
                self.miner.mempool_manager = self.mempool_manager
            except Exception:
                pass
            try:
                if hasattr(self.miner, 'auto_submit'):
                    self.miner.auto_submit = False
            except Exception:
                pass
            try:
                self._configure_cpu_backend(self.miner)
            except Exception:
                pass
            return True
        except Exception as e:
            try:
                log_mining_debug_event("miner_init_failed", {"error": str(e)}, scope="app")
            except Exception:
                pass
            return False
        finally:
            try:
                self._miner_init_lock.release()
            except Exception:
                pass

    def _ensure_cpu_miner_ready(self) -> bool:
        """Ensure CPU miner is initialized (may block)."""
        if self.miner and not isinstance(self.miner, _MinerPlaceholder):
            return True
        return self._init_miner_sync()

    def _configure_cuda_sm3(self, miner=None):
        """Best-effort enablement of lunalib 2.4.1 SM3 CUDA kernel."""
        target_miner = miner or self.miner
        if not target_miner:
            return
        cuda_manager = getattr(target_miner, "cuda_manager", None)
        if not cuda_manager:
            return
        if getattr(self, "hash_algorithm", "sha256") != "sm3":
            return

        has_kernel = False
        try:
            from lunalib.mining.sm3_cuda import sm3_gpu  # type: ignore
            if hasattr(sm3_gpu, "gpu_sm3_hash_messages"):
                has_kernel = True
        except Exception:
            has_kernel = False

        # Try known lunalib 2.4.1 hooks if present
        try:
            for attr in ("set_hash_algorithm", "set_algorithm", "set_algo"):
                if hasattr(cuda_manager, attr):
                    try:
                        getattr(cuda_manager, attr)("sm3")
                    except Exception:
                        pass
            for attr in ("enable_sm3_cuda", "enable_sm3_kernel", "use_sm3_cuda", "use_sm3_kernel"):
                if hasattr(cuda_manager, attr):
                    try:
                        getattr(cuda_manager, attr)(bool(has_kernel))
                    except Exception:
                        pass
            if hasattr(cuda_manager, "hash_algorithm"):
                try:
                    cuda_manager.hash_algorithm = "sm3"
                except Exception:
                    pass
        except Exception:
            pass

        # If lunalib exposes sm3_cuda module, keep a reference (side-effect: module import)
        try:
            _ = LUNALIB_SM3_CUDA
        except Exception:
            pass

        log_mining_debug_event(
            "cuda_sm3_config",
            {
                "has_kernel": bool(has_kernel),
                "cuda_available": bool(getattr(cuda_manager, "cuda_available", False)),
                "device_name": getattr(cuda_manager, "device_name", None),
            },
            scope="cuda",
        )

        if not has_kernel:
            self._log_message("CUDA SM3 kernel not available; GPU mining will fall back to CPU hashing", "warning")

    def _probe_cuda_runtime(self):
        """Capture CUDA runtime availability for packaged builds."""
        try:
            nvcuda_path = os.path.join(os.environ.get("SystemRoot", "C:\\Windows"), "System32", "nvcuda.dll")
        except Exception:
            nvcuda_path = None
        try:
            nvcuda_exists = bool(nvcuda_path and os.path.exists(nvcuda_path))
        except Exception:
            nvcuda_exists = False

        probe = {
            "nvcuda_exists": nvcuda_exists,
            "cuda_path": os.environ.get("CUDA_PATH"),
        }

        try:
            import cupy as cp
            device_count = int(cp.cuda.runtime.getDeviceCount())
            probe["cupy_version"] = getattr(cp, "__version__", None)
            probe["device_count"] = device_count
            if device_count > 0:
                try:
                    with cp.cuda.Device(0):
                        probe["device_name"] = cp.cuda.runtime.getDeviceProperties(0)["name"]
                except Exception as e:
                    probe["device_name_error"] = str(e)
        except Exception as e:
            probe["cupy_error"] = str(e)

        log_mining_debug_event("cuda_runtime_probe", probe, scope="cuda")

    def _configure_cpu_backend(self, miner=None) -> None:
        """Enable LunaLib multithreaded CPU backend / C extension when available."""
        target_miner = miner or self.miner
        if not target_miner:
            return
        try:
            cpu_workers = int(getattr(self.config, "cpu_threads", 1) or getattr(self.config, "sm3_workers", 1) or 1)
        except Exception:
            cpu_workers = 1

        try:
            if hasattr(target_miner, "set_cpu_workers"):
                target_miner.set_cpu_workers(cpu_workers)
        except Exception:
            pass

        # Enable multithreaded CPU mode if exposed
        for attr in (
            "enable_multithreaded_cpu",
            "enable_multithread_cpu",
            "use_multithreaded_cpu",
            "use_multithread_cpu",
        ):
            try:
                value = getattr(target_miner, attr, None)
                if callable(value):
                    value(True)
                elif value is not None:
                    setattr(target_miner, attr, True)
            except Exception:
                pass

        for attr in (
            "set_multithreaded",
            "set_cpu_multithreaded",
            "set_multithreaded_cpu",
        ):
            try:
                func = getattr(target_miner, attr, None)
                if callable(func):
                    func(True)
            except Exception:
                pass

        # Prefer C-extension SM3 batch if available
        if LUNALIB_SM3_BATCH:
            backend_set = False
            for attr in (
                "set_hash_backend",
                "set_cpu_backend",
                "set_sm3_backend",
                "set_hash_impl",
                "set_sm3_impl",
            ):
                try:
                    func = getattr(target_miner, attr, None)
                    if callable(func):
                        for backend in ("sm3_batch", "c_extension", "native", "fast", "auto"):
                            try:
                                func(backend)
                                backend_set = True
                                break
                            except Exception:
                                continue
                        if backend_set:
                            break
                except Exception:
                    continue

            try:
                existing = getattr(target_miner, "sm3_batch", None)
                if existing is None:
                    setattr(target_miner, "sm3_batch", LUNALIB_SM3_BATCH)
            except Exception:
                pass

    def _apply_parallel_mining(self, miner=None) -> None:
        """Enable LunaLib parallel CPU+GPU mining if supported by miner."""
        target_miner = miner or self.miner
        if not target_miner:
            return
        enabled = bool(getattr(self.config, "parallel_mining", False))
        for attr in (
            "parallel_mining",
            "parallel_cpu_gpu",
            "enable_parallel_mining",
            "allow_parallel_mining",
        ):
            try:
                if hasattr(target_miner, attr):
                    setattr(target_miner, attr, enabled)
            except Exception:
                pass
        for attr in (
            "set_parallel_mining",
            "set_parallel_cpu_gpu",
            "enable_parallel_cpu_gpu",
        ):
            try:
                func = getattr(target_miner, attr, None)
                if callable(func):
                    func(enabled)
            except Exception:
                pass

    def _resolve_cuda_batch_size(self) -> int:
        """Resolve GPU batch size (static or dynamic max based on mempool size)."""
        base = int(getattr(self.config, "cuda_batch_size", 100000) or 100000)
        if base < 1000:
            base = 1000
        dynamic = bool(getattr(self.config, "gpu_batch_dynamic", False))

        warmup = bool(getattr(self, "_gpu_batch_warmup", False))
        warmup_size = min(base, 20000)

        mempool_len = 0
        try:
            cached = getattr(self, "_net_cache", {}).get("mempool", [])
            if isinstance(cached, list):
                mempool_len = len(cached)
        except Exception:
            mempool_len = 0

        if mempool_len <= 0:
            try:
                mempool = self.mempool_manager.get_pending_transactions() if self.mempool_manager else []
                mempool_len = len(mempool) if isinstance(mempool, list) else 0
            except Exception:
                mempool_len = 0

        if not dynamic:
            if warmup:
                self._gpu_batch_warmup = False
                return warmup_size
            return base

        if mempool_len > 0:
            scaled = mempool_len * 1000
            if scaled > 1_000_000:
                scaled = 1_000_000
            if scaled < 1000:
                scaled = 1000
            if warmup:
                self._gpu_batch_warmup = False
                return min(warmup_size, scaled)
            return min(base, scaled)
        if warmup:
            self._gpu_batch_warmup = False
            return warmup_size
        return base

    def _apply_hash_algorithm(self):
        algo = str(self.hash_algorithm or "sha256").lower().strip()
        normalized_algo = _normalize_hash_algo(algo)
        if normalized_algo not in ("sha256", "sm3"):
            algo = "sha256"
        elif normalized_algo == "sm3":
            algo = "sm3"
        else:
            algo = "sha256"

        if algo == "sm3" and not _load_sm3_impl():
            self._log_message("SM3 selected but LunaLib SM3 is unavailable; mining will be blocked", "error")

        self.hash_algorithm = algo

        def _calculate_block_hash(index: int, previous_hash: str, timestamp: float,
                                  transactions: List[Dict], nonce: int, miner: str, difficulty: int) -> str:
            try:
                hash_mode = os.getenv("LUNALIB_MINING_HASH_MODE", "json").lower().strip()
                if hash_mode == "compact" and hasattr(self.miner, "_calculate_block_hash_compact"):
                    try:
                        return self.miner._calculate_block_hash_compact(
                            int(index),
                            str(previous_hash),
                            float(timestamp),
                            int(nonce),
                            str(miner),
                            int(difficulty),
                        )
                    except Exception:
                        pass
                block_data = {
                    "difficulty": int(difficulty),
                    "index": int(index),
                    "miner": str(miner),
                    "nonce": int(nonce),
                    "previous_hash": str(previous_hash),
                    "timestamp": float(timestamp),
                    "transactions": [],
                    "version": "1.0"
                }
                block_string = json.dumps(block_data, sort_keys=True)
                if algo == "sm3":
                    return compute_sm3_hexdigest(block_string.encode())
                return hashlib.sha256(block_string.encode()).hexdigest()
            except Exception:
                return "0" * 64

        try:
            self.miner._calculate_block_hash = _calculate_block_hash
        except Exception:
            pass

        cuda_manager = getattr(self.miner, "cuda_manager", None)
        if cuda_manager and hasattr(cuda_manager, "_compute_hashes_parallel"):
            def _compute_hashes_parallel(base_data: Dict, nonces: list) -> list:
                start_ts = time.time()
                hashes = []
                hash_mode = os.getenv("LUNALIB_MINING_HASH_MODE", "json").lower().strip()
                if hash_mode == "compact" and hasattr(self.miner, "_calculate_block_hash_compact"):
                    for nonce in nonces:
                        try:
                            hashes.append(
                                self.miner._calculate_block_hash_compact(
                                    int(base_data.get("index", 0)),
                                    str(base_data.get("previous_hash", "")),
                                    float(base_data.get("timestamp", 0.0)),
                                    int(nonce),
                                    str(base_data.get("miner", "")),
                                    int(base_data.get("difficulty", 0)),
                                )
                            )
                        except Exception:
                            mining_data = base_data.copy()
                            mining_data["nonce"] = int(nonce)
                            payload = json.dumps(mining_data, sort_keys=True).encode()
                            hashes.append(compute_sm3_hexdigest(payload) if algo == "sm3" else hashlib.sha256(payload).hexdigest())
                elif algo == "sm3" and LUNALIB_SM3_BATCH:
                    payloads = []
                    for nonce in nonces:
                        mining_data = base_data.copy()
                        mining_data["nonce"] = int(nonce)
                        payloads.append(json.dumps(mining_data, sort_keys=True).encode())
                    workers = int(getattr(self.config, "sm3_workers", 0) or 0)
                    try:
                        batch_result = LUNALIB_SM3_BATCH(payloads, max_workers=workers)
                        hashes = [h.hex() if isinstance(h, bytes) else h for h in batch_result]
                    except Exception:
                        hashes = [compute_sm3_hexdigest(p) for p in payloads]
                else:
                    for nonce in nonces:
                        mining_data = base_data.copy()
                        mining_data["nonce"] = int(nonce)
                        data_string = json.dumps(mining_data, sort_keys=True)
                        if algo == "sm3":
                            hashes.append(compute_sm3_hexdigest(data_string.encode()))
                        else:
                            hashes.append(hashlib.sha256(data_string.encode()).hexdigest())

                try:
                    elapsed = time.time() - start_ts
                    nonce_count = len(nonces) if nonces is not None else 0
                    if elapsed > 0 and nonce_count > 0:
                        self.stats['cuda_hash_rate'] = nonce_count / elapsed
                        self.stats['cuda_last_nonce'] = int(nonces[-1])
                        if hashes:
                            self.stats['cuda_last_hash'] = hashes[-1]
                except Exception:
                    pass

                return hashes

            try:
                cuda_manager._compute_hashes_parallel = _compute_hashes_parallel
            except Exception:
                pass

        self._log_message(f"Hash algorithm set to: {self.hash_algorithm.upper()}", "info")

    def _ensure_sm3_available(self) -> bool:
        if self.hash_algorithm == "sm3" and not _load_sm3_impl():
            self._log_message("SM3 is required but LunaLib SM3 is unavailable. Please update LunaLib.", "error")
            return False
        return True
            
    def _on_block_mined(self, block_data: Dict):
        """Handle newly mined block (manual mining path)"""
        try:
            success, message = self.submit_block(block_data)
            if success:
                self.stats['successful_blocks'] += 1
                try:
                    self._last_mined_ts = time.time()
                except Exception:
                    pass
                reward_tx = self._create_reward_transaction(block_data)
                if self.new_reward_callback:
                    self.new_reward_callback(reward_tx)
                if self.new_bill_callback:
                    self.new_bill_callback(block_data)
                if self.history_updated_callback:
                    self.history_updated_callback()
                # Force UI/stat update after mining
                try:
                    if hasattr(self, 'main_page') and hasattr(self.main_page, 'update_mining_stats'):
                        self.main_page.update_mining_stats()
                    if hasattr(self, 'sidebar') and hasattr(self.sidebar, 'update_status'):
                        self.sidebar.update_status(self.get_status())
                except Exception:
                    pass
            else:
                self._log_message(f"Block #{block_data['index']} rejected: {message}", "warning")
                self.stats['failed_attempts'] += 1
        except Exception as e:
            self._log_message(f"Error processing mined block: {str(e)}", "error")
            self.stats['failed_attempts'] += 1

    def _on_block_mined_ui(self, block_data: Dict):
        """Handle newly mined block from lunalib miner (already submitted)."""
        try:
            self.stats['successful_blocks'] += 1
            try:
                self._last_mined_ts = time.time()
            except Exception:
                pass
            # Persist mining history so blocks/rewards update immediately
            try:
                block_index = block_data.get("index") if isinstance(block_data, dict) else None
                block_hash = block_data.get("hash") if isinstance(block_data, dict) else None
                nonce = block_data.get("nonce", 0) if isinstance(block_data, dict) else 0
                difficulty = block_data.get("difficulty", self.config.difficulty) if isinstance(block_data, dict) else self.config.difficulty
                mining_time = block_data.get("mining_time", 0) if isinstance(block_data, dict) else 0
                transactions = block_data.get("transactions", []) if isinstance(block_data, dict) else []
                reward = block_data.get("reward") if isinstance(block_data, dict) else None
                is_empty_block = False
                if reward is None:
                    try:
                        reward, is_empty_block = self._calculate_expected_block_reward(block_data if isinstance(block_data, dict) else {})
                        if isinstance(block_data, dict):
                            block_data["reward"] = reward
                            block_data["is_empty_block"] = is_empty_block
                    except Exception:
                        reward = 0.0
                method = "cuda" if (self.gpu_miner and (getattr(self.gpu_miner, "is_mining", False) or getattr(self.gpu_miner, "mining_active", False))) else "cpu"
                record = {
                    "timestamp": time.time(),
                    "status": "success",
                    "block_index": block_index,
                    "hash": block_hash,
                    "nonce": nonce,
                    "difficulty": difficulty,
                    "mining_time": mining_time,
                    "transactions": transactions,
                    "reward": reward,
                    "method": method,
                    "is_empty_block": is_empty_block,
                }
                try:
                    history = self.get_mining_history()
                except Exception:
                    history = []
                history.append(record)
                try:
                    if self.miner and isinstance(getattr(self.miner, "mining_history", None), list):
                        self.miner.mining_history.append(record)
                except Exception:
                    pass
                try:
                    if self.gpu_miner and isinstance(getattr(self.gpu_miner, "mining_history", None), list):
                        self.gpu_miner.mining_history.append(record)
                except Exception:
                    pass
                self.data_manager.save_mining_history(history)
                self._recalculate_reward_stats()
                try:
                    status = self._apply_mining_totals_to_status(self._cached_status or {}, save_cache=True)
                    self.data_manager.save_stats(status)
                except Exception:
                    pass
            except Exception:
                pass
            reward_tx = self._create_reward_transaction(block_data)
            if self.new_reward_callback:
                self.new_reward_callback(reward_tx)
            if self.new_bill_callback:
                self.new_bill_callback(block_data)
            if self.history_updated_callback:
                self.history_updated_callback()
            try:
                if hasattr(self, 'main_page') and hasattr(self.main_page, 'update_mining_stats'):
                    self.main_page.update_mining_stats()
                if hasattr(self, 'sidebar') and hasattr(self.sidebar, 'update_status'):
                    self.sidebar.update_status(self.get_status())
            except Exception:
                pass
        except Exception as e:
            self._log_message(f"Error processing mined block: {str(e)}", "error")

    def _register_miner_callbacks(self, miner, engine: str) -> None:
        """Attach all available lunalib miner callbacks."""
        try:
            miner.hashrate_callback = lambda rate, _engine=engine: self._on_hashrate_update(rate, _engine)
        except Exception:
            pass
        try:
            if hasattr(miner, "on_cpu_hashrate"):
                miner.on_cpu_hashrate(lambda rate, _engine="cpu": self._on_hashrate_update(rate, _engine))
        except Exception:
            pass
        try:
            if hasattr(miner, "on_mining_status"):
                miner.on_mining_status(lambda data, _engine=engine: self._on_mining_status(data, _engine))
        except Exception:
            pass
        try:
            if hasattr(miner, "on_gpu_hashrate"):
                miner.on_gpu_hashrate(lambda rate, _engine="gpu": self._on_hashrate_update(rate, _engine))
        except Exception:
            pass

    def _on_hashrate_update(self, rate: float, engine: str) -> None:
        try:
            if engine == "gpu":
                self.stats["cuda_hash_rate"] = float(rate)
            else:
                self.stats["cpu_hash_rate"] = float(rate)
        except Exception:
            pass
        try:
            if hasattr(self, 'main_page') and hasattr(self.main_page, 'update_mining_stats'):
                self.main_page.update_mining_stats()
            if hasattr(self, 'sidebar') and hasattr(self.sidebar, 'update_status'):
                self.sidebar.update_status(self.get_status())
        except Exception:
            pass

    def _on_mining_status(self, data: Dict, engine: str) -> None:
        """Receive mining status updates from lunalib and refresh UI."""
        try:
            if isinstance(data, dict):
                rate = data.get("hash_rate")
                if isinstance(rate, (int, float)):
                    self._on_hashrate_update(rate, engine)
                current_hash = data.get("current_hash") or data.get("hash")
                current_nonce = data.get("current_nonce")
                if current_nonce is None:
                    current_nonce = data.get("nonce")
                if engine == "gpu":
                    if current_hash:
                        self.stats["cuda_last_hash"] = str(current_hash)
                    if current_nonce is not None:
                        try:
                            self.stats["cuda_last_nonce"] = int(current_nonce)
                        except Exception:
                            pass
                else:
                    if current_hash:
                        self.stats["cpu_last_hash"] = str(current_hash)
                    if current_nonce is not None:
                        try:
                            self.stats["cpu_last_nonce"] = int(current_nonce)
                        except Exception:
                            pass
        except Exception:
            pass
        try:
            if hasattr(self, 'main_page') and hasattr(self.main_page, 'update_mining_stats'):
                self.main_page.update_mining_stats()
            if hasattr(self, 'sidebar') and hasattr(self.sidebar, 'update_status'):
                self.sidebar.update_status(self.get_status())
        except Exception:
            pass
    
    def _create_reward_transaction(self, block_data: Dict) -> Dict:
        """Create mining reward transaction based on block rewards"""
        reward_amount = block_data.get('reward', 50.0)

        reward_tx = {
            'type': 'reward',
            'from': 'Ling Country Mines',
            'to': self.config.miner_address,
            'amount': reward_amount,
            'timestamp': time.time(),
            'block_hash': block_data['hash'],
            'block_index': block_data['index'],
            'hash': f"reward_{block_data['hash']}",
            'status': 'pending',
            'description': f'Mining reward for block #{block_data["index"]}'
        }
        return reward_tx

    def _calculate_expected_block_reward(self, block_data: Dict) -> Tuple[float, bool]:
        """Calculate block reward using LunaLib daemon formula (linear/exponential + bonuses)."""
        try:
            difficulty = int(block_data.get("difficulty") or getattr(self.config, "difficulty", 1) or 1)
        except Exception:
            difficulty = 1

        transactions = block_data.get("transactions", [])
        if not isinstance(transactions, list):
            transactions = []

        non_reward_txs = [
            tx
            for tx in transactions
            if isinstance(tx, dict) and str(tx.get("type") or "").lower() not in ("reward", "mining_reward")
        ]
        is_empty_block = len(non_reward_txs) == 0
        tx_count = len(non_reward_txs)

        fees_total = sum(
            float(tx.get("fee", 0) or 0)
            for tx in non_reward_txs
            if str(tx.get("type") or "").lower() == "transaction"
        )

        gtx_denom_total = 0.0
        for tx in non_reward_txs:
            if str(tx.get("type") or "").lower() in {"gtx_genesis", "genesis_bill"}:
                try:
                    denom = float(tx.get("amount", tx.get("denomination", 0)) or 0)
                except Exception:
                    denom = 0.0
                try:
                    gtx_denom_total += float(self.difficulty_system.gtx_reward_units(denom))
                except Exception:
                    gtx_denom_total += 0.0

        reward_mode = os.getenv("LUNALIB_BLOCK_REWARD_MODE", "linear").lower().strip()
        base_reward = None
        if is_empty_block or reward_mode == "linear":
            base_reward = float(difficulty or 0)

        try:
            reward = float(
                self.difficulty_system.calculate_block_reward(
                    difficulty,
                    block_height=block_data.get("index"),
                    tx_count=0 if is_empty_block else tx_count,
                    fees_total=0.0 if is_empty_block else fees_total,
                    gtx_denom_total=0.0 if is_empty_block else gtx_denom_total,
                    base_reward=base_reward,
                )
            )
        except Exception:
            reward = float(base_reward or 0)

        if is_empty_block:
            try:
                empty_mult = float(os.getenv("LUNALIB_EMPTY_BLOCK_MULT", "0.0001"))
            except Exception:
                empty_mult = 0.0001
            reward = max(0.0, reward * empty_mult)

        return reward, is_empty_block

    def scan_transactions_for_address_cached(self, address: str) -> List[Dict]:
        """Scan blockchain for address transactions starting from last cached height."""
        try:
            start_height = max(0, int(getattr(self.config, "last_scan_height", 0)))
        except Exception:
            start_height = 0
        end_height = self.blockchain_manager.get_blockchain_height()
        if end_height < start_height:
            return []
        transactions = self.blockchain_manager.scan_transactions_for_address(
            address,
            start_height=start_height,
            end_height=end_height,
        )
        self.config.last_scan_height = end_height
        self.config.save_to_storage()
        return transactions

    def _sync_mining_history_from_chain(self, force: bool = False) -> None:
        """Backfill mining history from on-chain reward transactions when local cache is empty."""
        try:
            now_ts = time.time()
            if not force and (now_ts - getattr(self, "_last_reward_sync_ts", 0)) < 60:
                return
            self._last_reward_sync_ts = now_ts
            if not self.blockchain_manager:
                return
            address = getattr(self.config, "miner_address", None)
            if not address:
                return
            history = self.get_mining_history()
            if history and not force:
                return
            txs = self.blockchain_manager.scan_transactions_for_address(address, start_height=0, end_height=self.blockchain_manager.get_blockchain_height())
            if not isinstance(txs, list) or not txs:
                return
            records = []
            for tx in txs:
                if not isinstance(tx, dict):
                    continue
                tx_type = str(tx.get("type", "")).lower()
                if tx_type not in ("reward", "mining_reward") and str(tx.get("from", "")).lower() not in ("network", "ling country mines", "coinbase", "system"):
                    continue
                if str(tx.get("to", "")) != str(address):
                    continue
                block_index = tx.get("block_height") or tx.get("block_index") or tx.get("index")
                block_hash = tx.get("block_hash") or tx.get("hash")
                try:
                    reward_amount = float(tx.get("amount", 0) or 0)
                except Exception:
                    reward_amount = 0.0
                records.append({
                    "timestamp": tx.get("timestamp", time.time()),
                    "status": "success",
                    "block_index": block_index,
                    "hash": block_hash,
                    "nonce": tx.get("nonce", 0) if isinstance(tx.get("nonce", 0), (int, float, str)) else 0,
                    "difficulty": tx.get("difficulty", self.config.difficulty),
                    "mining_time": tx.get("mining_time", 0),
                    "transactions": [tx],
                    "reward": reward_amount,
                    "method": "chain",
                    "is_empty_block": True,
                })
            if not records:
                return
            records.sort(key=lambda r: float(r.get("timestamp", 0) or 0), reverse=True)
            self.data_manager.save_mining_history(records)
            self._recalculate_reward_stats()
            try:
                status = self.get_status()
                if isinstance(status, dict):
                    self.data_manager.save_stats(status)
            except Exception:
                pass
        except Exception:
            pass

    def scan_transactions_for_addresses_cached(self, addresses: List[str]) -> Dict[str, List[Dict]]:
        """Scan blockchain for multiple addresses using lunalib batch scanning."""
        if not addresses:
            return {}
        try:
            start_height = max(0, int(getattr(self.config, "last_scan_height", 0)))
        except Exception:
            start_height = 0
        end_height = self.blockchain_manager.get_blockchain_height()
        if end_height < start_height:
            return {addr: [] for addr in addresses}
        results = self.blockchain_manager.scan_transactions_for_addresses(
            addresses,
            start_height=start_height,
            end_height=end_height,
        )
        self.config.last_scan_height = end_height
        self.config.save_to_storage()
        return results

    def sync_blockchain_cache(self, progress_callback=None, batch_size: int = 200) -> Dict:
        """Warm lunalib blockchain cache using range API."""
        try:
            latest_height = self.blockchain_manager.get_blockchain_height()
            if latest_height <= 0:
                return {"success": True, "height": latest_height}

            start_height = max(0, int(getattr(self.config, "last_scan_height", 0)))
            total = max(1, latest_height - start_height + 1)
            downloaded = 0

            for batch_start in range(start_height, latest_height + 1, batch_size):
                batch_end = min(batch_start + batch_size - 1, latest_height)
                try:
                    self.blockchain_manager.get_blocks_range(batch_start, batch_end)
                except Exception:
                    pass
                downloaded += (batch_end - batch_start + 1)
                if progress_callback:
                    progress = min(99, int((downloaded / total) * 100))
                    progress_callback(progress, f"Caching blocks {batch_start}-{batch_end}")

            if progress_callback:
                progress_callback(100, "Blockchain cache updated")
            return {"success": True, "height": latest_height}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _log_message(self, message: str, msg_type: str = "info"):
        """Log message with callback and save to storage"""
        message = sanitize_for_console(message)

        log_entry = {
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'message': message,
            'type': msg_type
        }
        safe_print(f"DEBUG: Log entry created: {log_entry}")
        self.logs.append(log_entry)
        
        if len(self.logs) > 1000:
            self.logs.pop(0)
            
        self.data_manager.save_logs(self.logs)
        safe_print("DEBUG: Logs saved to storage.")
            
        if self.log_callback:
            self.log_callback(message, msg_type)
            safe_print("DEBUG: Log callback executed.")

    def _recalculate_reward_stats(self):
        try:
            blocks_mined, _empty_blocks_mined, total_reward = self._calculate_mining_totals()
            self.miner.blocks_mined = blocks_mined
            self.miner.total_reward = total_reward
            try:
                if isinstance(self._cached_status, dict):
                    self._apply_mining_totals_to_status(self._cached_status, save_cache=True)
            except Exception:
                pass
        except Exception:
            pass

    def _is_success_record(self, record: Dict) -> bool:
        if not isinstance(record, dict):
            return False
        status = str(record.get("status", "")).lower()
        if status == "success":
            return True
        if record.get("success") is True or record.get("valid") is True:
            return True
        if record.get("hash") and (record.get("block_index") is not None or record.get("index") is not None):
            return True
        return False

    def _calculate_mining_totals(self) -> Tuple[int, int, float]:
        """Calculate blocks mined, empty blocks, and total rewards from mining history."""
        try:
            history = self.get_mining_history()
            success_records = [r for r in history if self._is_success_record(r)]
            empty_blocks_mined = 0
            for record in success_records:
                if record.get("is_empty_block") is True:
                    empty_blocks_mined += 1
                    continue
                txs = record.get("transactions")
                if isinstance(txs, list):
                    non_reward = [
                        tx
                        for tx in txs
                        if isinstance(tx, dict) and str(tx.get("type", "")).lower() not in ("reward", "mining_reward")
                    ]
                    if len(non_reward) == 0:
                        empty_blocks_mined += 1
            total_reward = 0.0
            for record in success_records:
                reward = record.get("reward")
                if reward is None and isinstance(record.get("transactions"), list):
                    try:
                        reward = next(
                            (tx.get("amount") for tx in record.get("transactions", [])
                             if isinstance(tx, dict) and str(tx.get("type", "")).lower() in ("reward", "mining_reward")),
                            0.0,
                        )
                    except Exception:
                        reward = 0.0
                if reward is None:
                    reward = 0.0
                try:
                    total_reward += float(reward)
                except Exception:
                    pass
            return len(success_records), empty_blocks_mined, total_reward
        except Exception:
            return 0, 0, 0.0

    def _apply_mining_totals_to_status(self, status: Dict, save_cache: bool = False) -> Dict:
        """Ensure cached status includes correct mined totals."""
        if not isinstance(status, dict):
            return status
        blocks_mined, empty_blocks_mined, total_reward = self._calculate_mining_totals()
        status["blocks_mined"] = blocks_mined
        status["empty_blocks_mined"] = empty_blocks_mined
        status["total_reward"] = total_reward
        status["reward_transactions"] = blocks_mined
        if save_cache:
            self._cached_status = status
            try:
                self.data_manager.save_stats(status)
            except Exception:
                pass
        return status

    def _default_status(self) -> Dict:
        return {
            'network_height': 0,
            'network_difficulty': 1,
            'mining_difficulty': self.config.difficulty,
            'previous_hash': '0' * 64,
            'miner_address': self.config.miner_address,
            'blocks_mined': self.miner.blocks_mined,
            'auto_mining': self._is_mining_active(),
            'cpu_mining_active': False,
            'gpu_mining_active': False,
            'cpu_hash_rate': 0,
            'gpu_hash_rate': 0,
            'configured_difficulty': self.config.difficulty,
            'total_reward': self.miner.total_reward,
            'empty_blocks_mined': 0,
            'total_transactions': 0,
            'reward_transactions': self.miner.blocks_mined,
            'connection_status': 'disconnected',
            'p2p_connected': False,
            'p2p_peers': 0,
            'uptime': time.time() - self.stats['start_time'],
            'total_mining_attempts': len(self.miner.mining_history),
            'success_rate': 0,
            'avg_mining_time': 0,
            'current_hash_rate': 0,
            'current_hash': '',
            'current_nonce': 0,
            'cpu_nonce': 0,
            'gpu_nonce': 0,
            'cuda_available': False,
            'mining_method': 'CPU'
        }

    def _is_mining_active(self) -> bool:
        """Return True if any miner (CPU/GPU) is actively mining."""
        try:
            return bool(
                (self.miner and (getattr(self.miner, "is_mining", False) or getattr(self.miner, "mining_active", False) or getattr(self.miner, "running", False) or getattr(self.miner, "started", False)))
                or (self.cpu_miner and (getattr(self.cpu_miner, "is_mining", False) or getattr(self.cpu_miner, "mining_active", False) or getattr(self.cpu_miner, "running", False) or getattr(self.cpu_miner, "started", False)))
                or (self.gpu_miner and (getattr(self.gpu_miner, "is_mining", False) or getattr(self.gpu_miner, "mining_active", False) or getattr(self.gpu_miner, "running", False) or getattr(self.gpu_miner, "started", False)))
            )
        except Exception:
            return False

    def _merge_status(self, status: Dict) -> Dict:
        defaults = self._default_status()
        if not isinstance(status, dict):
            return defaults
        merged = {**defaults}
        for key, value in status.items():
            if value is not None:
                merged[key] = value
        return merged

    def enable_live_stats(self):
        """Switch from cached stats to live stats"""
        self._prefer_cached_stats = False
    
    def get_status(self) -> Dict:
        """Get node status, preferring P2P for blocks/mempool if peers are available"""
        try:
            disable_cache = os.getenv("LUNANODE_DISABLE_STATS_CACHE", "0") == "1"
            fast_startup = os.getenv("LUNANODE_FAST_STARTUP", "0") == "1"
            now_ts = time.time()
            recent_mine = (now_ts - getattr(self, "_last_mined_ts", 0)) < 30
            if not disable_cache and fast_startup and (time.time() - getattr(self, "_startup_ts", 0)) < 30 and not recent_mine:
                cached = self._cached_status or self.data_manager.load_stats()
                if isinstance(cached, dict) and cached:
                    cached = self._apply_mining_totals_to_status(cached, save_cache=True)
                    cached['hash_algorithm'] = self.hash_algorithm
                    return self._merge_status(cached)
                status = self._default_status()
                status['hash_algorithm'] = self.hash_algorithm
                return status
            if not disable_cache and self._prefer_cached_stats and not self._is_mining_active() and not recent_mine:
                cached = self._cached_status or self.data_manager.load_stats()
                if isinstance(cached, dict) and cached:
                    cached = self._apply_mining_totals_to_status(cached, save_cache=True)
                    cached['hash_algorithm'] = self.hash_algorithm
                    return self._merge_status(cached)
            now = time.time()
            use_p2p = self.p2p_client and hasattr(self.p2p_client, 'is_connected') and self.p2p_client.is_connected() and len(self.peers) > 0
            if now - self._net_cache_ts >= self.net_poll_interval:
                if use_p2p:
                    # Prefer P2P for blocks and mempool
                    try:
                        current_height = self.p2p_client.get_blockchain_height()
                        latest_block = self.p2p_client.get_latest_block() if current_height > 0 else None
                        mempool = self.p2p_client.get_pending_transactions() if hasattr(self.p2p_client, 'get_pending_transactions') else []
                    except Exception:
                        current_height = self.blockchain_manager.get_blockchain_height()
                        latest_block = self.blockchain_manager.get_latest_block() if current_height > 0 else None
                        mempool = self.mempool_manager.get_pending_transactions() if self.mempool_manager else []
                else:
                    current_height = self.blockchain_manager.get_blockchain_height()
                    latest_block = self.blockchain_manager.get_latest_block() if current_height > 0 else None
                    mempool = self.mempool_manager.get_pending_transactions() if self.mempool_manager else []
                self._net_cache_ts = now
                self._net_cache = {
                    "height": current_height,
                    "latest_block": latest_block,
                    "mempool": mempool,
                }
            else:
                current_height = self._net_cache.get("height", 0)
                latest_block = self._net_cache.get("latest_block")
                mempool = self._net_cache.get("mempool", [])
            # Backfill mining history from chain if local cache is empty
            try:
                self._sync_mining_history_from_chain()
            except Exception:
                pass
            merged_history = self.get_mining_history()
            success_records = [r for r in merged_history if self._is_success_record(r)]
            empty_blocks_mined = 0
            for record in success_records:
                if record.get("is_empty_block") is True:
                    empty_blocks_mined += 1
                    continue
                txs = record.get("transactions")
                if isinstance(txs, list):
                    non_reward = [tx for tx in txs if isinstance(tx, dict) and str(tx.get("type", "")).lower() not in ("reward", "mining_reward")]
                    if len(non_reward) == 0:
                        empty_blocks_mined += 1
            total_mining_time = sum(record.get('mining_time', 0) for record in merged_history)
            avg_mining_time = total_mining_time / len(merged_history) if merged_history else 0
            blocks_mined = len(success_records)
            total_reward = 0.0
            for record in success_records:
                reward = record.get("reward")
                if reward is None and isinstance(record.get("transactions"), list):
                    try:
                        reward = next(
                            (tx.get("amount") for tx in record.get("transactions", [])
                             if isinstance(tx, dict) and str(tx.get("type", "")).lower() in ("reward", "mining_reward")),
                            0.0,
                        )
                    except Exception:
                        reward = 0.0
                if reward is None:
                    reward = 0.0
                try:
                    total_reward += float(reward)
                except Exception:
                    pass
            try:
                self.miner.blocks_mined = blocks_mined
                self.miner.total_reward = total_reward
            except Exception:
                pass
            cuda_available = self.miner.cuda_manager.cuda_available if self.miner.cuda_manager else False
            cpu_active = bool(self.cpu_miner and (getattr(self.cpu_miner, "is_mining", False) or getattr(self.cpu_miner, "mining_active", False)))
            gpu_active = bool(
                self.gpu_miner
                and (
                    getattr(self.gpu_miner, "is_mining", False)
                    or getattr(self.gpu_miner, "mining_active", False)
                    or getattr(self.gpu_miner, "gpu_enabled", False)
                    or getattr(self.gpu_miner, "running", False)
                    or getattr(self.gpu_miner, "started", False)
                )
            )
            using_cuda = cuda_available and self.config.use_gpu
            gpu_stats = {}
            if self.gpu_miner:
                try:
                    gpu_stats = self.gpu_miner.get_mining_stats() if hasattr(self.gpu_miner, "get_mining_stats") else {}
                except Exception:
                    gpu_stats = {}
            gpu_hash_rate = 0.0
            if gpu_stats:
                try:
                    gpu_hash_rate = float(gpu_stats.get('hash_rate', 0) or 0)
                except Exception:
                    gpu_hash_rate = 0.0
            if not gpu_hash_rate:
                try:
                    gpu_hash_rate = float(self.stats.get('cuda_hash_rate', 0) or 0)
                except Exception:
                    gpu_hash_rate = 0.0
            if not gpu_hash_rate and self.gpu_miner:
                try:
                    gpu_hash_rate = float(
                        getattr(self.gpu_miner, "last_gpu_hashrate", 0)
                        or getattr(self.gpu_miner, "hash_rate", 0)
                        or getattr(self.gpu_miner, "gpu_hash_rate", 0)
                        or getattr(self.gpu_miner, "cuda_hash_rate", 0)
                        or 0
                    )
                except Exception:
                    gpu_hash_rate = 0.0
            if not gpu_hash_rate:
                try:
                    cuda_mgr = getattr(self.gpu_miner, "cuda_manager", None) if self.gpu_miner else None
                    gpu_hash_rate = float(getattr(cuda_mgr, "hash_rate", 0) or getattr(cuda_mgr, "gpu_hash_rate", 0) or 0)
                except Exception:
                    gpu_hash_rate = 0.0

            if using_cuda and (self.stats.get('cuda_hash_rate', 0) > 0 or gpu_stats):
                current_hash_rate = gpu_stats.get('hash_rate', 0) or self.stats['cuda_hash_rate']
                current_hash = gpu_stats.get('current_hash', '') or gpu_stats.get('hash', '') or self.stats.get('cuda_last_hash', '')
                current_nonce = gpu_stats.get('current_nonce', 0) or gpu_stats.get('nonce', 0) or self.stats.get('cuda_last_nonce', 0)
                if not current_nonce and self.gpu_miner:
                    try:
                        current_nonce = int(
                            getattr(self.gpu_miner, 'current_nonce', 0)
                            or getattr(self.gpu_miner, 'last_nonce', 0)
                            or getattr(getattr(self.gpu_miner, 'cuda_manager', None), 'last_nonce', 0)
                            or 0
                        )
                    except Exception:
                        pass
                if not current_hash and self.gpu_miner:
                    try:
                        current_hash = (
                            getattr(self.gpu_miner, 'current_hash', '')
                            or getattr(self.gpu_miner, 'last_hash', '')
                            or getattr(getattr(self.gpu_miner, 'cuda_manager', None), 'last_hash', '')
                            or ''
                        )
                    except Exception:
                        pass
            else:
                mining_stats = self.miner.get_mining_stats() if hasattr(self.miner, 'get_mining_stats') else {}
                current_hash_rate = mining_stats.get('hash_rate', 0)
                current_hash = mining_stats.get('current_hash', '')
                current_nonce = mining_stats.get('current_nonce', 0)
                if not current_hash_rate:
                    current_hash_rate = getattr(self.miner, 'last_cpu_hashrate', 0) or getattr(self.miner, 'hash_rate', 0) or self.stats.get('cpu_hash_rate', 0)
                if not current_hash:
                    current_hash = self.stats.get('cpu_last_hash', '')
                if not current_nonce:
                    try:
                        current_nonce = int(self.stats.get('cpu_last_nonce', 0) or 0)
                    except Exception:
                        pass
            cpu_nonce = 0
            gpu_nonce = 0
            try:
                cpu_nonce = int(self.stats.get('cpu_last_nonce', 0) or 0)
            except Exception:
                cpu_nonce = 0
            try:
                gpu_nonce = int(self.stats.get('cuda_last_nonce', 0) or 0)
            except Exception:
                gpu_nonce = 0
            try:
                if mining_stats:
                    cpu_nonce = int(mining_stats.get('current_nonce', 0) or mining_stats.get('nonce', 0) or cpu_nonce)
            except Exception:
                pass
            try:
                if gpu_stats:
                    gpu_nonce = int(gpu_stats.get('current_nonce', 0) or gpu_stats.get('nonce', 0) or gpu_nonce)
            except Exception:
                pass
            if not cpu_nonce:
                try:
                    cpu_nonce = int(
                        getattr(self.miner, 'current_nonce', 0)
                        or getattr(self.miner, 'last_nonce', 0)
                        or cpu_nonce
                    )
                except Exception:
                    pass
            if not gpu_nonce:
                try:
                    gpu_nonce = int(
                        getattr(self.gpu_miner, 'current_nonce', 0)
                        or getattr(self.gpu_miner, 'last_nonce', 0)
                        or getattr(getattr(self.gpu_miner, 'cuda_manager', None), 'last_nonce', 0)
                        or gpu_nonce
                    )
                except Exception:
                    pass
            if (not cpu_nonce or not gpu_nonce) and merged_history:
                try:
                    for rec in merged_history:
                        if not isinstance(rec, dict):
                            continue
                        method = str(rec.get('method', '')).lower()
                        if not cpu_nonce and method == 'cpu':
                            try:
                                cpu_nonce = int(rec.get('nonce', 0) or 0)
                            except Exception:
                                pass
                        if not gpu_nonce and method == 'cuda':
                            try:
                                gpu_nonce = int(rec.get('nonce', 0) or 0)
                            except Exception:
                                pass
                        if cpu_nonce and gpu_nonce:
                            break
                except Exception:
                    pass
            if not current_nonce or not current_hash:
                try:
                    latest = None
                    if merged_history:
                        latest = merged_history[0]
                    if isinstance(latest, dict):
                        if not current_nonce:
                            try:
                                current_nonce = int(latest.get("nonce", 0) or 0)
                            except Exception:
                                pass
                        if not current_hash:
                            current_hash = latest.get("hash", "") or current_hash
                except Exception:
                    pass
            try:
                cpu_hash_rate = float(self.stats.get('cpu_hash_rate', 0) or 0)
            except Exception:
                cpu_hash_rate = 0.0
            try:
                if mining_stats:
                    cpu_hash_rate = float(mining_stats.get('hash_rate', 0) or cpu_hash_rate)
            except Exception:
                pass
            if not cpu_hash_rate:
                try:
                    cpu_hash_rate = float(getattr(self.miner, 'last_cpu_hashrate', 0) or getattr(self.miner, 'hash_rate', 0) or cpu_hash_rate)
                except Exception:
                    pass
            p2p_status = self.get_p2p_status()
            status = {
                'network_height': current_height,
                'network_difficulty': latest_block.get('difficulty', 1) if latest_block else 1,
                'mining_difficulty': self.config.difficulty,
                'previous_hash': latest_block.get('hash', '0' * 64) if latest_block else '0' * 64,
                'miner_address': self.config.miner_address,
                'blocks_mined': blocks_mined,
                'auto_mining': self._is_mining_active(),
                'cpu_mining_active': cpu_active,
                'gpu_mining_active': gpu_active,
                'cpu_hash_rate': cpu_hash_rate,
                'gpu_hash_rate': gpu_hash_rate,
                'configured_difficulty': self.config.difficulty,
                'total_reward': total_reward,
                'empty_blocks_mined': empty_blocks_mined,
                'total_transactions': len(mempool),
                'reward_transactions': blocks_mined,
                'connection_status': 'connected' if current_height >= 0 else 'disconnected',
                'p2p_connected': p2p_status.get('connected', False),
                'p2p_peers': p2p_status.get('peers', 0),
                'uptime': time.time() - self.stats['start_time'],
                'total_mining_attempts': len(merged_history),
                'success_rate': (self.stats['successful_blocks'] / len(merged_history)) * 100 if merged_history else 0,
                'avg_mining_time': avg_mining_time,
                'current_hash_rate': current_hash_rate,
                'current_hash': current_hash,
                'current_nonce': current_nonce,
                'cpu_nonce': cpu_nonce,
                'gpu_nonce': gpu_nonce,
                'cuda_available': cuda_available,
                'mining_method': (
                    'CPU + GPU'
                    if cpu_active and gpu_active
                    else 'CUDA'
                    if gpu_active
                    else 'CPU'
                    if cpu_active
                    else 'CUDA'
                    if using_cuda
                    else 'CPU'
                )
            }
            self._cached_status = status
            self.data_manager.save_stats(status)
            status['hash_algorithm'] = self.hash_algorithm
            return status
        except Exception as e:
            return {
                'network_height': 0,
                'network_difficulty': 1,
                'mining_difficulty': self.config.difficulty,
                'previous_hash': '0' * 64,
                'miner_address': self.config.miner_address,
                'blocks_mined': self.miner.blocks_mined,
                'auto_mining': self.miner.is_mining,
                'configured_difficulty': self.config.difficulty,
                'total_reward': self.miner.total_reward,
                'total_transactions': 0,
                'reward_transactions': self.miner.blocks_mined,
                'connection_status': 'error',
                'p2p_connected': False,
                'p2p_peers': 0,
                'uptime': time.time() - self.stats['start_time'],
                'total_mining_attempts': len(self.miner.mining_history),
                'success_rate': 0,
                'avg_mining_time': 0,
                'current_hash_rate': 0,
                'current_hash': '',
                'current_nonce': 0,
                'cuda_available': False,
                'mining_method': 'CPU',
                'hash_algorithm': self.hash_algorithm,
                'error': str(e)
            }
    
    def mine_single_block(self, miner=None, force_cuda: Optional[bool] = None) -> Tuple[bool, str]:
        """Mine a single block (lunalib 1.8.7 GenesisMiner対応)"""
        try:
            if not self._ensure_sm3_available():
                return False, "SM3 unavailable"
            target_miner = miner or self.miner
            log_cpu_mining_event("mine_single_block_called", {})
            # lunalib 1.8.7 Miner: mine_block()を使う
            mining_start = time.time()
            result = target_miner.mine_block()
            safe_print(f"[DEBUG] mine_block() result: {result}")
            log_cpu_mining_event("mine_block_result", {"result": str(result)})
            success, message, block_data = False, '', None
            if isinstance(result, tuple) and len(result) == 3:
                success, message, block_data = result
            elif isinstance(result, dict):
                success = result.get('success', False)
                message = result.get('error', '')
                block_data = result.get('block', result)
            else:
                success = bool(result)
                message = ''
                block_data = result if isinstance(result, dict) else None
            if not success and isinstance(message, str) and "Previous hash mismatch" in message:
                return False, "Stale block detected (chain advanced)"
            safe_print(f"[DEBUG] Parsed block_data: {block_data}")
            safe_print(f"[DEBUG] success: {success}, message: {message}")
            if success and block_data:
                log_cpu_mining_event("block_mined", {"block_index": block_data.get('index'), "block_data": block_data})
                block_index = block_data.get('index', 'unknown')
                block_difficulty = block_data.get('difficulty', self.config.difficulty)
                if not block_difficulty or block_difficulty < 1:
                    block_difficulty = self.config.difficulty
                reward, is_empty_block = self._calculate_expected_block_reward(block_data)
                block_data['reward'] = reward
                nonce = block_data.get('nonce', 0)
                block_hash = block_data.get('hash', '')
                mining_time = time.time() - mining_start
                tx_count = len(block_data.get('transactions', []))
                safe_print(f"[DEBUG] Mined block keys: {list(block_data.keys())}")
                safe_print(f"[DEBUG] nonce: {nonce}, mining_time: {mining_time}, hash: {block_hash}, difficulty: {block_difficulty}")
                # --- 報酬トランザクションのself-transfer修正を必ず適用 ---
                fixed_transactions = []
                miner_addr = self.config.miner_address
                for tx in block_data.get('transactions', []):
                    is_reward = (
                        tx.get('type') == 'reward' or
                        tx.get('type') == 'mining_reward' or
                        tx.get('from') == 'network' or
                        tx.get('from') == 'coinbase' or
                        tx.get('from') == 'system' or
                        tx.get('from') == '' or
                        tx.get('from') is None or
                        tx.get('from') == tx.get('to') or
                        'reward' in str(tx.get('hash', '')).lower()
                    )
                    if is_reward:
                        fixed_tx = tx.copy()
                        fixed_tx['type'] = 'reward'
                        fixed_tx['from'] = 'Ling Country Mines'
                        fixed_tx['to'] = miner_addr
                        fixed_tx['amount'] = reward
                        fixed_tx['is_empty_block'] = is_empty_block
                        fixed_transactions.append(fixed_tx)
                    else:
                        fixed_transactions.append(tx)
                block_data['transactions'] = fixed_transactions
                # --- ここまで ---
                if force_cuda is None:
                    cuda_used = hasattr(target_miner, 'cuda_manager') and target_miner.cuda_manager and getattr(target_miner.cuda_manager, 'cuda_available', False) and self.config.use_gpu
                else:
                    cuda_used = bool(force_cuda)
                if cuda_used and mining_time > 0:
                    self.stats['cuda_hash_rate'] = nonce / mining_time
                    self.stats['cuda_last_nonce'] = nonce
                    self.stats['cuda_last_hash'] = block_hash
                    self.stats['last_mining_method'] = 'cuda'
                    safe_print(f"[DEBUG] CUDA mining: cuda_hash_rate={self.stats['cuda_hash_rate']}")
                    log_mining_debug_event(
                        "cuda_mining_result",
                        {
                            "nonce": nonce,
                            "mining_time": mining_time,
                            "hash_rate": self.stats.get("cuda_hash_rate", 0),
                            "block_index": block_data.get("index"),
                        },
                        scope="cuda",
                    )
                else:
                    if hasattr(target_miner, 'get_mining_stats'):
                        mining_stats = target_miner.get_mining_stats()
                        safe_print(f"[DEBUG] mining_stats: {mining_stats}")
                        self.stats['cpu_hash_rate'] = mining_stats.get('hash_rate', 0)
                        safe_print(f"[DEBUG] CPU mining: cpu_hash_rate={self.stats['cpu_hash_rate']} (lunalib), nonce={nonce}, mining_time={mining_time}")
                    else:
                        if mining_time > 0:
                            self.stats['cpu_hash_rate'] = nonce / mining_time
                            safe_print(f"[DEBUG] CPU mining: cpu_hash_rate={self.stats['cpu_hash_rate']}, nonce={nonce}, mining_time={mining_time}")
                    self.stats['last_mining_method'] = 'cpu'
                submit_success, submit_message = self.submit_block(block_data)
                log_cpu_mining_event("submit_block_result", {"success": submit_success, "message": submit_message, "block_index": block_data.get('index')})
                if submit_success:
                    log_cpu_mining_event("block_submitted", {"block_index": block_data.get('index')})
                    self._log_message(f"Block #{block_index} mined & submitted ({tx_count} txs) - Reward: {reward}", "success")
                    try:
                        self._last_mined_ts = time.time()
                    except Exception:
                        pass
                    # Refresh local cache/stats immediately
                    try:
                        self.data_manager.save_submitted_block(block_data)
                    except Exception:
                        pass
                    try:
                        self._update_bills_cache_from_block(block_data)
                    except Exception:
                        pass
                    try:
                        # Update cached status snapshot so UI reflects new totals
                        status = self.get_status()
                        if isinstance(status, dict):
                            status = self._apply_mining_totals_to_status(status)
                            self.data_manager.save_stats(status)
                    except Exception:
                        pass
                    reward_tx = self._create_reward_transaction(block_data)
                    # Update local mining stats/history so rewards are detected immediately
                    try:
                        self.miner.blocks_mined = getattr(self.miner, "blocks_mined", 0) + 1
                        self.miner.total_reward = getattr(self.miner, "total_reward", 0) + reward
                        if target_miner is not self.miner:
                            target_miner.blocks_mined = getattr(target_miner, "blocks_mined", 0) + 1
                            target_miner.total_reward = getattr(target_miner, "total_reward", 0) + reward
                    except Exception:
                        pass
                    try:
                        history = getattr(target_miner, "mining_history", None)
                        if history is None:
                            history = []
                            target_miner.mining_history = history
                        record = {
                            "timestamp": time.time(),
                            "status": "success",
                            "block_index": block_index,
                            "hash": block_hash,
                            "nonce": nonce,
                            "difficulty": block_difficulty,
                            "mining_time": mining_time,
                            "transactions": block_data.get("transactions", []),
                            "reward": reward,
                            "method": "cuda" if cuda_used else "cpu",
                        }
                        history.append(record)
                        self.data_manager.save_mining_history(history)
                        self._recalculate_reward_stats()
                        try:
                            status = self._apply_mining_totals_to_status(self._cached_status or {}, save_cache=True)
                            self.data_manager.save_stats(status)
                        except Exception:
                            pass
                    except Exception:
                        pass
                    if self.new_reward_callback:
                        try:
                            self.new_reward_callback(reward_tx)
                        except Exception:
                            pass
                    if self.history_updated_callback:
                        try:
                            self.history_updated_callback()
                        except Exception:
                            pass
                    return True, f"Block #{block_index} mined & submitted ({tx_count} txs) - Reward: {reward}"
                else:
                    log_cpu_mining_event("block_submission_failed", {"block_index": block_data.get('index'), "submit_message": submit_message})
                    self._log_message(f"Block #{block_index} mined but submission failed: {submit_message}", "warning")
                    return False, f"Block #{block_index} mined but submission failed: {submit_message}"
            else:
                log_cpu_mining_event("mining_failed", {"message": message})
                self._log_message(f"Mining failed: {message}", "error")
                return False, f"Mining failed: {message}"
        except Exception as e:
            log_cpu_mining_event("mining_exception", {"error": str(e)})
            self._log_message(f"Mining error: {str(e)}", "error")
            return False, f"Mining error: {str(e)}"

    def mine_genesis_bill(self, denomination: float, bill_data: Optional[Dict] = None) -> Tuple[bool, str, Optional[Dict]]:
        """Mine a GTX Genesis bill using LunaLib GenesisMiner."""
        if not self.genesis_miner:
            return False, "Genesis miner unavailable", None
        if not self._ensure_sm3_available():
            return False, "SM3 unavailable", None
        try:
            result = self.genesis_miner.mine_bill(denomination, self.config.miner_address, bill_data or {})
            if isinstance(result, dict) and result.get("success"):
                return True, "Genesis bill mined", result
            message = "Genesis bill mining failed"
            if isinstance(result, dict) and result.get("error"):
                message = result.get("error")
            return False, message, result if isinstance(result, dict) else None
        except Exception as e:
            return False, f"Genesis mining error: {str(e)}", None
    
    def start_auto_mining(self):
        """Start auto-mining (CPU:従来通り, GPU:lunalib 2.4.0仕様)"""
        self.stop_auto_mining()
        self._log_message("Auto-mining invoked", "info")
        if not self._ensure_sm3_available():
            self._log_message("Auto-mining blocked (SM3 unavailable)", "error")
            return False
        if not self._ensure_cpu_miner_ready():
            self._log_message("CPU miner unavailable", "error")
            return False
        self.enable_live_stats()
        self._stop_mining_event.clear()

        if bool(getattr(self.config, "adapt_load_balance", False)):
            try:
                self.config.enable_cpu_mining = True
                self.config.enable_gpu_mining = True
                self.config.gpu_batch_dynamic = True
                self.config.cpu_threads = max(1, (os.cpu_count() or 4) - 1)
                self.config.save_to_storage()
            except Exception:
                pass

        # Keep lunalib-style separate CPU/GPU miners
        self._configure_cpu_backend(self.cpu_miner)
        self._apply_parallel_mining(self.cpu_miner)
        self._apply_parallel_mining(self.gpu_miner)

        cpu_enabled = bool(getattr(self.config, "enable_cpu_mining", True))
        gpu_enabled = bool(getattr(self.config, "enable_gpu_mining", self.config.use_gpu))
        gpu_ready = bool(
            gpu_enabled
            and self.gpu_miner
            and getattr(self.gpu_miner, "cuda_manager", None)
            and getattr(self.gpu_miner.cuda_manager, "cuda_available", False)
        )
        if gpu_ready:
            self._gpu_batch_warmup = True

        started_any = False
        started_cpu = False
        started_gpu = False
        if cpu_enabled and self.cpu_miner:
            try:
                self.cpu_miner.cpu_enabled = True
                self.cpu_miner.gpu_enabled = False
                if hasattr(self.cpu_miner, "cuda_manager"):
                    self.cpu_miner.cuda_manager = None
                self.cpu_miner.start_mining()
                started_any = True
                started_cpu = True
            except Exception as e:
                self._log_message(f"Failed to start CPU mining: {e}", "error")

        if gpu_ready:
            try:
                self._configure_cuda_sm3(self.gpu_miner)
                self.gpu_miner.gpu_enabled = True
                self.gpu_miner.cpu_enabled = False
                self.gpu_miner.start_mining()
                try:
                    self.gpu_miner.is_mining = True
                except Exception:
                    pass
                started_any = True
                started_gpu = True
            except Exception as e:
                self._log_message(f"Failed to start GPU mining: {e}", "error")

        if started_any:
            if started_cpu and started_gpu:
                self._log_message("Auto-mining started (CPU + GPU)", "info")
            elif started_gpu:
                self._log_message("Auto-mining started (GPU)", "info")
            elif started_cpu:
                self._log_message("Auto-mining started (CPU)", "info")
        return started_any

    def start_cpu_mining(self) -> bool:
        """Start CPU mining only."""
        if not self._ensure_sm3_available():
            self._log_message("CPU mining blocked (SM3 unavailable)", "error")
            return False
        if not self._ensure_cpu_miner_ready() or not self.cpu_miner:
            self._log_message("CPU miner unavailable", "error")
            return False
        self.enable_live_stats()
        try:
            self._configure_cpu_backend(self.cpu_miner)
            self._apply_parallel_mining(self.cpu_miner)
            self.cpu_miner.cpu_enabled = True
            self.cpu_miner.gpu_enabled = False
            if hasattr(self.cpu_miner, "cuda_manager"):
                self.cpu_miner.cuda_manager = None
            self.cpu_miner.start_mining()
            self._log_message("CPU mining started", "info")
            return True
        except Exception as e:
            self._log_message(f"Failed to start CPU mining: {e}", "error")
            return False

    def stop_cpu_mining(self) -> None:
        """Stop CPU mining only."""
        if not self.cpu_miner:
            return
        try:
            self.cpu_miner.is_mining = False
            for attr in ("abort_mining", "abort", "request_abort"):
                try:
                    func = getattr(self.cpu_miner, attr, None)
                    if callable(func):
                        func()
                        break
                except Exception:
                    continue
            self.cpu_miner.stop_mining()
            self._log_message("CPU mining stopped", "info")
        except Exception as e:
            self._log_message(f"Failed to stop CPU mining: {e}", "error")

    def start_gpu_mining(self) -> bool:
        """Start GPU mining only."""
        if not self._ensure_sm3_available():
            self._log_message("GPU mining blocked (SM3 unavailable)", "error")
            return False
        if not self.gpu_miner or not getattr(self.gpu_miner, "cuda_manager", None):
            if not self._ensure_gpu_miner_ready():
                self._log_message("GPU miner unavailable", "error")
                return False
        gpu_ready = bool(
            getattr(self.gpu_miner, "cuda_manager", None)
            and getattr(self.gpu_miner.cuda_manager, "cuda_available", False)
        )
        log_mining_debug_event(
            "gpu_mining_start_attempt",
            {
                "gpu_ready": gpu_ready,
                "cuda_available": bool(getattr(getattr(self.gpu_miner, "cuda_manager", None), "cuda_available", False)),
                "device_name": getattr(getattr(self.gpu_miner, "cuda_manager", None), "device_name", None),
            },
            scope="cuda",
        )
        if not gpu_ready:
            self._log_message("GPU mining not available (CUDA not ready)", "error")
            return False
        self.enable_live_stats()
        try:
            self._gpu_batch_warmup = True
            self._configure_cuda_sm3(self.gpu_miner)
            self._apply_parallel_mining(self.gpu_miner)
            self.gpu_miner.gpu_enabled = True
            self.gpu_miner.cpu_enabled = False
            self.gpu_miner.start_mining()
            try:
                self.gpu_miner.is_mining = True
            except Exception:
                pass
            self._log_message("GPU mining started", "info")
            log_mining_debug_event("gpu_mining_started", {}, scope="cuda")
            return True
        except Exception as e:
            self._log_message(f"Failed to start GPU mining: {e}", "error")
            log_mining_debug_event("gpu_mining_start_failed", {"error": str(e)}, scope="cuda")
            return False

    def _ensure_gpu_miner_ready(self) -> bool:
        """Lazy-create GPU miner when GPU init was deferred at startup."""
        if not LunaLibMiner:
            return False
        try:
            self.config.enable_gpu_mining = True
            self.config.use_gpu = True
            self.config.save_to_storage()
        except Exception:
            pass

        try:
            self.gpu_miner = LunaLibMiner(
                self.config,
                self.data_manager,
                mining_started_callback=self.mining_started_callback,
                mining_completed_callback=self.mining_completed_callback,
                block_mined_callback=self._on_block_mined_ui,
                block_added_callback=self._post_submit_refresh,
            )
            self._register_miner_callbacks(self.gpu_miner, "gpu")
            self._apply_parallel_mining(self.gpu_miner)
            self.gpu_miner.blockchain_manager = self.blockchain_manager
            self.gpu_miner.mempool_manager = self.mempool_manager
            try:
                if hasattr(self.gpu_miner, "set_cpu_workers"):
                    self.gpu_miner.set_cpu_workers(1)
            except Exception:
                pass
            self.gpu_miner.use_cuda = True
            if hasattr(self.gpu_miner, "use_cpu"):
                self.gpu_miner.use_cpu = False
            self._configure_cuda_sm3(self.gpu_miner)
            available = bool(
                getattr(self.gpu_miner, "cuda_manager", None)
                and getattr(self.gpu_miner.cuda_manager, "cuda_available", False)
            )
            log_mining_debug_event(
                "gpu_miner_lazy_init",
                {"cuda_available": available, "device_name": getattr(getattr(self.gpu_miner, "cuda_manager", None), "device_name", None)},
                scope="cuda",
            )
            return available
        except Exception as e:
            log_mining_debug_event("gpu_miner_lazy_init_failed", {"error": str(e)}, scope="cuda")
            return False

    def stop_gpu_mining(self) -> None:
        """Stop GPU mining only."""
        if not self.gpu_miner:
            return
        try:
            self.gpu_miner.is_mining = False
            for attr in ("abort_mining", "abort", "request_abort"):
                try:
                    func = getattr(self.gpu_miner, attr, None)
                    if callable(func):
                        func()
                        break
                except Exception:
                    continue
            self.gpu_miner.stop_mining()
            self._log_message("GPU mining stopped", "info")
        except Exception as e:
            self._log_message(f"Failed to stop GPU mining: {e}", "error")
    
    def stop_auto_mining(self):
        """Stop auto-mining (lunalib 2.4.0仕様: stop_miningのみ)"""
        self._stop_mining_event.set()
        try:
            def _abort_miner(miner_obj):
                if not miner_obj:
                    return
                for attr in ("abort_mining", "abort", "request_abort"):
                    try:
                        func = getattr(miner_obj, attr, None)
                        if callable(func):
                            func()
                            break
                    except Exception:
                        continue
            if self.miner:
                self.miner.is_mining = False
                _abort_miner(self.miner)
                self.miner.stop_mining()
            if self.cpu_miner:
                self.cpu_miner.is_mining = False
                _abort_miner(self.cpu_miner)
                self.cpu_miner.stop_mining()
            if self.gpu_miner:
                self.gpu_miner.is_mining = False
                _abort_miner(self.gpu_miner)
                self.gpu_miner.stop_mining()
            self._log_message("Stopped mining (CPU/GPU)", "info")
        except Exception as e:
            self._log_message(f"Failed to stop mining: {e}", "error")

    def update_performance_level(self, level: int):
        """Update CPU mining throttle level (10-100)."""
        try:
            level = int(level)
        except Exception:
            return
        if level < 10:
            level = 10
        if level > 100:
            level = 100
        self.config.performance_level = level
        try:
            self.config.save_to_storage()
        except Exception:
            pass
        self._log_message(f"Performance level set to {level}%", "info")
    
    def sync_network(self, progress_callback=None) -> Dict:
        """Sync with network and refresh P2P peers"""
        try:
            if progress_callback:
                progress_callback(0, "Starting network sync...")
            
            # Refresh peer list from daemon
            if progress_callback:
                progress_callback(25, "Fetching peers from daemon...")
            self._fetch_peers_from_daemon()
            
            # Get current status
            if progress_callback:
                progress_callback(50, "Syncing blockchain status...")
            status = self.get_status()

            if progress_callback:
                progress_callback(65, "Updating blockchain cache...")
            self.sync_blockchain_cache(progress_callback=progress_callback)
            
            # Sync mempool via P2P if available
            if progress_callback:
                progress_callback(75, "Syncing mempool...")
            if self.p2p_client and hasattr(self.p2p_client, 'sync_mempool'):
                try:
                    self.p2p_client.sync_mempool()
                except Exception as e:
                    print(f"[DEBUG] Mempool sync error: {e}")
            
            if progress_callback:
                progress_callback(100, "Sync completed")
            
            peer_count = len(self.peers) if self.peers else 0
            self._log_message(f"Network sync completed - Height: {status['network_height']}, Peers: {peer_count}", "info")
            
            if self.history_updated_callback:
                self.history_updated_callback()
                
            return {'success': True, 'status': status, 'peers': peer_count}
            
        except Exception as e:
            error_msg = f"Sync error: {str(e)}"
            if progress_callback:
                progress_callback(0, error_msg)
            self._log_message(error_msg, "error")
            return {'error': error_msg}

    def _sync_cache_only(self, batch_size: int = 50) -> None:
        """Lightweight cache refresh during mining."""
        try:
            self.sync_blockchain_cache(batch_size=batch_size)
        except Exception:
            pass
        try:
            self._update_bills_cache_from_mined_bills()
        except Exception:
            pass
        try:
            self._recalculate_reward_stats()
        except Exception:
            pass
        try:
            status = self.get_status()
            if isinstance(status, dict):
                status = self._apply_mining_totals_to_status(status)
                self.data_manager.save_stats(status)
        except Exception:
            pass
        if self.history_updated_callback:
            try:
                self.history_updated_callback()
            except Exception:
                pass
    
    def get_mining_history(self) -> List[Dict]:
        """Get mining history"""
        records: List[Dict] = []
        try:
            if self.miner and hasattr(self.miner, "get_mining_history"):
                records.extend(self.miner.get_mining_history())
        except Exception:
            pass
        try:
            if self.miner and isinstance(self.miner.mining_history, list):
                records.extend(self.miner.mining_history)
        except Exception:
            pass
        try:
            if self.gpu_miner and isinstance(self.gpu_miner.mining_history, list):
                records.extend(self.gpu_miner.mining_history)
        except Exception:
            pass
        try:
            cached = self.data_manager.load_mining_history()
            if isinstance(cached, list):
                records.extend(cached)
        except Exception:
            pass

        deduped = {}
        for rec in records:
            if not isinstance(rec, dict):
                continue
            block_index = rec.get("block_index")
            block_hash = rec.get("hash")
            key = (block_index, block_hash)
            existing = deduped.get(key)
            if not existing:
                deduped[key] = rec
                continue
            try:
                if float(rec.get("timestamp", 0)) >= float(existing.get("timestamp", 0)):
                    deduped[key] = rec
            except Exception:
                pass

        merged = list(deduped.values())
        try:
            merged.sort(key=lambda r: float(r.get("timestamp", 0)), reverse=True)
        except Exception:
            pass
        return merged

    def get_mined_rewards(self) -> List[Dict]:
        """Get mined reward transactions from lunalib caches."""
        rewards: List[Dict] = []
        try:
            if self.miner and hasattr(self.miner, "mined_rewards"):
                rewards.extend(getattr(self.miner, "mined_rewards") or [])
        except Exception:
            pass
        try:
            if hasattr(self.data_manager, "load_mined_rewards"):
                cached = self.data_manager.load_mined_rewards()
                if isinstance(cached, list):
                    rewards.extend(cached)
        except Exception:
            pass
        return rewards

    def get_mined_bills(self) -> List[Dict]:
        """Get mined GTX Genesis transactions from lunalib caches."""
        bills: List[Dict] = []
        try:
            if self.miner and hasattr(self.miner, "mined_bills"):
                bills.extend(getattr(self.miner, "mined_bills") or [])
        except Exception:
            pass
        try:
            if hasattr(self.data_manager, "load_mined_bills"):
                cached = self.data_manager.load_mined_bills()
                if isinstance(cached, list):
                    bills.extend(cached)
        except Exception:
            pass
        return bills
    
    def get_logs(self) -> List[Dict]:
        """Get application logs"""
        return self.logs
    
    def submit_block(self, block_data: Dict) -> Tuple[bool, str]:
        """Submit mined block using LunaLib blockchain manager"""
        miner_address = getattr(self.config, "miner_address", "")
        if not is_valid_luna_address(miner_address):
            err = "Invalid miner address. Please set a valid LUN_ address before submitting blocks."
            self._log_message(err, "error")
            return False, err
        if not self._submit_lock.acquire(blocking=False):
            return False, "Submission already in progress"
        try:
            log_cpu_mining_event("submit_block_called", {"block_index": block_data.get('index'), "block_data": block_data})
            log_mining_debug_event(
                "submit_block_called",
                {
                    "block_index": block_data.get("index"),
                    "hash": block_data.get("hash"),
                    "difficulty": block_data.get("difficulty"),
                    "miner": block_data.get("miner"),
                },
                scope="submit",
            )
            self._normalize_block_for_lunalib(block_data)

            # Validate block hash against local fields (avoid submitting mutated/stale data)
            try:
                if hasattr(self.miner, "_calculate_block_hash") and isinstance(block_data, dict):
                    computed_hash = self.miner._calculate_block_hash(
                        block_data.get("index", 0),
                        block_data.get("previous_hash", ""),
                        block_data.get("timestamp", time.time()),
                        block_data.get("transactions", []),
                        block_data.get("nonce", 0),
                        block_data.get("miner", ""),
                        block_data.get("difficulty", self.config.difficulty),
                    )
                    if computed_hash and block_data.get("hash") and str(computed_hash) != str(block_data.get("hash")):
                        err = "Stale block detected (local hash mismatch)"
                        log_mining_debug_event("block_validation_stale", {"computed": computed_hash, "provided": block_data.get("hash")}, scope="validation")
                        self._log_message(err, "info")
                        return False, err
            except Exception:
                pass

            # Early stale-block detection using latest chain tip
            try:
                latest_block = None
                latest_height = None
                if self.blockchain_manager and hasattr(self.blockchain_manager, "get_blockchain_height"):
                    latest_height = self.blockchain_manager.get_blockchain_height()
                if self.blockchain_manager and hasattr(self.blockchain_manager, "get_latest_block"):
                    latest_block = self.blockchain_manager.get_latest_block()

                if latest_height is not None and (not isinstance(latest_block, dict) or str(latest_block.get("index")) != str(latest_height)):
                    for method_name in ("get_block", "get_block_by_index", "get_block_by_height"):
                        method = getattr(self.blockchain_manager, method_name, None)
                        if callable(method):
                            try:
                                latest_block = method(int(latest_height))
                                if isinstance(latest_block, dict):
                                    break
                            except Exception:
                                pass

                if latest_height is None or not isinstance(latest_block, dict):
                    try:
                        import requests
                        node_url = getattr(self.config, "node_url", "https://bank.linglin.art")
                        height_resp = requests.get(f"{node_url}/blockchain/height", timeout=10)
                        if height_resp.ok:
                            height_data = height_resp.json()
                            latest_height = height_data.get("height", latest_height)
                        if latest_height is not None:
                            latest_resp = requests.get(f"{node_url}/blockchain/block/{int(latest_height)}", timeout=10)
                            if latest_resp.ok:
                                latest_data = latest_resp.json()
                                if isinstance(latest_data, dict) and isinstance(latest_data.get("block"), dict):
                                    latest_block = latest_data.get("block")
                                elif isinstance(latest_data, dict):
                                    latest_block = latest_data
                    except Exception:
                        pass

                if latest_height is None and isinstance(latest_block, dict):
                    try:
                        latest_height = int(latest_block.get("index"))
                    except Exception:
                        pass

                if latest_height is not None:
                    expected_index = int(latest_height) + 1
                    current_index = block_data.get("index")
                    if current_index is not None:
                        try:
                            current_index = int(current_index)
                            if current_index != expected_index:
                                err = f"Stale block detected (chain advanced; expected {expected_index}, got {current_index})"
                                log_mining_debug_event("block_validation_stale", {"expected": expected_index, "got": current_index}, scope="validation")
                                self._log_message(err, "info")
                                return False, err
                        except Exception:
                            pass
                if isinstance(latest_block, dict):
                    latest_hash = latest_block.get("hash")
                    if latest_hash and block_data.get("previous_hash") and str(block_data.get("previous_hash")) != str(latest_hash):
                        err = "Stale block detected (chain advanced)"
                        log_mining_debug_event("block_validation_stale", {"expected_hash": latest_hash, "got": block_data.get("previous_hash")}, scope="validation")
                        self._log_message(err, "info")
                        return False, err
                    if latest_hash and not block_data.get("previous_hash"):
                        err = "Stale block detected (missing previous hash)"
                        log_mining_debug_event("block_validation_stale", {"expected_hash": latest_hash, "got": None}, scope="validation")
                        self._log_message(err, "info")
                        return False, err
            except Exception:
                pass

            # Pre-validate with LunaLib's internal validator for clearer errors
            try:
                validation = self.blockchain_manager._validate_block_structure(block_data)
                log_mining_debug_event(
                    "block_validation_checked",
                    {"valid": bool(validation.get("valid", False)), "issues": validation.get("issues", [])},
                    scope="validation",
                )
                if not validation.get("valid", False):
                    issues = validation.get("issues", [])
                    issues_text = " ".join([str(i) for i in issues])
                    if "Previous hash mismatch" in issues_text:
                        err = "Stale block detected (chain advanced)"
                        log_cpu_mining_event("block_validation_stale", {"error": issues, "block_index": block_data.get('index')})
                        log_mining_debug_event("block_validation_stale", {"issues": issues}, scope="validation")
                        self._log_message(err, "info")
                        return False, err
                    err = f"Block validation failed: {issues}"
                    log_cpu_mining_event("block_validation_failed", {"error": issues, "block_index": block_data.get('index')})
                    log_mining_debug_event("block_validation_failed", {"issues": issues}, scope="validation")
                    self._log_message(err, "error")
                    return False, err
            except Exception:
                pass

            # Avoid re-submitting the exact same block repeatedly
            try:
                now_ts = time.time()
                current_hash = block_data.get("hash")
                current_index = block_data.get("index")
                if current_hash and current_hash == self._last_submitted_hash:
                    if (now_ts - self._last_submitted_ts) < 60 and self._last_submitted_success:
                        msg = f"Duplicate block submission suppressed (index {current_index})"
                        log_cpu_mining_event("block_submit_duplicate_suppressed", {
                            "block_index": current_index,
                            "hash": current_hash,
                        })
                        self._log_message(msg, "warning")
                        return True, msg
            except Exception:
                pass
            
            # Submit using LunaLib BlockchainManager if available (preferred)
            submit_ok, submit_msg = False, ""
            if self.blockchain_manager and hasattr(self.blockchain_manager, "submit_block"):
                try:
                    result = self.blockchain_manager.submit_block(block_data)
                    if isinstance(result, dict):
                        submit_ok = bool(result.get("success", False))
                        submit_msg = result.get("message") or result.get("error") or "Block submitted"
                    elif isinstance(result, tuple) and len(result) >= 2:
                        submit_ok = bool(result[0])
                        submit_msg = str(result[1])
                    else:
                        submit_ok = bool(result)
                        submit_msg = "Block submitted" if submit_ok else "Submission failed"
                    log_mining_debug_event(
                        "submit_block_result",
                        {"ok": submit_ok, "message": submit_msg},
                        scope="submit",
                    )
                except Exception as e:
                    submit_ok = False
                    submit_msg = f"LunaLib submit failed: {e}"
                    log_mining_debug_event(
                        "submit_block_exception",
                        {"error": str(e)},
                        scope="submit",
                    )

            # Fallback: Submit plain JSON (server rejects gzip payloads)
            if not submit_ok:
                submit_ok, submit_msg = self._submit_block_plain_json(block_data)
            if submit_ok:
                self._last_submitted_hash = block_data.get("hash")
                self._last_submitted_index = block_data.get("index")
                self._last_submitted_ts = time.time()
                self._last_submitted_success = True
                self._post_submit_refresh(block_data)
                # --- ここで本当にチェーンに載ったか即時確認 ---
                try:
                    latest_block = self.blockchain_manager.get_latest_block()
                    # index, hash, miner で自分のブロックか判定
                    if latest_block and str(latest_block.get("hash")) == str(block_data.get("hash")) and str(latest_block.get("miner")) == str(self.config.miner_address):
                        log_mining_debug_event("block_confirmed", {"method": "latest_hash"}, scope="submit")
                        return True, submit_msg + " (confirmed on chain)"
                    # 直近でindex一致かつminer一致も許容（P2P遅延対策）
                    if latest_block and str(latest_block.get("index")) == str(block_data.get("index")) and str(latest_block.get("miner")) == str(self.config.miner_address):
                        log_mining_debug_event("block_confirmed", {"method": "latest_index"}, scope="submit")
                        return True, submit_msg + " (confirmed by index/miner)"
                    # /get_block/{id} で確認
                    confirmed = self._confirm_block_by_id(block_data)
                    if confirmed:
                        log_mining_debug_event("block_confirmed", {"method": "get_block"}, scope="submit")
                        return True, submit_msg + " (confirmed by get_block)"
                    # 反映されていない場合は確認待ちとして成功扱い
                    warn_msg = submit_msg + " (confirmation pending)"
                    self._log_message(warn_msg, "warning")
                    log_mining_debug_event("block_confirmation_pending", {}, scope="submit")
                    return True, warn_msg
                except Exception as e:
                    err_msg = submit_msg + f" (confirmation error: {e})"
                    self._log_message(err_msg, "error")
                    log_mining_debug_event("block_confirmation_error", {"error": str(e)}, scope="submit")
                    return True, err_msg
            return False, submit_msg

            log_cpu_mining_event("block_submit_failed", {"block_index": block_data.get('index')})
            self._log_message(f"Block #{block_data['index']} submission failed", "warning")
            self._save_block_locally(block_data)
            return False, "Submission failed"
        except Exception as e:
            error_msg = f"Block submission error: {str(e)}"
            log_cpu_mining_event("block_submit_exception", {"block_index": block_data.get('index'), "error": str(e)})
            self._log_message(error_msg, "error")
            self._save_block_locally(block_data)
            return False, error_msg
        finally:
            try:
                self._submit_lock.release()
            except Exception:
                pass

    def _normalize_block_for_lunalib(self, block_data: Dict) -> None:
        """Ensure block structure matches LunaLib validator expectations."""
        if not isinstance(block_data, dict):
            return

        # Basic field normalization
        if "index" in block_data and block_data.get("index") not in (None, ""):
            try:
                block_data["index"] = int(block_data.get("index"))
            except Exception:
                pass
        else:
            try:
                latest = self.blockchain_manager.get_latest_block()
                latest_index = int(latest.get("index", 0)) if latest else 0
                block_data["index"] = latest_index + 1
            except Exception:
                block_data["index"] = 0
        if "difficulty" in block_data:
            try:
                block_data["difficulty"] = int(block_data.get("difficulty"))
            except Exception:
                pass
        if "nonce" in block_data:
            try:
                block_data["nonce"] = int(block_data.get("nonce"))
            except Exception:
                pass
        else:
            block_data["nonce"] = 0
        if "timestamp" in block_data:
            try:
                block_data["timestamp"] = float(block_data.get("timestamp"))
            except Exception:
                pass
        else:
            block_data["timestamp"] = time.time()

        if not block_data.get("miner"):
            block_data["miner"] = self.config.miner_address

    def _confirm_block_by_id(self, block_data: Dict) -> bool:
        """Confirm block on chain via /get_block/{id}."""
        try:
            import requests
        except Exception:
            return False

        try:
            node_url = getattr(self.config, "node_url", "https://bank.linglin.art")
            block_id = block_data.get("index")
            if block_id is None:
                return False
            url = f"{node_url}/get_block/{block_id}"
            resp = requests.get(url, timeout=10)
            if not resp.ok:
                return False
            data = resp.json()
            block = data.get("block") if isinstance(data, dict) else data
            if not isinstance(block, dict):
                return False
            if str(block.get("hash")) == str(block_data.get("hash")) and str(block.get("miner")) == str(self.config.miner_address):
                try:
                    self.data_manager.save_submitted_block(block)
                except Exception:
                    pass
                return True
        except Exception:
            return False
        return False

    def _post_submit_refresh(self, block_data: Dict) -> None:
        """Update caches and UI after a successful submit."""
        try:
            self._last_mined_ts = time.time()
        except Exception:
            pass
        try:
            self.data_manager.save_submitted_block(block_data)
        except Exception:
            pass
        try:
            self._update_bills_cache_from_block(block_data)
        except Exception:
            pass
        try:
            self._update_bills_cache_from_mined_bills()
        except Exception:
            pass
        # Ensure mining history reflects the submitted block so stats update immediately
        try:
            history = self.get_mining_history()
        except Exception:
            history = []
        try:
            if not isinstance(history, list):
                history = []
            block_index = block_data.get("index") if isinstance(block_data, dict) else None
            block_hash = block_data.get("hash") if isinstance(block_data, dict) else None
            already_exists = False
            for record in history:
                if not isinstance(record, dict):
                    continue
                if record.get("status") != "success":
                    continue
                if block_hash and record.get("hash") == block_hash:
                    already_exists = True
                    break
                if block_index is not None and record.get("block_index") == block_index:
                    already_exists = True
                    break
            if not already_exists:
                reward = block_data.get("reward") if isinstance(block_data, dict) else None
                is_empty_block = bool(block_data.get("is_empty_block")) if isinstance(block_data, dict) else False
                if reward is None:
                    try:
                        reward, is_empty_block = self._calculate_expected_block_reward(block_data if isinstance(block_data, dict) else {})
                        if isinstance(block_data, dict):
                            block_data["reward"] = reward
                            block_data["is_empty_block"] = is_empty_block
                    except Exception:
                        reward = 0.0
                method = "submit"
                try:
                    if self.gpu_miner and (getattr(self.gpu_miner, "is_mining", False) or getattr(self.gpu_miner, "mining_active", False)):
                        method = "cuda"
                    elif self.miner and (getattr(self.miner, "is_mining", False) or getattr(self.miner, "mining_active", False)):
                        method = "cpu"
                except Exception:
                    pass
                record = {
                    "timestamp": time.time(),
                    "status": "success",
                    "block_index": block_index,
                    "hash": block_hash,
                    "nonce": block_data.get("nonce", 0) if isinstance(block_data, dict) else 0,
                    "difficulty": block_data.get("difficulty", self.config.difficulty) if isinstance(block_data, dict) else self.config.difficulty,
                    "mining_time": block_data.get("mining_time", 0) if isinstance(block_data, dict) else 0,
                    "transactions": block_data.get("transactions", []) if isinstance(block_data, dict) else [],
                    "reward": reward,
                    "method": method,
                    "is_empty_block": is_empty_block,
                }
                history.append(record)
                try:
                    if self.miner and isinstance(getattr(self.miner, "mining_history", None), list):
                        self.miner.mining_history.append(record)
                except Exception:
                    pass
                try:
                    if self.gpu_miner and isinstance(getattr(self.gpu_miner, "mining_history", None), list):
                        self.gpu_miner.mining_history.append(record)
                except Exception:
                    pass
                try:
                    self.data_manager.save_mining_history(history)
                except Exception:
                    pass
        except Exception:
            pass
        try:
            self._recalculate_reward_stats()
        except Exception:
            pass
        try:
            status = self.get_status()
            if isinstance(status, dict):
                self.data_manager.save_stats(status)
        except Exception:
            pass
        if self.history_updated_callback:
            try:
                self.history_updated_callback()
            except Exception:
                pass
        try:
            if hasattr(self, "main_page") and hasattr(self.main_page, "update_mining_stats"):
                self.main_page.update_mining_stats()
            if hasattr(self, "sidebar") and hasattr(self.sidebar, "update_status"):
                self.sidebar.update_status(self.get_status())
        except Exception:
            pass

        # Ensure previous_hash is set
        if not block_data.get("previous_hash"):
            try:
                latest = self.blockchain_manager.get_latest_block()
                if latest and latest.get("hash"):
                    block_data["previous_hash"] = latest.get("hash")
            except Exception:
                pass

        if "version" not in block_data:
            block_data["version"] = "1.0"

        if not isinstance(block_data.get("transactions"), list):
            block_data["transactions"] = []

        # Ensure a reward transaction has required fields
        reward_tx = None
        for tx in block_data.get("transactions", []):
            if isinstance(tx, dict) and (tx.get("type") == "reward" or tx.get("type") == "mining_reward"):
                reward_tx = tx
                break
        if reward_tx:
            reward_tx.setdefault("from", "network")
            reward_tx.setdefault("to", self.config.miner_address)
            reward_tx.setdefault("amount", float(block_data.get("reward", 0) or 0))
            reward_tx.setdefault("timestamp", block_data.get("timestamp", time.time()))
            reward_tx.setdefault("hash", f"reward_{block_data.get('index', 0)}_{int(block_data.get('timestamp', time.time()))}")
        elif block_data.get("reward") is not None:
            block_data["transactions"].append({
                "type": "reward",
                "from": "network",
                "to": self.config.miner_address,
                "amount": float(block_data.get("reward", 0) or 0),
                "timestamp": block_data.get("timestamp", time.time()),
                "hash": f"reward_{block_data.get('index', 0)}_{int(block_data.get('timestamp', time.time()))}",
            })

        # Normalize required fields for all transactions
        for tx in block_data.get("transactions", []):
            if not isinstance(tx, dict):
                continue
            tx_type = str(tx.get("type", "")).lower()
            if "from" not in tx or tx.get("from") in (None, ""):
                tx["from"] = "network" if tx_type in ("reward", "mining_reward") else "unknown"
            if "to" not in tx or tx.get("to") in (None, ""):
                tx["to"] = self.config.miner_address if tx_type in ("reward", "mining_reward") else "unknown"
            if "timestamp" not in tx or tx.get("timestamp") in (None, ""):
                tx["timestamp"] = block_data.get("timestamp", time.time())
            if "amount" not in tx or tx.get("amount") in (None, ""):
                tx["amount"] = float(0)

        # Recalculate hash if missing/invalid or difficulty mismatch
        try:
            difficulty = int(block_data.get("difficulty") or 0)
            block_hash = block_data.get("hash", "")
            if (len(block_hash) != 64) or (difficulty > 0 and not block_hash.startswith("0" * difficulty)):
                if hasattr(self.miner, "_calculate_block_hash"):
                    block_data["hash"] = self.miner._calculate_block_hash(
                        block_data.get("index", 0),
                        block_data.get("previous_hash", "0" * 64),
                        block_data.get("timestamp", time.time()),
                        block_data.get("transactions", []),
                        block_data.get("nonce", 0),
                        block_data.get("miner", ""),
                        difficulty,
                    )
        except Exception:
            pass

    def _submit_block_plain_json(self, block_data: Dict) -> Tuple[bool, str]:
        """Fallback submission using plain JSON (no gzip)."""
        try:
            endpoint = f"{self.config.node_url}/blockchain/submit-block"
            log_mining_debug_event(
                "plain_submit_request",
                {"endpoint": endpoint, "block_index": block_data.get("index"), "hash": block_data.get("hash")},
                scope="submit",
            )
            response = requests.post(
                endpoint,
                json=block_data,
                headers={"Content-Type": "application/json", "Accept-Encoding": "identity"},
                timeout=30,
            )
            if response.status_code in (200, 201):
                try:
                    data = response.json()
                except Exception:
                    data = {}
                message = data.get("message", "Block submitted")
                skipped = bool(data.get("skipped"))
                already_exists = "already exists" in (message or "").lower()
                log_mining_debug_event(
                    "plain_submit_response",
                    {
                        "status": response.status_code,
                        "message": message,
                        "skipped": skipped,
                        "already_exists": already_exists,
                    },
                    scope="submit",
                )
                if skipped or already_exists:
                    warn_msg = f"Block #{block_data.get('index')} already exists on chain"
                    try:
                        history = self.get_mining_history()
                        record = {
                            "timestamp": time.time(),
                            "status": "success",
                            "block_index": block_data.get("index"),
                            "hash": block_data.get("hash"),
                            "nonce": block_data.get("nonce", 0),
                            "difficulty": block_data.get("difficulty", self.config.difficulty),
                            "mining_time": block_data.get("mining_time", 0),
                            "transactions": block_data.get("transactions", []),
                            "reward": block_data.get("reward", 0),
                            "method": "cuda" if self.config.use_gpu else "cpu",
                        }
                        history.append(record)
                        self.data_manager.save_mining_history(history)
                        self._recalculate_reward_stats()
                    except Exception:
                        pass
                    self._log_message(warn_msg, "warning")
                    return True, warn_msg
                self._log_message(f"Block #{block_data.get('index')} submitted", "success")
                return True, message
            try:
                error_text = response.text
            except Exception:
                error_text = ""
            log_mining_debug_event(
                "plain_submit_failed",
                {"status": response.status_code, "error": error_text},
                scope="submit",
            )
            if error_text:
                return False, f"HTTP {response.status_code}: {error_text}"
            return False, f"HTTP {response.status_code}"
        except Exception as e:
            log_mining_debug_event("plain_submit_exception", {"error": str(e)}, scope="submit")
            return False, f"Plain submit failed: {e}"
    
    def _save_block_locally(self, block_data: Dict) -> bool:
        """Save block locally when network submission fails"""
        try:
            blocks_dir = "./data/blocks"
            if not os.path.exists(blocks_dir):
                os.makedirs(blocks_dir)
            
            block_file = os.path.join(blocks_dir, f"block_{block_data['index']}_{int(time.time())}.json")
            with open(block_file, 'w') as f:
                json.dump(block_data, f, indent=2, default=str)
            
            self._log_message(f"Block saved locally: {block_file}", "info")
            return True
        except Exception as e:
            self._log_message(f"Failed to save block locally: {str(e)}", "error")
            return False

    def _update_bills_cache_from_block(self, block_data: Dict) -> None:
        """Update bills cache with a newly mined block."""
        if not isinstance(block_data, dict):
            return
        block_index = block_data.get("index")
        transactions = block_data.get("transactions", [])
        if block_index is None:
            return
        cache_file = os.path.join(self.data_manager.data_dir, "bills_cache.json")
        try:
            if os.path.exists(cache_file):
                with open(cache_file, "r", encoding="utf-8") as f:
                    cache = json.load(f)
            else:
                cache = {}
        except Exception:
            cache = {}

        mined_blocks = set(cache.get("mined_blocks", []))
        thumbnails = cache.get("thumbnails", {})
        banknotes = cache.get("banknotes", {})
        thumbnail_urls = cache.get("thumbnail_urls", {})

        mined_blocks.add(block_index)
        block_gtx_hashes = []
        for tx in transactions:
            if isinstance(tx, dict) and tx.get("type") == "GTX_Genesis" and tx.get("hash"):
                tx_hash = tx.get("hash")
                block_gtx_hashes.append(tx_hash)
                banknotes[tx_hash] = tx
                serial_id = tx.get("serial_id") or tx.get("serial_number")
                img_url_front = f"https://bank.linglin.art/transaction-thumbnail/{tx_hash}?side=front&scale=2"
                if serial_id:
                    img_url_back = f"https://bank.linglin.art/banknote-matching-thumbnail/{serial_id}?side=match&scale=2"
                else:
                    img_url_back = f"https://bank.linglin.art/transaction-thumbnail/{tx_hash}?side=back&scale=2"
                thumbnail_urls[tx_hash] = {
                    "front": f"{img_url_front}&flip=front",
                    "back": f"{img_url_back}&flip=back",
                }

        if block_gtx_hashes:
            existing = thumbnails.get(str(block_index), []) or []
            thumbnails[str(block_index)] = list({*existing, *block_gtx_hashes})

        cache["mined_blocks"] = list(mined_blocks)
        cache["thumbnails"] = thumbnails
        cache["banknotes"] = banknotes
        cache["thumbnail_urls"] = thumbnail_urls

        try:
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(cache, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def _update_bills_cache_from_mined_bills(self) -> None:
        """Update bills cache from lunalib mined_bills list."""
        try:
            mined_bills = self.get_mined_bills()
        except Exception:
            mined_bills = []
        if not mined_bills:
            return

        cache_file = os.path.join(self.data_manager.data_dir, "bills_cache.json")
        try:
            if os.path.exists(cache_file):
                with open(cache_file, "r", encoding="utf-8") as f:
                    cache = json.load(f)
            else:
                cache = {}
        except Exception:
            cache = {}

        mined_blocks = set(cache.get("mined_blocks", []))
        thumbnails = cache.get("thumbnails", {})
        banknotes = cache.get("banknotes", {})
        thumbnail_urls = cache.get("thumbnail_urls", {})

        for tx in mined_bills:
            if not isinstance(tx, dict):
                continue
            tx_hash = tx.get("hash")
            if not tx_hash:
                continue
            banknotes[tx_hash] = tx
            block_index = tx.get("block_height") or tx.get("block_index")
            if block_index is None:
                block_key = "pending"
            else:
                block_key = str(block_index)
                try:
                    mined_blocks.add(int(block_index))
                except Exception:
                    pass
            serial_id = tx.get("serial_id") or tx.get("serial_number")
            img_url_front = f"https://bank.linglin.art/transaction-thumbnail/{tx_hash}?side=front&scale=2"
            if serial_id:
                img_url_back = f"https://bank.linglin.art/banknote-matching-thumbnail/{serial_id}?side=match&scale=2"
            else:
                img_url_back = f"https://bank.linglin.art/transaction-thumbnail/{tx_hash}?side=back&scale=2"
            thumbnail_urls[tx_hash] = {
                "front": f"{img_url_front}&flip=front",
                "back": f"{img_url_back}&flip=back",
            }
            existing = thumbnails.get(block_key, []) or []
            if tx_hash not in existing:
                thumbnails[block_key] = list({*existing, tx_hash})

        cache["mined_blocks"] = list(mined_blocks)
        cache["thumbnails"] = thumbnails
        cache["banknotes"] = banknotes
        cache["thumbnail_urls"] = thumbnail_urls

        try:
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(cache, f, ensure_ascii=False, indent=2)
        except Exception:
            pass
    
    def update_wallet_address(self, new_address: str):
        """Update miner wallet address"""
        self.config.miner_address = new_address
        self.config.save_to_storage()
        self._log_message(f"Wallet address updated to: {new_address}", "info")
    
    def update_difficulty(self, new_difficulty: int):
        """Update mining difficulty"""
        self.config.difficulty = new_difficulty
        self.config.save_to_storage()
        
        # Also update the miner's config reference
        if self.miner and hasattr(self.miner, 'config'):
            self.miner.config.difficulty = new_difficulty
        
        self._log_message(f"Mining difficulty set to: {new_difficulty}", "info")
    
    def update_node_url(self, new_url: str):
        """Update node URL and reinitialize miner/P2P client"""
        self.config.node_url = new_url
        self.config.save_to_storage()
        
        # Stop existing P2P client
        if self.p2p_client:
            try:
                self.p2p_client.stop()
            except Exception as e:
                print(f"[DEBUG] Error stopping P2P client: {e}")
        
        # Reinitialize managers with new URL (use LunaLib managers)
        self.blockchain_manager = BlockchainManager(endpoint_url=new_url)
        self.mempool_manager = MempoolManager([new_url])
        if TransactionManager:
            try:
                self.tx_manager = TransactionManager([new_url])
            except Exception:
                self.tx_manager = None
        
        # Reinitialize miner and link managers
        self.miner = LunaLibMiner(self.config, self.data_manager)
        self.miner.blockchain_manager = self.blockchain_manager
        self.miner.mempool_manager = self.mempool_manager
        if hasattr(self.miner, 'auto_submit'):
            self.miner.auto_submit = False
        
        # Reinitialize P2P with LunaLib client
        self._init_p2p_client()
        self._log_message(f"Node URL updated to: {new_url}", "info")
    
    def update_mining_interval(self, new_interval: int):
        """Update mining interval"""
        self.config.mining_interval = new_interval
        self.config.save_to_storage()
        self._log_message(f"Mining interval updated to: {new_interval} seconds", "info")
    
    def toggle_gpu_acceleration(self, enabled: bool):
        """Toggle GPU/CUDA acceleration for mining (lunalib 2.4.0仕様)"""
        self.config.use_gpu = enabled
        self.config.enable_gpu_mining = bool(enabled)
        self.config.save_to_storage()
        if self.miner:
            self.miner.use_cuda = bool(enabled)
            if hasattr(self.miner, "use_cpu"):
                self.miner.use_cpu = not bool(enabled)
        self._log_message(f"GPU acceleration {'enabled' if enabled else 'disabled'} (lunalib 2.4.0)", "info")
    
    def toggle_auto_mining(self, enabled: bool):
        """Toggle auto-mining"""
        self.config.auto_mine = enabled
        self.config.save_to_storage()
        if enabled:
            self.start_auto_mining()
            self._log_message("Auto-mining enabled", "info")
        else:
            self.stop_auto_mining()
            self._log_message("Auto-mining disabled", "info")
    
    def cleanup(self):
        """Cleanup resources"""
        self.is_running = False
        self.stop_auto_mining()
        try:
            self._sync_stop_event.set()
            if self._sync_thread and self._sync_thread.is_alive():
                self._sync_thread.join(timeout=2)
        except Exception:
            pass
        
        # Stop P2P client
        if self.p2p_client:
            try:
                self.p2p_client.stop()
                self._log_message("P2P client stopped", "info")
            except Exception as e:
                print(f"[DEBUG] Error stopping P2P client: {e}")

    def _resolve_p2p_connected(self) -> bool:
        """Best-effort P2P connection state across lunalib versions."""
        if not self.p2p_client:
            return False
        peer_list = getattr(self, 'peers', None)
        if isinstance(peer_list, list) and len(peer_list) > 0:
            return True
        for obj in (self.p2p_client, getattr(self.p2p_client, 'p2p', None)):
            if not obj:
                continue
            for attr in ("is_connected", "connected", "is_running", "running", "started"):
                if hasattr(obj, attr):
                    try:
                        value = getattr(obj, attr)
                        return bool(value() if callable(value) else value)
                    except Exception:
                        continue
        return False
    
    def get_p2p_status(self) -> Dict:
        """Get P2P network status (real if P2P enabled)"""
        if self.p2p_client:
            connected = self._resolve_p2p_connected()
            peer_list = getattr(self, 'peers', [])
            return {
                'connected': connected,
                'peers': len(peer_list),
                'peer_list': peer_list,
                'status': 'p2p enabled' if connected else 'p2p offline'
            }
        return {
            'connected': False,
            'peers': 0,
            'peer_list': [],
            'status': 'p2p disabled'
        }
    
    def _fetch_peers_from_daemon(self):
        """P2P peer fetching disabled (use LunaLib P2P if needed)."""
        return False

    def _start_sync_loop(self):
        """Background sync loop to keep blockchain cache and UI up to date."""
        if self._sync_thread and self._sync_thread.is_alive():
            return

        interval = float(os.getenv("LUNANODE_SYNC_INTERVAL", "60"))
        if interval < 10:
            interval = 10
        startup_delay = float(os.getenv("LUNANODE_STARTUP_SYNC_DELAY", "0"))
        if startup_delay < 0:
            startup_delay = 0

        def _sync_loop():
            if startup_delay > 0:
                if self._sync_stop_event.wait(startup_delay):
                    return
            while self.is_running and not self._sync_stop_event.is_set():
                try:
                    if getattr(self.miner, "is_mining", False):
                        self._sync_cache_only()
                    else:
                        self.sync_network()
                except Exception:
                    pass
                if self._sync_stop_event.wait(interval):
                    break

        self._sync_thread = threading.Thread(target=_sync_loop, daemon=True)
        self._sync_thread.start()
        
    def register_peer(self, peer_url: str) -> bool:
        """
        Register this node as a peer with the daemon.
        Args:
            peer_url: Your public peer URL (e.g., 'https://mynode.example.com:8545')
                If not provided, registration will be skipped.
        Returns:
            True if registration succeeded, False otherwise.
        """
        self._log_message("Peer registration disabled (non-lunalib operation)", "warning")
        return False