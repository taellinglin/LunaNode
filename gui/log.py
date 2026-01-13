import flet as ft
from datetime import datetime
from typing import List

class LogPage:
    def __init__(self, app):
        self.app = app
        self.log_output = ft.Column(scroll=ft.ScrollMode.ALWAYS)

    def create_log_tab(self):
        """Create log tab"""
        clear_button = ft.Button(
            "Clear Log",
            on_click=lambda e: self.clear_log(),
            style=ft.ButtonStyle(
                color="#ffffff",
                bgcolor="#00a1ff",
                padding=ft.Padding.symmetric(horizontal=16, vertical=10),
                shape=ft.RoundedRectangleBorder(radius=3)
            ),
            height=38
        )
        
        log_content = ft.Container(
            content=self.log_output,
            expand=True,
            border=ft.Border.all(1, "#1e3a5c"),
            border_radius=3,
            padding=10,
            bgcolor="#0f1a2a"
        )
        
        return ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Text("Application Log", size=16, color="#e3f2fd"),
                    clear_button
                ]),
                ft.Container(
                    content=ft.ListView([log_content], expand=True),
                    expand=True
                )
            ], expand=True),
            padding=10
        )

    def add_log_message(self, message: str, msg_type: str = "info"):
        """Add message to log"""
        try:
            message = message.encode('utf-8').decode('utf-8')  # Ensure UTF-8 encoding
        except UnicodeEncodeError:
            message = "[Invalid Unicode Character]"

        color_map = {
            "info": "#17a2b8",
            "success": "#28a745", 
            "warning": "#ffc107",
            "error": "#dc3545"
        }
        
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = ft.Row([
            ft.Text(f"[{timestamp}]", size=10, color="#6c757d", width=70),
            ft.Text(message, size=12, color=color_map.get(msg_type, "#e3f2fd"), expand=True)
        ], spacing=5)
        
        self.log_output.controls.append(log_entry)
        
        if len(self.log_output.controls) > 1000:
            self.log_output.controls.pop(0)
            
        if self.app.page and self.app.current_tab_index == 3:
            self.app.page.update()
        
    def clear_log(self):
        """Clear log output"""
        self.log_output.controls.clear()
        if self.app.page:
            self.app.page.update()