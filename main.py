import flet as ft
import threading
import time
import requests
from typing import Dict, List, Optional, Tuple
import hashlib
import json
from datetime import datetime
import sys
import os

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
            with open(self.settings_file, 'w') as f:
                json.dump(settings, f, indent=2)
            return True
        except Exception as e:
            print(f"Error saving settings: {e}")
            return False
    
    def load_settings(self) -> Dict:
        """Load settings from file"""
        try:
            if os.path.exists(self.settings_file):
                with open(self.settings_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            print(f"Error loading settings: {e}")
        return {}
    
    def save_mining_history(self, history: List[Dict]):
        """Save mining history to file"""
        try:
            with open(self.mining_history_file, 'w') as f:
                json.dump(history, f, indent=2, default=str)
            return True
        except Exception as e:
            print(f"Error saving mining history: {e}")
            return False
    
    def load_mining_history(self) -> List[Dict]:
        """Load mining history from file"""
        try:
            if os.path.exists(self.mining_history_file):
                with open(self.mining_history_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            print(f"Error loading mining history: {e}")
        return []
    
    def save_blockchain_cache(self, blockchain: List[Dict]):
        """Save blockchain cache to file"""
        try:
            with open(self.blockchain_cache_file, 'w') as f:
                json.dump(blockchain, f, indent=2, default=str)
            return True
        except Exception as e:
            print(f"Error saving blockchain cache: {e}")
            return False
    
    def load_blockchain_cache(self) -> List[Dict]:
        """Load blockchain cache from file"""
        try:
            if os.path.exists(self.blockchain_cache_file):
                with open(self.blockchain_cache_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            print(f"Error loading blockchain cache: {e}")
        return []
    
    def save_mempool_cache(self, mempool: List[Dict]):
        """Save mempool cache to file"""
        try:
            with open(self.mempool_cache_file, 'w') as f:
                json.dump(mempool, f, indent=2, default=str)
            return True
        except Exception as e:
            print(f"Error saving mempool cache: {e}")
            return False
    
    def load_mempool_cache(self) -> List[Dict]:
        """Load mempool cache from file"""
        try:
            if os.path.exists(self.mempool_cache_file):
                with open(self.mempool_cache_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            print(f"Error loading mempool cache: {e}")
        return []
    
    def save_logs(self, logs: List[Dict]):
        """Save logs to file"""
        try:
            with open(self.logs_file, 'w') as f:
                json.dump(logs, f, indent=2, default=str)
            return True
        except Exception as e:
            print(f"Error saving logs: {e}")
            return False
    
    def load_logs(self) -> List[Dict]:
        """Load logs from file"""
        try:
            if os.path.exists(self.logs_file):
                with open(self.logs_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            print(f"Error loading logs: {e}")
        return []


class Block:
    """Block representation"""
    def __init__(self, index: int, previous_hash: str, timestamp: float, 
                 transactions: List[Dict], miner: str, difficulty: int):
        self.index = index
        self.previous_hash = previous_hash
        self.timestamp = timestamp
        self.transactions = transactions
        self.miner = miner
        self.difficulty = difficulty
        self.nonce = 0
        self.hash = self.calculate_hash()
        
    def calculate_hash(self) -> str:
        """Calculate block hash"""
        block_data = f"{self.index}{self.previous_hash}{self.timestamp}{self.transactions}{self.miner}{self.difficulty}{self.nonce}"
        return hashlib.sha256(block_data.encode()).hexdigest()
    
    def mine_block(self) -> bool:
        """Mine the block (simplified PoW)"""
        target = "0" * self.difficulty
        while not self.hash.startswith(target):
            if self.nonce > 100000:  # Safety limit
                return False
            self.nonce += 1
            self.hash = self.calculate_hash()
            if self.nonce % 1000 == 0:
                return False
        return True
    
    def to_dict(self) -> Dict:
        """Convert block to dictionary"""
        return {
            'index': self.index,
            'previous_hash': self.previous_hash,
            'timestamp': self.timestamp,
            'transactions': self.transactions,
            'miner': self.miner,
            'difficulty': self.difficulty,
            'nonce': self.nonce,
            'hash': self.hash
        }


class NodeConfig:
    """Node configuration with data persistence"""
    
    def __init__(self, data_manager: DataManager):
        self.data_manager = data_manager
        self.load_from_storage()
    
    def load_from_storage(self):
        """Load configuration from storage"""
        settings = self.data_manager.load_settings()
        self.miner_address = settings.get('miner_address', "LUN_Node_Miner_Default")
        self.difficulty = settings.get('difficulty', 2)
        self.auto_mine = settings.get('auto_mine', False)
        self.node_url = settings.get('node_url', "https://bank.linglin.art")
        self.mining_interval = settings.get('mining_interval', 30)
    
    def save_to_storage(self):
        """Save configuration to storage"""
        settings = {
            'miner_address': self.miner_address,
            'difficulty': self.difficulty,
            'auto_mine': self.auto_mine,
            'node_url': self.node_url,
            'mining_interval': self.mining_interval
        }
        return self.data_manager.save_settings(settings)


class BlockchainManager:
    """Blockchain manager with progress tracking and caching"""
    
    def __init__(self, node_url: str, data_manager: DataManager):
        self.node_url = node_url
        self.data_manager = data_manager
        self.blockchain_cache = []
        self.mempool_cache = []
        self.last_update_time = 0
        self.cache_duration = 300  # 5 minutes cache
        
        # Load cached data
        self.load_cached_data()
        
    def load_cached_data(self):
        """Load cached blockchain and mempool data"""
        self.blockchain_cache = self.data_manager.load_blockchain_cache()
        self.mempool_cache = self.data_manager.load_mempool_cache()
        print(f"DEBUG: Loaded {len(self.blockchain_cache)} cached blocks and {len(self.mempool_cache)} cached mempool transactions")
    
    def save_cached_data(self):
        """Save blockchain and mempool data to cache"""
        self.data_manager.save_blockchain_cache(self.blockchain_cache)
        self.data_manager.save_mempool_cache(self.mempool_cache)
    def get_blockchain_with_progress(self, progress_callback=None):
        """Get blockchain with detailed progress tracking"""
        try:
            if progress_callback:
                progress_callback(0, "Initializing blockchain sync...")
            
            # Step 1: Get current blockchain height
            if progress_callback:
                progress_callback(10, "Getting current blockchain height...")
            
            current_height = 0
            try:
                # Try optimized endpoint first
                response = requests.get("https://bank.linglin.art/blockchain/latest", timeout=10)
                if response.status_code == 200:
                    latest_block = response.json()
                    current_height = latest_block.get('index', 0)
                    if progress_callback:
                        progress_callback(20, f"Current height: {current_height}")
                else:
                    # Fallback to full chain
                    if progress_callback:
                        progress_callback(15, "Falling back to full chain...")
                    response = requests.get("https://bank.linglin.art/blockchain", timeout=30)
                    if response.status_code == 200:
                        blockchain = response.json()
                        current_height = len(blockchain) - 1 if blockchain else 0
                        if progress_callback:
                            progress_callback(20, f"Current height: {current_height} (from full chain)")
            except Exception as e:
                if progress_callback:
                    progress_callback(0, f"Failed to get blockchain height: {str(e)}")
                return []

            if current_height == 0:
                if progress_callback:
                    progress_callback(100, "No blocks available")
                return []

            # Step 2: Check cache status
            if progress_callback:
                progress_callback(25, "Checking cache...")
            
            cached_height = self.wallet_core.blockchain_cache.get_highest_cached_height()
            start_height = 0 if cached_height < 0 else cached_height + 1
            
            if start_height > current_height:
                if progress_callback:
                    progress_callback(100, "Cache is up to date")
                # Return cached blocks
                return self.wallet_core.blockchain_cache.get_block_range(0, current_height)

            total_blocks = current_height - start_height + 1
            if progress_callback:
                progress_callback(30, f"Need to download {total_blocks} new blocks")

            all_blocks = []
            batch_size = 50
            downloaded = 0

            # Step 3: Download in batches
            for batch_start in range(start_height, current_height + 1, batch_size):
                batch_end = min(batch_start + batch_size - 1, current_height)
                batch_size_actual = batch_end - batch_start + 1
                
                # Update progress
                downloaded += batch_size_actual
                progress = 30 + int((downloaded / total_blocks) * 60)
                if progress_callback:
                    progress_callback(progress, f"Downloading blocks {batch_start}-{batch_end}")

                # Get blocks using range endpoint if available
                blocks = []
                try:
                    response = requests.get(
                        f"https://bank.linglin.art/blockchain/range?start={batch_start}&end={batch_end}",
                        timeout=30
                    )
                    if response.status_code == 200:
                        blocks = response.json()
                        if progress_callback:
                            progress_callback(progress + 5, f"Processing {len(blocks)} blocks...")
                    else:
                        # Fallback: get full chain and filter
                        if progress_callback:
                            progress_callback(progress, "Using full chain fallback...")
                        response = requests.get("https://bank.linglin.art/blockchain", timeout=60)
                        if response.status_code == 200:
                            full_chain = response.json()
                            blocks = [block for block in full_chain 
                                    if batch_start <= block.get('index', 0) <= batch_end]
                except Exception as e:
                    if progress_callback:
                        progress_callback(progress, f"Batch error: {str(e)}")
                    continue

                if blocks:
                    # Step 4: Cache blocks
                    if progress_callback:
                        progress_callback(progress + 2, f"Caching {len(blocks)} blocks...")
                    
                    for block in blocks:
                        height = block.get('index', batch_start)
                        block_hash = block.get('hash', '')
                        self.wallet_core.blockchain_cache.save_block(height, block_hash, block)
                    
                    all_blocks.extend(blocks)
                    
                    if progress_callback:
                        progress_callback(progress + 5, f"Cached {len(blocks)} blocks")

                # Small delay to be nice to the server
                time.sleep(0.1)

            # Step 5: Get all blocks from cache for consistency
            if progress_callback:
                progress_callback(95, "Finalizing blockchain data...")
            
            final_blocks = self.wallet_core.blockchain_cache.get_block_range(0, current_height)
            
            if progress_callback:
                progress_callback(100, f"Sync complete: {len(final_blocks)} blocks loaded")
            
            return final_blocks

        except requests.exceptions.Timeout:
            error_msg = "Blockchain download timed out"
            if progress_callback:
                progress_callback(0, error_msg)
            self.add_log_message(error_msg, "warning")
            return []
        except requests.exceptions.ConnectionError:
            error_msg = "Cannot connect to blockchain server"
            if progress_callback:
                progress_callback(0, error_msg)
            self.add_log_message(error_msg, "warning")
            return []
        except Exception as e:
            error_msg = f"Blockchain error: {str(e)}"
            print(f"Blockchain error: {e}")
            if progress_callback:
                progress_callback(0, error_msg)
            self.add_log_message(error_msg, "error")
            return []
    def get_mempool_with_progress(self, progress_callback=None):
        """Get mempool with progress tracking"""
        try:
            if progress_callback:
                progress_callback(0, "Connecting to mempool...")
            
            # Step 1: Initial connection
            if progress_callback:
                progress_callback(20, "Fetching mempool data...")
            
            response = requests.get("https://bank.linglin.art/mempool", timeout=15)
            
            if progress_callback:
                progress_callback(60, "Processing transactions...")
            
            if response.status_code == 200:
                mempool = response.json()
                
                # Step 2: Process and cache transactions
                if progress_callback:
                    progress_callback(80, f"Caching {len(mempool)} transactions...")
                
                # Cache mempool transactions
                our_addresses = {wallet['address'].lower() for wallet in self.wallet_core.wallets} if self.wallet_core.wallets else set()
                
                for tx in mempool:
                    tx_hash = tx.get('hash')
                    if tx_hash:
                        # Check if this involves our addresses
                        from_addr = (tx.get('from') or tx.get('sender') or '').lower()
                        to_addr = (tx.get('to') or tx.get('receiver') or '').lower()
                        
                        involved_address = ""
                        if from_addr in our_addresses or to_addr in our_addresses:
                            involved_address = from_addr if from_addr in our_addresses else to_addr
                        
                        # Cache the transaction
                        self.wallet_core.blockchain_cache.save_mempool_tx(tx_hash, tx, involved_address)
                
                if progress_callback:
                    progress_callback(100, f"Loaded {len(mempool)} mempool transactions")
                
                return mempool
            else:
                error_msg = f"Mempool error: {response.status_code}"
                if progress_callback:
                    progress_callback(0, error_msg)
                self.add_log_message(error_msg, "warning")
                return []
                
        except requests.exceptions.Timeout:
            error_msg = "Mempool request timed out"
            if progress_callback:
                progress_callback(0, error_msg)
            self.add_log_message(error_msg, "warning")
            return []
        except requests.exceptions.ConnectionError:
            error_msg = "Cannot connect to mempool server"
            if progress_callback:
                progress_callback(0, error_msg)
            self.add_log_message(error_msg, "warning")
            return []
        except Exception as e:
            error_msg = f"Mempool error: {str(e)}"
            print(f"Mempool error: {e}")
            if progress_callback:
                progress_callback(0, error_msg)
            self.add_log_message(error_msg, "error")
            return []
    
    def get_current_height(self) -> int:
        """Get current blockchain height"""
        if self.blockchain_cache:
            return len(self.blockchain_cache) - 1
        return 0
    
    def get_recent_blocks(self, count: int = 10) -> List[Dict]:
        """Get recent blocks"""
        if self.blockchain_cache:
            return self.blockchain_cache[-count:]
        return []
    
    def get_latest_block(self) -> Optional[Dict]:
        """Get latest block"""
        if self.blockchain_cache:
            return self.blockchain_cache[-1]
        return None
    def get_blockchain_with_progress(self, progress_callback=None) -> Tuple[List[Dict], bool]:
        """Get blockchain with progress updates - CORRECTED ENDPOINT"""
        try:
            # Check if cache is still valid
            current_time = time.time()
            if (self.blockchain_cache and 
                current_time - self.last_update_time < self.cache_duration):
                if progress_callback:
                    progress_callback(100, "Using cached blockchain data")
                return self.blockchain_cache, True
            
            if progress_callback:
                progress_callback(0, "Connecting to blockchain network...")
            
            # Use correct endpoint from app.py
            response = requests.get(f"{self.node_url}/blockchain", timeout=30)
            if response.status_code == 200:
                blockchain = response.json()
                
                if progress_callback:
                    progress_callback(50, f"Processing {len(blockchain)} blocks...")
                
                # Update cache
                self.blockchain_cache = blockchain
                self.last_update_time = current_time
                self.save_cached_data()
                
                if progress_callback:
                    progress_callback(100, "Blockchain loaded successfully")
                
                return blockchain, True
            else:
                if progress_callback:
                    progress_callback(0, f"Network error: {response.status_code}")
                return self.blockchain_cache, False
                
        except Exception as e:
            error_msg = f"Blockchain loading error: {str(e)}"
            print(f"DEBUG: {error_msg}")
            if progress_callback:
                progress_callback(0, error_msg)
            return self.blockchain_cache, False
    def refresh_data(self):
        """Force refresh of all data"""
        self.last_update_time = 0
        self.blockchain_cache = []
        self.mempool_cache = []


class Miner:
    """Miner class with optimized blockchain access"""
    
    def __init__(self, config: NodeConfig, data_manager: DataManager,
                 mining_started_callback=None,
                 mining_completed_callback=None,
                 block_mined_callback=None):
        self.config = config
        self.data_manager = data_manager
        self.is_mining = False
        self.blocks_mined = 0
        self.total_reward = 0.0
        self.mining_started_callback = mining_started_callback
        self.mining_completed_callback = mining_completed_callback
        self.block_mined_callback = block_mined_callback
        
        # Load mining history from storage
        self.mining_history = self.data_manager.load_mining_history()
        
        self.blockchain_manager = BlockchainManager(config.node_url, data_manager)
        self.current_hash = ""
        self.current_nonce = 0
        self.hash_rate = 0
        self.mining_thread = None
        self.should_stop_mining = False
        
    def start_mining(self):
        """Start auto-mining"""
        if self.is_mining:
            return
            
        self.is_mining = True
        self.should_stop_mining = False
        if self.mining_started_callback:
            self.mining_started_callback()
        
    def stop_mining(self):
        """Stop auto-mining"""
        self.is_mining = False
        self.should_stop_mining = True
        
    def save_mining_history(self):
        """Save mining history to storage"""
        self.data_manager.save_mining_history(self.mining_history)
        
    def mine_block(self) -> Tuple[bool, str, Optional[Dict]]:
        """Mine a single block with optimized blockchain access"""
        try:
            # Get blockchain data first
            blockchain, success = self.blockchain_manager.get_blockchain_with_progress()
            if not success or not blockchain:
                return False, "Cannot connect to blockchain network", None
            
            current_height = len(blockchain) - 1
            latest_block = blockchain[-1]
            new_index = latest_block.get('index', 0) + 1
            
            # Get mempool transactions
            mempool, mempool_success = self.blockchain_manager.get_mempool_with_progress()
            if not mempool_success:
                mempool = []
                
            block = Block(
                index=new_index,
                previous_hash=latest_block.get('hash', '0' * 64),
                timestamp=time.time(),
                transactions=mempool,
                miner=self.config.miner_address,
                difficulty=self.config.difficulty
            )
            
            start_time = time.time()
            hash_count = 0
            last_hash_update = start_time
            
            # Mine the block
            target = "0" * self.config.difficulty
            max_nonce = 100000  # Safety limit
            
            while not block.hash.startswith(target):
                if self.should_stop_mining or block.nonce >= max_nonce:
                    return False, "Mining interrupted", None
                    
                block.nonce += 1
                block.hash = block.calculate_hash()
                hash_count += 1
                self.current_hash = block.hash
                self.current_nonce = block.nonce
                
                # Update hash rate every second
                current_time = time.time()
                if current_time - last_hash_update >= 1:
                    self.hash_rate = hash_count / (current_time - last_hash_update)
                    hash_count = 0
                    last_hash_update = current_time
                
                if block.nonce % 1000 == 0:
                    if not self.is_mining:
                        return False, "Mining interrupted", None
            
            mining_time = time.time() - start_time
            
            # Successfully mined block
            self.blocks_mined += 1
            block_data = block.to_dict()
            
            mining_record = {
                'block_index': new_index,
                'timestamp': time.time(),
                'mining_time': mining_time,
                'difficulty': self.config.difficulty,
                'nonce': block.nonce,
                'hash': block.hash,
                'status': 'success'
            }
            self.mining_history.append(mining_record)
            self.save_mining_history()
            
            if self.mining_completed_callback:
                self.mining_completed_callback(True, f"Block #{new_index} mined successfully")
            
            if self.block_mined_callback:
                self.block_mined_callback(block_data)
                
            return True, f"Block #{new_index} mined", block_data
                
        except Exception as e:
            error_msg = f"Mining error: {str(e)}"
            print(error_msg)
            return False, error_msg, None


class LunaNode:
    """Main Luna Node class with optimized blockchain access"""
    
    def __init__(self, cuda_available: bool = False,
                 log_callback=None,
                 new_bill_callback=None,
                 new_reward_callback=None,
                 history_updated_callback=None,
                 mining_started_callback=None,
                 mining_completed_callback=None):
        
        self.cuda_available = cuda_available
        self.data_manager = DataManager()
        
        # Load logs from storage
        self.logs = self.data_manager.load_logs()
        
        self.config = NodeConfig(self.data_manager)
        self.stats = {
            'start_time': time.time(),
            'total_hash_attempts': 0,
            'successful_blocks': 0,
            'failed_attempts': 0
        }
        
        self.miner = Miner(
            self.config,
            self.data_manager,
            mining_started_callback=mining_started_callback,
            mining_completed_callback=mining_completed_callback,
            block_mined_callback=self._on_block_mined
        )
        
        self.log_callback = log_callback
        self.new_bill_callback = new_bill_callback
        self.new_reward_callback = new_reward_callback
        self.history_updated_callback = history_updated_callback
        self.mining_started_callback = mining_started_callback
        self.mining_completed_callback = mining_completed_callback
        
        self.is_running = True
        
        if self.config.auto_mine:
            self.start_auto_mining()
            
    def _on_block_mined(self, block_data: Dict):
        """Handle newly mined block"""
        try:
            success = self.submit_block(block_data)
            if success:
                self._log_message(f"Block #{block_data['index']} submitted successfully", "success")
                self.stats['successful_blocks'] += 1
                
                reward_tx = self._create_reward_transaction(block_data)
                
                if self.new_reward_callback:
                    self.new_reward_callback(reward_tx)
                
                if self.new_bill_callback:
                    self.new_bill_callback(block_data)
                
                if self.history_updated_callback:
                    self.history_updated_callback()
                    
            else:
                self._log_message(f"Failed to submit block #{block_data['index']}", "warning")
                self.stats['failed_attempts'] += 1
                
        except Exception as e:
            self._log_message(f"Error processing mined block: {str(e)}", "error")
            self.stats['failed_attempts'] += 1
    
    def _create_reward_transaction(self, block_data: Dict) -> Dict:
        """Create mining reward transaction"""
        reward_amount = 50.0
        reward_tx = {
            'type': 'reward',
            'from': 'network',
            'to': self.config.miner_address,
            'amount': reward_amount,
            'timestamp': time.time(),
            'block_hash': block_data['hash'],
            'hash': f"reward_{block_data['hash']}",
            'status': 'pending'
        }
        self.miner.total_reward += reward_amount
        return reward_tx
    
    def _log_message(self, message: str, msg_type: str = "info"):
        """Log message with callback and save to storage"""
        log_entry = {
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'message': message,
            'type': msg_type
        }
        self.logs.append(log_entry)
        
        if len(self.logs) > 1000:
            self.logs.pop(0)
            
        self.data_manager.save_logs(self.logs)
            
        if self.log_callback:
            self.log_callback(message, msg_type)
    
    def get_status(self) -> Dict:
        """Get node status with optimized blockchain access"""
        try:
            blockchain, success = self.miner.blockchain_manager.get_blockchain_with_progress()
            current_height = len(blockchain) - 1 if blockchain else 0
            latest_block = blockchain[-1] if blockchain else {}
            
            total_mining_time = sum(record.get('mining_time', 0) for record in self.miner.mining_history)
            avg_mining_time = total_mining_time / len(self.miner.mining_history) if self.miner.mining_history else 0
            
            return {
                'network_height': current_height,
                'network_difficulty': latest_block.get('difficulty', 1),
                'previous_hash': latest_block.get('hash', '0' * 64),
                'miner_address': self.config.miner_address,
                'blocks_mined': self.miner.blocks_mined,
                'auto_mining': self.miner.is_mining,
                'configured_difficulty': self.config.difficulty,
                'total_reward': self.miner.total_reward,
                'total_transactions': sum(len(block.get('transactions', [])) for block in blockchain[-10:]) if blockchain else 0,
                'reward_transactions': self.miner.blocks_mined,
                'connection_status': 'connected' if current_height > 0 else 'disconnected',
                'uptime': time.time() - self.stats['start_time'],
                'total_mining_attempts': len(self.miner.mining_history),
                'success_rate': (self.stats['successful_blocks'] / len(self.miner.mining_history)) * 100 if self.miner.mining_history else 0,
                'avg_mining_time': avg_mining_time,
                'current_hash_rate': self.miner.hash_rate,
                'current_hash': self.miner.current_hash,
                'current_nonce': self.miner.current_nonce
            }
                
        except Exception as e:
            return {
                'network_height': 0,
                'network_difficulty': 1,
                'previous_hash': '0' * 64,
                'miner_address': self.config.miner_address,
                'blocks_mined': self.miner.blocks_mined,
                'auto_mining': self.miner.is_mining,
                'configured_difficulty': self.config.difficulty,
                'total_reward': self.miner.total_reward,
                'total_transactions': 0,
                'reward_transactions': self.miner.blocks_mined,
                'connection_status': 'error',
                'uptime': time.time() - self.stats['start_time'],
                'total_mining_attempts': len(self.miner.mining_history),
                'success_rate': 0,
                'avg_mining_time': 0,
                'current_hash_rate': 0,
                'current_hash': '',
                'current_nonce': 0,
                'error': str(e)
            }
    
    def mine_single_block(self) -> Tuple[bool, str]:
        """Mine a single block"""
        try:
            success, message, block_data = self.miner.mine_block()
            return success, message
        except Exception as e:
            return False, f"Mining error: {str(e)}"
    
    def start_auto_mining(self):
        """Start auto-mining"""
        if self.miner.is_mining:
            return
            
        self.miner.start_mining()
        self._log_message("Auto-mining started", "info")
        
        def mining_loop():
            while self.miner.is_mining and self.is_running:
                success, message = self.mine_single_block()
                if success:
                    self._log_message(message, "success")
                else:
                    self._log_message(message, "warning")
                
                time.sleep(self.config.mining_interval)
        
        self.miner.mining_thread = threading.Thread(target=mining_loop, daemon=True)
        self.miner.mining_thread.start()
    
    def stop_auto_mining(self):
        """Stop auto-mining"""
        self.miner.stop_mining()
        self._log_message("Auto-mining stopped", "info")
    
    def sync_network(self, progress_callback=None) -> Dict:
        """Sync with network with progress updates"""
        try:
            if progress_callback:
                progress_callback(0, "Starting network sync...")
            
            # Refresh blockchain data
            blockchain, blockchain_success = self.miner.blockchain_manager.get_blockchain_with_progress(
                lambda progress, msg: progress_callback(progress // 2, msg) if progress_callback else None
            )
            
            if progress_callback:
                progress_callback(50, "Loading mempool...")
            
            # Refresh mempool data
            mempool, mempool_success = self.miner.blockchain_manager.get_mempool_with_progress(
                lambda progress, msg: progress_callback(50 + progress // 2, msg) if progress_callback else None
            )
            
            status = self.get_status()
            
            if progress_callback:
                progress_callback(100, "Sync completed")
            
            self._log_message(f"Network sync completed - Height: {status['network_height']}", "info")
            
            if self.history_updated_callback:
                self.history_updated_callback()
                
            return {'success': True, 'status': status}
            
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
    
    def submit_block(self, block_data: Dict) -> bool:
        """Submit mined block to network - CORRECTED ENDPOINTS"""
        try:
            # Use the correct endpoint from app.py
            endpoint = f"{self.config.node_url}/blockchain/submit-block"
            
            self._log_message(f"Submitting block #{block_data['index']} to: {endpoint}", "info")
            
            response = requests.post(
                endpoint,
                json=block_data,
                timeout=30,
                headers={'Content-Type': 'application/json'}
            )
            
            self._log_message(f"Response status: {response.status_code}", "info")
            
            if response.status_code in [200, 201]:
                result = response.json()
                if result.get("success"):
                    status = result.get("status", "added")
                    
                    if status == "already_exists":
                        self._log_message(f"Block #{block_data['index']} already exists in blockchain", "warning")
                        return True  # Still count as success
                    else:
                        self._log_message(f"Block #{block_data['index']} submitted successfully!", "success")
                        return True
                else:
                    error_msg = result.get('error', 'Unknown error')
                    self._log_message(f"Block rejected: {error_msg}", "warning")
            else:
                self._log_message(f"Submission failed: {response.status_code} - {response.text}", "warning")
                
            # Fallback: Try alternative endpoints if main one fails
            alternative_endpoints = [
                f"{self.config.node_url}/blockchain/add",
                f"{self.config.node_url}/blocks"
            ]
            
            for alt_endpoint in alternative_endpoints:
                try:
                    self._log_message(f"Trying alternative endpoint: {alt_endpoint}", "info")
                    response = requests.post(
                        alt_endpoint,
                        json=block_data,
                        timeout=15,
                        headers={'Content-Type': 'application/json'}
                    )
                    
                    if response.status_code in [200, 201]:
                        self._log_message(f"Block submitted via alternative endpoint!", "success")
                        return True
                        
                except Exception as e:
                    self._log_message(f"Alternative endpoint failed: {str(e)}", "warning")
                    continue
            
            # If all endpoints failed, save block locally
            self._log_message("All submission attempts failed. Saving block locally.", "warning")
            return self._save_block_locally(block_data)
            
        except Exception as e:
            error_msg = f"Block submission error: {str(e)}"
            self._log_message(error_msg, "error")
            # Save block locally as fallback
            return self._save_block_locally(block_data)

    
                
        except Exception as e:
            error_msg = f"Blockchain loading error: {str(e)}"
            print(f"DEBUG: {error_msg}")
            if progress_callback:
                progress_callback(0, error_msg)
            return self.blockchain_cache, False

    
    def _save_block_locally(self, block_data: Dict) -> bool:
        """Save block locally when network submission fails"""
        try:
            # Create local blocks directory
            blocks_dir = "./data/blocks"
            if not os.path.exists(blocks_dir):
                os.makedirs(blocks_dir)
            
            # Save block to file
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
        self._log_message(f"Difficulty updated to: {new_difficulty}", "info")
    
    def update_node_url(self, new_url: str):
        """Update node URL"""
        self.config.node_url = new_url
        self.config.save_to_storage()
        self.miner.blockchain_manager.node_url = new_url
        self.miner.blockchain_manager.refresh_data()  # Clear cache when URL changes
        self._log_message(f"Node URL updated to: {new_url}", "info")
    
    def update_mining_interval(self, new_interval: int):
        """Update mining interval"""
        self.config.mining_interval = new_interval
        self.config.save_to_storage()
        self._log_message(f"Mining interval updated to: {new_interval} seconds", "info")
    
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


class LunaNodeApp:
    """Luna Node Application with Blue Theme"""
    
    def __init__(self):
        self.node = None
        self.minimized_to_tray = False
        self.current_tab_index = 0
        self.page = None
        
    def create_main_ui(self, page: ft.Page):
        """Create the main node interface"""
        self.page = page
        
        # Page setup with blue theme
        page.title = "🔵 Luna Node"
        page.theme_mode = ft.ThemeMode.DARK
        page.fonts = {
            "Custom": "./font.ttf"
        }
        page.theme = ft.Theme(
            font_family="Custom", # Try this if available
        )
        page.padding = 0
        page.window.width = 1024
        page.window.height = 768
        page.window.min_width = 800
        page.window.min_height = 600
        page.window.center()
        
        page.on_window_event = self.on_window_event
        
        main_layout = self.create_main_layout()
        page.add(main_layout)
        
        self.initialize_node_async()
        
    def create_main_layout(self):
        """Create the main layout with sidebar and content area"""
        sidebar = self.create_sidebar()
        main_content = self.create_main_content()
        
        return ft.Row(
            [sidebar, ft.VerticalDivider(width=1, color="#1e3a5c"), main_content],
            expand=True,
            spacing=0
        )
        
    def create_sidebar(self):
        """Create the sidebar with node info and quick actions"""
        sidebar_width = 240
        
        # Node status
        self.lbl_node_status = ft.Text("Status: Initializing...", size=12, color="#e3f2fd")
        self.lbl_network_height = ft.Text("Network Height: --", size=10, color="#e3f2fd")
        self.lbl_difficulty = ft.Text("Difficulty: --", size=10, color="#e3f2fd")
        self.lbl_blocks_mined = ft.Text("Blocks Mined: --", size=10, color="#e3f2fd")
        self.lbl_total_reward = ft.Text("Total Reward: --", size=10, color="#e3f2fd")
        self.lbl_connection = ft.Text("Connection: --", size=10, color="#e3f2fd")
        self.lbl_uptime = ft.Text("Uptime: --", size=10, color="#e3f2fd")
        
        node_status = ft.Container(
            content=ft.Column([
                ft.Text("🖥️ Node Status", size=14, color="#e3f2fd"),
                self.lbl_node_status,
                self.lbl_network_height,
                self.lbl_difficulty,
                self.lbl_blocks_mined,
                self.lbl_total_reward,
                self.lbl_connection,
                self.lbl_uptime,
            ], spacing=4),
            padding=10,
            bgcolor="#1a2b3c",
            border_radius=4,
            margin=5,
            width=sidebar_width - 30
        )
        
        # Quick actions - all blue buttons
        button_style = ft.ButtonStyle(
            color="#ffffff",
            bgcolor="#00a1ff",
            padding=ft.padding.symmetric(horizontal=16, vertical=6),
            shape=ft.RoundedRectangleBorder(radius=2)
        )
        
        self.btn_start_mining = ft.ElevatedButton(
            "⛏️ Start Mining",
            on_click=lambda e: self.start_mining(),
            style=button_style,
            height=32
        )
        
        self.btn_stop_mining = ft.ElevatedButton(
            "⏹️ Stop Mining",
            on_click=lambda e: self.stop_mining(),
            style=button_style,
            height=32,
            disabled=True
        )
        
        self.btn_sync = ft.ElevatedButton(
            "🔄 Sync Network",
            on_click=lambda e: self.sync_network(),
            style=button_style,
            height=32
        )
        
        self.btn_single_mine = ft.ElevatedButton(
            "⚡ Mine Single Block",
            on_click=lambda e: self.mine_single_block(),
            style=button_style,
            height=32
        )
        
        quick_actions = ft.Container(
            content=ft.Column([
                ft.Text("Quick Actions", size=14, color="#e3f2fd"),
                self.btn_start_mining,
                self.btn_stop_mining,
                self.btn_sync,
                self.btn_single_mine,
            ], spacing=8),
            padding=10,
            bgcolor="#1a2b3c",
            border_radius=4,
            margin=5,
            width=sidebar_width - 30
        )
        
        # Mining stats
        self.lbl_hash_rate = ft.Text("Hash Rate: --", size=12, color="#e3f2fd")
        self.lbl_current_hash = ft.Text("Current Hash: --", size=10, color="#e3f2fd")
        self.lbl_nonce = ft.Text("Nonce: --", size=10, color="#e3f2fd")
        self.progress_mining = ft.ProgressBar(
            visible=False,
            color="#00a1ff",
            bgcolor="#1e3a5c"
        )
        
        mining_stats = ft.Container(
            content=ft.Column([
                ft.Text("⛏️ Mining Stats", size=14, color="#e3f2fd"),
                self.lbl_hash_rate,
                self.lbl_current_hash,
                self.lbl_nonce,
                self.progress_mining
            ], spacing=6),
            padding=10,
            bgcolor="#1a2b3c",
            border_radius=4,
            margin=5,
            width=sidebar_width - 30
        )
        
        # Blue node icon at bottom (like wallet)
        app_icon = ft.Container(
            content=ft.Row([
                ft.Container(
                    content=ft.Image(
                        src="node_icon.svg",
                        width=64,
                        height=64,
                        fit=ft.ImageFit.CONTAIN,
                        color="#00a1ff",
                        color_blend_mode=ft.BlendMode.SRC_IN,
                        error_content=ft.Text("🔵", size=24)
                    ),
                    padding=10,
                    bgcolor="#00000000",
                    border_radius=4,
                )
            ], alignment=ft.MainAxisAlignment.CENTER),
            padding=10,
            margin=5,
            width=sidebar_width - 30
        )
        
        # Sidebar layout with menu and smaller header icon
        sidebar_content = ft.Column([
            ft.Container(
                content=ft.Row([
                    ft.PopupMenuButton(
                        content=ft.Text("☰", color="#e3f2fd", size=16),
                        tooltip="System Menu",
                        items=[
                            ft.PopupMenuItem(text="Restore", on_click=lambda e: self.restore_from_tray()),
                            ft.PopupMenuItem(text="Minimize to Tray", on_click=lambda e: self.minimize_to_tray()),
                            ft.PopupMenuItem(),
                            ft.PopupMenuItem(text="Start Mining", on_click=lambda e: self.start_mining()),
                            ft.PopupMenuItem(text="Stop Mining", on_click=lambda e: self.stop_mining()),
                            ft.PopupMenuItem(text="Sync Network", on_click=lambda e: self.sync_network()),
                            ft.PopupMenuItem(),
                            ft.PopupMenuItem(text="About", on_click=lambda e: self.show_about_dialog()),
                            ft.PopupMenuItem(text="Exit", on_click=lambda e: self.page.window.close()),
                        ]
                    ),
                    ft.Container(
                        content=ft.Image(
                            src="node_icon.svg",
                            width=32,
                            height=32,
                            fit=ft.ImageFit.CONTAIN,
                            color="#00a1ff",
                            color_blend_mode=ft.BlendMode.SRC_IN,
                            error_content=ft.Text("🔵", size=16)
                        ),
                        margin=ft.margin.only(right=8),
                    ),
                    ft.Text("Luna Node", size=24, color="#e3f2fd"),
                ]),
                width=sidebar_width - 30,
                bgcolor="transparent"
            ),
            ft.Divider(height=1, color="#1e3a5c"),
            node_status,
            ft.Divider(height=1, color="#1e3a5c"),
            quick_actions,
            mining_stats,
            ft.Container(expand=True),
            app_icon
        ], spacing=10, horizontal_alignment=ft.CrossAxisAlignment.CENTER)
        
        return ft.Container(
            content=sidebar_content,
            width=sidebar_width,
            padding=15,
            bgcolor="#0f1a2a"
        )
        
    def create_main_content(self):
        """Create the main content area with tabs"""
        mining_tab = self.create_mining_tab()
        settings_tab = self.create_settings_tab()
        history_tab = self.create_history_tab()
        log_tab = self.create_log_tab()
        
        tabs = ft.Tabs(
            selected_index=0,
            on_change=self.on_tab_change,
            tabs=[
                ft.Tab(text="⛏️ Mining", content=mining_tab),
                ft.Tab(text="⚙️ Settings", content=settings_tab),
                ft.Tab(text="📊 History", content=history_tab),
                ft.Tab(text="📋 Log", content=log_tab),
            ],
            expand=True,
            label_color="#00a1ff",
            unselected_label_color="#466994",
            indicator_color="#00a1ff"
        )
        
        return ft.Container(
            content=tabs,
            expand=True,
            padding=10,
            bgcolor="#1a2b3c"
        )
        
    def create_mining_tab(self):
        """Create mining progress tab"""
        self.mining_stats = ft.Column()
        
        return ft.Container(
            content=ft.Column([
                ft.Text("Mining Progress", size=16, color="#e3f2fd"),
                ft.Container(
                    content=self.mining_stats,
                    expand=True,
                    border=ft.border.all(1, "#1e3a5c"),
                    border_radius=3,
                    padding=10,
                    bgcolor="#0f1a2a"
                )
            ], expand=True),
            padding=10
        )
        
    def create_settings_tab(self):
        """Create settings tab"""
        self.settings_content = ft.Column()
        
        return ft.Container(
            content=ft.Column([
                ft.Text("Node Settings", size=16, color="#e3f2fd"),
                ft.Container(
                    content=self.settings_content,
                    expand=True,
                    border=ft.border.all(1, "#1e3a5c"),
                    border_radius=3,
                    padding=10,
                    bgcolor="#0f1a2a"
                )
            ], expand=True),
            padding=10
        )
        
    def create_history_tab(self):
        """Create mining history tab"""
        self.history_table = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("Date", color="#e3f2fd")),
                ft.DataColumn(ft.Text("Block", color="#e3f2fd")),
                ft.DataColumn(ft.Text("Time", color="#e3f2fd")),
                ft.DataColumn(ft.Text("Nonce", color="#e3f2fd")),
                ft.DataColumn(ft.Text("Status", color="#e3f2fd")),
            ],
            rows=[],
            vertical_lines=ft.BorderSide(1, "#1e3a5c"),
            horizontal_lines=ft.BorderSide(1, "#1e3a5c"),
            bgcolor="#0f1a2a",
        )
        
        return ft.Container(
            content=ft.Column([
                ft.Text("Mining History", size=16, color="#e3f2fd"),
                ft.Container(
                    content=ft.ListView([self.history_table], expand=True),
                    expand=True,
                    border=ft.border.all(1, "#1e3a5c"),
                    border_radius=3
                )
            ], expand=True),
            padding=10
        )
        
    def create_log_tab(self):
        """Create log tab"""
        clear_button = ft.ElevatedButton(
            "Clear Log",
            on_click=lambda e: self.clear_log(),
            style=ft.ButtonStyle(
                color="#ffffff",
                bgcolor="#00a1ff",
                padding=ft.padding.symmetric(horizontal=16, vertical=10),
                shape=ft.RoundedRectangleBorder(radius=3)
            ),
            height=38
        )
        
        self.log_output = ft.Column(scroll=ft.ScrollMode.ALWAYS)
        
        log_content = ft.Container(
            content=self.log_output,
            expand=True,
            border=ft.border.all(1, "#1e3a5c"),
            border_radius=3,
            padding=10,
            bgcolor="#0f1a2a"
        )
        
        return ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Text("Application Log", size=16, color="#e3f2fd"),
                    clear_button
                ]),
                ft.Container(
                    content=ft.ListView([log_content], expand=True),
                    expand=True
                )
            ], expand=True),
            padding=10
        )
        
    def on_tab_change(self, e):
        """Handle tab changes"""
        self.current_tab_index = e.control.selected_index
        if self.current_tab_index == 0:
            self.update_mining_stats()
        elif self.current_tab_index == 1:
            self.update_settings_content()
        elif self.current_tab_index == 2:
            self.update_history_content()
            
    def on_window_event(self, e):
        """Handle window events"""
        if e.data == "close":
            self.minimize_to_tray()
            return False
        return True
        
    def minimize_to_tray(self):
        """Minimize to system tray"""
        self.minimized_to_tray = True
        self.page.window.minimized = True
        self.page.window.visible = False
        self.page.update()
        self.show_snack_bar("Luna Node minimized to system tray")
        
    def restore_from_tray(self):
        """Restore from system tray"""
        self.minimized_to_tray = False
        self.page.window.visible = True
        self.page.window.minimized = False
        self.page.update()
        
    def show_snack_bar(self, message: str):
        """Show snack bar message"""
        snack_bar = ft.SnackBar(
            content=ft.Text(message),
            shape=ft.RoundedRectangleBorder(radius=3),
            bgcolor="#00a1ff"
        )
        self.page.overlay.append(snack_bar)
        snack_bar.open = True
        self.page.update()
        def remove_snack():
            time.sleep(3)
            self.page.overlay.remove(snack_bar)
            self.page.update()
        threading.Thread(target=remove_snack, daemon=True).start()
        
    def initialize_node_async(self):
        """Initialize node in background thread"""
        def init_thread():
            try:
                self.node = LunaNode(
                    log_callback=self.add_log_message,
                    new_bill_callback=lambda bill: self.add_log_message(f"New bill mined: {bill}", "success"),
                    new_reward_callback=lambda reward: self.add_log_message(f"New reward: {reward}", "success"),
                    history_updated_callback=self.update_history_content,
                    mining_started_callback=self.on_mining_started,
                    mining_completed_callback=self.on_mining_completed
                )
                
                self.page.run_thread(self.on_node_initialized)
                
            except Exception as e:
                error_msg = f"Node initialization failed: {str(e)}"
                print(error_msg)
                self.page.run_thread(lambda: self.add_log_message(error_msg, "error"))
        
        threading.Thread(target=init_thread, daemon=True).start()
        
    def on_mining_started(self):
        """Called when mining starts"""
        self.page.run_thread(lambda: self.add_log_message("Mining started", "info"))
        
    def on_mining_completed(self, success, message):
        """Called when mining completes"""
        msg_type = "success" if success else "warning"
        self.page.run_thread(lambda: self.add_log_message(message, msg_type))
        
    def on_node_initialized(self):
        """Called when node is successfully initialized"""
        self.add_log_message("Luna Node initialized successfully", "success")
        self.add_log_message("Loaded data from ./data/ directory", "info")
        self.update_status_display()
        self.update_settings_content()
        
        self.start_status_updates()
        
    def start_status_updates(self):
        """Start periodic status updates"""
        def update_loop():
            while self.node and self.node.is_running:
                try:
                    self.page.run_thread(self.update_status_display)
                    time.sleep(2)
                except Exception as e:
                    print(f"Status update error: {e}")
                    time.sleep(5)
        
        threading.Thread(target=update_loop, daemon=True).start()
        
    def update_status_display(self):
        """Update all status displays"""
        if not self.node:
            return
            
        status = self.node.get_status()
        
        # Update sidebar status
        self.lbl_node_status.value = f"Status: {'🟢 Running' if status['connection_status'] == 'connected' else '🟡 Disconnected'}"
        self.lbl_network_height.value = f"Network Height: {status['network_height']}"
        self.lbl_difficulty.value = f"Difficulty: {status['network_difficulty']}"
        self.lbl_blocks_mined.value = f"Blocks Mined: {status['blocks_mined']}"
        self.lbl_total_reward.value = f"Total Reward: {status['total_reward']:.2f} LUN"
        self.lbl_connection.value = f"Connection: {status['connection_status']}"
        
        uptime_seconds = int(status['uptime'])
        hours = uptime_seconds // 3600
        minutes = (uptime_seconds % 3600) // 60
        seconds = uptime_seconds % 60
        self.lbl_uptime.value = f"Uptime: {hours:02d}:{minutes:02d}:{seconds:02d}"
            
        # Update mining stats
        hash_rate = status['current_hash_rate']
        if hash_rate > 1000000:
            self.lbl_hash_rate.value = f"Hash Rate: {hash_rate/1000000:.2f} MH/s"
        elif hash_rate > 1000:
            self.lbl_hash_rate.value = f"Hash Rate: {hash_rate/1000:.2f} kH/s"
        else:
            self.lbl_hash_rate.value = f"Hash Rate: {hash_rate:.0f} H/s"
            
        current_hash = status['current_hash']
        if current_hash:
            short_hash = current_hash[:16] + "..." if len(current_hash) > 16 else current_hash
            self.lbl_current_hash.value = f"Current Hash: {short_hash}"
        else:
            self.lbl_current_hash.value = "Current Hash: --"
            
        self.lbl_nonce.value = f"Nonce: {status['current_nonce']}"
        
        # Update mining progress
        is_mining = self.node.miner.is_mining if self.node else False
        self.progress_mining.visible = is_mining
        
        # Update button states
        self.btn_start_mining.disabled = is_mining
        self.btn_stop_mining.disabled = not is_mining
        
        if self.current_tab_index == 0:
            self.update_mining_stats()
            
        self.page.update()
        
    def update_mining_stats(self):
        """Update mining statistics tab"""
        if not self.node:
            return
            
        status = self.node.get_status()
        
        self.mining_stats.controls.clear()
        
        stats_grid = ft.ResponsiveRow([
            self.create_stat_card("⛏️ Mining Status", 
                                "🟢 Active" if self.node.miner.is_mining else "🔴 Inactive",
                                "#00a1ff" if self.node.miner.is_mining else "#6c757d"),
            self.create_stat_card("📊 Total Blocks", str(status['blocks_mined']), "#00a1ff"),
            self.create_stat_card("💰 Total Reward", f"{status['total_reward']:.2f} LUN", "#00a1ff"),
            self.create_stat_card("⚡ Hash Rate", f"{status['current_hash_rate']:.0f} H/s", "#00a1ff"),
            self.create_stat_card("🎯 Success Rate", f"{status['success_rate']:.1f}%", "#00a1ff"),
            self.create_stat_card("⏱️ Avg Mining Time", f"{status['avg_mining_time']:.2f}s", "#00a1ff"),
        ])
        
        self.mining_stats.controls.append(stats_grid)
        
    def create_stat_card(self, title: str, value: str, color: str):
        """Create a statistics card"""
        return ft.Container(
            content=ft.Column([
                ft.Text(title, size=12, color="#e3f2fd"),
                ft.Text(value, size=16, weight=ft.FontWeight.BOLD, color=color),
            ], spacing=2),
            padding=15,
            margin=3,
            bgcolor="#0f1a2a",
            border=ft.border.all(1, "#1e3a5c"),
            border_radius=4,
            width=180,
            height=80,
            col={"xs": 6, "sm": 4, "md": 3}
        )
        
    def update_settings_content(self):
        """Update settings tab content"""
        if not self.node:
            return
            
        self.settings_content.controls.clear()
        
        wallet_field = ft.TextField(
            label="Miner Wallet Address",
            value=self.node.config.miner_address,
            on_change=lambda e: self.node.update_wallet_address(e.control.value),
            border_color="#1e3a5c",
            bgcolor="#0f1a2a",
            color="#e3f2fd"
        )
        
        difficulty_field = ft.TextField(
            label="Mining Difficulty",
            value=str(self.node.config.difficulty),
            on_change=lambda e: self.node.update_difficulty(int(e.control.value)) if e.control.value.isdigit() else None,
            border_color="#1e3a5c",
            bgcolor="#0f1a2a",
            color="#e3f2fd"
        )
        
        node_url_field = ft.TextField(
            label="Node URL",
            value=self.node.config.node_url,
            on_change=lambda e: self.node.update_node_url(e.control.value),
            border_color="#1e3a5c",
            bgcolor="#0f1a2a",
            color="#e3f2fd"
        )
        
        auto_mining_switch = ft.Switch(
            label="Auto Mining",
            value=self.node.config.auto_mine,
            on_change=lambda e: self.node.toggle_auto_mining(e.control.value),
            active_color="#00a1ff"
        )
        
        interval_field = ft.TextField(
            label="Mining Interval (seconds)",
            value=str(self.node.config.mining_interval),
            on_change=lambda e: self.node.update_mining_interval(int(e.control.value)) if e.control.value.isdigit() else None,
            border_color="#1e3a5c",
            bgcolor="#0f1a2a",
            color="#e3f2fd"
        )
        
        settings_form = ft.Column([
            ft.Text("Node Configuration", size=16, color="#e3f2fd"),
            wallet_field,
            difficulty_field,
            node_url_field,
            auto_mining_switch,
            interval_field,
            ft.Container(height=20),
            ft.ElevatedButton(
                "Save Settings",
                on_click=lambda e: self.save_settings(),
                style=ft.ButtonStyle(
                    color="#ffffff",
                    bgcolor="#00a1ff",
                    padding=ft.padding.symmetric(horizontal=20, vertical=12)
                )
            )
        ], spacing=12)
        
        self.settings_content.controls.append(settings_form)
        self.page.update()
        
    def update_history_content(self):
        """Update mining history tab"""
        if not self.node:
            return
            
        history = self.node.get_mining_history()
        
        self.history_table.rows.clear()
        
        for record in reversed(history[-50:]):
            timestamp = datetime.fromtimestamp(record['timestamp']).strftime("%Y-%m-%d %H:%M:%S")
            mining_time = f"{record.get('mining_time', 0):.2f}s"
            status_text = "✅" if record.get('status') == 'success' else "❌"
            status_color = "#28a745" if record.get('status') == 'success' else "#dc3545"
            
            row = ft.DataRow(cells=[
                ft.DataCell(ft.Text(timestamp, color="#e3f2fd")),
                ft.DataCell(ft.Text(f"#{record.get('block_index', 'N/A')}", color="#e3f2fd")),
                ft.DataCell(ft.Text(mining_time, color="#e3f2fd")),
                ft.DataCell(ft.Text(str(record.get('nonce', 0)), color="#e3f2fd")),
                ft.DataCell(ft.Text(status_text, color=status_color)),
            ])
            self.history_table.rows.append(row)
            
        self.page.update()
        
    def add_log_message(self, message: str, msg_type: str = "info"):
        """Add message to log"""
        color_map = {
            "info": "#17a2b8",
            "success": "#28a745", 
            "warning": "#ffc107",
            "error": "#dc3545"
        }
        
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = ft.Row([
            ft.Text(f"[{timestamp}]", size=10, color="#6c757d", width=70),
            ft.Text(message, size=12, color=color_map.get(msg_type, "#e3f2fd"), expand=True)
        ], spacing=5)
        
        self.log_output.controls.append(log_entry)
        
        if len(self.log_output.controls) > 1000:
            self.log_output.controls.pop(0)
            
        if self.current_tab_index == 3:
            self.page.update()
        
    def clear_log(self):
        """Clear log output"""
        self.log_output.controls.clear()
        self.page.update()
            
    def start_mining(self):
        """Start auto-mining"""
        if self.node:
            self.node.start_auto_mining()
            self.add_log_message("Auto-mining started", "info")
            
    def stop_mining(self):
        """Stop auto-mining"""
        if self.node:
            self.node.stop_auto_mining()
            self.add_log_message("Auto-mining stopped", "info")
            
    def mine_single_block(self):
        """Mine a single block"""
        if self.node:
            def mine_thread():
                success, message = self.node.mine_single_block()
                self.page.run_thread(lambda: self.add_log_message(message, "success" if success else "warning"))
                
            threading.Thread(target=mine_thread, daemon=True).start()
            
    def sync_network(self):
        """Sync with network with progress indicator"""
        if self.node:
            # Create progress dialog
            progress_bar = ft.ProgressBar(width=400, color="#00a1ff", bgcolor="#1e3a5c")
            progress_text = ft.Text("Starting sync...", color="#e3f2fd")
            
            progress_dialog = ft.AlertDialog(
                modal=True,
                title=ft.Text("Syncing Network", color="#e3f2fd"),
                content=ft.Column([
                    progress_text,
                    progress_bar
                ], tight=True),
                actions=[
                    ft.TextButton("Cancel", on_click=lambda e: self.close_progress_dialog(progress_dialog))
                ]
            )
            
            self.page.dialog = progress_dialog
            progress_dialog.open = True
            self.page.update()
            
            def sync_thread():
                def progress_callback(progress, message):
                    self.page.run_thread(lambda: self.update_progress(progress_bar, progress_text, progress, message))
                
                result = self.node.sync_network(progress_callback)
                
                self.page.run_thread(lambda: self.close_progress_dialog(progress_dialog))
                
                if 'error' in result:
                    self.page.run_thread(lambda: self.add_log_message(f"Sync failed: {result['error']}", "error"))
                else:
                    self.page.run_thread(lambda: self.add_log_message("Network sync completed", "success"))
                    
            threading.Thread(target=sync_thread, daemon=True).start()
            
    def update_progress(self, progress_bar, progress_text, progress, message):
        """Update progress dialog"""
        progress_bar.value = progress / 100
        progress_text.value = message
        self.page.update()
        
    def close_progress_dialog(self, dialog):
        """Close progress dialog"""
        dialog.open = False
        self.page.update()
            
    def save_settings(self):
        """Save all settings"""
        self.add_log_message("Settings saved to ./data/settings.json", "success")
        self.show_snack_bar("Settings saved successfully")
        
    def show_about_dialog(self):
        """Show about dialog using sliding overlay"""
        overlay_container = ft.Container(
            width=self.page.width - 240,
            height=self.page.height,
            left=240,
            top=0,
            bgcolor="#0f1a2a",
            border=ft.border.only(left=ft.BorderSide(4, "#1e3a5c")),
            animate_position=ft.Animation(300, "easeOut"),
            padding=20,
        )
        
        def close_dialog(e):
            overlay_container.left = self.page.width
            self.page.update()
            time.sleep(0.3)
            self.page.overlay.remove(overlay_container)
            self.page.update()
        
        dialog_content = ft.Column([
            ft.Row([
                ft.Container(
                    content=ft.Image(
                        src="node_icon.svg",
                        width=32,
                        height=32,
                        fit=ft.ImageFit.CONTAIN,
                        color="#00a1ff",
                        color_blend_mode=ft.BlendMode.SRC_IN,
                        error_content=ft.Text("🔵", size=20)
                    ),
                    margin=ft.margin.only(right=12),
                ),
                ft.Text("About Luna Node", size=24, color="#00a1ff", weight="bold"),
            ], alignment=ft.MainAxisAlignment.START),
            ft.Container(height=30),
            ft.Text("Luna Node Miner", size=18, color="#e3f2fd"),
            ft.Text("Version 1.0", size=14, color="#e3f2fd"),
            ft.Text("A lightweight blockchain node for Luna Network", size=14, color="#e3f2fd"),
            ft.Text("Optimized for fast startup and low memory usage", size=12, color="#e3f2fd"),
            ft.Container(height=20),
            ft.Text("Features:", size=16, color="#e3f2fd", weight="bold"),
            ft.Text("• Fast blockchain synchronization", size=12, color="#e3f2fd"),
            ft.Text("• Optimized memory usage", size=12, color="#e3f2fd"),
            ft.Text("• Real-time mining statistics", size=12, color="#e3f2fd"),
            ft.Text("• System tray integration", size=12, color="#e3f2fd"),
            ft.Text("• Data persistence in ./data/ directory", size=12, color="#e3f2fd"),
            ft.Container(height=40),
            ft.ElevatedButton(
                "Close",
                on_click=close_dialog,
                style=ft.ButtonStyle(
                    color="#ffffff",
                    bgcolor="#00a1ff",
                    padding=ft.padding.symmetric(horizontal=20, vertical=12),
                    shape=ft.RoundedRectangleBorder(radius=4)
                )
            )
        ], scroll=ft.ScrollMode.ADAPTIVE, horizontal_alignment=ft.CrossAxisAlignment.CENTER)
        
        overlay_container.content = dialog_content
        self.page.overlay.append(overlay_container)
        self.page.update()


def main(page: ft.Page):
    """Main application entry point"""
    try:
        app = LunaNodeApp()
        app.create_main_ui(page)
    except Exception as e:
        error_dialog = ft.AlertDialog(
            title=ft.Text("Application Error"),
            content=ft.Text(f"Failed to initialize Luna Node:\n{str(e)}"),
            actions=[
                ft.TextButton("Exit", on_click=lambda e: page.window.close())
            ]
        )
        page.dialog = error_dialog
        error_dialog.open = True
        page.update()


if __name__ == "__main__":
    ft.app(target=main)