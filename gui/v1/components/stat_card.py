"""
Stat Card Component - Declarative with hooks
"""
import flet as ft
from flet import IconData

from ..theme import Colors, Spacing, Typography


def stat_card(icon: IconData, icon_color: str, label: str, value: str):
    """
    A card displaying a statistic with an icon, label, and value
    Pure functional component using hooks
    """
    return ft.Container(
        content=ft.Column(
            controls=[
                # Icon and label row
                ft.Row(
                    controls=[
                        ft.Icon(icon, color=icon_color, size=20),
                        ft.Text(
                            label,
                            size=Typography.SIZE_SM,
                            color=Colors.TEXT_SECONDARY,
                            weight=ft.FontWeight.NORMAL
                        )
                    ],
                    spacing=Spacing.SM
                ),
                ft.Container(height=Spacing.SM),
                # Value
                ft.Text(
                    value,
                    size=Typography.SIZE_HEADING,
                    color=Colors.TEXT_PRIMARY,
                    weight=ft.FontWeight.BOLD
                )
            ],
            spacing=0,
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN
        ),
        bgcolor=Colors.BG_CARD,
        padding=Spacing.LG,
        border_radius=8,
        border=ft.Border.all(1, Colors.BORDER),
        height=100,
        expand=True
    )
