import os
import json
import time
import hashlib
import socket
import requests
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import threading

# Import lunalib components (1.6.6)
try:
    from lunalib.core.blockchain import BlockchainManager
    from lunalib.core.mempool import MempoolManager
    from lunalib.core.p2p import HybridBlockchainClient
    from lunalib.mining.difficulty import DifficultySystem
    from lunalib.mining.cuda_manager import CUDAManager
    from lunalib.mining.miner import Miner as LunaLibMiner
    LUNA_LIB_AVAILABLE = True
    P2P_AVAILABLE = True
except ImportError as e:
    print(f"LunaLib import error: {e}")
    LUNA_LIB_AVAILABLE = False
    P2P_AVAILABLE = False

class DataManager:
    """Manages data storage in ./data/ directory"""
    
    def __init__(self):
        self.data_dir = "./data"
        self.settings_file = os.path.join(self.data_dir, "settings.json")
        self.mining_history_file = os.path.join(self.data_dir, "mining_history.json")
        self.blockchain_cache_file = os.path.join(self.data_dir, "blockchain_cache.json")
        self.mempool_cache_file = os.path.join(self.data_dir, "mempool_cache.json")
        self.logs_file = os.path.join(self.data_dir, "logs.json")
        
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
            'mining_interval': 30
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
        """Load logs from file"""
        try:
            if os.path.exists(self.logs_file):
                with open(self.logs_file, 'r', encoding='utf-8') as f:
                    logs = json.load(f)
                    print("[DEBUG] DataManager.load_logs: Loaded logs:", logs)
                    print("[DEBUG] DataManager.load_logs: Type of logs:", type(logs))
                    return logs
        except Exception as e:
            print(f"Error loading logs: {e}")
        return []

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
    
    def save_to_storage(self):
        """Save configuration to storage"""
        settings = {
            'miner_address': self.miner_address,
            'difficulty': self.difficulty,
            'auto_mine': self.auto_mine,
            'node_url': self.node_url,
            'mining_interval': self.mining_interval,
            'use_gpu': self.use_gpu
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
        
        self.is_running = True
        
        # Peer list for P2P networking
        self.peers = []
        
        # Initialize BlockchainManager and MempoolManager first
        self.blockchain_manager = BlockchainManager(endpoint_url=self.config.node_url)
        self.mempool_manager = MempoolManager([self.config.node_url])
        
        # Initialize LunaLib Miner (uses config, data_manager signature)
        self.miner = LunaLibMiner(self.config, self.data_manager)
        
        # Link managers to miner
        self.miner.blockchain_manager = self.blockchain_manager
        self.miner.mempool_manager = self.mempool_manager
        
        # Disable auto-submission so we can handle it ourselves
        if hasattr(self.miner, 'auto_submit'):
            self.miner.auto_submit = False
        
        # Initialize HybridBlockchainClient for P2P networking (optional, non-blocking)
        self.p2p_client = None
        if P2P_AVAILABLE:
            try:
                self.p2p_client = HybridBlockchainClient(
                    self.config.node_url,
                    self.blockchain_manager,
                    self.mempool_manager
                )
                # Start P2P in background - don't block on failures
                try:
                    self.p2p_client.start()
                    print("[DEBUG] P2P HybridBlockchainClient started")
                except Exception as e:
                    print(f"[DEBUG] P2P start warning (non-critical): {e}")
                
                # Try to fetch peers - non-blocking, failures are OK
                threading.Thread(target=self._fetch_peers_from_daemon, daemon=True).start()
            except Exception as e:
                print(f"[DEBUG] P2P client initialization skipped: {e}")
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
            'from': 'network',
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
    
    def _log_message(self, message: str, msg_type: str = "info"):
        """Log message with callback and save to storage"""
        try:
            message = message.encode('utf-8').decode('utf-8')  # Ensure UTF-8 encoding
        except UnicodeEncodeError:
            print(f"DEBUG: UnicodeEncodeError encountered for message: {message}")
            message = "[Invalid Unicode Character]"

        log_entry = {
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'message': message,
            'type': msg_type
        }
        print(f"DEBUG: Log entry created: {log_entry}")
        self.logs.append(log_entry)
        
        if len(self.logs) > 1000:
            self.logs.pop(0)
            
        self.data_manager.save_logs(self.logs)
        print("DEBUG: Logs saved to storage.")
            
        if self.log_callback:
            self.log_callback(message, msg_type)
            print("DEBUG: Log callback executed.")
    
    def get_status(self) -> Dict:
        """Get node status"""
        try:
            current_height = self.blockchain_manager.get_blockchain_height()
            latest_block = self.blockchain_manager.get_block(current_height) if current_height > 0 else None
            
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
                current_hash_rate = getattr(self.miner, 'hash_rate', 0)
                current_hash = getattr(self.miner, 'current_hash', '')
                current_nonce = getattr(self.miner, 'current_nonce', 0)
            
            # Get mempool
            try:
                mempool = self.mempool_manager.get_pending_transactions() if self.mempool_manager else []
            except:
                mempool = self.blockchain_manager.get_mempool() if self.blockchain_manager else []
            
            # Get P2P status
            p2p_status = self.get_p2p_status()
            
            return {
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
                'error': str(e)
            }
    
    def mine_single_block(self) -> Tuple[bool, str]:
        """Mine a single block"""
        try:
            # Check if mining was stopped before starting
            if self.miner.should_stop_mining:
                return False, "Mining aborted"
            
            # Track mining start time for hashrate calculation
            mining_start = time.time()
            
            # Reset stop flag before mining (will be set again if stop is requested)
            self.miner.should_stop_mining = False
            
            # mine_block() returns (success, message, block_data)
            result = self.miner.mine_block()
            
            # Check if mining was stopped during the process
            if self.miner.should_stop_mining:
                return False, "Mining aborted by user"
            
            # Handle different return formats
            if isinstance(result, tuple) and len(result) == 3:
                success, message, block_data = result
            elif isinstance(result, dict):
                success = result.get('success', False)
                message = result.get('message', '')
                block_data = result.get('block', result)
            else:
                success = bool(result)
                message = ''
                block_data = result if isinstance(result, dict) else None
            
            if success and block_data:
                block_index = block_data.get('index', 'unknown')
                reward = block_data.get('reward', 1.0)
                nonce = block_data.get('nonce', 0)
                block_hash = block_data.get('hash', '')
                mining_time = time.time() - mining_start
                tx_count = len(block_data.get('transactions', []))
                
                # Debug: Log block data keys to check structure
                print(f"[DEBUG] Mined block keys: {list(block_data.keys())}")
                
                # Update stats based on mining method
                cuda_used = self.miner.cuda_manager and self.miner.cuda_manager.cuda_available and self.config.use_gpu
                if cuda_used and mining_time > 0:
                    self.stats['cuda_hash_rate'] = nonce / mining_time
                    self.stats['cuda_last_nonce'] = nonce
                    self.stats['cuda_last_hash'] = block_hash
                    self.stats['last_mining_method'] = 'cuda'
                else:
                    self.stats['last_mining_method'] = 'cpu'
                
                # Submit block (auto_submit is disabled)
                submit_success, submit_message = self.submit_block(block_data)
                
                if submit_success:
                    self._log_message(f"Block #{block_index} mined & submitted ({tx_count} txs) - Reward: {reward}", "success")
                    self._create_reward_transaction(block_data)
                    return True, f"Block #{block_index} mined & submitted ({tx_count} txs) - Reward: {reward}"
                else:
                    self._log_message(f"Block #{block_index} mined but submission failed: {submit_message}", "warning")
                    return False, f"Block #{block_index} mined but submission failed: {submit_message}"
            else:
                self._log_message(f"Mining failed: {message}", "error")
                return False, f"Mining failed: {message}"
        except Exception as e:
            self._log_message(f"Mining error: {str(e)}", "error")
            return False, f"Mining error: {str(e)}"
    
    def start_auto_mining(self):
        """Start auto-mining"""
        if self.miner.is_mining:
            return
            
        self.miner.start_mining()
        
        # Log mining method being used
        cuda_status = self.miner.cuda_manager.cuda_available if self.miner.cuda_manager else False
        if cuda_status and self.config.use_gpu:
            self._log_message("Auto-mining started (GPU/CUDA enabled)", "info")
        else:
            self._log_message("Auto-mining started (CPU)", "info")
        
        def mining_loop():
            while self.miner.is_mining and self.is_running:
                success, message = self.mine_single_block()
                if success:
                    self._log_message(message, "success")
                    # After successful mining, wait longer to allow server to process
                    time.sleep(5)
                else:
                    # Check if it's a CUDA error
                    if "CUDA" in message or "dtype" in message:
                        self._log_message("CUDA mining error - falling back to CPU", "warning")
                        self.miner.use_cuda = False
                    self._log_message(message, "warning")
                    time.sleep(self.config.mining_interval)
        
        self.miner.mining_thread = threading.Thread(target=mining_loop, daemon=True)
        self.miner.mining_thread.start()
    
    def stop_auto_mining(self):
        """Stop auto-mining and abort current block"""
        # Signal immediate stop
        self.miner.is_mining = False
        self.miner.should_stop_mining = True
        
        self._log_message("Stopping mining... (aborting current block)", "info")
        
        # Call the miner's stop method (waits for thread to finish)
        # But don't wait too long - use a timeout approach
        if self.miner.mining_thread and self.miner.mining_thread.is_alive():
            # Give it a short time to finish gracefully
            self.miner.mining_thread.join(timeout=2.0)
            if self.miner.mining_thread.is_alive():
                self._log_message("Mining thread still running, will terminate on next check", "warning")
            else:
                self._log_message("Mining stopped successfully", "info")
        else:
            self._log_message("Auto-mining stopped", "info")
    
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
        """Submit mined block to network via direct HTTP POST"""
        try:
            # Normalize block field names for server compatibility
            # Server expects 'previous_hash', lunalib may use 'prev_hash'
            if 'previous_hash' not in block_data:
                if 'prev_hash' in block_data:
                    block_data['previous_hash'] = block_data['prev_hash']
                else:
                    # Fetch previous hash from chain
                    try:
                        current_height = self.blockchain_manager.get_blockchain_height()
                        if current_height > 0:
                            prev_block = self.blockchain_manager.get_block(current_height)
                            if prev_block:
                                block_data['previous_hash'] = prev_block.get('hash', '0' * 64)
                    except Exception as e:
                        print(f"[DEBUG] Could not get previous hash: {e}")
            
            # Fix reward calculation: server expects BASE_REWARD * difficulty
            # BASE_REWARD is 1.0, so reward = 1.0 * difficulty
            block_difficulty = block_data.get('difficulty', 1)
            expected_reward = 1.0 * block_difficulty  # BASE_REWARD = 1.0
            
            # Update block reward if it doesn't match expected
            current_reward = block_data.get('reward', 1.0)
            if current_reward != expected_reward:
                print(f"[DEBUG] Fixing reward: {current_reward} -> {expected_reward} (difficulty={block_difficulty})")
                block_data['reward'] = expected_reward
                
                # Also fix reward transaction amount in transactions list
                for tx in block_data.get('transactions', []):
                    if tx.get('type') == 'reward':
                        tx['amount'] = expected_reward
            
            # Debug: Log block structure before submission
            print(f"[DEBUG] Submitting block #{block_data.get('index')}")
            print(f"[DEBUG] Block keys: {list(block_data.keys())}")
            print(f"[DEBUG] previous_hash: {block_data.get('previous_hash', 'MISSING')[:20]}...")
            print(f"[DEBUG] difficulty: {block_difficulty}, reward: {block_data.get('reward')}")
            
            # Try multiple submission endpoints via direct HTTP
            endpoints = [
                f"{self.config.node_url}/api/blockchain/submit",
                f"{self.config.node_url}/api/block/submit", 
                f"{self.config.node_url}/api/blocks/submit",
                f"{self.config.node_url}/api/mine/submit",
                f"{self.config.node_url}/submit_block",
            ]
            
            for endpoint in endpoints:
                try:
                    response = requests.post(
                        endpoint,
                        json=block_data,
                        headers={'Content-Type': 'application/json'},
                        timeout=30
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        success = data.get('success', True)
                        message = data.get('message', 'Block submitted')
                        
                        if success:
                            self._log_message(f"Block #{block_data['index']} submitted: {message}", "success")
                            
                            # Notify P2P peers about the new block
                            if self.p2p_client and hasattr(self.p2p_client, 'broadcast_block'):
                                try:
                                    self.p2p_client.broadcast_block(block_data)
                                except Exception as e:
                                    print(f"[DEBUG] P2P broadcast failed: {e}")
                            
                            return True, message
                        else:
                            error_msg = data.get('error', message)
                            print(f"[DEBUG] Submission rejected by {endpoint}: {error_msg}")
                            continue
                    elif response.status_code == 404:
                        continue  # Try next endpoint
                    else:
                        print(f"[DEBUG] HTTP {response.status_code} from {endpoint}")
                        continue
                        
                except requests.exceptions.RequestException as e:
                    print(f"[DEBUG] Request to {endpoint} failed: {e}")
                    continue
            
            # All endpoints failed
            self._log_message(f"Block #{block_data['index']} submission failed - no valid endpoint", "warning")
            self._save_block_locally(block_data)
            return False, "No valid submission endpoint found"
            
        except Exception as e:
            error_msg = f"Block submission error: {str(e)}"
            self._log_message(error_msg, "error")
            self._save_block_locally(block_data)
            return False, error_msg
    
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
        
        # Reinitialize managers with new URL
        self.blockchain_manager = BlockchainManager(endpoint_url=new_url)
        self.mempool_manager = MempoolManager([new_url])
        
        # Reinitialize miner and link managers
        self.miner = LunaLibMiner(self.config, self.data_manager)
        self.miner.blockchain_manager = self.blockchain_manager
        self.miner.mempool_manager = self.mempool_manager
        if hasattr(self.miner, 'auto_submit'):
            self.miner.auto_submit = False
        
        # Reinitialize P2P client
        if P2P_AVAILABLE:
            try:
                self.p2p_client = HybridBlockchainClient(
                    new_url,
                    self.blockchain_manager,
                    self.mempool_manager
                )
                self.p2p_client.start()
                self._fetch_peers_from_daemon()
                self._log_message(f"Node URL updated to: {new_url} (P2P reconnected)", "info")
            except Exception as e:
                self._log_message(f"Node URL updated but P2P failed: {e}", "warning")
        else:
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
        
        # Update miner's CUDA state
        if self.miner and self.miner.cuda_manager:
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
        if not self.p2p_client:
            return {
                'connected': False,
                'peers': 0,
                'peer_list': [],
                'status': 'P2P not available'
            }
        
        try:
            # Get peers from client or our local list
            peer_count = len(self.peers) if self.peers else 0
            if hasattr(self.p2p_client, 'peers') and self.p2p_client.peers:
                peer_count = len(self.p2p_client.peers)
                
            return {
                'connected': self.p2p_client.is_running if hasattr(self.p2p_client, 'is_running') else True,
                'peers': peer_count,
                'peer_list': self.peers[:10],  # Return first 10 peers
                'status': 'connected'
            }
        except Exception as e:
            return {
                'connected': False,
                'peers': 0,
                'peer_list': [],
                'status': f'Error: {e}'
            }
    
    def _fetch_peers_from_daemon(self):
        """Fetch peer list from the daemon running on node_url (non-blocking, failures OK)"""
        try:
            # Try common P2P daemon endpoints with short timeout
            endpoints = [
                f"{self.config.node_url}/api/peers",
                f"{self.config.node_url}/peers",
                f"{self.config.node_url}/api/p2p/peers",
            ]
            
            for endpoint in endpoints:
                try:
                    response = requests.get(endpoint, timeout=5)
                    if response.status_code == 200:
                        data = response.json()
                        
                        # Handle different response formats
                        if isinstance(data, list):
                            self.peers = data
                        elif isinstance(data, dict):
                            self.peers = data.get('peers', data.get('nodes', data.get('data', [])))
                        
                        if self.peers:
                            print(f"[DEBUG] Fetched {len(self.peers)} peers from {endpoint}")
                            
                            # Register peers with P2P client if available
                            if self.p2p_client and hasattr(self.p2p_client, 'add_peers'):
                                try:
                                    self.p2p_client.add_peers(self.peers)
                                except:
                                    pass
                            
                            return True
                except:
                    continue
            
            # No peers found - this is OK, not an error
            print("[DEBUG] No P2P peers available from daemon")
            return False
            
        except Exception as e:
            print(f"[DEBUG] Peer fetch skipped: {e}")
            return False
    
    def refresh_peers(self) -> Dict:
        """Manually refresh peer list from daemon"""
        success = self._fetch_peers_from_daemon()
        return {
            'success': success,
            'peers': len(self.peers),
            'peer_list': self.peers[:10]
        }
    
    def register_as_peer(self, my_address: str = None, my_port: int = None) -> bool:
        """Register this node as a peer with the daemon (optional, may not be supported)"""
        try:
            # Get local address if not provided
            if not my_address:
                try:
                    hostname = socket.gethostname()
                    my_address = socket.gethostbyname(hostname)
                except:
                    my_address = "127.0.0.1"
            
            if not my_port:
                my_port = 8545  # Default P2P port
            
            # Try to register with daemon
            endpoints = [
                f"{self.config.node_url}/api/peers/register",
                f"{self.config.node_url}/peers/register",
            ]
            
            registration_data = {
                'address': my_address,
                'port': my_port,
                'node_type': 'miner',
                'version': '1.0.0'
            }
            
            for endpoint in endpoints:
                try:
                    response = requests.post(endpoint, json=registration_data, timeout=5)
                    if response.status_code in [200, 201]:
                        print(f"[DEBUG] Registered as peer: {my_address}:{my_port}")
                        return True
                except:
                    continue
            
            # Registration not supported - this is OK
            return False
            
        except Exception as e:
            print(f"[DEBUG] Peer registration skipped: {e}")
            return False