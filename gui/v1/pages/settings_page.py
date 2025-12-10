import flet as ft

from gui.v1.theme import Colors


@ft.component
def SettingsPage():
    return ft.Container(
        content=ft.Text("Mining", color=Colors.TEXT_PRIMARY),
        expand=True
    )