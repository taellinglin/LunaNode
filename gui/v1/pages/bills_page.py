import flet as ft

from gui.v1.theme import Colors


@ft.component
def BillsPage():
    return ft.Container(
        content=ft.Text("Bills", color=Colors.TEXT_PRIMARY),
        expand=True
    )