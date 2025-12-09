import flet as ft


class MainPage:
    def __init__(self, app):
        self.app = app
        self.mining_stats = ft.Column()
        self.mining_controls = ft.Column()
    def update_settings_content(self):
        """Update settings content - delegate to settings page"""
        if hasattr(self, 'settings_page') and self.settings_page:
            self.settings_page.update_settings_content()
    def create_mining_tab(self):
        """Create mining progress tab with controls and stats"""
        return ft.Container(
            content=ft.Column([
                ft.Text("Mining Dashboard", size=18, color="#e3f2fd"),
                ft.Container(height=10),
                self._create_mining_controls(),
                ft.Container(height=20),
                ft.Text("Live Statistics", size=16, color="#e3f2fd"),
                ft.Container(
                    content=self.mining_stats,
                    expand=True,
                    border=ft.Border.all(1, "#1e3a5c"),
                    border_radius=3,
                    padding=10,
                    bgcolor="#0f1a2a"
                )
            ], expand=True),
            padding=10
        )

    def _create_mining_controls(self):
        """Create mining control buttons"""
        button_style = ft.ButtonStyle(
            color="#ffffff",
            padding=ft.padding.symmetric(horizontal=20, vertical=12),
            shape=ft.RoundedRectangleBorder(radius=4)
        )
        
        self.start_mining_btn = ft.ElevatedButton(
            "⛏️ Start Mining",
            on_click=lambda e: self.app.start_mining(),
            style=button_style,
            bgcolor="#28a745",
            height=40
        )
        
        self.stop_mining_btn = ft.ElevatedButton(
            "⏹️ Stop Mining",
            on_click=lambda e: self.app.stop_mining(),
            style=button_style,
            bgcolor="#dc3545",
            height=40,
            disabled=True
        )
        
        self.single_mine_btn = ft.ElevatedButton(
            "⚡ Mine Single Block",
            on_click=lambda e: self.app.mine_single_block(),
            style=button_style,
            bgcolor="#17a2b8",
            height=40
        )
        
        self.sync_btn = ft.ElevatedButton(
            "🔄 Sync Network",
            on_click=lambda e: self.app.sync_network(),
            style=button_style,
            bgcolor="#6c757d",
            height=40
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
                        ]),
                        ft.Container(height=10),
                        ft.Row([
                            self.single_mine_btn,
                            self.sync_btn
                        ])
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
            return
            
        status = self.app.node.get_status()
        
        self.mining_stats.controls.clear()
        
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
                "📊 Network Height", 
                f"{status['network_height']}", 
                "Current blockchain height",
                "#00a1ff"
            ),
            self._create_detailed_stat_card(
                "🎯 Network Difficulty", 
                f"{status['network_difficulty']}", 
                "Current mining difficulty",
                "#17a2b8"
            ),
            self._create_detailed_stat_card(
                "⛏️ Blocks Mined", 
                f"{status['blocks_mined']}", 
                "Total successful blocks",
                "#28a745"
            ),
            self._create_detailed_stat_card(
                "💰 Total Reward", 
                f"{status['total_reward']:.2f} LUN", 
                "Accumulated mining rewards",
                "#ffc107"
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
        
        self.mining_stats.controls.append(stats_grid)
        
        if self.app.page:
            self.app.page.update()

    def _create_detailed_stat_card(self, title: str, value: str, description: str, color: str):
        """Create a detailed statistics card with description"""
        return ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Text(title.split(" ")[0], size=14, color=color),  # Emoji
                    ft.Text(" ".join(title.split(" ")[1:]), size=12, color="#e3f2fd", expand=True),
                ], spacing=5),
                ft.Text(value, size=18, weight=ft.FontWeight.BOLD, color=color),
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