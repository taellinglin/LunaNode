"""
Donut Chart Component - Declarative with hooks
"""

import flet as ft
import flet_charts as fch
from flet import CrossAxisAlignment

from ..theme import Colors, Spacing, Typography


@ft.component
def LegendItem(color: str, label: str):
    """
    A single legend item with color indicator and label
    """
    return ft.Row(
        controls=[
            ft.Container(
                width=12,
                height=12,
                bgcolor=color,
                border_radius=2
            ),
            ft.Text(
                label,
                size=Typography.SIZE_SM,
                color=Colors.TEXT_SECONDARY
            )
        ],
        spacing=Spacing.SM,
        wrap=True
    )


@ft.component
def Legend(sections: list):
    """
    Legend component displaying all chart sections
    sections: list of dicts [{"value": 35, "color": "#0099ff", "label": "CPU: 35%"}]
    """
    legend_items = [
        LegendItem(color=section["color"], label=section["label"])
        for section in sections
    ]

    return ft.Row(
        controls=legend_items,
        wrap=True,
        spacing=Spacing.MD,
        alignment=ft.MainAxisAlignment.CENTER
    )


@ft.component
def DonutChart(title: str, sections: list):
    """
    A donut chart visualization with legend using flet_charts.PieChart
    sections: list of dicts [{"value": 35, "color": "#0099ff", "label": "CPU: 35%"}]
    """
    # Create PieChartSections from data
    pie_sections = [
        fch.PieChartSection(
            value=section["value"],
            color=section["color"],
            radius=40,
            title="",
        )
        for section in sections if section["value"] > 0
    ]

    # Create the pie chart with donut effect
    chart = fch.PieChart(
        sections=pie_sections,
        sections_space=2,
        center_space_radius=50,
        center_space_color=Colors.BG_CARD,
    )

    # Chart container
    chart_container = ft.Container(
        content=chart,
        width=150,
        height=150,
        alignment=ft.Alignment.CENTER,
    )

    return ft.Container(
        content=ft.Column(
            controls=[
                ft.Row(
                    controls=[
                        ft.Text(
                            title,
                            size=Typography.SIZE_MD,
                            color=Colors.TEXT_PRIMARY,
                            weight=ft.FontWeight.W_500
                        ),
                    ]
                ),
                chart_container,
                Legend(sections=sections)
            ],
            spacing=Spacing.XXL,
            expand=True,
            horizontal_alignment=CrossAxisAlignment.CENTER
        ),
        bgcolor=Colors.BG_CARD,
        padding=Spacing.LG,
        border_radius=8,
        border=ft.Border.all(1, Colors.BORDER),
        expand=True
    )
