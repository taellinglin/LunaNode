"""
Donut Chart Component - Declarative with hooks
"""
import flet as ft
from ..theme import Colors, Spacing, Typography



def donut_chart(title: str, sections: list):
    """
    A donut chart visualization with legend
    sections: list of dicts [{"value": 35, "color": "#0099ff", "label": "CPU: 35%"}]
    """
    # Calculate total for visualization
    total = sum(section["value"] for section in sections)

    # Create legend items
    legend_items = []
    for section in sections:
        legend_items.append(
            ft.Row(
                controls=[
                    ft.Container(
                        width=12,
                        height=12,
                        bgcolor=section["color"],
                        border_radius=2
                    ),
                    ft.Text(
                        section["label"],
                        size=Typography.SIZE_SM,
                        color=Colors.TEXT_SECONDARY
                    )
                ],
                spacing=Spacing.SM
            )
        )

    # Create pie chart sections
    pie_sections = []
    for section in sections:
        if section["value"] > 0:
            pie_sections.append(
                ft.PieChartSection(
                    value=section["value"],
                    color=section["color"],
                    radius=50,
                    border_side=ft.BorderSide(0, Colors.BG_CARD)
                )
            )

    # Visual chart
    visual_chart = ft.Container(
        content=ft.PieChart(
            sections=pie_sections if pie_sections else [
                ft.PieChartSection(value=1, color=Colors.TEXT_MUTED, radius=50)
            ],
            sections_space=2,
            center_space_radius=30,
            expand=True
        ) if pie_sections else ft.Text("No data", size=Typography.SIZE_SM, color=Colors.TEXT_SECONDARY),
        width=180,
        height=180,
        alignment=ft.alignment.center
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
                ft.Container(height=Spacing.MD),
                ft.Row(
                    controls=[
                        visual_chart,
                        ft.Container(width=Spacing.LG),
                        ft.Column(
                            controls=legend_items,
                            spacing=Spacing.MD,
                            alignment=ft.MainAxisAlignment.CENTER
                        )
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                    expand=True
                )
            ],
            spacing=0
        ),
        bgcolor=Colors.BG_CARD,
        padding=Spacing.LG,
        border_radius=8,
        border=ft.border.all(1, Colors.BORDER),
        height=320,
        expand=True
    )
