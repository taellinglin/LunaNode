import flet as ft
import time
from datetime import datetime, timedelta
from typing import Dict, List
import random  # For demo data, remove in production

class MiningHistory:
    def __init__(self, app):
        self.app = app
        self.stats_content = ft.Column()

    # (SVG chart code removed)

    def create_history_tab(self):
        """Mining history tab (table only)"""
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

        history_table = self._create_compact_history_table(history)
        self.stats_content.controls.append(history_table)

        if self.app.page:
            self.app.page.update()


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

