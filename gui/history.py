import flet as ft
import time
from datetime import datetime, timedelta
from typing import Dict, List
import random  # For demo data, remove in production

class MiningHistory:
    def __init__(self, app):
        self.app = app
        self.stats_content = ft.Column(expand=True, scroll=ft.ScrollMode.AUTO)

    # (SVG chart code removed)

    def create_history_tab(self):
        """Mining history tab (mined blocks only)"""
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
            expand=True,

        )

    def update_history_content(self):
        self.stats_content.controls.clear()

        # Mined Blocks panel (reuse bills page cards)
        if self.app and getattr(self.app, "bills_page", None):
            try:
                self.app.bills_page.update_bills_content(defer_scan=True)
            except Exception:
                pass
            cards = list(getattr(self.app.bills_page.tx_cards, "controls", []) or [])
            interleaved = []
            for idx, card in enumerate(cards):
                if idx > 0:
                    interleaved.append(ft.Divider(height=1, color="#1e3a5c"))
                interleaved.append(card)
            mined_blocks_panel = ft.Container(
                content=ft.Column([
                    ft.Text("Mined Blocks", size=14, color="#e3f2fd"),
                    ft.ListView(controls=interleaved, expand=True, spacing=0),

                ], expand=True, spacing=8),
                padding=10,
                bgcolor="#1a2b3c",
                border_radius=4,
                expand=True
            )
            
            
            self.stats_content.controls.append(mined_blocks_panel)

        if self.app.page:
            self.app.page.update()

