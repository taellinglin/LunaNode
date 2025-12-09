from typing import Container

import flet as ft

@ft.component
def MiningPage():
    return ft.Container(
        content=ft.Text("Mining"),
        expand=True
    )