"""
Stat Card Component - Declarative with hooks
"""
import flet as ft
from flet import IconData

from ..theme import Colors, Spacing, Typography

@ft.component
def StatsCard(icon: IconData, icon_color: str, label: str, value: str, value_color=Colors.TEXT_PRIMARY):
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
                    size=Typography.SIZE_TITLE,
                    color=value_color,
                    weight=ft.FontWeight.W_400
                )
            ],
            spacing=0,
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN
        ),
        bgcolor=Colors.TRANSPARENT,
        padding=Spacing.LG,
        border_radius=8,
        border=ft.Border.all(2, Colors.BORDER),
        # height=100,
        expand=True
    )
