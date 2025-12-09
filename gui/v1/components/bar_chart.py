"""
Bar Chart Component - Declarative with hooks
"""
import flet as ft
from ..theme import Colors, Spacing, Typography



def bar_chart_card(title: str, data: list, color: str, max_value: float = None):
    """
    A card containing a bar chart for trend visualization
    data: list of values for the bars
    """
    # Determine max value
    chart_max = max_value or (max(data) * 1.2 if data and any(v > 0 for v in data) else 100)

    # Create bars
    bars = []
    display_data = data if data and any(v > 0 for v in data) else [1] * 20
    bar_color = color if data and any(v > 0 for v in data) else Colors.BG_HOVER

    for value in display_data:
        normalized_height = (value / chart_max * 100) if chart_max > 0 else 10
        bars.append(
            ft.Container(
                width=8,
                height=max(4, normalized_height),
                bgcolor=bar_color,
                border_radius=2
            )
        )

    return ft.Container(
        content=ft.Column(
            controls=[
                ft.Text(
                    title,
                    size=Typography.SIZE_MD,
                    color=Colors.TEXT_PRIMARY,
                    weight=ft.FontWeight.W_500
                ),
                ft.Container(height=Spacing.SM),
                ft.Container(
                    content=ft.Row(
                        controls=bars,
                        spacing=4,
                        alignment=ft.MainAxisAlignment.SPACE_EVENLY,
                        vertical_alignment=ft.CrossAxisAlignment.END
                    ),
                    bgcolor=Colors.BG_DARK,
                    padding=Spacing.MD,
                    border_radius=4,
                    expand=True,
                    height=120
                )
            ],
            spacing=0,
            expand=True
        ),
        bgcolor=Colors.BG_CARD,
        padding=Spacing.LG,
        border_radius=8,
        border=ft.Border.all(1, Colors.BORDER),
        height=200,
        expand=True
    )
