import flet as ft
from typing import Dict
try:
    from lunalib.utils.formatting import format_amount as lunalib_format_amount
except Exception:
    lunalib_format_amount = None

class Sidebar:
    def __init__(self, app):
        self.stats_update_timer = None
        self.app = app
        self.lbl_node_status = ft.Text("Status: Initializing...", size=12, color="#e3f2fd")
        self.lbl_network_height = ft.Text("Network Height: --", size=10, color="#e3f2fd")
        self.lbl_difficulty = ft.Text("Difficulty: --", size=10, color="#e3f2fd")
        self.lbl_mining_difficulty = ft.Text("Mining Difficulty: --", size=10, color="#00e676")
        self.lbl_blocks_mined = ft.Text("Blocks Mined: --", size=10, color="#e3f2fd")
        self.lbl_total_reward = ft.Text("Total Reward: --", size=10, color="#e3f2fd")
        self.lbl_connection = ft.Text("Connection: --", size=10, color="#e3f2fd")
        self.lbl_p2p_status = ft.Text("P2P: --", size=10, color="#e3f2fd")
        self.lbl_uptime = ft.Text("Uptime: --", size=10, color="#e3f2fd")
        self.lbl_hash_rate = ft.Text("Hash Rate: --", size=12, color="#e3f2fd")
        self.lbl_hash_algo = ft.Text("Hash: --", size=10, color="#e3f2fd")
        self.lbl_method_label = ft.Text("Method:", size=10, color="#ffffff")
        self.lbl_method_tags = ft.Row(spacing=6)
        self.lbl_mining_method = ft.Row([self.lbl_method_label, self.lbl_method_tags], spacing=6)
        self.lbl_current_hash = ft.Text("Current Hash: --", size=10, color="#e3f2fd")
        self.lbl_nonce = ft.Text("Nonce: --", size=10, color="#e3f2fd")
        self.progress_mining = ft.ProgressBar(visible=False, color="#00a1ff", bgcolor="#1e3a5c")

    def _icon_label(self, icon_name: str, text: str, color: str = "#e3f2fd", icon_size: int = 14, text_size: int = 10):
        return ft.Row(
            [
                ft.Image(
                    src=f"assets/icons/feather/{icon_name}.svg",
                    width=icon_size,
                    height=icon_size,
                    color="#ffffff",
                    color_blend_mode=ft.BlendMode.SRC_IN,
                ),
                ft.Text(text, size=text_size, color=color),
            ],
            spacing=6,
        )

    def _set_button_label(self, button: ft.Button, icon_name: str, text: str):
        button.content = self._icon_label(icon_name, text, color="#ffffff", icon_size=14, text_size=10)
        
        # Quick action buttons
        button_style = ft.ButtonStyle(
            color="#ffffff",
            bgcolor="#00a1ff",
            padding=ft.Padding.symmetric(horizontal=16, vertical=6),
            shape=ft.RoundedRectangleBorder(radius=2)
        )
        
        self.btn_cpu_mining = ft.Button(
            content=self._icon_label("cpu", "Start CPU", color="#ffffff", icon_size=14, text_size=10),
            on_click=lambda e: self.app.toggle_cpu_mining(),
            style=button_style,
            height=32
        )

        self.btn_gpu_mining = ft.Button(
            content=self._icon_label("monitor", "Start GPU", color="#ffffff", icon_size=14, text_size=10),
            on_click=lambda e: self.app.toggle_gpu_mining(),
            style=button_style,
            height=32
        )
    
    def _start_stats_update_timer(self):
        # 既存タイマーがあれば停止
        if self.stats_update_timer:
            self.stats_update_timer.cancel()
        import threading
        def update_loop():
            while True:
                import time
                time.sleep(5)
                if not getattr(self.app, "ui_active", True):
                    break
                if hasattr(self.app, 'sidebar_tab_open') and not self.app.sidebar_tab_open:
                    break
                self.update_stats_tab()
        self.stats_update_timer = threading.Thread(target=update_loop, daemon=True)
        self.stats_update_timer.start()

    def update_stats_tab(self):
        # 最新のノード統計値でmining_statsを更新
        if not hasattr(self.app, 'node') or not self.app.node:
            return
        status = self.app.node.get_status()
        try:
            self.update_status(status)
        except Exception:
            pass
        self.app.safe_page_update()
    def create_sidebar(self):
        # サイドバー表示時にstats自動更新タイマーを開始
        self._start_stats_update_timer()
        
        """Create the sidebar with node info and quick actions"""
        sidebar_width = 240
        
        node_status = ft.Container(
            content=ft.Column([
                self._icon_label("server", "Node Status", color="#e3f2fd", icon_size=16, text_size=14),
                self.lbl_node_status,
                self.lbl_network_height,
                self.lbl_difficulty,
                self.lbl_mining_difficulty,
                self.lbl_blocks_mined,
                self.lbl_total_reward,
                self.lbl_connection,
                self.lbl_p2p_status,
                self.lbl_uptime,
            ], spacing=4),
            padding=10,
            bgcolor="#1a2b3c",
            border_radius=4,
            margin=5,
            width=sidebar_width - 30
        )
        

        
        mining_stats = ft.Container(
            content=ft.Column([
                self._icon_label("activity", "Mining Stats", color="#e3f2fd", icon_size=16, text_size=14),
                self.lbl_hash_rate,
                self.lbl_hash_algo,
                self.lbl_mining_method,
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
        
        app_icon = ft.Container(
            content=ft.Row([
                ft.Container(
                    content=ft.Image(
                        src="node_icon.svg",
                        width=64,
                        height=64,
                        fit="contain",
                        color="#00a1ff",
                        color_blend_mode=ft.BlendMode.SRC_IN,
                        error_content=ft.Text("LN", size=24)
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
        
        sidebar_content = ft.Column([
            ft.Container(
                content=ft.Row([
                    ft.PopupMenuButton(
                        content=ft.Text("☰", color="#e3f2fd", size=16),
                        tooltip="System Menu",
                        items=[
                            ft.PopupMenuItem(content=ft.Text("Restore"), on_click=lambda e: self.app.restore_from_tray()),
                            ft.PopupMenuItem(content=ft.Text("Minimize to Tray"), on_click=lambda e: self.app.minimize_to_tray()),
                            ft.PopupMenuItem(),
                            ft.PopupMenuItem(content=ft.Text("Start/Stop CPU Mining"), on_click=lambda e: self.app.toggle_cpu_mining()),
                            ft.PopupMenuItem(content=ft.Text("Start/Stop GPU Mining"), on_click=lambda e: self.app.toggle_gpu_mining()),
                            ft.PopupMenuItem(content=ft.Text("Sync Network"), on_click=lambda e: self.app.sync_network()),
                            ft.PopupMenuItem(),
                            ft.PopupMenuItem(content=ft.Text("About"), on_click=lambda e: self.app.show_about_dialog()),
                            ft.PopupMenuItem(content=ft.Text("Exit"), on_click=lambda e: self.app.page.window.close()),
                        ]
                    ),
                    ft.Container(
                        content=ft.Image(
                            src="node_icon.svg",
                            width=32,
                            height=32,
                            fit="contain",
                            color="#00a1ff",
                            color_blend_mode=ft.BlendMode.SRC_IN,
                            error_content=ft.Text("LN", size=16)
                        ),
                        margin=ft.Margin.only(right=8),
                    ),
                    ft.Text("Luna Node", size=24, color="#e3f2fd"),
                ]),
                width=sidebar_width - 30,
                bgcolor="transparent"
            ),
            ft.Divider(height=1, color="#1e3a5c"),
            node_status,
            ft.Divider(height=1, color="#1e3a5c"),
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

    def update_status(self, status: Dict):
        """Update sidebar status displays"""
        self.lbl_node_status.value = f"Status: {'Running' if status['connection_status'] == 'connected' else 'Disconnected'}"
        self.lbl_network_height.value = f"Network Height: {status['network_height']}"
        self.lbl_difficulty.value = f"Network Difficulty: {status['network_difficulty']}"
        self.lbl_mining_difficulty.value = f"Mining Difficulty: {status.get('mining_difficulty', '--')}"
        self.lbl_blocks_mined.value = f"Blocks Mined: {status['blocks_mined']}"
        self.lbl_total_reward.value = f"Total Reward: {self._format_lkc(status.get('total_reward', 0))}"
        self.lbl_connection.value = f"Connection: {status['connection_status']}"
        
        # Update P2P status
        p2p_connected = status.get('p2p_connected', False)
        p2p_peers = status.get('p2p_peers', 0)
        if p2p_connected:
            self.lbl_p2p_status.value = f"P2P: {p2p_peers} peers"
            self.lbl_p2p_status.color = "#00e676"
        else:
            self.lbl_p2p_status.value = "P2P: Offline"
            self.lbl_p2p_status.color = "#ff5252"

        uptime_seconds = int(status['uptime'])
        hours = uptime_seconds // 3600
        minutes = (uptime_seconds % 3600) // 60
        seconds = uptime_seconds % 60
        self.lbl_uptime.value = f"Uptime: {hours:02d}:{minutes:02d}:{seconds:02d}"

        # Update mining stats
        cpu_rate = status.get('cpu_hash_rate', 0) or 0
        gpu_rate = status.get('gpu_hash_rate', 0) or 0
        hash_rate = cpu_rate + gpu_rate
        mining_method = status.get('mining_method', 'CPU')
        hash_algo = status.get("hash_algorithm")
        if not hash_algo:
            try:
                if self.app and self.app.node and hasattr(self.app.node, "hash_algorithm"):
                    hash_algo = self.app.node.hash_algorithm
                elif self.app and self.app.node and hasattr(self.app.node, "config"):
                    hash_algo = getattr(self.app.node.config, "hash_algorithm", None)
            except Exception:
                hash_algo = None
        if not hash_algo:
            hash_algo = "sha256"
        self.lbl_hash_algo.value = f"Hash: {str(hash_algo).upper()}"
        
        if hash_rate > 1000000:
            self.lbl_hash_rate.value = f"Hash Rate: {hash_rate/1000000:.2f} MH/s"
        elif hash_rate > 1000:
            self.lbl_hash_rate.value = f"Hash Rate: {hash_rate/1000:.2f} kH/s"
        else:
            self.lbl_hash_rate.value = f"Hash Rate: {hash_rate:.0f} H/s"

    def _format_lkc(self, amount: float) -> str:
        if lunalib_format_amount:
            try:
                return lunalib_format_amount(amount, "LKC")
            except Exception:
                pass
        try:
            value = float(amount)
        except Exception:
            value = 0.0
        return f"{value:,.2f} LKC"
        # Show mining method tags
        try:
            self.lbl_method_tags.controls.clear()
        except Exception:
            pass
        cpu_active = bool(status.get("cpu_mining_active"))
        gpu_active = bool(status.get("gpu_mining_active"))
        cpu_threads = 0
        try:
            cpu_threads = int(getattr(self.app.node.config, "cpu_threads", 0) or getattr(self.app.node.config, "sm3_workers", 0) or 0)
        except Exception:
            cpu_threads = 0
        multi_gpu = False
        try:
            multi_gpu = bool(getattr(self.app.node.config, "multi_gpu_enabled", False))
        except Exception:
            multi_gpu = False
        if cpu_active:
            cpu_tag = ft.Container(
                content=ft.Text(f"CPU({cpu_threads if cpu_threads > 0 else '?'})", size=9, color="#ffffff"),
                bgcolor="#1e88e5",
                padding=ft.Padding(6, 2, 6, 2),
                border_radius=12,
            )
            self.lbl_method_tags.controls.append(cpu_tag)
        if gpu_active:
            gpu_count = "x2" if multi_gpu else "x1"
            gpu_tag = ft.Container(
                content=ft.Text(f"GPU({gpu_count})", size=9, color="#ffffff"),
                bgcolor="#2e7d32",
                padding=ft.Padding(6, 2, 6, 2),
                border_radius=12,
            )
            self.lbl_method_tags.controls.append(gpu_tag)
        if cpu_active or gpu_active:
            difficulty_val = status.get("mining_difficulty")
            difficulty_tag = ft.Container(
                content=ft.Text(f"Diff {difficulty_val}", size=9, color="#ffffff"),
                bgcolor="#9c27b0",
                padding=ft.Padding(6, 2, 6, 2),
                border_radius=12,
            )
            self.lbl_method_tags.controls.append(difficulty_tag)

        current_hash = status['current_hash']
        if current_hash:
            short_hash = current_hash[:16] + "..." if len(current_hash) > 16 else current_hash
            self.lbl_current_hash.value = f"Current Hash: {short_hash}"
        else:
            self.lbl_current_hash.value = "Current Hash: --"

        cpu_nonce = status.get('cpu_nonce', 0)
        gpu_nonce = status.get('gpu_nonce', 0)
        self.lbl_nonce.value = f"Nonce: CPU {cpu_nonce} | GPU {gpu_nonce}"

        if not getattr(self.app, "_mining_transition", False):
            auto_mining = bool(status.get("auto_mining"))
            cpu_active = bool(status.get("cpu_mining_active"))
            gpu_active = bool(status.get("gpu_mining_active"))
            cpu_enabled = bool(getattr(self.app.node.config, "enable_cpu_mining", True)) if self.app.node else True
            cuda_available = bool(status.get("cuda_available", False))
            gpu_enabled = cuda_available or bool(getattr(self.app.node.config, "enable_gpu_mining", True)) if self.app.node else cuda_available
            if auto_mining:
                cpu_active = cpu_active or cpu_enabled
                gpu_active = gpu_active or gpu_enabled
            self.btn_cpu_mining.disabled = not cpu_enabled
            self.btn_gpu_mining.disabled = not gpu_enabled
            self._set_button_label(self.btn_cpu_mining, "cpu", "Stop CPU" if cpu_active else "Start CPU")
            self._set_button_label(self.btn_gpu_mining, "monitor", "Stop GPU" if gpu_active else "Start GPU")

        # Update mining progress
        is_mining = bool(status.get("auto_mining"))
        self.progress_mining.visible = is_mining

    def refresh_non_balance(self, status: Dict):
        """Refresh sidebar without balance-related fields."""
        self.lbl_node_status.value = f"Status: {'Running' if status['connection_status'] == 'connected' else 'Disconnected'}"
        self.lbl_network_height.value = f"Network Height: {status['network_height']}"
        self.lbl_difficulty.value = f"Network Difficulty: {status['network_difficulty']}"
        self.lbl_mining_difficulty.value = f"Mining Difficulty: {status.get('mining_difficulty', '--')}"
        self.lbl_blocks_mined.value = f"Blocks Mined: {status['blocks_mined']}"
        self.lbl_connection.value = f"Connection: {status['connection_status']}"

        p2p_connected = status.get('p2p_connected', False)
        p2p_peers = status.get('p2p_peers', 0)
        if p2p_connected:
            self.lbl_p2p_status.value = f"P2P: {p2p_peers} peers"
            self.lbl_p2p_status.color = "#00e676"
        else:
            self.lbl_p2p_status.value = "P2P: Offline"
            self.lbl_p2p_status.color = "#ff5252"

        uptime_seconds = int(status['uptime'])
        hours = uptime_seconds // 3600
        minutes = (uptime_seconds % 3600) // 60
        seconds = uptime_seconds % 60
        self.lbl_uptime.value = f"Uptime: {hours:02d}:{minutes:02d}:{seconds:02d}"

        cpu_rate = status.get('cpu_hash_rate', 0) or 0
        gpu_rate = status.get('gpu_hash_rate', 0) or 0
        hash_rate = cpu_rate + gpu_rate
        mining_method = status.get('mining_method', 'CPU')
        if hash_rate > 1000000:
            self.lbl_hash_rate.value = f"Hash Rate: {hash_rate/1000000:.2f} MH/s"
        elif hash_rate > 1000:
            self.lbl_hash_rate.value = f"Hash Rate: {hash_rate/1000:.2f} kH/s"
        else:
            self.lbl_hash_rate.value = f"Hash Rate: {hash_rate:.0f} H/s"

        try:
            self.lbl_method_tags.controls.clear()
        except Exception:
            pass
        cpu_active = bool(status.get("cpu_mining_active"))
        gpu_active = bool(status.get("gpu_mining_active"))
        cpu_threads = 0
        try:
            cpu_threads = int(getattr(self.app.node.config, "cpu_threads", 0) or getattr(self.app.node.config, "sm3_workers", 0) or 0)
        except Exception:
            cpu_threads = 0
        multi_gpu = False
        try:
            multi_gpu = bool(getattr(self.app.node.config, "multi_gpu_enabled", False))
        except Exception:
            multi_gpu = False
        if cpu_active:
            cpu_tag = ft.Container(
                content=ft.Text(f"CPU({cpu_threads if cpu_threads > 0 else '?'})", size=9, color="#ffffff"),
                bgcolor="#1e88e5",
                padding=ft.Padding(6, 2, 6, 2),
                border_radius=12,
            )
            self.lbl_method_tags.controls.append(cpu_tag)
        if gpu_active:
            gpu_count = "x2" if multi_gpu else "x1"
            gpu_tag = ft.Container(
                content=ft.Text(f"GPU({gpu_count})", size=9, color="#ffffff"),
                bgcolor="#2e7d32",
                padding=ft.Padding(6, 2, 6, 2),
                border_radius=12,
            )
            self.lbl_method_tags.controls.append(gpu_tag)
        if cpu_active or gpu_active:
            difficulty_val = status.get("mining_difficulty")
            difficulty_tag = ft.Container(
                content=ft.Text(f"Diff {difficulty_val}", size=9, color="#ffffff"),
                bgcolor="#9c27b0",
                padding=ft.Padding(6, 2, 6, 2),
                border_radius=12,
            )
            self.lbl_method_tags.controls.append(difficulty_tag)

        current_hash = status['current_hash']
        if current_hash:
            short_hash = current_hash[:16] + "..." if len(current_hash) > 16 else current_hash
            self.lbl_current_hash.value = f"Current Hash: {short_hash}"
        else:
            self.lbl_current_hash.value = "Current Hash: --"

        cpu_nonce = status.get('cpu_nonce', 0)
        gpu_nonce = status.get('gpu_nonce', 0)
        self.lbl_nonce.value = f"Nonce: CPU {cpu_nonce} | GPU {gpu_nonce}"

        is_mining = bool(status.get("auto_mining"))
        self.progress_mining.visible = is_mining
        self.app.safe_page_update()