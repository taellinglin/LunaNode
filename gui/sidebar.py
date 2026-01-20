import flet as ft
from typing import Dict

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
        self.lbl_mining_method = ft.Text("Method: --", size=10, color="#e3f2fd")
        self.lbl_current_hash = ft.Text("Current Hash: --", size=10, color="#e3f2fd")
        self.lbl_nonce = ft.Text("Nonce: --", size=10, color="#e3f2fd")
        self.progress_mining = ft.ProgressBar(visible=False, color="#00a1ff", bgcolor="#1e3a5c")
        
        # Quick action buttons
        button_style = ft.ButtonStyle(
            color="#ffffff",
            bgcolor="#00a1ff",
            padding=ft.Padding.symmetric(horizontal=16, vertical=6),
            shape=ft.RoundedRectangleBorder(radius=2)
        )
        
        self.btn_start_mining = ft.Button(
            "⛏️ Start Mining",
            on_click=lambda e: self.app.start_mining(),
            style=button_style,
            height=32
        )
        
        self.btn_stop_mining = ft.Button(
            "⏹️ Stop Mining",
            on_click=lambda e: self.app.stop_mining(),
            style=button_style,
            height=32,
            disabled=True
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
        hash_rate = status['current_hash_rate']
        mining_method = status.get('mining_method', 'CPU')
        current_hash = status['current_hash']
        nonce = status.get('nonce', '--')
        self.lbl_hash_rate.value = f"Hash Rate: {hash_rate:.2f} H/s"
        self.lbl_mining_method.value = f"Method: {mining_method}"
        self.lbl_current_hash.value = f"Current Hash: {current_hash}"
        self.lbl_nonce.value = f"Nonce: {nonce}"
        self.app.safe_page_update()
    def create_sidebar(self):
        # サイドバー表示時にstats自動更新タイマーを開始
        self._start_stats_update_timer()
        
        """Create the sidebar with node info and quick actions"""
        sidebar_width = 240
        
        node_status = ft.Container(
            content=ft.Column([
                ft.Text("🖥️ Node Status", size=14, color="#e3f2fd"),
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
                ft.Text("⛏️ Mining Stats", size=14, color="#e3f2fd"),
                self.lbl_hash_rate,
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
                            ft.PopupMenuItem(content=ft.Text("Start Mining"), on_click=lambda e: self.app.start_mining()),
                            ft.PopupMenuItem(content=ft.Text("Stop Mining"), on_click=lambda e: self.app.stop_mining()),
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
                            error_content=ft.Text("🔵", size=16)
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
        self.lbl_node_status.value = f"Status: {'🟢 Running' if status['connection_status'] == 'connected' else '🟡 Disconnected'}"
        self.lbl_network_height.value = f"Network Height: {status['network_height']}"
        self.lbl_difficulty.value = f"Network Difficulty: {status['network_difficulty']}"
        self.lbl_mining_difficulty.value = f"Mining Difficulty: {status.get('mining_difficulty', '--')}"
        self.lbl_blocks_mined.value = f"Blocks Mined: {status['blocks_mined']}"
        self.lbl_total_reward.value = f"Total Reward: {status['total_reward']:.2f} LKC"
        self.lbl_connection.value = f"Connection: {status['connection_status']}"
        
        # Update P2P status
        p2p_connected = status.get('p2p_connected', False)
        p2p_peers = status.get('p2p_peers', 0)
        if p2p_connected:
            self.lbl_p2p_status.value = f"P2P: 🟢 {p2p_peers} peers"
            self.lbl_p2p_status.color = "#00e676"
        else:
            self.lbl_p2p_status.value = "P2P: 🔴 Offline"
            self.lbl_p2p_status.color = "#ff5252"

        uptime_seconds = int(status['uptime'])
        hours = uptime_seconds // 3600
        minutes = (uptime_seconds % 3600) // 60
        seconds = uptime_seconds % 60
        self.lbl_uptime.value = f"Uptime: {hours:02d}:{minutes:02d}:{seconds:02d}"

        # Update mining stats
        hash_rate = status['current_hash_rate']
        mining_method = status.get('mining_method', 'CPU')
        
        if hash_rate > 1000000:
            self.lbl_hash_rate.value = f"Hash Rate: {hash_rate/1000000:.2f} MH/s"
        elif hash_rate > 1000:
            self.lbl_hash_rate.value = f"Hash Rate: {hash_rate/1000:.2f} kH/s"
        else:
            self.lbl_hash_rate.value = f"Hash Rate: {hash_rate:.0f} H/s"
        # Show mining method with color indicator
        if mining_method == 'CUDA':
            self.lbl_mining_method.value = f"Method: 🟢 {mining_method}"
            self.lbl_mining_method.color = "#00e676"
        else:
            self.lbl_mining_method.value = f"Method: 🔵 {mining_method}"
            self.lbl_mining_method.color = "#00a1ff"

        current_hash = status['current_hash']
        if current_hash:
            short_hash = current_hash[:16] + "..." if len(current_hash) > 16 else current_hash
            self.lbl_current_hash.value = f"Current Hash: {short_hash}"
        else:
            self.lbl_current_hash.value = "Current Hash: --"

        self.lbl_nonce.value = f"Nonce: {status['current_nonce']}"

        # Update mining progress
        is_mining = self.app.node.miner.is_mining if self.app.node else False
        self.progress_mining.visible = is_mining

        # Update button states
        self.btn_start_mining.disabled = is_mining
        self.btn_stop_mining.disabled = not is_mining

    def refresh_non_balance(self, status: Dict):
        """Refresh sidebar without balance-related fields."""
        self.lbl_node_status.value = f"Status: {'🟢 Running' if status['connection_status'] == 'connected' else '🟡 Disconnected'}"
        self.lbl_network_height.value = f"Network Height: {status['network_height']}"
        self.lbl_difficulty.value = f"Network Difficulty: {status['network_difficulty']}"
        self.lbl_mining_difficulty.value = f"Mining Difficulty: {status.get('mining_difficulty', '--')}"
        self.lbl_blocks_mined.value = f"Blocks Mined: {status['blocks_mined']}"
        self.lbl_connection.value = f"Connection: {status['connection_status']}"

        p2p_connected = status.get('p2p_connected', False)
        p2p_peers = status.get('p2p_peers', 0)
        if p2p_connected:
            self.lbl_p2p_status.value = f"P2P: 🟢 {p2p_peers} peers"
            self.lbl_p2p_status.color = "#00e676"
        else:
            self.lbl_p2p_status.value = "P2P: 🔴 Offline"
            self.lbl_p2p_status.color = "#ff5252"

        uptime_seconds = int(status['uptime'])
        hours = uptime_seconds // 3600
        minutes = (uptime_seconds % 3600) // 60
        seconds = uptime_seconds % 60
        self.lbl_uptime.value = f"Uptime: {hours:02d}:{minutes:02d}:{seconds:02d}"

        hash_rate = status['current_hash_rate']
        mining_method = status.get('mining_method', 'CPU')
        if hash_rate > 1000000:
            self.lbl_hash_rate.value = f"Hash Rate: {hash_rate/1000000:.2f} MH/s"
        elif hash_rate > 1000:
            self.lbl_hash_rate.value = f"Hash Rate: {hash_rate/1000:.2f} kH/s"
        else:
            self.lbl_hash_rate.value = f"Hash Rate: {hash_rate:.0f} H/s"

        if mining_method == 'CUDA':
            self.lbl_mining_method.value = f"Method: 🟢 {mining_method}"
            self.lbl_mining_method.color = "#00e676"
        else:
            self.lbl_mining_method.value = f"Method: 🔵 {mining_method}"
            self.lbl_mining_method.color = "#00a1ff"

        current_hash = status['current_hash']
        if current_hash:
            short_hash = current_hash[:16] + "..." if len(current_hash) > 16 else current_hash
            self.lbl_current_hash.value = f"Current Hash: {short_hash}"
        else:
            self.lbl_current_hash.value = "Current Hash: --"

        self.lbl_nonce.value = f"Nonce: {status['current_nonce']}"

        is_mining = self.app.node.miner.is_mining if self.app.node else False
        self.progress_mining.visible = is_mining
        self.btn_start_mining.disabled = is_mining
        self.btn_stop_mining.disabled = not is_mining
        self.app.safe_page_update()