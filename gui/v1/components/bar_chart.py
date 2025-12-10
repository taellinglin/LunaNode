"""
Bar Chart Component - Declarative with hooks
"""
import flet as ft
import flet_charts as fch
from ..theme import Colors, Spacing, Typography


@ft.component
def BarChartCard(title: str, data: list, color: str, max_value: float = None):
    """
    A card containing a bar chart for trend visualization using flet_charts.BarChart
    data: list of values for the bars
    """
    # Determine max value for chart scaling
    chart_max = max_value or (max(data) * 1.2 if data and any(v > 0 for v in data) else 100)

    # Handle empty data
    display_data = data if data and any(v > 0 for v in data) else [1] * 20
    bar_color = color if data and any(v > 0 for v in data) else Colors.BG_HOVER

    # Create BarChartGroups with BarChartRods
    bar_groups = []
    for index, value in enumerate(display_data):
        bar_groups.append(
            fch.BarChartGroup(
                x=index,
                rods=[
                    fch.BarChartRod(
                        from_y=0,
                        to_y=value,
                        width=8,
                        color=bar_color,
                        border_radius=ft.BorderRadius(2, 2, 0, 0),
                        tooltip=str(value)
                    )
                ]
            )
        )

    # Create the bar chart
    chart = fch.BarChart(
        groups=bar_groups,
        baseline_y=0,
        max_y=chart_max,
        interactive=True,
        bgcolor=Colors.BG_DARK,
        expand=True,
        # Hide axes for cleaner look
        left_axis=fch.ChartAxis(
            label_size=0,
        ),
        bottom_axis=fch.ChartAxis(
            label_size=0,
        ),
        # Remove grid lines
        horizontal_grid_lines=fch.ChartGridLines(
            interval=chart_max,
            color="transparent",
            width=0,
        ),
        vertical_grid_lines=fch.ChartGridLines(
            interval=1,
            color="transparent",
            width=0,
        ),
    )

    # Chart container
    chart_container = ft.Container(
        content=chart,
        bgcolor=Colors.BG_DARK,
        padding=Spacing.MD,
        border_radius=4,
        expand=True,
        height=120
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
                chart_container
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
