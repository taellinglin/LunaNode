import hashlib
import json
import os
import threading
import time
from datetime import datetime
from typing import Dict, List, Optional, Tuple

# Import lunalib components
try:
    from lunalib.core.blockchain import BlockchainManager
    from lunalib.mining.difficulty import DifficultySystem
    from lunalib.mining.cuda_manager import CUDAManager
    LUNA_LIB_AVAILABLE = True
except ImportError as e:
    print(f"LunaLib import error: {e}")
    LUNA_LIB_AVAILABLE = False

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

class Miner:
    """Miner class that uses lunalib directly"""
    
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
        
        self.mining_history = self.data_manager.load_mining_history()
        
        # Use lunalib directly
        self.blockchain_manager = BlockchainManager(endpoint_url=config.node_url)
        self.difficulty_system = DifficultySystem() if LUNA_LIB_AVAILABLE else None
        self.cuda_manager = CUDAManager() if LUNA_LIB_AVAILABLE else None
        
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
    
    def _calculate_block_reward(self, transactions: List[Dict]) -> float:
        """Calculate total reward based on transactions in the block using lunalib"""
        total_reward = 0.0
        
        for tx in transactions:
            if tx.get('type') == 'genesis_bill':
                # GTX Genesis bill - use lunalib to calculate reward
                denomination = tx.get('denomination', 0)
                if self.difficulty_system:
                    # Get difficulty for this bill
                    bill_difficulty = self.difficulty_system.get_bill_difficulty(denomination)
                    # Use average mining time for reward calculation (will be updated with actual time)
                    avg_mining_time = 15.0
                    bill_reward = self.difficulty_system.calculate_mining_reward(denomination, avg_mining_time)
                    total_reward += bill_reward
                    print(f"GTX Genesis bill reward: {bill_reward} (denomination: {denomination}, difficulty: {bill_difficulty})")
                else:
                    total_reward += denomination
                
            elif tx.get('type') == 'transaction':
                # Regular transaction - reward is the fee
                fee = tx.get('fee', 0)
                total_reward += fee
                print(f"Transaction fee reward: {fee}")
            elif tx.get('type') == 'reward':
                # Already a reward transaction, just track it
                reward_amount = tx.get('amount', 0)
                total_reward += reward_amount
                print(f"Included reward transaction: {reward_amount}")
        
        # Minimum reward for empty blocks
        if total_reward == 0:
            total_reward = 1.0  # Base reward for empty block
            
        return total_reward
    
    def _calculate_block_difficulty(self, transactions: List[Dict]) -> int:
        """Calculate overall block difficulty based on transactions using lunalib"""
        if not transactions:
            return self.config.difficulty
            
        max_difficulty = self.config.difficulty
        
        for tx in transactions:
            if tx.get('type') == 'genesis_bill':
                denomination = tx.get('denomination', 0)
                # Use lunalib's bill difficulty calculation - 9 tier system
                tx_difficulty = self.difficulty_system.get_bill_difficulty(denomination) if self.difficulty_system else self.config.difficulty
                max_difficulty = max(max_difficulty, tx_difficulty)
                
            elif tx.get('type') == 'transaction':
                amount = tx.get('amount', 0)
                # Use lunalib's transaction difficulty calculation - 9 tier system
                tx_difficulty = self.difficulty_system.get_transaction_difficulty(amount) if self.difficulty_system else self.config.difficulty
                max_difficulty = max(max_difficulty, tx_difficulty)
            elif tx.get('type') == 'reward':
                # Reward transactions have minimal difficulty
                max_difficulty = max(max_difficulty, 1)
        
        # Ensure difficulty is at least the configured minimum
        return max(max_difficulty, self.config.difficulty)
    
    def mine_block(self) -> Tuple[bool, str, Optional[Dict]]:
        """Mine a block using lunalib directly - FIXED SYNC"""
        try:
            # Get the ACTUAL latest block from server
            latest_block = self.blockchain_manager.get_latest_block()
            
            if not latest_block:
                print("❌ Could not get latest block from server")
                return False, "Server connection failed", None
            
            # Get the actual current state from the latest block
            current_index = latest_block.get('index', 0)
            actual_previous_hash = latest_block.get('hash', '0' * 64)
            
            print(f"📊 Server state: Latest block index: {current_index}")
            print(f"📊 Latest block hash: {actual_previous_hash[:32]}...")
            
            # Next block should be current_index + 1
            new_index = current_index + 1
            print(f"⛏️  Mining next block at index: {new_index}")
            print(f"🔗 Using previous hash: {actual_previous_hash[:32]}...")
            
            # Get mempool transactions
            mempool = self.blockchain_manager.get_mempool()
            print(f"📦 Mempool has {len(mempool)} transactions available")
            
            # If no transactions in mempool, create at least one reward transaction
            if not mempool:
                print("⚠️  Mempool is empty, creating reward transaction")
                reward_tx = {
                    'type': 'reward',
                    'from': 'network',
                    'to': self.config.miner_address,
                    'amount': 1.0,
                    'timestamp': time.time(),
                    'block_height': new_index,
                    'hash': f"reward_{new_index}_{int(time.time())}",
                    'description': 'Empty block mining reward'
                }
                mempool = [reward_tx]
            
            # Calculate block difficulty and reward
            block_difficulty = self._calculate_block_difficulty(mempool)
            total_reward = self._calculate_block_reward(mempool)
            
            print(f"⛏️ Mining block #{new_index} with {len(mempool)} transactions")
            print(f"   Difficulty: {block_difficulty}, Reward: {total_reward}")
            
            # Create block data with CORRECT sync data
            block_data = {
                'index': new_index,  # This should match server's expected next index
                'previous_hash': actual_previous_hash,  # This MUST match server's latest block hash
                'timestamp': time.time(),
                'transactions': mempool,
                'miner': self.config.miner_address,
                'difficulty': block_difficulty,
                'nonce': 0,
                'reward': total_reward,
                'hash': ''
            }
            
            # Try CUDA mining first if available
            if self.cuda_manager and self.cuda_manager.cuda_available:
                print("Attempting CUDA mining with lunalib...")
                try:
                    cuda_result = self.cuda_manager.cuda_mine_batch(
                        block_data, block_difficulty, batch_size=100000
                    )
                    if cuda_result and cuda_result.get('success'):
                        # Process successful CUDA mining result
                        block_data['hash'] = cuda_result['hash']
                        block_data['nonce'] = cuda_result['nonce']
                        
                        mining_record = {
                            'block_index': new_index,
                            'timestamp': time.time(),
                            'mining_time': cuda_result['mining_time'],
                            'difficulty': block_difficulty,
                            'nonce': cuda_result['nonce'],
                            'hash': cuda_result['hash'],
                            'method': 'cuda',
                            'reward': total_reward,
                            'status': 'success'
                        }
                        self.mining_history.append(mining_record)
                        self.save_mining_history()
                        
                        self.blocks_mined += 1
                        self.total_reward += total_reward
                        
                        if self.mining_completed_callback:
                            self.mining_completed_callback(True, f"Block #{new_index} mined with CUDA - Reward: {total_reward}")
                        
                        if self.block_mined_callback:
                            self.block_mined_callback(block_data)
                        
                        return True, f"Block #{new_index} mined with CUDA - Reward: {total_reward}", block_data
                    else:
                        print(f"CUDA mining returned no result or failed")
                        
                except Exception as cuda_error:
                    print(f"CUDA mining failed: {cuda_error}")
            
            # Fallback to CPU mining - USE SERVER'S HASH CALCULATION
            print("Using CPU mining...")
            start_time = time.time()
            target = "0" * block_difficulty
            nonce = 0
            hash_count = 0
            last_hash_update = start_time
            
            while not self.should_stop_mining and nonce < 1000000:
                # Use the SAME hash calculation as the server
                block_hash = self.calculate_block_hash(
                    new_index,
                    actual_previous_hash,  # USE THE CORRECT PREVIOUS HASH
                    block_data['timestamp'],
                    mempool,
                    nonce
                )
                
                if block_hash.startswith(target):
                    mining_time = time.time() - start_time
                    
                    # Add hash to block data
                    block_data['hash'] = block_hash
                    block_data['nonce'] = nonce
                    
                    # Record mining history
                    mining_record = {
                        'block_index': new_index,
                        'timestamp': time.time(),
                        'mining_time': mining_time,
                        'difficulty': block_difficulty,
                        'nonce': nonce,
                        'hash': block_hash,
                        'method': 'cpu',
                        'reward': total_reward,
                        'status': 'success'
                    }
                    self.mining_history.append(mining_record)
                    self.save_mining_history()
                    
                    self.blocks_mined += 1
                    self.total_reward += total_reward
                    
                    if self.mining_completed_callback:
                        self.mining_completed_callback(True, f"Block #{new_index} mined successfully - Reward: {total_reward}")
                    
                    if self.block_mined_callback:
                        self.block_mined_callback(block_data)
                    
                    return True, f"Block #{new_index} mined - Reward: {total_reward}", block_data
                
                nonce += 1
                hash_count += 1
                self.current_nonce = nonce
                self.current_hash = block_hash
                
                # Update hash rate
                current_time = time.time()
                if current_time - last_hash_update >= 1:
                    self.hash_rate = hash_count / (current_time - last_hash_update)
                    hash_count = 0
                    last_hash_update = current_time
                
                if nonce % 1000 == 0 and not self.is_mining:
                    return False, "Mining interrupted", None
            
            return False, "Mining timeout - no solution found", None
                
        except Exception as e:
            error_msg = f"Mining error: {str(e)}"
            print(f"DEBUG Mining Error: {error_msg}")
            return False, error_msg, None
    def _prepare_cuda_mining_data(self, block_data):
        """Prepare block data for CUDA mining by ensuring proper data types"""
        try:
            # Create a simplified version for CUDA
            cuda_data = {
                'index': int(block_data['index']),
                'previous_hash': str(block_data['previous_hash']),
                'timestamp': float(block_data['timestamp']),
                'miner': str(block_data['miner']),
                'difficulty': int(block_data['difficulty']),
                'nonce': int(block_data['nonce']),
                'reward': float(block_data['reward'])
            }
            
            # Limit transaction data for CUDA to avoid string dtype issues
            transactions = block_data.get('transactions', [])
            cuda_data['transactions_count'] = len(transactions)
            
            # Only include essential transaction data
            simplified_txs = []
            for tx in transactions[:10]:  # Limit to first 10 transactions for CUDA
                simple_tx = {
                    'type': str(tx.get('type', '')),
                    'amount': float(tx.get('amount', 0)),
                    'timestamp': float(tx.get('timestamp', 0))
                }
                simplified_txs.append(simple_tx)
            
            cuda_data['transactions'] = simplified_txs
            return cuda_data
            
        except Exception as e:
            print(f"Error preparing CUDA data: {e}")
            return block_data  # Fallback to original data
    def _calculate_final_reward(self, transactions: List[Dict], actual_mining_time: float) -> float:
        """Calculate final reward using actual mining time"""
        total_reward = 0.0
        
        for tx in transactions:
            if tx.get('type') == 'genesis_bill':
                denomination = tx.get('denomination', 0)
                if self.difficulty_system:
                    bill_reward = self.difficulty_system.calculate_mining_reward(denomination, actual_mining_time)
                    total_reward += bill_reward
                else:
                    total_reward += denomination
            elif tx.get('type') == 'transaction':
                total_reward += tx.get('fee', 0)
            elif tx.get('type') == 'reward':
                total_reward += tx.get('amount', 0)
        
        # Minimum reward for empty blocks
        if total_reward == 0:
            total_reward = 1.0
            
        return total_reward

    def calculate_block_hash(self, index, previous_hash, timestamp, transactions, nonce):
        """Calculate block hash using the SAME method as the server"""
        import json
        block_string = f"{index}{previous_hash}{timestamp}{json.dumps(transactions, sort_keys=True)}{nonce}"
        return hashlib.sha256(block_string.encode()).hexdigest()

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
        """Get node status"""
        try:
            current_height = self.miner.blockchain_manager.get_blockchain_height()
            latest_block = self.miner.blockchain_manager.get_block(current_height) if current_height > 0 else None
            
            total_mining_time = sum(record.get('mining_time', 0) for record in self.miner.mining_history)
            avg_mining_time = total_mining_time / len(self.miner.mining_history) if self.miner.mining_history else 0
            
            # Check CUDA status
            cuda_available = self.miner.cuda_manager.cuda_available if self.miner.cuda_manager else False
            
            return {
                'network_height': current_height,
                'network_difficulty': latest_block.get('difficulty', 1) if latest_block else 1,
                'previous_hash': latest_block.get('hash', '0' * 64) if latest_block else '0' * 64,
                'miner_address': self.config.miner_address,
                'blocks_mined': self.miner.blocks_mined,
                'auto_mining': self.miner.is_mining,
                'configured_difficulty': self.config.difficulty,
                'total_reward': self.miner.total_reward,
                'total_transactions': len(self.miner.blockchain_manager.get_mempool()),
                'reward_transactions': self.miner.blocks_mined,
                'connection_status': 'connected' if current_height >= 0 else 'disconnected',
                'uptime': time.time() - self.stats['start_time'],
                'total_mining_attempts': len(self.miner.mining_history),
                'success_rate': (self.stats['successful_blocks'] / len(self.miner.mining_history)) * 100 if self.miner.mining_history else 0,
                'avg_mining_time': avg_mining_time,
                'current_hash_rate': self.miner.hash_rate,
                'current_hash': self.miner.current_hash,
                'current_nonce': self.miner.current_nonce,
                'cuda_available': cuda_available,
                'mining_method': 'CUDA' if cuda_available else 'CPU'
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
                'cuda_available': False,
                'mining_method': 'CPU',
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
        """Sync with network"""
        try:
            if progress_callback:
                progress_callback(0, "Starting network sync...")
            
            # Simple sync - just get current status
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
        """Submit mined block to network"""
        try:
            # FIX: Use submit_mined_block instead of broadcast_block
            success = self.miner.blockchain_manager.submit_mined_block(block_data)
            
            if success:
                self._log_message(f"Block #{block_data['index']} submitted successfully!", "success")
                return True
            else:
                self._log_message(f"Block #{block_data['index']} submission failed", "warning")
                return self._save_block_locally(block_data)
            
        except Exception as e:
            error_msg = f"Block submission error: {str(e)}"
            self._log_message(error_msg, "error")
            return self._save_block_locally(block_data)
    
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
        self._log_message(f"Difficulty updated to: {new_difficulty}", "info")
    
    def update_node_url(self, new_url: str):
        """Update node URL"""
        self.config.node_url = new_url
        self.config.save_to_storage()
        # Reinitialize blockchain manager with new URL
        self.miner.blockchain_manager = BlockchainManager(endpoint_url=new_url)
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