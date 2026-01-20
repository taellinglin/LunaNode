import flet as ft
import time
from datetime import datetime, timedelta
from typing import Dict, List
import random  # For demo data, remove in production

class MiningHistory:
    def __init__(self, app):
        self.app = app
        self.stats_content = ft.Column()
        # (SVG chart demo data removed)
        self.current_session_stats = ft.Column()

    # (SVG chart code removed)

    def create_history_tab(self):
        """Task Manager Performance-style stats tab (dummy data)"""
        # Initial content
        self.update_history_content()
        return ft.Container(
            content=ft.Column([
                ft.Container(
                    content=self.stats_content,
                    expand=True,
                    border=ft.Border.all(1, "#1e3a5c"),
                    border_radius=8,
                    padding=20,
                    bgcolor=None
                )
            ], expand=True, spacing=20),
            padding=20,
            bgcolor=None,
            expand=True
        )

    def update_history_content(self):
        self.stats_content.controls.clear()

        history = []
        if self.app and getattr(self.app, "node", None):
            try:
                history = self.app.node.get_mining_history()
            except Exception:
                history = []

        session_stats = self._create_session_stats(history)
        performance_charts = self._create_performance_charts(history)
        history_table = self._create_compact_history_table(history)

        self.stats_content.controls.append(session_stats)
        self.stats_content.controls.append(performance_charts)
        self.stats_content.controls.append(history_table)

        if self.app.page:
            self.app.page.update()

    def _create_session_stats(self, history: List[Dict]):
        """Create current session statistics"""
        if not history:
            return ft.Container(
                content=ft.Text("No mining data available", color="#6c757d", size=14),
                padding=20,
                bgcolor="#1a2b3c",
                border_radius=4
            )
        
        # Calculate session stats
        successful_blocks = len([r for r in history if r.get('status') == 'success'])
        total_attempts = len(history)
        success_rate = (successful_blocks / total_attempts * 100) if total_attempts > 0 else 0
        
        total_mining_time = sum(r.get('mining_time', 0) for r in history)
        avg_mining_time = total_mining_time / total_attempts if total_attempts > 0 else 0
        
        # Get recent hash rate from node
        current_hash_rate = self.app.node.miner.hash_rate if self.app.node and self.app.node.miner else 0
        
        return ft.Container(
            content=ft.ResponsiveRow([
                self._create_stat_card("⛏️ Blocks Mined", str(successful_blocks), "#00a1ff"),
                self._create_stat_card("🎯 Success Rate", f"{success_rate:.1f}%", 
                                     "#28a745" if success_rate > 50 else "#ffc107"),
                self._create_stat_card("⚡ Hash Rate", f"{current_hash_rate:,.0f} H/s", "#00a1ff"),
                self._create_stat_card("⏱️ Avg Time", f"{avg_mining_time:.2f}s", 
                                     "#28a745" if avg_mining_time < 10 else "#ffc107"),
                self._create_stat_card(" Total Attempts", str(total_attempts), "#6c757d"),
                self._create_stat_card("💰 Total Reward", f"{successful_blocks * 50:.2f} LKC", "#28a745"),
            ]),
            padding=10,
            bgcolor="#1a2b3c",
            border_radius=4
        )

    def _create_performance_charts(self, history: List[Dict]):
        """Create performance charts"""
        if len(history) < 2:
            return ft.Container(
                content=ft.Text("Need more data to display charts", color="#6c757d", size=14),
                padding=20,
                bgcolor="#1a2b3c",
                border_radius=4
            )
        
        # Prepare chart data (last 20 records)
        recent_history = history[-20:]
        
        # Hash Rate Chart
        hash_rate_data = self._prepare_hash_rate_data(recent_history)
        hash_rate_chart = self._create_line_chart("Hash Rate (H/s)", hash_rate_data, "#00a1ff")
        
        # Success Rate Chart (rolling window)
        success_rate_data = self._prepare_success_rate_data(recent_history)
        success_rate_chart = self._create_line_chart("Success Rate (%)", success_rate_data, "#28a745")
        
        # Mining Time Chart
        mining_time_data = self._prepare_mining_time_data(recent_history)
        mining_time_chart = self._create_line_chart("Mining Time (s)", mining_time_data, "#ffc107")
        
        return ft.ResponsiveRow([
            ft.Container(
                content=ft.Column([
                    ft.Text("Hash Rate Trend", size=14, color="#e3f2fd"),
                    hash_rate_chart
                ]),
                padding=10,
                bgcolor="#1a2b3c",
                border_radius=4,
                col={"sm": 12, "md": 6, "lg": 4}
            ),
            ft.Container(
                content=ft.Column([
                    ft.Text("Success Rate Trend", size=14, color="#e3f2fd"),
                    success_rate_chart
                ]),
                padding=10,
                bgcolor="#1a2b3c",
                border_radius=4,
                col={"sm": 12, "md": 6, "lg": 4}
            ),
            ft.Container(
                content=ft.Column([
                    ft.Text("Mining Time Trend", size=14, color="#e3f2fd"),
                    mining_time_chart
                ]),
                padding=10,
                bgcolor="#1a2b3c",
                border_radius=4,
                col={"sm": 12, "md": 6, "lg": 4}
            ),
        ])

    def _create_system_performance(self):
        """Create system performance metrics"""
        # These would be populated from actual system monitoring
        # For now, using demo data
        cpu_usage = random.randint(20, 80)
        memory_usage = random.randint(30, 70)
        gpu_usage = random.randint(10, 90) if self.app.node and self.app.node.cuda_available else 0
        network_latency = random.randint(50, 200)
        
        return ft.Container(
            content=ft.ResponsiveRow([
                self._create_gauge_card("💻 CPU Usage", f"{cpu_usage}%", cpu_usage, "#00a1ff"),
                self._create_gauge_card("🧠 Memory Usage", f"{memory_usage}%", memory_usage, "#17a2b8"),
                self._create_gauge_card("🎮 GPU Usage", f"{gpu_usage}%", gpu_usage, "#28a745"),
                self._create_gauge_card("🌐 Network Latency", f"{network_latency}ms", 
                                      max(0, 100 - (network_latency / 2)), "#ffc107"),
            ]),
            padding=10,
            bgcolor="#1a2b3c",
            border_radius=4
        )

    def _create_compact_history_table(self, history: List[Dict]):
        """Create compact history table"""
        table = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("Time", color="#e3f2fd", size=12)),
                ft.DataColumn(ft.Text("Block", color="#e3f2fd", size=12)),
                ft.DataColumn(ft.Text("Duration", color="#e3f2fd", size=12)),
                ft.DataColumn(ft.Text("Hash Rate", color="#e3f2fd", size=12)),
                ft.DataColumn(ft.Text("Status", color="#e3f2fd", size=12)),
            ],
            rows=[],
            vertical_lines=ft.BorderSide(1, "#1e3a5c"),
            horizontal_lines=ft.BorderSide(1, "#1e3a5c"),
            bgcolor="#0f1a2a",
        )
        
        for record in reversed(history[-10:]):  # Show last 10
            timestamp = datetime.fromtimestamp(record['timestamp']).strftime("%H:%M:%S")
            mining_time = f"{record.get('mining_time', 0):.2f}s"
            
            # Calculate hash rate for this attempt
            hash_rate = record.get('nonce', 0) / max(record.get('mining_time', 1), 0.1)
            hash_rate_display = f"{hash_rate:,.0f} H/s"
            
            status_text = "✅" if record.get('status') == 'success' else "❌"
            status_color = "#28a745" if record.get('status') == 'success' else "#dc3545"
            
            row = ft.DataRow(cells=[
                ft.DataCell(ft.Text(timestamp, color="#e3f2fd", size=11)),
                ft.DataCell(ft.Text(f"#{record.get('block_index', 'N/A')}", color="#e3f2fd", size=11)),
                ft.DataCell(ft.Text(mining_time, color="#e3f2fd", size=11)),
                ft.DataCell(ft.Text(hash_rate_display, color="#00a1ff", size=11)),
                ft.DataCell(ft.Text(status_text, color=status_color, size=11)),
            ])
            table.rows.append(row)
        
        return ft.Container(
            content=ft.Column([
                ft.Text("Recent Mining Activity", size=14, color="#e3f2fd"),
                table
            ]),
            padding=10,
            bgcolor="#1a2b3c",
            border_radius=4
        )

    def _create_stat_card(self, title: str, value: str, color: str):
        """Create a statistics card"""
        return ft.Container(
            content=ft.Column([
                ft.Text(title, size=12, color="#e3f2fd"),
                ft.Text(value, size=16, weight=ft.FontWeight.BOLD, color=color),
            ], spacing=2, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            padding=15,
            margin=3,
            bgcolor="#0f1a2a",
            border=ft.Border.all(1, "#1e3a5c"),
            border_radius=4,
            col={"xs": 6, "sm": 4, "md": 3, "lg": 2}
        )

    def _create_gauge_card(self, title: str, value: str, percentage: int, color: str):
        """Create a gauge-style performance card"""
        return ft.Container(
            content=ft.Column([
                ft.Text(title, size=12, color="#e3f2fd"),
                ft.Text(value, size=14, weight=ft.FontWeight.BOLD, color=color),
                ft.Container(
                    content=ft.Container(
                        width=percentage * 0.8,  # Scale to container
                        height=4,
                        bgcolor=color,
                        border_radius=2
                    ),
                    width=80,
                    height=4,
                    bgcolor="#1e3f5c",
                    border_radius=2,
                    margin=ft.margin.only(top=5)
                )
            ], spacing=2, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            padding=15,
            margin=3,
            bgcolor="#0f1a2a",
            border=ft.Border.all(1, "#1e3a5c"),
            border_radius=4,
            col={"xs": 6, "sm": 4, "md": 3, "lg": 3}
        )

    def _create_line_chart(self, title: str, data_points: List, color: str):
        print(f"[DEBUG] _create_line_chart called with title={title}, data_points={data_points}")
        # Flatten in case data_points is a list of lists
        if any(isinstance(y, list) for y in data_points):
            data_points = [item for sublist in data_points for item in (sublist if isinstance(sublist, list) else [sublist])]
        print(f"[DEBUG] _create_line_chart flattened data_points={data_points}")
        if not data_points:
            return ft.Container(
                content=ft.Text("No data", color="#6c757d", size=12),
                height=100,
                alignment="center"
            )
        
        # Create simple line chart using containers
        max_value = max(data_points) if data_points else 1
        min_value = min(data_points) if data_points else 0
        value_range = max_value - min_value if max_value != min_value else 1
        
        chart_points = []
        for i, value in enumerate(data_points):
            normalized_height = ((value - min_value) / value_range) * 80  # Scale to 80px height
            chart_points.append(
                ft.Container(
                    width=4,
                    height=normalized_height,
                    bgcolor=color,
                    border_radius=2,
                    margin=ft.margin.only(right=2)
                )
            )
        
        return ft.Container(
            content=ft.Column([
                ft.Container(
                    content=ft.Row(chart_points, spacing=2),
                    height=80,
                    alignment=ft.alignment.bottom_center
                ),
                ft.Container(height=5),
                ft.Text(f"Min: {min_value:.1f} | Max: {max_value:.1f}", size=10, color="#6c757d")
            ]),
            height=100,
            alignment="center"
        )

    def _prepare_hash_rate_data(self, history: List[Dict]):
        """Prepare hash rate data for charting"""
        data = []
        for record in history:
            if record.get('mining_time', 0) > 0:
                hash_rate = record.get('nonce', 0) / record['mining_time']
                data.append(hash_rate)
        return data or [0]

    def _prepare_success_rate_data(self, history: List[Dict]):
        """Prepare success rate data for charting (rolling window)"""
        data = []
        window_size = 5
        for i in range(len(history)):
            window = history[max(0, i - window_size + 1):i + 1]
            successful = len([r for r in window if r.get('status') == 'success'])
            rate = (successful / len(window)) * 100 if window else 0
            data.append(rate)
        return data or [0]

    def _prepare_mining_time_data(self, history: List[Dict]):
        """Prepare mining time data for charting"""
        data = [r.get('mining_time', 0) for r in history]
        return data or [0]