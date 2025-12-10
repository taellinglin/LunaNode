"""
Donut Chart Component - Declarative with hooks
"""
import flet as ft
from ..theme import Colors, Spacing, Typography


@ft.component
def DonutChart(title: str, sections: list):
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

    # Create visual donut chart using Stack with circular containers
    # Calculate angles for each section
    circle_containers = []
    if total > 0:
        current_angle = -90  # Start at top
        for section in sections:
            if section["value"] > 0:
                percentage = section["value"] / total
                angle = percentage * 360

                # Create a colored segment indicator
                circle_containers.append(
                    ft.Container(
                        width=10,
                        height=10,
                        bgcolor=section["color"],
                        border_radius=5
                    )
                )
                current_angle += angle

    # Create donut visualization using concentric circles
    donut_layers = [
        # Outer colored ring (simplified representation)
        ft.Container(
            width=160,
            height=160,
            border_radius=80,
            bgcolor=Colors.BG_DARK,
            content=ft.Stack(
                controls=[
                    # Color segments arranged in a grid pattern
                    ft.Container(
                        content=ft.Row(
                            controls=[
                                ft.Column(
                                    controls=[
                                        ft.Container(
                                            width=70,
                                            height=70,
                                            bgcolor=sections[0]["color"] if len(sections) > 0 else Colors.TEXT_MUTED,
                                            border_radius=ft.BorderRadius.only(top_left=80)
                                        ),
                                        ft.Container(
                                            width=70,
                                            height=70,
                                            bgcolor=sections[2]["color"] if len(sections) > 2 else Colors.TEXT_MUTED,
                                            border_radius=ft.BorderRadius.only(bottom_left=80)
                                        ),
                                    ],
                                    spacing=0
                                ),
                                ft.Column(
                                    controls=[
                                        ft.Container(
                                            width=70,
                                            height=70,
                                            bgcolor=sections[1]["color"] if len(sections) > 1 else Colors.TEXT_MUTED,
                                            border_radius=ft.BorderRadius.only(top_right=80)
                                        ),
                                        ft.Container(
                                            width=70,
                                            height=70,
                                            bgcolor=sections[3]["color"] if len(sections) > 3 else sections[2]["color"] if len(sections) > 2 else Colors.TEXT_MUTED,
                                            border_radius=ft.BorderRadius.only(bottom_right=80)
                                        ),
                                    ],
                                    spacing=0
                                ),
                            ],
                            spacing=0,
                            alignment=ft.MainAxisAlignment.CENTER
                        ),
                        alignment=ft.Alignment.CENTER
                    ),
                    # Center hole to create donut effect
                    ft.Container(
                        width=90,
                        height=90,
                        border_radius=45,
                        bgcolor=Colors.BG_CARD,
                        alignment=ft.Alignment.CENTER
                    )
                ],
                expand=True
            ),
            alignment=ft.Alignment.CENTER,
            padding=10
        )
    ]

    # Visual chart
    visual_chart = ft.Container(
        content=ft.Stack(
            controls=donut_layers,
            expand=True
        ) if total > 0 else ft.Text("No data", size=Typography.SIZE_SM, color=Colors.TEXT_SECONDARY),
        width=180,
        height=180,
        alignment=ft.Alignment.CENTER
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
        border=ft.Border.all(1, Colors.BORDER),
        height=320,
        expand=True
    )
