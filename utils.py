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

try:
    from gmssl import sm3, func
    SM3_AVAILABLE = True
except Exception:
    sm3 = None
    func = None
    SM3_AVAILABLE = False

LUNALIB_SM3_FUNC = None

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

def sanitize_for_console(message: str) -> str:
    if not isinstance(message, str):
        message = str(message)
    encoding = getattr(sys.stdout, "encoding", None) or "utf-8"
    return message.encode(encoding, errors="replace").decode(encoding, errors="replace")

def safe_print(*args, **kwargs):
    try:
        print(*args, **kwargs)
    except Exception:
        pass

def compute_sm3_hexdigest(data: bytes) -> str:
    if LUNALIB_SM3_FUNC:
        try:
            result = LUNALIB_SM3_FUNC(data)
            if isinstance(result, bytes):
                return result.hex()
            if isinstance(result, str):
                return result
        except Exception:
            pass
    raise RuntimeError("LunaLib SM3 is not available")

def _normalize_hash_algo(value: str) -> str:
    if not isinstance(value, str):
        return ""
    return "".join(ch for ch in value.lower() if ch.isalnum())

# Import lunalib components (2.0.2 compatible with fallbacks)
try:
    import lunalib
    LUNALIB_VERSION = getattr(lunalib, "__version__", "unknown")

    from lunalib.core.blockchain import BlockchainManager
    from lunalib.core.mempool import MempoolManager

    try:
        from lunalib.core.p2p import HybridBlockchainClient
        P2P_AVAILABLE = True
    except Exception:
        HybridBlockchainClient = None
        P2P_AVAILABLE = False

    from lunalib.mining.difficulty import DifficultySystem
    from lunalib.mining.cuda_manager import CUDAManager

    LUNALIB_SM3_FUNC = None
    try:
        from lunalib.utils.hash import sm3_hex as _sm3_hex
        LUNALIB_SM3_FUNC = _sm3_hex
    except Exception:
        try:
            from lunalib.core.sm3 import sm3_hex as _sm3_hex
            LUNALIB_SM3_FUNC = _sm3_hex
        except Exception:
            LUNALIB_SM3_FUNC = None
    LUNALIB_SM3_BATCH = None
    try:
        from lunalib.core.sm3 import sm3_batch as _sm3_batch
        LUNALIB_SM3_BATCH = _sm3_batch
    except Exception:
        LUNALIB_SM3_BATCH = None

    try:
        from lunalib.mining.miner import Miner as LunaLibMiner
    except Exception:
        LunaLibMiner = None

    try:
        from lunalib.mining.miner import GenesisMiner as LunaLibGenesisMiner
    except Exception:
        LunaLibGenesisMiner = None

    try:
        from lunalib.transactions.transactions import TransactionManager
    except Exception:
        TransactionManager = None

    LUNA_LIB_AVAILABLE = True
except ImportError as e:
    print(f"LunaLib import error: {e}")
    LUNALIB_VERSION = "not-installed"
    LUNA_LIB_AVAILABLE = False
    P2P_AVAILABLE = False
    BlockchainManager = None
    MempoolManager = None
    HybridBlockchainClient = None
    DifficultySystem = None
    CUDAManager = None
    LunaLibMiner = None
    LunaLibGenesisMiner = None
    TransactionManager = None
    LUNALIB_SM3_FUNC = None
    LUNALIB_SM3_BATCH = None

