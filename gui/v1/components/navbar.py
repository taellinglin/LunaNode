"""
NavBar Component - Declarative with hooks
"""
from dataclasses import dataclass

import flet as ft

from ..theme import Colors, Spacing, Typography, Layout


@dataclass
class NavBarTab:
    label: str
    page: str


tabs = [
    NavBarTab(label="Mining", page="mining"),
    NavBarTab(label="Bills", page="bills"),
    NavBarTab(label="Stats", page="stats"),
    NavBarTab(label="Settings", page="settings"),
    NavBarTab(label="Log", page="log")
]


@ft.component
def NavBar(current_page: NavBarTab, on_navigate):
    """
    Top navigation bar with tabs
    Pure functional component - UI = f(current_page, on_navigate)
    """

    # Create tab buttons
    tab_buttons = []
    for tab in tabs:
        is_active = current_page == tab
        tab_buttons.append(
            ft.Container(
                content=ft.Column(
                    controls=[
                        ft.Text(
                            tab.label,
                            size=Typography.SIZE_MD,
                            color=Colors.PRIMARY if is_active else Colors.TEXT_SECONDARY,
                            weight=ft.FontWeight.W_500 if is_active else ft.FontWeight.NORMAL
                        ),
                        ft.Container(
                            height=2,
                            bgcolor=Colors.PRIMARY if is_active else "transparent",
                            margin=ft.Margin.only(top=Spacing.MD)
                        )
                    ],
                    spacing=0,
                    horizontal_alignment=ft.CrossAxisAlignment.START
                ),
                on_click=lambda _, p=tab: on_navigate(p),
                padding=0
            )
        )

    return ft.Container(
        content=ft.Row(
            controls=tab_buttons,
            spacing=Spacing.XL,
            alignment=ft.MainAxisAlignment.START
        ),
        height=Layout.NAVBAR_HEIGHT,
        bgcolor=Colors.BG_DARK,
        padding=ft.Padding.only(left=Spacing.XL, right=Spacing.XL, top=Spacing.MD, bottom=0)
    )
