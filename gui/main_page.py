import flet as ft
from typing import Dict

class MainPage:
    def __init__(self, app):
        self.app = app
        self.mining_stats = ft.Column()
        self.mining_controls = ft.Column()
        self.loading = True
        self.stats_panel = ft.Container(
            content=ft.Column([]),
            visible=False,
            bgcolor= "#00000000",
            padding=10,
            border_radius=4
        )
        # 統計用属性の初期化
        self.cpu_hashrate = 0.0
        self.gpu_hashrate = 0.0
        self.mined_blocks = 0
        self.rejected_blocks = 0
        print(f"[DEBUG] __init__: stats_panel.content={self.stats_panel.content}")
    def update_settings_content(self):
        """Update settings content - delegate to settings page"""
        if hasattr(self, 'settings_page') and self.settings_page:
            self.settings_page.update_settings_content()
    def create_mining_tab(self):
        """Create mining progress tab with controls and stats"""
        self.loading_ring = ft.ProgressRing(color="#00a1ff", width=72, height=72, visible=self.loading)
        print(f"[DEBUG] create_mining_tab: stats_panel.content={self.stats_panel.content}")
        # stats_panelは常に配置し、ローディング中はvisible=False
        stats_panel_box = self.stats_panel
        loading_box = None
        if self.loading:
            loading_box = ft.Row([
                ft.Container(expand=True),
                self.loading_ring,
                ft.Container(expand=True)
            ], alignment="center", expand=True)
        return ft.Container(
            content=ft.Column([
                ft.Text("Mining Dashboard", size=18, color="#e3f2fd"),
                ft.Container(height=10),
                self._create_mining_controls(),
                ft.Container(height=20),
                ft.Text("Live Statistics", size=16, color="#e3f2fd"),
                stats_panel_box,
                loading_box if self.loading else None,
                ft.Container(height=25),
            ], alignment=ft.MainAxisAlignment.START, expand=True),
            expand=True,
            padding=10
        )

    def _create_mining_controls(self):
        """Create mining control buttons"""
        button_style = ft.ButtonStyle(
            color="#ffffff",
            padding=ft.Padding.symmetric(horizontal=20, vertical=12),
            shape=ft.RoundedRectangleBorder(radius=4)
        )
        
        self.start_mining_btn = ft.Button(
            "⛏️ Start Mining",
            on_click=lambda e: self.app.start_mining(),
            style=button_style,
            bgcolor="#28a745",
            height=40
        )
        
        self.stop_mining_btn = ft.Button(
            "⏹️ Stop Mining",
            on_click=lambda e: self.app.stop_mining(),
            style=button_style,
            bgcolor="#dc3545",
            height=40,
            disabled=True
        )
        
        
        # Status indicator
        self.mining_status = ft.Container(
            content=ft.Row([
                ft.Container(
                    width=12,
                    height=12,
                    border_radius=6,
                    bgcolor="#dc3545"  # Red for stopped
                ),
                ft.Text("Mining Stopped", color="#e3f2fd", size=12)
            ], spacing=8),
            padding=10,
            bgcolor="#1a2b3c",
            border_radius=4
        )
        
        return ft.Container(
            content=ft.ResponsiveRow([
                ft.Container(
                    content=ft.Column([
                        ft.Text("Quick Actions", size=14, color="#e3f2fd"),
                        ft.Row([
                            self.start_mining_btn,
                            self.stop_mining_btn
                        ])
                        # Mine Single BlockとSync Networkボタンは削除
                    ]),
                    col={"sm": 12, "md": 8}
                ),
                ft.Container(
                    content=ft.Column([
                        ft.Text("Status", size=14, color="#e3f2fd"),
                        self.mining_status
                    ]),
                    col={"sm": 12, "md": 4}
                )
            ]),
            padding=15,
            bgcolor="#1a2b3c",
            border_radius=4
        )

    def update_mining_stats(self):
        """Update mining statistics tab"""
        if not self.app.node:
            self.loading = True
            if hasattr(self, 'loading_ring'):
                self.loading_ring.visible = True
            self.app.safe_page_update()
            return  # ここで必ずreturnし、status未定義で以降に進まない
        status = self.app.node.get_status()
        if hasattr(self.app, "sidebar") and self.app.sidebar:
            try:
                self.app.sidebar.update_status(status)
            except Exception:
                pass
        # データ取得できたらローディング非表示
        if self.loading:
            self.loading = False
            if hasattr(self, 'loading_ring'):
                self.loading_ring.visible = False
            self.stats_panel.visible = True
        total_reward_text = f"{status['total_reward']:.0f} LKC"
        # 2x4のテーブル状タイル（ラベル＋値）で統計を表示
        stat_items = [
            ("Network Height", f"{status['network_height']}", "#00a1ff", 20),
            ("Network Difficulty", f"{status['network_difficulty']}", "#17a2b8", 20),
            ("Blocks Mined", f"{status['blocks_mined']}", "#28a745", 20),
            ("Total Reward", total_reward_text, "#ffc107", 14),
            ("Hash Rate", f"{self._format_hash_rate(status['current_hash_rate'])}", "#00a1ff", 20),
            ("Success Rate", f"{status['success_rate']:.1f}%", "#28a745" if status['success_rate'] > 50 else "#ffc107", 20),
            ("Avg Mining Time", f"{status['avg_mining_time']:.2f}s", "#17a2b8", 20),
            ("Uptime", f"{self._format_uptime(status['uptime'])}", "#6c757d", 20),
        ]
        table_rows = []
        for i in range(2):
            row_cells = []
            for j in range(4):
                idx = i * 4 + j
                label, value, color, value_size = stat_items[idx]
                row_cells.append(
                    ft.Container(
                        content=ft.Column([
                            ft.Text(label, size=13, color="#e3f2fd"),
                            ft.Text(value, size=value_size, weight=ft.FontWeight.BOLD, color=color),
                        ], alignment=ft.MainAxisAlignment.CENTER),
                        padding=ft.padding.all(16),
                        bgcolor="#1a2b3c",
                        border_radius=1,
                        # alignment指定を削除
                        expand=True
                    )
                )
            table_rows.append(ft.Row(row_cells, alignment=ft.MainAxisAlignment.CENTER, expand=True, spacing=18))
        stats_table = ft.Column(table_rows, alignment=ft.MainAxisAlignment.CENTER, expand=True, spacing=18)
        self.stats_panel.content = ft.Container(
            content=stats_table,
            padding=ft.padding.symmetric(vertical=16, horizontal=16),
            bgcolor="#03111f",
            border_radius=8,
            expand=True,
            shadow=ft.BoxShadow(blur_radius=16, color="#00000044", offset=ft.Offset(0, 4)),
        )
        self.stats_panel.visible = True
        self.app.safe_page_update()
        status = self.app.node.get_status()
        # 必要な統計値をセット
        self.cpu_hashrate = status.get('cpu_hashrate', 0.0)
        self.gpu_hashrate = status.get('gpu_hashrate', 0.0)
        self.mined_blocks = status.get('blocks_mined', 0)
        self.rejected_blocks = status.get('rejected_blocks', 0)
        # Update mining status indicator
        if self.app.node.miner.is_mining:
            self.mining_status.content.controls[0].bgcolor = "#28a745"  # Green
            self.mining_status.content.controls[1].value = "Mining Active"
            self.start_mining_btn.disabled = True
            self.stop_mining_btn.disabled = False
        else:
            self.mining_status.content.controls[0].bgcolor = "#dc3545"  # Red
            self.mining_status.content.controls[1].value = "Mining Stopped"
            self.start_mining_btn.disabled = False
            self.stop_mining_btn.disabled = True
        # Create detailed stats cards
        stats_grid = ft.ResponsiveRow([
            self._create_detailed_stat_card(
                " Network Height", 
                f"{status['network_height']}", 
                "Current blockchain height",
                "#00a1ff"
            ),
            self._create_detailed_stat_card(
                "🎯 Network Difficulty", 
                f"{status['network_difficulty']}", 
                "Network's current difficulty",
                "#17a2b8"
            ),
            self._create_detailed_stat_card(
                "⚙️ Mining Difficulty", 
                f"{status.get('mining_difficulty', '--')}", 
                "Your configured difficulty",
                "#00e676"
            ),
            self._create_detailed_stat_card(
                "⛏️ Blocks Mined", 
                f"{status['blocks_mined']}", 
                "Total successful blocks",
                "#28a745"
            ),
            self._create_detailed_stat_card(
                "💰 Total Reward", 
                f"{status['total_reward']:.0f} LKC", 
                "Accumulated mining rewards",
                "#ffc107",
                value_size=10
            ),
            self._create_detailed_stat_card(
                "⚡ Current Hash Rate", 
                f"{self._format_hash_rate(status['current_hash_rate'])}", 
                "Real-time hashing speed",
                "#00a1ff"
            ),
            self._create_detailed_stat_card(
                "📈 Success Rate", 
                f"{status['success_rate']:.1f}%", 
                "Mining success percentage",
                "#28a745" if status['success_rate'] > 50 else "#ffc107"
            ),
            self._create_detailed_stat_card(
                "⏱️ Avg Mining Time", 
                f"{status['avg_mining_time']:.2f}s", 
                "Average block mining time",
                "#17a2b8"
            ),
            self._create_detailed_stat_card(
                "🕐 Uptime", 
                f"{self._format_uptime(status['uptime'])}", 
                "Node running time",
                "#6c757d"
            ),
            self._create_detailed_stat_card(
                "🔗 Connection", 
                f"{status['connection_status'].title()}", 
                "Network connection status",
                "#28a745" if status['connection_status'] == 'connected' else "#dc3545"
            ),
            self._create_detailed_stat_card(
                "📨 Mempool", 
                f"{status['total_transactions']}", 
                "Pending transactions",
                "#6c757d"
            ),
        ])
        # duplicate stats panel rendering removed to keep style consistent

    def _create_detailed_stat_card(self, title: str, value: str, description: str, color: str, value_size: int = 18):
        """Create a detailed statistics card with description"""
        return ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Text(title.split(" ")[0], size=14, color=color),  # Emoji
                    ft.Text(" ".join(title.split(" ")[1:]), size=12, color="#e3f2fd", expand=True),
                ], spacing=5),
                ft.Text(value, size=value_size, weight=ft.FontWeight.BOLD, color=color),
                ft.Container(height=2),
                ft.Text(description, size=10, color="#6c757d"),
            ], spacing=2),
            padding=15,
            margin=3,
            bgcolor="#1a2b3c",
            border=ft.Border.all(1, "#1e3a5c"),
            border_radius=4,
            col={"xs": 12, "sm": 6, "md": 4, "lg": 3}
        )

    def _format_hash_rate(self, hash_rate: float) -> str:
        """Format hash rate for display"""
        if hash_rate > 1000000:
            return f"{hash_rate/1000000:.2f} MH/s"
        elif hash_rate > 1000:
            return f"{hash_rate/1000:.2f} kH/s"
        else:
            return f"{hash_rate:.0f} H/s"

    def _format_uptime(self, seconds: float) -> str:
        """Format uptime for display"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        
        if hours > 0:
            return f"{hours}h {minutes}m"
        else:
            return f"{minutes}m"