def log_cpu_mining_event(event: str, data: dict = None):
    """追跡用: CPUマイニングの詳細イベントをlogs/cpu_mining.logへ追記"""
    import os
    import json
    from datetime import datetime
    log_dir = os.path.join(get_app_data_dir(), "logs")
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, "cpu_mining.log")
    entry = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "event": event,
        "data": data or {}
    }
    try:
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception as e:
        print(f"[LOGGING ERROR] Could not write cpu_mining.log: {e}")

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
            'cuda_batch_size': 100000
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
            'cuda_batch_size': self.cuda_batch_size
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

        # Prevent repeated submissions of the same block
        self._last_submitted_hash = None
        self._last_submitted_index = None
        self._last_submitted_ts = 0.0
        self._last_submitted_success = False
        
        self.is_running = True
        self._stop_mining_event = threading.Event()

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
        self.blockchain_manager = BlockchainManager(endpoint_url=self.config.node_url)
        self.mempool_manager = MempoolManager([self.config.node_url])

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
        
        # Initialize LunaLib Miner (uses config, data_manager signature)
        self.miner = LunaLibMiner(self.config, self.data_manager) if LunaLibMiner else None

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

        # Override CUDA batch size if configured
        try:
            if hasattr(self.miner, "_cuda_mine") and self.miner.cuda_manager:
                original_cuda_mine = self.miner._cuda_mine

                def _cuda_mine_with_batch(block_data: Dict, difficulty: int):
                    batch_size = int(getattr(self.config, "cuda_batch_size", 100000) or 100000)
                    if batch_size < 1000:
                        batch_size = 1000
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
        try:
            cached_history = self.data_manager.load_mining_history()
            if isinstance(cached_history, list) and cached_history:
                self.miner.mining_history = cached_history
            self._recalculate_reward_stats()
        except Exception:
            pass
        
        # Link managers to miner
        self.miner.blockchain_manager = self.blockchain_manager
        self.miner.mempool_manager = self.mempool_manager
        
        # Disable auto-submission so we can handle it ourselves
        if hasattr(self.miner, 'auto_submit'):
            self.miner.auto_submit = False
        
        # Initialize HybridBlockchainClient for P2P networking (disabled in non-lunalib mode)
        self.p2p_client = None
        
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
        
        # Debugging DataManager and NodeConfig initialization
        print("[DEBUG] DataManager initialized:", self.data_manager)
        print("[DEBUG] NodeConfig initialized:", self.config)

        # Use LunaLib CPU mining implementation without overrides

    def _apply_hash_algorithm(self):
        algo = str(self.hash_algorithm or "sha256").lower().strip()
        normalized_algo = _normalize_hash_algo(algo)
        if normalized_algo not in ("sha256", "sm3"):
            algo = "sha256"
        elif normalized_algo == "sm3":
            algo = "sm3"
        else:
            algo = "sha256"

        if algo == "sm3" and not LUNALIB_SM3_FUNC:
            self._log_message("SM3 selected but LunaLib SM3 is unavailable; mining will be blocked", "error")

        self.hash_algorithm = algo

        def _calculate_block_hash(index: int, previous_hash: str, timestamp: float,
                                  transactions: List[Dict], nonce: int, miner: str, difficulty: int) -> str:
            try:
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
                if algo == "sm3" and LUNALIB_SM3_BATCH:
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
        if self.hash_algorithm == "sm3" and not LUNALIB_SM3_FUNC:
            self._log_message("SM3 is required but LunaLib SM3 is unavailable. Please update LunaLib.", "error")
            return False
        return True
            
    def _on_block_mined(self, block_data: Dict):
        """Handle newly mined block"""
        try:
            success, message = self.submit_block(block_data)
            if success:
                self.stats['successful_blocks'] += 1
                
                reward_tx = self._create_reward_transaction(block_data)
                
                if self.new_reward_callback:
                    self.new_reward_callback(reward_tx)
                
                if self.new_bill_callback:
                    self.new_bill_callback(block_data)
                
                if self.history_updated_callback:
                    self.history_updated_callback()
                    
            else:
                self._log_message(f"Block #{block_data['index']} rejected: {message}", "warning")
                self.stats['failed_attempts'] += 1
                
        except Exception as e:
            self._log_message(f"Error processing mined block: {str(e)}", "error")
            self.stats['failed_attempts'] += 1
    
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
            history = getattr(self.miner, "mining_history", []) or []
            success_records = [r for r in history if isinstance(r, dict) and r.get("status") == "success"]
            blocks_mined = len(success_records)
            total_reward = 0.0
            for record in success_records:
                reward = record.get("reward")
                if reward is None:
                    reward = 50.0
                try:
                    total_reward += float(reward)
                except Exception:
                    pass
            self.miner.blocks_mined = blocks_mined
            self.miner.total_reward = total_reward
        except Exception:
            pass

    def _default_status(self) -> Dict:
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
            'cuda_available': False,
            'mining_method': 'CPU'
        }

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
        """Get node status"""
        try:
            if self._prefer_cached_stats and not self.miner.is_mining:
                cached = self._cached_status or self.data_manager.load_stats()
                if isinstance(cached, dict) and cached:
                    cached['hash_algorithm'] = self.hash_algorithm
                    return self._merge_status(cached)
            now = time.time()
            if now - self._net_cache_ts >= self.net_poll_interval:
                current_height = self.blockchain_manager.get_blockchain_height()
                latest_block = self.blockchain_manager.get_latest_block() if current_height > 0 else None
                if not latest_block and current_height > 0:
                    latest_block = self.blockchain_manager.get_block(current_height)
                try:
                    mempool = self.mempool_manager.get_pending_transactions() if self.mempool_manager else []
                except Exception:
                    mempool = self.blockchain_manager.get_mempool() if self.blockchain_manager else []

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
            
            total_mining_time = sum(record.get('mining_time', 0) for record in self.miner.mining_history)
            avg_mining_time = total_mining_time / len(self.miner.mining_history) if self.miner.mining_history else 0
            
            # Check CUDA status
            cuda_available = self.miner.cuda_manager.cuda_available if self.miner.cuda_manager else False
            using_cuda = cuda_available and self.config.use_gpu
            
            # Get hashrate - use CUDA stats if GPU mining
            if using_cuda and self.stats.get('cuda_hash_rate', 0) > 0:
                current_hash_rate = self.stats['cuda_hash_rate']
                current_hash = self.stats.get('cuda_last_hash', '')
                current_nonce = self.stats.get('cuda_last_nonce', 0)
            else:
                # Miner.get_mining_stats()のhash_rateを直接参照
                mining_stats = self.miner.get_mining_stats() if hasattr(self.miner, 'get_mining_stats') else {}
                current_hash_rate = mining_stats.get('hash_rate', 0)
                current_hash = mining_stats.get('current_hash', '')
                current_nonce = mining_stats.get('current_nonce', 0)
                if not current_hash_rate:
                    current_hash_rate = getattr(self.miner, 'last_cpu_hashrate', 0) or getattr(self.miner, 'hash_rate', 0) or self.stats.get('cpu_hash_rate', 0)
            
            # Get P2P status
            p2p_status = self.get_p2p_status()
            
            status = {
                'network_height': current_height,
                'network_difficulty': latest_block.get('difficulty', 1) if latest_block else 1,
                'mining_difficulty': self.config.difficulty,
                'previous_hash': latest_block.get('hash', '0' * 64) if latest_block else '0' * 64,
                'miner_address': self.config.miner_address,
                'blocks_mined': self.miner.blocks_mined,
                'auto_mining': self.miner.is_mining,
                'configured_difficulty': self.config.difficulty,
                'total_reward': self.miner.total_reward,
                'total_transactions': len(mempool),
                'reward_transactions': self.miner.blocks_mined,
                'connection_status': 'connected' if current_height >= 0 else 'disconnected',
                'p2p_connected': p2p_status.get('connected', False),
                'p2p_peers': p2p_status.get('peers', 0),
                'uptime': time.time() - self.stats['start_time'],
                'total_mining_attempts': len(self.miner.mining_history),
                'success_rate': (self.stats['successful_blocks'] / len(self.miner.mining_history)) * 100 if self.miner.mining_history else 0,
                'avg_mining_time': avg_mining_time,
                'current_hash_rate': current_hash_rate,
                'current_hash': current_hash,
                'current_nonce': current_nonce,
                'cuda_available': cuda_available,
                'mining_method': 'CUDA' if using_cuda else 'CPU'
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
    
    def mine_single_block(self) -> Tuple[bool, str]:
        """Mine a single block (lunalib 1.8.7 GenesisMiner対応)"""
        try:
            if not self._ensure_sm3_available():
                return False, "SM3 unavailable"
            log_cpu_mining_event("mine_single_block_called", {})
            # lunalib 1.8.7 Miner: mine_block()を使う
            mining_start = time.time()
            result = self.miner.mine_block()
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
                reward = 1.0 * (10 ** (block_difficulty - 1))
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
                        fixed_transactions.append(fixed_tx)
                    else:
                        fixed_transactions.append(tx)
                block_data['transactions'] = fixed_transactions
                # --- ここまで ---
                cuda_used = hasattr(self.miner, 'cuda_manager') and self.miner.cuda_manager and getattr(self.miner.cuda_manager, 'cuda_available', False) and self.config.use_gpu
                if cuda_used and mining_time > 0:
                    self.stats['cuda_hash_rate'] = nonce / mining_time
                    self.stats['cuda_last_nonce'] = nonce
                    self.stats['cuda_last_hash'] = block_hash
                    self.stats['last_mining_method'] = 'cuda'
                    safe_print(f"[DEBUG] CUDA mining: cuda_hash_rate={self.stats['cuda_hash_rate']}")
                else:
                    if hasattr(self.miner, 'get_mining_stats'):
                        mining_stats = self.miner.get_mining_stats()
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
                    reward_tx = self._create_reward_transaction(block_data)
                    # Update local mining stats/history so rewards are detected immediately
                    try:
                        self.miner.blocks_mined = getattr(self.miner, "blocks_mined", 0) + 1
                        self.miner.total_reward = getattr(self.miner, "total_reward", 0) + reward
                    except Exception:
                        pass
                    try:
                        history = getattr(self.miner, "mining_history", None)
                        if history is None:
                            history = []
                            self.miner.mining_history = history
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
        """Start auto-mining"""
        if self.miner.is_mining:
            return True

        self._log_message("Auto-mining invoked", "info")

        if not self._ensure_sm3_available():
            self._log_message("Auto-mining blocked (SM3 unavailable)", "error")
            return False

        self.enable_live_stats()

        if hasattr(self.miner, "should_stop_mining"):
            self.miner.should_stop_mining = False

        self._stop_mining_event.clear()

        try:
            self.miner.start_mining()
        except Exception:
            self.miner.is_mining = False
            return False
        # Ensure mining flag is set
        self.miner.is_mining = True
        
        # Log mining method being used
        cuda_status = self.miner.cuda_manager.cuda_available if self.miner.cuda_manager else False
        if cuda_status and self.config.use_gpu:
            self._log_message("Auto-mining started (GPU/CUDA enabled)", "info")
        else:
            self._log_message("Auto-mining started (CPU)", "info")
        
        def mining_loop():
            print("[DEBUG] mining_loop started")
            self._log_message("Mining loop started", "info")
            while self.miner.is_mining and self.is_running:
                if getattr(self.miner, "should_stop_mining", False):
                    break
                if self._stop_mining_event.is_set():
                    break
                self._log_message("Mining tick: starting block attempt", "info")
                success, message = self.mine_single_block()
                if success:
                    self._log_message(message, "success")
                    print("[DEBUG] Block mined successfully")
                    # After successful mining, wait longer to allow server to process
                    if self._stop_mining_event.wait(5):
                        break
                else:
                    # Check if it's a CUDA error
                    if "CUDA" in message or "dtype" in message:
                        self._log_message("CUDA mining error - falling back to CPU", "warning")
                        self.miner.use_cuda = False
                    if "Stale block detected" in message:
                        self._log_message(message, "info")
                    else:
                        self._log_message(message, "warning")
                    print(f"[DEBUG] Mining failed: {message}")
                    if self._stop_mining_event.wait(self.config.mining_interval):
                        break
            self._log_message("Mining loop stopped", "info")
        
        self.miner.mining_thread = threading.Thread(target=mining_loop, daemon=True)
        self.miner.mining_thread.start()
        return True
    
    def stop_auto_mining(self):
        """Stop auto-mining and abort current block"""
        # Signal immediate stop
        self.miner.is_mining = False
        self.miner.should_stop_mining = True
        self._stop_mining_event.set()
        
        self._log_message("Stopping mining... (aborting current block)", "info")
        
        if hasattr(self.miner, "stop_mining"):
            try:
                self.miner.stop_mining()
            except Exception:
                pass

        cuda_manager = getattr(self.miner, "cuda_manager", None)
        if cuda_manager:
            for method_name in ("stop_mining", "stop", "stop_cuda_mining", "shutdown"):
                method = getattr(cuda_manager, method_name, None)
                if callable(method):
                    try:
                        method()
                    except Exception:
                        pass

        # Call the miner's stop method (waits for thread to finish)
        # But don't wait too long - use a timeout approach
        if self.miner.mining_thread and self.miner.mining_thread.is_alive():
            # Give it a very short time to finish gracefully
            self.miner.mining_thread.join(timeout=0.5)
            if self.miner.mining_thread.is_alive():
                self._log_message("Mining thread still running, will terminate on next check", "warning")
            else:
                self._log_message("Mining stopped successfully", "info")
        else:
            self._log_message("Auto-mining stopped", "info")

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
    
    def get_mining_history(self) -> List[Dict]:
        """Get mining history"""
        return self.miner.mining_history
    
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
        try:
            log_cpu_mining_event("submit_block_called", {"block_index": block_data.get('index'), "block_data": block_data})
            self._normalize_block_for_lunalib(block_data)

            # Pre-validate with LunaLib's internal validator for clearer errors
            try:
                validation = self.blockchain_manager._validate_block_structure(block_data)
                if not validation.get("valid", False):
                    issues = validation.get("issues", [])
                    err = f"Block validation failed: {issues}"
                    log_cpu_mining_event("block_validation_failed", {"error": issues, "block_index": block_data.get('index')})
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
            
            # Submit plain JSON (server rejects gzip payloads)
            submit_ok, submit_msg = self._submit_block_plain_json(block_data)
            if submit_ok:
                self._last_submitted_hash = block_data.get("hash")
                self._last_submitted_index = block_data.get("index")
                self._last_submitted_ts = time.time()
                self._last_submitted_success = True
                return True, submit_msg
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
        if "timestamp" in block_data:
            try:
                block_data["timestamp"] = float(block_data.get("timestamp"))
            except Exception:
                pass

        if not block_data.get("miner"):
            block_data["miner"] = self.config.miner_address

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
                if skipped or already_exists:
                    warn_msg = f"Block #{block_data.get('index')} already exists on chain"
                    self._log_message(warn_msg, "warning")
                    return True, warn_msg
                self._log_message(f"Block #{block_data.get('index')} submitted", "success")
                return True, message
            try:
                error_text = response.text
            except Exception:
                error_text = ""
            if error_text:
                return False, f"HTTP {response.status_code}: {error_text}"
            return False, f"HTTP {response.status_code}"
        except Exception as e:
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
        
        # Reinitialize P2P (manual fetch only, no lunalib P2P)
        self.p2p_client = None
        self._log_message(f"Node URL updated to: {new_url}", "info")
    
    def update_mining_interval(self, new_interval: int):
        """Update mining interval"""
        self.config.mining_interval = new_interval
        self.config.save_to_storage()
        self._log_message(f"Mining interval updated to: {new_interval} seconds", "info")
    
    def toggle_gpu_acceleration(self, enabled: bool):
        """Toggle GPU/CUDA acceleration for mining"""
        self.config.use_gpu = enabled
        self.config.save_to_storage()
        
        # Refresh miner to apply GPU flag changes (lunalib reads flags at init)
        if self.miner is None:
            self.cuda_available = False
            if enabled:
                self._log_message("GPU acceleration enabled but miner is unavailable", "warning")
            else:
                self._log_message("GPU acceleration disabled", "info")
            return

        if enabled:
            try:
                self.miner = LunaLibMiner(self.config, self.data_manager)
                self.miner.blockchain_manager = self.blockchain_manager
                self.miner.mempool_manager = self.mempool_manager
                if hasattr(self.miner, 'auto_submit'):
                    self.miner.auto_submit = False
            except Exception:
                pass

        # Update miner's CUDA state
        if self.miner and getattr(self.miner, "cuda_manager", None):
            cuda_available = self.miner.cuda_manager.cuda_available
            if enabled and cuda_available:
                self.cuda_available = True
                self._log_message("GPU acceleration enabled - CUDA available", "success")
            elif enabled and not cuda_available:
                self.cuda_available = False
                self._log_message("GPU acceleration enabled but CUDA not available - falling back to CPU", "warning")
            else:
                self.cuda_available = False
                self._log_message("GPU acceleration disabled - using CPU mining", "info")
        else:
            self.cuda_available = False
            if enabled:
                self._log_message("GPU acceleration enabled but CUDA manager unavailable - using CPU mining", "warning")
            else:
                self._log_message("GPU acceleration disabled", "info")
    
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
        
        # Stop P2P client
        if self.p2p_client:
            try:
                self.p2p_client.stop()
                self._log_message("P2P client stopped", "info")
            except Exception as e:
                print(f"[DEBUG] Error stopping P2P client: {e}")
    
    def get_p2p_status(self) -> Dict:
        """Get P2P network status"""
        return {
            'connected': False,
            'peers': 0,
            'peer_list': [],
            'status': 'p2p disabled'
        }
    
    def _fetch_peers_from_daemon(self):
        """P2P peer fetching disabled (use LunaLib P2P if needed)."""
        return False
        
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