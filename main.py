import threading
import time
import os
import json
import shutil
from datetime import datetime
import base64
from typing import Dict, List, Optional, Tuple
import sqlite3
from pathlib import Path
import certifi
import PIL
import sys
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
# Lunalib backend selection (SM2). Use env override if provided.
os.environ.setdefault("LUNALIB_SM2_BACKEND", "phos")
os.environ.setdefault("LUNALIB_MINING_HASH_MODE", "compact")
os.environ.setdefault("LUNALIB_BLOCK_REWARD_MODE", "linear")
os.environ.setdefault("LUNALIB_CUDA_SM3", "1")

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
    os.environ.setdefault("LUNANODE_FAST_STARTUP", "1")
    os.environ.setdefault("LUNANODE_STARTUP_SYNC_DELAY", "30")
    os.environ.setdefault("LUNANODE_DISABLE_GPU_INIT", "0")
os.environ.setdefault("REQUESTS_CA_BUNDLE", certifi.where())
os.environ.setdefault("SSL_CERT_FILE", certifi.where())

def _ensure_cuda_env():
    """Best-effort CUDA env normalization for packaged builds."""
    try:
        if os.name != "nt":
            return

        if "CUDA_VISIBLE_DEVICES" in os.environ and not os.environ.get("CUDA_VISIBLE_DEVICES"):
            os.environ.pop("CUDA_VISIBLE_DEVICES", None)
        os.environ.setdefault("CUDA_VISIBLE_DEVICES", "0")

        cuda_path = os.environ.get("CUDA_PATH")
        if not cuda_path:
            candidates = [
                r"C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.4",
                r"C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.3",
                r"C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.2",
                r"C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.1",
                r"C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.0",
                r"C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v11.8",
                r"C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v11.7",
                r"C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v11.6",
                r"C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v10.2",
            ]
            for candidate in candidates:
                if os.path.isdir(candidate):
                    cuda_path = candidate
                    os.environ["CUDA_PATH"] = candidate
                    break

        if cuda_path:
            cuda_bin = os.path.join(cuda_path, "bin")
            current_path = os.environ.get("PATH", "")
            if cuda_bin and cuda_bin not in current_path:
                os.environ["PATH"] = cuda_bin + os.pathsep + current_path
    except Exception:
        pass

_ensure_cuda_env()

# Preconfigure data dirs to avoid MissingPlatformDirectoryException on Linux
if sys.platform != "emscripten":
    if os.name != "nt":
        os.environ.setdefault("HOME", os.path.expanduser("~"))
    if os.name == "nt":
        base_data = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local")) / "LunaNode"
    else:
        base_data = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share")) / "LunaNode"
    try:
        base_data.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass
    os.environ.setdefault("LUNALIB_DATA_DIR", str(base_data))
    os.environ.setdefault("XDG_DATA_HOME", str(base_data))
    os.environ.setdefault("XDG_CONFIG_HOME", str(base_data))
    os.environ.setdefault("XDG_CACHE_HOME", str(base_data))
    os.environ.setdefault("XDG_DOCUMENTS_DIR", str(base_data))

import flet as ft

from utils import DataManager, NodeConfig, is_valid_luna_address, log_mining_debug_event

# Import unified balance utilities (if needed)
from utils import LunaNode

try:
    log_mining_debug_event(
        "app_start",
        {
            "frozen": bool(getattr(sys, "frozen", False)),
            "frozen_like": _is_frozen_like(),
            "executable": sys.executable,
            "meipass": getattr(sys, "_MEIPASS", None),
        },
        scope="app",
    )
except Exception:
    pass

# Ensure cache directory exists
if sys.platform == "emscripten":
    cache_dir = Path("/home/pyodide/.lunalib/cache")
else:
    if os.name == "nt":
        base_cache = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    else:
        base_cache = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache"))
    cache_dir = base_cache / "lunalib" / "cache"
cache_dir.mkdir(parents=True, exist_ok=True)
os.environ["LUNALIB_CACHE_DIR"] = str(cache_dir)

