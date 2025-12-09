"""
Metric Card Component - Declarative with hooks
"""
import flet as ft
from ..theme import Colors, Spacing, Typography



def metric_card(icon: str, label: str, value: str, percentage: float, color: str):
    """
    A card displaying a system metric with progress bar
    Pure functional component
    """
    return ft.Container(
        content=ft.Column(
            controls=[
                # Icon and label
                ft.Row(
                    controls=[
                        ft.Icon(icon, color=color, size=18),
                        ft.Text(
                            label,
                            size=Typography.SIZE_SM,
                            color=Colors.TEXT_SECONDARY
                        )
                    ],
                    spacing=Spacing.SM
                ),
                ft.Container(height=Spacing.MD),
                # Value
                ft.Text(
                    value,
                    size=Typography.SIZE_XXL,
                    color=color,
                    weight=ft.FontWeight.BOLD
                ),
                ft.Container(height=Spacing.SM),
                # Progress bar
                ft.ProgressBar(
                    value=percentage / 100,
                    color=color,
                    bgcolor=Colors.BG_DARK,
                    height=6,
                    border_radius=3
                )
            ],
            spacing=0
        ),
        bgcolor=Colors.BG_CARD,
        padding=Spacing.LG,
        border_radius=8,
        border=ft.border.all(1, Colors.BORDER),
        height=100,
        expand=True
    )
