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
from lunalib.core.blockchain import BlockchainManager
from lunalib.core.crypto import KeyManager
from lunalib.core.wallet import LunaWallet
from lunalib.storage.cache import BlockchainCache
from lunalib.storage.database import WalletDatabase
from lunalib.storage.encryption import EncryptionManager
from lunalib.mining.difficulty import DifficultySystem
from lunalib.mining.cuda_manager import CUDAManager
from lunalib.gtx.digital_bill import DigitalBill

from utils import LunaNode
from gui.sidebar import Sidebar
from gui.main_page import MainPage
from gui.mining_history import MiningHistory
from gui.bills import BillsPage
from gui.log import LogPage
from gui.settings import SettingsPage
class LunaNodeApp:
    """Luna Node Application with Blue Theme"""
    
    def __init__(self):
        self.node = None
        self.minimized_to_tray = False
        self.current_tab_index = 0
        self.page = None
        
        # Initialize GUI components
        self.sidebar = Sidebar(self)
        self.main_page = MainPage(self)
        self.mining_history = MiningHistory(self)
        self.bills_page = BillsPage(self)
        self.settings_page = SettingsPage(self)  # Add this line
        self.log_page = LogPage(self)
    def submit_mined_block(self, block_data: Dict) -> bool:
        """Submit a mined block directly to the network"""
        try:
            import requests
            import json
            
            # Submit to the node URL
            node_url = self.endpoint_url if hasattr(self, 'endpoint_url') else "https://bank.linglin.art"
            
            # Prepare the submission payload
            submission_data = {
                'block': block_data,
                'miner_address': getattr(self, 'miner_address', 'unknown'),
                'timestamp': time.time()
            }
            
            # Send to node API
            response = requests.post(
                f"{node_url}/api/blocks/submit",
                json=submission_data,
                headers={'Content-Type': 'application/json'},
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get('success'):
                    print(f"✅ Block #{block_data.get('index')} submitted successfully")
                    return True
                else:
                    print(f"❌ Block submission rejected: {result.get('message', 'Unknown error')}")
                    return False
            else:
                print(f"❌ HTTP error {response.status_code}: {response.text}")
                return False
                
        except requests.exceptions.RequestException as e:
            print(f"❌ Network error submitting block: {e}")
            return False
        except Exception as e:
            print(f"💥 Error submitting block: {e}")
            return False
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
            font_family="Custom",
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
        sidebar = self.sidebar.create_sidebar()
        main_content = self.create_main_content()
        
        return ft.Row(
            [sidebar, ft.VerticalDivider(width=1, color="#1e3a5c"), main_content],
            expand=True,
            spacing=0
        )
        
    def create_main_content(self):
        """Create the main content area with tabs"""
        tabs = ft.Tabs(
            selected_index=0,
            on_change=self.on_tab_change,
            tabs=[
                ft.Tab(text="⛏️ Mining", content=self.main_page.create_mining_tab()),
                ft.Tab(text="💰 Bills", content=self.bills_page.create_bills_tab()),
                ft.Tab(text="📊 Stats", content=self.mining_history.create_history_tab()),
                ft.Tab(text="⚙️ Settings", content=self.settings_page.create_settings_tab()),
                ft.Tab(text="📋 Log", content=self.log_page.create_log_tab()),
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
        
    def on_tab_change(self, e):
        """Handle tab changes"""
        self.current_tab_index = e.control.selected_index
        if self.current_tab_index == 0:
            self.main_page.update_mining_stats()
        elif self.current_tab_index == 1:
            self.bills_page.update_bills_content()
        elif self.current_tab_index == 2:
            self.mining_history.update_history_content()
        elif self.current_tab_index == 3:  # Settings tab
            self.settings_page.update_settings_content()
            
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
        # Remove this line: self.main_page.update_settings_content()  # This causes the AttributeError
        
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
        
        # Update sidebar
        self.sidebar.update_status(status)
            
        # Update mining progress
        is_mining = self.node.miner.is_mining if self.node else False
        
        if self.current_tab_index == 0:
            self.main_page.update_mining_stats()
            
        self.page.update()
        
    def add_log_message(self, message: str, msg_type: str = "info"):
        """Add message to log"""
        self.log_page.add_log_message(message, msg_type)
        
    def clear_log(self):
        """Clear log output"""
        self.log_page.clear_log()
            
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
        
    def update_history_content(self):
        """Update history content"""
        self.mining_history.update_history_content()
        
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