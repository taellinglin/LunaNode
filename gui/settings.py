import flet as ft


class SettingsPage:
    def __init__(self, app):
        self.app = app
        self.settings_content = ft.Column()

    def create_settings_tab(self):
        """Create settings tab with categorized options"""
        # First update the content to ensure it's populated
        self.update_settings_content()
        
        return ft.Container(
            content=ft.Column([
                ft.Container(
                    content=ft.Text("Node Settings", size=20, color="#e3f2fd", weight="bold"),
                    padding=ft.padding.only(bottom=15)
                ),
                ft.Container(
                    content=ft.Column([
                        self.settings_content,
                    ], scroll=ft.ScrollMode.ADAPTIVE),
                    expand=True,
                    border=ft.border.all(1, "#1e3a5c"),
                    border_radius=8,
                    padding=15,
                    bgcolor="#0f1a2a"
                )
            ], expand=True),
            padding=15,
            expand=True
        )

    def update_settings_content(self):
        """Update settings content with current values"""
        self.settings_content.controls.clear()
        
        if not self.app.node:
            self.settings_content.controls.append(
                ft.Container(
                    content=ft.Column([
                        ft.Icon(ft.Icons.WARNING, size=48, color="#ffd700"),
                        ft.Text("Node Not Available", size=18, color="#ffd700", weight="bold"),
                        ft.Text("Please start the node to access settings", size=14, color="#e3f2fd"),
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10),
                    padding=40,
                    alignment=ft.alignment.center
                )
            )
            if self.app.page:
                self.app.page.update()
            return
            
        # Create settings categories
        mining_section = self._create_mining_settings()
        network_section = self._create_network_settings()
        performance_section = self._create_performance_settings()
        wallet_section = self._create_wallet_settings()
        advanced_section = self._create_advanced_settings()
        
        # Add all sections
        self.settings_content.controls.extend([
            mining_section,
            ft.Divider(height=25, color="#1e3a5c"),
            network_section,
            ft.Divider(height=25, color="#1e3a5c"),
            performance_section,
            ft.Divider(height=25, color="#1e3a5c"),
            wallet_section,
            ft.Divider(height=25, color="#1e3a5c"),
            advanced_section,
            ft.Container(height=20),
            self._create_action_buttons()
        ])
        
        if self.app.page:
            self.app.page.update()

    def _create_mining_settings(self):
        """Create mining-related settings"""
        self.auto_mining_switch = ft.Switch(
            label="Auto Mining",
            value=self.app.node.config.auto_mine if self.app.node else False,
            on_change=lambda e: self._on_auto_mining_changed(e.control.value),
            active_color="#00a1ff"
        )
        
        self.difficulty_field = ft.TextField(
            label="Mining Difficulty",
            value=str(self.app.node.config.difficulty) if self.app.node else "2",
            on_change=lambda e: self._on_difficulty_changed(e.control.value),
            border_color="#1e3a5c",
            bgcolor="#0a1423",
            color="#e3f2fd",
            keyboard_type=ft.KeyboardType.NUMBER,
            width=150
        )
        
        self.mining_interval_field = ft.TextField(
            label="Mining Interval (seconds)",
            value=str(self.app.node.config.mining_interval) if self.app.node else "30",
            on_change=lambda e: self._on_mining_interval_changed(e.control.value),
            border_color="#1e3a5c",
            bgcolor="#0a1423",
            color="#e3f2fd",
            keyboard_type=ft.KeyboardType.NUMBER,
            width=180
        )
        
        self.gpu_acceleration_switch = ft.Switch(
            label="GPU Acceleration",
            value=self.app.node.cuda_available if self.app.node else False,
            on_change=lambda e: self._on_gpu_acceleration_changed(e.control.value),
            active_color="#00a1ff"
        )
        
        return ft.Container(
            content=ft.Column([
                ft.Text("⛏️ Mining Settings", size=18, color="#00a1ff", weight=ft.FontWeight.BOLD),
                ft.Container(height=15),
                ft.Row([
                    self.auto_mining_switch,
                    ft.Container(width=20),
                    self.gpu_acceleration_switch
                ]),
                ft.Container(height=15),
                ft.Row([
                    self.difficulty_field,
                    ft.Container(width=20),
                    self.mining_interval_field
                ]),
                ft.Container(height=10),
                ft.Text(
                    "Difficulty: Higher values make mining harder but more rewarding",
                    size=12, color="#8b9cb5"
                ),
                ft.Text(
                    "Interval: Time between auto-mining attempts",
                    size=12, color="#8b9cb5"
                )
            ]),
            padding=20,
            bgcolor="#1a2b3c",
            border_radius=8,
            border=ft.border.all(1, "#2d4a6c")
        )

    def _create_network_settings(self):
        """Create network-related settings"""
        self.node_url_field = ft.TextField(
            label="Node URL",
            value=self.app.node.config.node_url if self.app.node else "https://bank.linglin.art",
            on_change=lambda e: self._on_node_url_changed(e.control.value),
            border_color="#1e3a5c",
            bgcolor="#0a1423",
            color="#e3f2fd",
            width=400
        )
        
        self.network_timeout_field = ft.TextField(
            label="Network Timeout (seconds)",
            value="30",
            on_change=lambda e: self._on_network_timeout_changed(e.control.value),
            border_color="#1e3a5c",
            bgcolor="#0a1423",
            color="#e3f2fd",
            keyboard_type=ft.KeyboardType.NUMBER,
            width=180
        )
        
        self.auto_sync_field = ft.TextField(
            label="Auto Sync Interval (minutes)",
            value="5",
            on_change=lambda e: self._on_auto_sync_changed(e.control.value),
            border_color="#1e3a5c",
            bgcolor="#0a1423",
            color="#e3f2fd",
            keyboard_type=ft.KeyboardType.NUMBER,
            width=180
        )
        
        return ft.Container(
            content=ft.Column([
                ft.Text("🌐 Network Settings", size=18, color="#00a1ff", weight=ft.FontWeight.BOLD),
                ft.Container(height=15),
                self.node_url_field,
                ft.Container(height=15),
                ft.Row([
                    self.network_timeout_field,
                    ft.Container(width=20),
                    self.auto_sync_field
                ]),
                ft.Container(height=10),
                ft.Text(
                    "Node URL: The blockchain node to connect to",
                    size=12, color="#8b9cb5"
                ),
                ft.Text(
                    "Auto Sync: How often to automatically sync with the network",
                    size=12, color="#8b9cb5"
                )
            ]),
            padding=20,
            bgcolor="#1a2b3c",
            border_radius=8,
            border=ft.border.all(1, "#2d4a6c")
        )

    def _create_performance_settings(self):
        """Create performance-related settings"""
        self.thread_count_field = ft.TextField(
            label="Mining Threads",
            value="1",
            on_change=lambda e: self._on_thread_count_changed(e.control.value),
            border_color="#1e3a5c",
            bgcolor="#0a1423",
            color="#e3f2fd",
            keyboard_type=ft.KeyboardType.NUMBER,
            width=120
        )
        
        self.batch_size_field = ft.TextField(
            label="Batch Size",
            value="100000",
            on_change=lambda e: self._on_batch_size_changed(e.control.value),
            border_color="#1e3a5c",
            bgcolor="#0a1423",
            color="#e3f2fd",
            keyboard_type=ft.KeyboardType.NUMBER,
            width=120
        )
        
        self.cache_size_field = ft.TextField(
            label="Cache Size (MB)",
            value="100",
            on_change=lambda e: self._on_cache_size_changed(e.control.value),
            border_color="#1e3a5c",
            bgcolor="#0a1423",
            color="#e3f2fd",
            keyboard_type=ft.KeyboardType.NUMBER,
            width=120
        )
        
        self.performance_dropdown = ft.Dropdown(
            label="Performance Mode",
            value="balanced",
            options=[
                ft.dropdown.Option("power_saver", "Power Saver"),
                ft.dropdown.Option("balanced", "Balanced"),
                ft.dropdown.Option("high_performance", "High Performance"),
            ],
            border_color="#1e3a5c",
            bgcolor="#0a1423",
            color="#e3f2fd",
            width=180,
            on_change=lambda e: self._on_performance_mode_changed(e.control.value)
        )
        
        return ft.Container(
            content=ft.Column([
                ft.Text("⚡ Performance Settings", size=18, color="#00a1ff", weight=ft.FontWeight.BOLD),
                ft.Container(height=15),
                ft.Row([
                    self.thread_count_field,
                    ft.Container(width=20),
                    self.batch_size_field,
                    ft.Container(width=20),
                    self.cache_size_field
                ]),
                ft.Container(height=15),
                self.performance_dropdown,
                ft.Container(height=10),
                ft.Text(
                    "Threads: More threads can improve mining speed but use more CPU",
                    size=12, color="#8b9cb5"
                ),
                ft.Text(
                    "Performance Mode: Adjusts resource usage for different scenarios",
                    size=12, color="#8b9cb5"
                )
            ]),
            padding=20,
            bgcolor="#1a2b3c",
            border_radius=8,
            border=ft.border.all(1, "#2d4a6c")
        )

    def _create_wallet_settings(self):
        """Create wallet-related settings"""
        self.miner_address_field = ft.TextField(
            label="Miner Wallet Address",
            value=self.app.node.config.miner_address if self.app.node else "LUN_Node_Miner_Default",
            on_change=lambda e: self._on_miner_address_changed(e.control.value),
            border_color="#1e3a5c",
            bgcolor="#0a1423",
            color="#e3f2fd",
            width=300
        )
        
        self.rewards_address_field = ft.TextField(
            label="🎯 Rewards Address",
            hint_text="Enter your Luna wallet address for receiving rewards",
            value=getattr(self.app.node.config, 'rewards_address', '') if self.app.node else "",
            on_change=lambda e: self._on_rewards_address_changed(e.control.value),
            border_color="#1e3a5c",
            bgcolor="#0a1423",
            color="#e3f2fd",
            width=300
        )
        
        self.wallet_encryption_switch = ft.Switch(
            label="Encrypt Wallet Data",
            value=True,
            on_change=lambda e: self._on_wallet_encryption_changed(e.control.value),
            active_color="#00a1ff"
        )
        
        self.auto_backup_switch = ft.Switch(
            label="Auto Backup Wallet",
            value=True,
            on_change=lambda e: self._on_auto_backup_changed(e.control.value),
            active_color="#00a1ff"
        )
        
        return ft.Container(
            content=ft.Column([
                ft.Text("💰 Wallet Settings", size=18, color="#00a1ff", weight=ft.FontWeight.BOLD),
                ft.Container(height=15),
                self.miner_address_field,
                ft.Container(height=15),
                self.rewards_address_field,
                ft.Container(height=15),
                ft.Row([
                    self.wallet_encryption_switch,
                    ft.Container(width=20),
                    self.auto_backup_switch
                ]),
                ft.Container(height=10),
                ft.Text(
                    "Miner Address: Internal address for mining operations",
                    size=12, color="#8b9cb5"
                ),
                ft.Text(
                    "Rewards Address: Your personal Luna wallet address to receive mining rewards",
                    size=12, color="#90EE90"
                ),
                ft.Text(
                    "Encryption: Secures your wallet data with password protection",
                    size=12, color="#8b9cb5"
                )
            ]),
            padding=20,
            bgcolor="#1a2b3c",
            border_radius=8,
            border=ft.border.all(1, "#2d4a6c")
        )

    def _create_advanced_settings(self):
        """Create advanced settings"""
        self.log_level_dropdown = ft.Dropdown(
            label="Log Level",
            value="info",
            options=[
                ft.dropdown.Option("debug", "Debug"),
                ft.dropdown.Option("info", "Info"),
                ft.dropdown.Option("warning", "Warning"),
                ft.dropdown.Option("error", "Error"),
            ],
            border_color="#1e3a5c",
            bgcolor="#0a1423",
            color="#e3f2fd",
            width=150,
            on_change=lambda e: self._on_log_level_changed(e.control.value)
        )
        
        self.data_retention_field = ft.TextField(
            label="Data Retention (days)",
            value="30",
            on_change=lambda e: self._on_data_retention_changed(e.control.value),
            border_color="#1e3a5c",
            bgcolor="#0a1423",
            color="#e3f2fd",
            keyboard_type=ft.KeyboardType.NUMBER,
            width=120
        )
        
        self.reset_stats_button = ft.ElevatedButton(
            "Reset Statistics",
            on_click=lambda e: self._on_reset_stats_clicked(),
            style=ft.ButtonStyle(
                color="#ffffff",
                bgcolor="#dc3545",
                padding=ft.padding.symmetric(horizontal=16, vertical=8)
            ),
            height=32
        )
        
        return ft.Container(
            content=ft.Column([
                ft.Text("🔧 Advanced Settings", size=18, color="#00a1ff", weight=ft.FontWeight.BOLD),
                ft.Container(height=15),
                ft.Row([
                    self.log_level_dropdown,
                    ft.Container(width=20),
                    self.data_retention_field
                ]),
                ft.Container(height=15),
                ft.Row([self.reset_stats_button]),
                ft.Container(height=10),
                ft.Text(
                    "Log Level: Controls how much detail is recorded in logs",
                    size=12, color="#8b9cb5"
                ),
                ft.Text(
                    "Data Retention: How long to keep historical data",
                    size=12, color="#8b9cb5"
                )
            ]),
            padding=20,
            bgcolor="#1a2b3c",
            border_radius=8,
            border=ft.border.all(1, "#2d4a6c")
        )

    def _create_action_buttons(self):
        """Create action buttons for settings"""
        return ft.Container(
            content=ft.Row([
                ft.ElevatedButton(
                    "💾 Save Settings",
                    on_click=lambda e: self._on_save_settings_clicked(),
                    style=ft.ButtonStyle(
                        color="#ffffff",
                        bgcolor="#28a745",
                        padding=ft.padding.symmetric(horizontal=24, vertical=12)
                    ),
                    height=44
                ),
                ft.Container(width=15),
                ft.ElevatedButton(
                    "🔄 Reset to Defaults",
                    on_click=lambda e: self._on_reset_defaults_clicked(),
                    style=ft.ButtonStyle(
                        color="#ffffff",
                        bgcolor="#6c757d",
                        padding=ft.padding.symmetric(horizontal=24, vertical=12)
                    ),
                    height=44
                ),
                ft.Container(width=15),
                ft.ElevatedButton(
                    "📤 Export Settings",
                    on_click=lambda e: self._on_export_settings_clicked(),
                    style=ft.ButtonStyle(
                        color="#ffffff",
                        bgcolor="#17a2b8",
                        padding=ft.padding.symmetric(horizontal=24, vertical=12)
                    ),
                    height=44
                )
            ], alignment=ft.MainAxisAlignment.CENTER),
            padding=20
        )

    # Event handlers for settings changes
    def _on_auto_mining_changed(self, value: bool):
        if self.app.node:
            self.app.node.toggle_auto_mining(value)

    def _on_difficulty_changed(self, value: str):
        if self.app.node and value.isdigit():
            self.app.node.update_difficulty(int(value))

    def _on_mining_interval_changed(self, value: str):
        if self.app.node and value.isdigit():
            self.app.node.update_mining_interval(int(value))

    def _on_gpu_acceleration_changed(self, value: bool):
        self.app.add_log_message(f"GPU acceleration {'enabled' if value else 'disabled'}", "info")

    def _on_node_url_changed(self, value: str):
        if self.app.node:
            self.app.node.update_node_url(value)

    def _on_network_timeout_changed(self, value: str):
        if value.isdigit():
            self.app.add_log_message(f"Network timeout set to {value}s", "info")

    def _on_auto_sync_changed(self, value: str):
        if value.isdigit():
            self.app.add_log_message(f"Auto-sync interval set to {value} minutes", "info")

    def _on_thread_count_changed(self, value: str):
        if value.isdigit():
            self.app.add_log_message(f"Mining threads set to {value}", "info")

    def _on_batch_size_changed(self, value: str):
        if value.isdigit():
            self.app.add_log_message(f"Batch size set to {value}", "info")

    def _on_cache_size_changed(self, value: str):
        if value.isdigit():
            self.app.add_log_message(f"Cache size set to {value}MB", "info")

    def _on_performance_mode_changed(self, value: str):
        self.app.add_log_message(f"Performance mode set to {value}", "info")

    def _on_miner_address_changed(self, value: str):
        if self.app.node:
            self.app.node.update_wallet_address(value)

    def _on_wallet_encryption_changed(self, value: bool):
        self.app.add_log_message(f"Wallet encryption {'enabled' if value else 'disabled'}", "info")

    def _on_auto_backup_changed(self, value: bool):
        self.app.add_log_message(f"Auto backup {'enabled' if value else 'disabled'}", "info")

    def _on_log_level_changed(self, value: str):
        self.app.add_log_message(f"Log level set to {value}", "info")

    def _on_data_retention_changed(self, value: str):
        if value.isdigit():
            self.app.add_log_message(f"Data retention set to {value} days", "info")

    def _on_rewards_address_changed(self, value: str):
        """Handle rewards address changes"""
        if self.app.node:
            if not hasattr(self.app.node.config, 'rewards_address'):
                self.app.node.config.rewards_address = ""
            
            self.app.node.config.rewards_address = value.strip()
            
            if hasattr(self.app.node.config, 'save_to_storage'):
                self.app.node.config.save_to_storage()
            
            self.app.add_log_message(f"Rewards address updated: {value}", "success")

    def _on_reset_stats_clicked(self):
        def confirm_reset(e):
            self.app.add_log_message("Statistics reset", "info")
            dialog.open = False
            self.app.page.update()
        
        dialog = ft.AlertDialog(
            modal=True,
            title=ft.Text("Reset Statistics"),
            content=ft.Text("Are you sure you want to reset all mining statistics? This action cannot be undone."),
            actions=[
                ft.TextButton("Cancel", on_click=lambda e: setattr(dialog, 'open', False)),
                ft.TextButton("Reset", on_click=confirm_reset, style=ft.ButtonStyle(color="#dc3545")),
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        
        self.app.page.dialog = dialog
        dialog.open = True
        self.app.page.update()

    def _on_save_settings_clicked(self):
        self.app.save_settings()

    def _on_reset_defaults_clicked(self):
        if self.app.node:
            self.app.node.config.miner_address = "LUN_Node_Miner_Default"
            self.app.node.config.difficulty = 2
            self.app.node.config.auto_mine = False
            self.app.node.config.mining_interval = 30
            self.app.node.config.node_url = "https://bank.linglin.art"
            
            if hasattr(self.app.node.config, 'rewards_address'):
                self.app.node.config.rewards_address = ""
            
            self.app.node.config.save_to_storage()
            
            self.update_settings_content()
            self.app.add_log_message("Settings reset to defaults", "success")

    def _on_export_settings_clicked(self):
        self.app.add_log_message("Settings export feature coming soon", "info")