# Patch lunalib data dir for Pyodide (package path is read-only)
if sys.platform == "emscripten":
    try:
        from lunalib.storage.cache import SecureDataManager as _LunaSecureDataManager
        from lunalib.storage.cache import BlockchainCache as _LunaBlockchainCache

        _pyodide_base_dir = cache_dir.parent

        def _pyodide_data_dir():
            _pyodide_base_dir.mkdir(parents=True, exist_ok=True)
            return str(_pyodide_base_dir)

        _LunaSecureDataManager.get_data_dir = staticmethod(_pyodide_data_dir)

        _orig_cache_init = _LunaBlockchainCache.__init__

        def _patched_cache_init(self, cache_dir_override=None):
            if cache_dir_override is None:
                cache_dir_override = str(cache_dir)
            Path(cache_dir_override).mkdir(parents=True, exist_ok=True)
            _orig_cache_init(self, cache_dir=cache_dir_override)

        _LunaBlockchainCache.__init__ = _patched_cache_init
    except Exception:
        pass

# Import lunalib after cache setup
# Import GUI modules
from gui.sidebar import Sidebar
from gui.main_page import MainPage
from gui.history import MiningHistory
from gui.bills import BillsPage
from gui.log import LogPage
from gui.settings import SettingsPage

# Import lunalib after cache setup
import lunalib

def resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller bundle."""
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

class LunaNodeApp:
    def show_first_boot_wizard(self):
        if not self.page or not self.node:
            return

        config = self.node.config

        wallet_field = ft.TextField(label="Wallet Address", value=getattr(config, "miner_address", ""), width=420)
        node_url_field = ft.TextField(label="Node Endpoint", value=getattr(config, "node_url", "https://bank.linglin.art"), width=420)
        difficulty_field = ft.TextField(label="Mining Difficulty", value=str(getattr(config, "difficulty", 2)), width=180)
        mining_interval_field = ft.TextField(label="Mining Interval (seconds)", value=str(getattr(config, "mining_interval", 30)), width=220)
        auto_mine_switch = ft.Switch(label="Auto Mining", value=getattr(config, "auto_mine", False))
        gpu_switch = ft.Switch(label="GPU Acceleration", value=getattr(config, "use_gpu", False))
        error_text = ft.Text("", color="#ff5252", size=12)

        steps = []

        def step_wallet():
            return ft.Column([
                ft.Text("Step 1 of 3: Wallet"),
                wallet_field,
                error_text,
            ], tight=True, spacing=10)

        def step_network():
            return ft.Column([
                ft.Text("Step 2 of 3: Network"),
                node_url_field,
            ], tight=True, spacing=10)

        def step_mining():
            return ft.Column([
                ft.Text("Step 3 of 3: Mining"),
                ft.Row([difficulty_field, mining_interval_field]),
                ft.Row([auto_mine_switch, gpu_switch]),
            ], tight=True, spacing=10)

        steps[:] = [step_wallet, step_network, step_mining]
        step_index = {"value": 0}

        content = ft.Column([], tight=True, spacing=10)

        def render_step():
            content.controls.clear()
            content.controls.append(steps[step_index["value"]]())
            dialog.title = ft.Text("First-time Setup")
            prev_btn.disabled = step_index["value"] == 0
            next_btn.visible = step_index["value"] < len(steps) - 1
            finish_btn.visible = step_index["value"] == len(steps) - 1
            self.page.update()

        def go_next(_):
            if step_index["value"] == 0:
                value = (wallet_field.value or "").strip()
                if not is_valid_luna_address(value):
                    error_text.value = "Invalid address format. Use LUN_..."
                    self.page.update()
                    return
                error_text.value = ""
            step_index["value"] += 1
            render_step()

        def go_prev(_):
            step_index["value"] = max(0, step_index["value"] - 1)
            render_step()

        def finish(_):
            value = (wallet_field.value or "").strip()
            if not is_valid_luna_address(value):
                error_text.value = "Invalid address format. Use LUN_..."
                self.page.update()
                return

            config.miner_address = value
            config.node_url = (node_url_field.value or "").strip() or config.node_url
            try:
                config.difficulty = int(difficulty_field.value or config.difficulty)
            except Exception:
                pass
            try:
                config.mining_interval = int(mining_interval_field.value or config.mining_interval)
            except Exception:
                pass
            config.auto_mine = bool(auto_mine_switch.value)
            config.use_gpu = bool(gpu_switch.value)
            config.setup_complete = True
            config.save_to_storage()

            dialog.open = False
            self.page.update()

            if config.auto_mine:
                threading.Thread(target=self.start_mining, daemon=True).start()

        prev_btn = ft.TextButton("Back", on_click=go_prev)
        next_btn = ft.TextButton("Next", on_click=go_next)
        finish_btn = ft.TextButton("Finish", on_click=finish)

        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("First-time Setup"),
            content=content,
            actions=[prev_btn, next_btn, finish_btn],
            actions_alignment=ft.MainAxisAlignment.END,
        )

        self.page.dialog = dialog
        dialog.open = True
        render_step()

    def show_address_setup_dialog(self):
        """Prompt for a valid wallet address on startup."""
        if not self.page or not self.node:
            return

        address_field = ft.TextField(
            label="Wallet Address",
            hint_text="LUN_...",
            width=420,
        )
        error_text = ft.Text("", color="#ff5252", size=12)

        def save_address(_):
            value = (address_field.value or "").strip()
            if not is_valid_luna_address(value):
                error_text.value = "Invalid address format. Use LUN_..."
                self.page.update()
                return
            self.node.config.miner_address = value
            self.node.config.save_to_storage()
            dialog.open = False
            self.page.update()
            self.add_log_message("Wallet address updated", "success")
            threading.Thread(target=self.start_mining, daemon=True).start()

        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Set Wallet Address"),
            content=ft.Column([
                ft.Text("Please enter a valid LUN_ wallet address to enable mining."),
                address_field,
                error_text,
            ], tight=True),
            actions=[
                ft.TextButton("Save", on_click=save_address),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )

        self.page.dialog = dialog
        dialog.open = True
        self.page.update()

    def _set_mining_ui_state(self, is_mining: bool, pending: bool = False, status_text: str = None):
        if hasattr(self, "main_page") and self.main_page:
            try:
                if pending:
                    if hasattr(self.main_page, "cpu_toggle_btn"):
                        self.main_page.cpu_toggle_btn.disabled = True
                    if hasattr(self.main_page, "gpu_toggle_btn"):
                        self.main_page.gpu_toggle_btn.disabled = True
                    if status_text:
                        self.main_page.mining_status.content.controls[1].value = status_text
                else:
                    if status_text:
                        self.main_page.mining_status.content.controls[1].value = status_text
            except Exception:
                pass

        if hasattr(self, "sidebar") and self.sidebar:
            try:
                if pending:
                    if hasattr(self.sidebar, "btn_cpu_mining"):
                        self.sidebar.btn_cpu_mining.disabled = True
                    if hasattr(self.sidebar, "btn_gpu_mining"):
                        self.sidebar.btn_gpu_mining.disabled = True
            except Exception:
                pass

        if self.page:
            try:
                self.page.update()
            except Exception:
                pass

    def on_mining_started(self):
        """Called when mining starts"""
        self.safe_run_thread(lambda: self.add_log_message("Mining started", "info"))

    def start_mining(self):
        """Start auto-mining"""
        if getattr(self, "_mining_transition", False):
            return
        self.add_log_message("Start Mining clicked", "info")
        if not self.node:
            self.add_log_message("Node is still initializing. Please wait...", "warning")
            if self.page:
                self.safe_run_thread(lambda: self._set_mining_ui_state(False, pending=False, status_text="Mining Stopped"))
            return

        if not is_valid_luna_address(getattr(self.node.config, "miner_address", "")):
            self.add_log_message("Set a valid LUN_ address before mining.", "warning")
            self.safe_run_thread(self.show_address_setup_dialog)
            if self.page:
                self.safe_run_thread(lambda: self._set_mining_ui_state(False, pending=False, status_text="Mining Stopped"))
            return

        if self.node:
            try:
                self._mining_transition = True
                if self.page:
                    self.safe_run_thread(lambda: self._set_mining_ui_state(True, pending=True, status_text="Starting..."))

                def _start():
                    try:
                        try:
                            self.node.config.auto_mine = True
                            self.node.config.save_to_storage()
                        except Exception:
                            pass
                        started = self.node.start_auto_mining()
                        if started:
                            self.safe_run_thread(lambda: self.add_log_message("Auto-mining started", "success"))
                        else:
                            self.safe_run_thread(lambda: self.add_log_message("Auto-mining could not start. Check logs for details.", "error"))
                    except Exception as e:
                        self.safe_run_thread(lambda: self.add_log_message(f"Failed to start mining: {e}", "error"))
                    finally:
                        self.safe_run_thread(lambda: self._set_mining_ui_state(False, pending=False, status_text=None))
                        self._mining_transition = False

                threading.Thread(target=_start, daemon=True).start()
            except Exception as e:
                self.add_log_message(f"Failed to start mining: {e}", "error")
                self._mining_transition = False

    def stop_mining(self):
        """Stop auto-mining"""
        if getattr(self, "_mining_transition", False):
            return
        if self.node:
            try:
                self._mining_transition = True
                if self.page:
                    self.safe_run_thread(lambda: self._set_mining_ui_state(False, pending=True, status_text="Stopping..."))
                def _stop():
                    try:
                        self.node.stop_auto_mining()
                        self.safe_run_thread(lambda: self.add_log_message("Auto-mining stopped", "info"))
                    except Exception as e:
                        self.safe_run_thread(lambda: self.add_log_message(f"Failed to stop mining: {e}", "error"))
                    finally:
                        self.safe_run_thread(lambda: self._set_mining_ui_state(False, pending=False, status_text=None))
                        self._mining_transition = False
                threading.Thread(target=_stop, daemon=True).start()
            except Exception as e:
                self.add_log_message(f"Failed to stop mining: {e}", "error")
                self._mining_transition = False

    def toggle_cpu_mining(self):
        """Toggle CPU mining on/off."""
        if getattr(self, "_mining_transition", False):
            return
        if not self.node:
            self.add_log_message("Node is still initializing. Please wait...", "warning")
            return
        self._mining_transition = True
        if self.page:
            self.safe_run_thread(lambda: self._set_mining_ui_state(False, pending=True, status_text="CPU: Switching..."))

        def _toggle():
            try:
                status = self.node.get_status() if self.node else {}
                is_active = bool(status.get("cpu_mining_active"))
                if is_active:
                    self.node.stop_cpu_mining()
                else:
                    self.node.start_cpu_mining()
            except Exception as e:
                self.safe_run_thread(lambda: self.add_log_message(f"CPU mining toggle failed: {e}", "error"))
            finally:
                self.safe_run_thread(lambda: self._set_mining_ui_state(False, pending=False, status_text=None))
                self._mining_transition = False

        threading.Thread(target=_toggle, daemon=True).start()

    def toggle_gpu_mining(self):
        """Toggle GPU mining on/off."""
        if getattr(self, "_mining_transition", False):
            return
        if not self.node:
            self.add_log_message("Node is still initializing. Please wait...", "warning")
            return
        self._mining_transition = True
        if self.page:
            self.safe_run_thread(lambda: self._set_mining_ui_state(False, pending=True, status_text="GPU: Switching..."))

        def _toggle():
            try:
                status = self.node.get_status() if self.node else {}
                is_active = bool(status.get("gpu_mining_active"))
                if is_active:
                    self.node.stop_gpu_mining()
                else:
                    self.node.start_gpu_mining()
            except Exception as e:
                self.safe_run_thread(lambda: self.add_log_message(f"GPU mining toggle failed: {e}", "error"))
            finally:
                self.safe_run_thread(lambda: self._set_mining_ui_state(False, pending=False, status_text=None))
                self._mining_transition = False

        threading.Thread(target=_toggle, daemon=True).start()
   
    def __init__(self):
        self.node = None
        self.minimized_to_tray = False
        self.current_tab_index = 0
        self._stats_updater_started = False
        self.ui_active = True
        try:
            from colorama import init as colorama_init
            stdout = getattr(sys, "stdout", None)
            stderr = getattr(sys, "stderr", None)
            is_tty = bool(stdout and stdout.isatty()) and bool(stderr and stderr.isatty())
            if is_tty:
                colorama_init(autoreset=True)
        except Exception:
            pass
        self.page = None
        self.data_manager = DataManager()
        
        # Initialize GUI components
        self.sidebar = Sidebar(self)
        self.main_page = MainPage(self)
        self.mining_history = MiningHistory(self)
        self.bills_page = BillsPage(self)
        self.settings_page = SettingsPage(self)
        self.log_page = LogPage(self)

        # Miner is managed by LunaNode

    def submit_mined_block(self, block_data: Dict) -> bool:
        if not self.node:
            return False
        success, _message = self.node.submit_block(block_data)
        return bool(success)
    def create_main_ui(self, page: ft.Page):
        """Create the main node interface"""
        self.page = page
        # Page setup with blue theme
        page.title = "Luna Node"
        page.theme_mode = ft.ThemeMode.DARK
        page.fonts = {
            "Custom": "./font.ttf"
        }
        page.theme = ft.Theme(
            font_family="Custom",
        )
        # タスクバーアイコンを設定
        icon_path = os.path.abspath("node_icon.ico")
        if os.path.exists(icon_path):
            page.window.icon = icon_path
        page.padding = 0
        page.window.width = 1024
        page.window.height = 768
        page.window.min_width = 800
        page.window.min_height = 600
        page.window.center()
        page.on_window_event = self.on_window_event
        page.on_disconnect = self.on_disconnect
        main_layout = self.create_main_layout()
        page.add(main_layout)
        self.start_stats_updater()
        self.initialize_node_async()
        print("[DEBUG] create_main_ui completed")

    def on_disconnect(self, e=None):
        """Handle session disconnect to stop UI updates"""
        self.ui_active = False

    def safe_page_update(self):
        if not self.page or not self.ui_active:
            return False
        try:
            self.page.update()
            return True
        except Exception:
            self.ui_active = False
            return False

    def safe_run_thread(self, fn):
        if not self.page or not self.ui_active:
            return False
        try:
            self.page.run_thread(fn)
            return True
        except Exception:
            self.ui_active = False
            return False

    def start_stats_updater(self):
        if self._stats_updater_started:
            return
        self._stats_updater_started = True

        def stats_loop():
            while True:
                try:
                    if self.page and self.ui_active:
                        self.safe_run_thread(self.main_page.update_mining_stats)
                    elif not self.ui_active:
                        break
                except Exception:
                    pass
                try:
                    sleep_s = 5
                    if self.node and not self.node.miner.is_mining:
                        sleep_s = 15
                except Exception:
                    sleep_s = 5
                time.sleep(sleep_s)

        threading.Thread(target=stats_loop, daemon=True).start()
        
    def create_main_layout(self):
        """Create the main layout with sidebar and content area"""
        sidebar = self.sidebar.create_sidebar()
        main_content = self.create_main_content()
        layout = ft.Row([
            sidebar,
            ft.Container(
                content=main_content,
                expand=True,
                bgcolor="#1a2b3c",
                padding=0,
                margin=0,
            )
        ], expand=True, spacing=0)
        return layout
        
    def create_main_content(self):
        def _tab_label(icon_name: str, text: str):
            return ft.Tab(
                label=ft.Row(
                    [
                        ft.Image(
                            src=f"assets/icons/feather/{icon_name}.svg",
                            width=16,
                            height=16,
                            color="#e3f2fd",
                            color_blend_mode=ft.BlendMode.SRC_IN,
                        ),
                        ft.Text(text, size=12, color="#e3f2fd"),
                    ],
                    spacing=6,
                    alignment=ft.MainAxisAlignment.CENTER,
                )
            )

        tab_labels = [
            _tab_label("activity", "Mining"),
            _tab_label("clock", "History"),
            _tab_label("dollar-sign", "Bills"),
            _tab_label("settings", "Settings"),
            _tab_label("file-text", "Log"),
        ]
        tab_contents = [
            self.main_page.create_mining_tab(),
            self.mining_history.create_history_tab(),
            self.bills_page.create_bills_tab(),
            self.settings_page.create_settings_tab(),
            self.log_page.create_log_tab(),
        ]
        tab_bar = ft.TabBar(tabs=tab_labels)
        tab_bar_view = ft.TabBarView(controls=tab_contents, expand=True)
        tabs_control = ft.Tabs(
            content=ft.Column([
                tab_bar,
                tab_bar_view,
            ], expand=True),
            length=len(tab_labels),
            selected_index=0,
            on_change=self.on_tab_change,
            expand=True,
        )
        return tabs_control
        
    def on_tab_change(self, e):
        """Handle tab changes"""
        self.current_tab_index = e.control.selected_index
        if self.current_tab_index == 0:
            print("[DEBUG] Mining tab selected: updating mining stats")
            self.main_page.update_mining_stats()
            if self.node:
                try:
                    status = self.node.get_status()
                    self.sidebar.refresh_non_balance(status)
                except Exception:
                    pass
        elif self.current_tab_index == 1:
            print("[DEBUG] History tab selected: updating history content")
            self.mining_history.update_history_content()
        elif self.current_tab_index == 2:
            print("[DEBUG] Bills tab selected: updating bills content")
            self.bills_page.update_bills_content()
        elif self.current_tab_index == 3:  # Settings tab
            print("[DEBUG] Settings tab selected: updating settings content")
            self.settings_page.update_settings_content()
        elif self.current_tab_index == 4:  # Log tab
            print("[DEBUG] Log tab selected")
            
    def on_window_event(self, e):
        """Handle window events"""
        if e.data == "close":
            self.minimize_to_tray()
            return False
        return True
        
            # concise: skip debug
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
            # concise: skip debug
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
            # concise: skip debug
                print("[DEBUG] Initializing LunaNode")
                
                self.node = LunaNode(
                    log_callback=self.add_log_message,
                    new_bill_callback=lambda bill: self.add_log_message(f"New bill mined: {bill}", "success"),
                    new_reward_callback=lambda reward: self.add_log_message(f"New reward: {reward}", "success"),
                    history_updated_callback=self.update_history_content,
                    mining_started_callback=self.on_mining_started,
                    mining_completed_callback=self.on_mining_completed
                )
                self.safe_run_thread(self.on_node_initialized)
                
            except Exception as e:
                print(f"[ERROR] {e}")
                self.safe_run_thread(lambda e=e: self.add_log_message(str(e), "error"))
        threading.Thread(target=init_thread, daemon=True).start()
        
                # concise: skip debug
        """Called when mining starts"""
        self.safe_run_thread(lambda: self.add_log_message("Mining started", "info"))
        
    def on_mining_completed(self, success, message):
        """Called when mining completes"""
        msg_type = "success" if success else "warning"
        self.safe_run_thread(lambda: self.add_log_message(message, msg_type))
        
    def on_node_initialized(self):
        """Called when node is successfully initialized"""
        self.add_log_message("Luna Node initialized successfully", "success")
        self.add_log_message("Loaded data from ./data/ directory", "info")
        # Debugging DataManager and NodeConfig initialization
        print("[DEBUG] Initializing DataManager")
        data_manager = DataManager()
        print("[DEBUG] DataManager initialized:", data_manager)
        print("[DEBUG] Initializing NodeConfig")
        config = NodeConfig(data_manager)
        print("[DEBUG] NodeConfig initialized:", config)
        print("[DEBUG] Type of data_manager before load_mining_history:", type(data_manager))
        print("[DEBUG] Value of data_manager before load_mining_history:", data_manager)
        print("[DEBUG] Type of data_manager before calling load_mining_history:", type(data_manager))
        print("[DEBUG] Value of data_manager before calling load_mining_history:", data_manager)
        # Load mining history using DataManager
        #mining_history = data_manager.load_mining_history()
        #print("[DEBUG] Loaded mining history:", mining_history)
        # Refresh settings tab so it shows real settings after node is ready
        if hasattr(self, "settings_page"):
            try:
                self.settings_page.update_settings_content()
            except Exception as e:
                print(f"[DEBUG] settings_page.update_settings_content() failed: {e}")
        # Miningタブの統計を初期化し、自動マイニングを開始（シングルブロックマイニング等は絶対に行わない）
        if hasattr(self, "main_page"):
            try:
                self.main_page.update_mining_stats()
            except Exception as e:
                print(f"[DEBUG] main_page.update_mining_stats() failed: {e}")
        # 初回起動ウィザード or 既存設定
        try:
            needs_setup = not getattr(self.node.config, "setup_complete", False)
            invalid_address = not is_valid_luna_address(self.node.config.miner_address)

            if needs_setup or invalid_address:
                self.safe_run_thread(self.show_first_boot_wizard)
            elif is_valid_luna_address(self.node.config.miner_address):
                if getattr(self.node.config, "auto_mine", False):
                    threading.Thread(target=self.start_mining, daemon=True).start()
            else:
                self.safe_run_thread(self.show_address_setup_dialog)
        except Exception as e:
            print(f"[DEBUG] start_mining() failed: {e}")
        print("[DEBUG] LunaNode instance after initialization:", self.node)
        print("[DEBUG] Type of self.node.data_manager:", type(self.node.data_manager))
                    # concise: skip debug
        # Bills content is loaded lazily when the Bills tab is opened



        
    def update_status_display(self):
        """Update all status displays"""
        if not self.node:
            return
            
        status = self.node.get_status()
        # Update sidebar
        self.sidebar.update_status(status)
            
        # Update mining progress
        is_mining = self.node.miner.is_mining if self.node else False
        
        # Miningタブの統計は常に更新（タブ切替時以外も）
        self.main_page.update_mining_stats()
        if self.current_tab_index == 0:
            pass
            
        self.page.update()
        
    def add_log_message(self, message: str, msg_type: str = "info"):
        """Add message to log"""
        self.log_page.add_log_message(message, msg_type)
        
    def clear_log(self):
        self.log_page.clear_log()
            
    def mine_single_block(self):
        """Mine a single block using LunaLib"""
        if not self.node:
            self.add_log_message("Node not initialized", "error")
            return

        success, message = self.node.mine_single_block()
        msg_type = "success" if success else "warning"
        self.add_log_message(message, msg_type)
                

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
        if self.node and hasattr(self.node, 'config'):
            self.node.config.save_to_storage()
            self.add_log_message("Settings saved to ./data/settings.json", "success")
            self.show_snack_bar("Settings saved successfully")
        else:
            self.add_log_message("Settings could not be saved: node or config missing", "error")
        
    def update_history_content(self):
        """Update history content"""
        def _refresh():
            self.mining_history.update_history_content()
            if self.node and self.main_page:
                try:
                    self.main_page.update_mining_stats()
                except Exception:
                    pass
            if self.node and self.sidebar:
                try:
                    status = self.node.get_status()
                    self.sidebar.update_status(status)
                except Exception:
                    pass
            if self.bills_page:
                try:
                    self.bills_page.update_bills_content()
                except Exception:
                    pass
        self.safe_run_thread(_refresh)
        
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
                        error_content=ft.Text("LN", size=20)
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
            ft.Button(
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
    print("main() started")
    try:
        app = LunaNodeApp()
        print("LunaNodeApp created")
        app.create_main_ui(page)
        print("[DEBUG] create_main_ui completed")
        # Bills UI is loaded lazily on tab selection
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"Exception: {e}")
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
        print("Error dialog shown")

if __name__ == "__main__":
    ft.run(main)