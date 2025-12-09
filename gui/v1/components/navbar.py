"""
NavBar Component - Declarative with hooks
"""
from dataclasses import dataclass
from enum import Enum

import flet as ft
from flet import IconData, Icons, CrossAxisAlignment

from ..theme import Colors, Spacing, Typography, Layout

class AppPage(Enum):
    MINING = 1
    BILLS = 2
    STATS = 3
    SETTINGS = 4
    LOG = 5

@dataclass
class NavBarTab:
    label: str
    page: AppPage
    icon: IconData




# TODO: Replace icons
# List of icons here: https://fonts.google.com/icons
tabs = [
    NavBarTab(label="Mining", page=AppPage.MINING, icon=Icons.CONSTRUCTION_ROUNDED),
    NavBarTab(label="Bills", page=AppPage.BILLS, icon=Icons.CURRENCY_BITCOIN),
    NavBarTab(label="Stats", page=AppPage.STATS, icon=Icons.QUERY_STATS),
    NavBarTab(label="Settings", page=AppPage.SETTINGS, icon=Icons.SETTINGS),
    NavBarTab(label="Log", page=AppPage.LOG, icon=Icons.NOTE)
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
                        ft.Row(
                            controls=[
                                ft.Icon(
                                    tab.icon,
                                    color=Colors.PRIMARY if is_active else Colors.TEXT_SECONDARY
                                ),
                                ft.Text(
                                    tab.label,
                                    size=Typography.SIZE_MD,
                                    color=Colors.PRIMARY if is_active else Colors.TEXT_SECONDARY,
                                    weight=ft.FontWeight.W_500 if is_active else ft.FontWeight.NORMAL
                                ),
                            ]
                        ),
                        ft.Container(
                            height=2,
                            width=40,
                            bgcolor=Colors.PRIMARY if is_active else "transparent",
                            margin=ft.Margin.only(top=Spacing.MD)
                        )
                    ],
                    spacing=0,
                    horizontal_alignment=CrossAxisAlignment.CENTER
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
