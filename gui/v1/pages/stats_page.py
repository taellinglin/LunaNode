"""
Stats Page - Declarative with hooks
"""
import flet as ft

from ..components.donut_chart import DonutChart
from ..components.metric_card import metric_card
from ..components.stat_card import StatsCard
from ..theme import Colors, Spacing, Typography, create_button_style


@ft.component
def StatsPage(node_status: dict, mining_stats: dict, chart_data: dict, on_refresh):
    """
    Stats page showing mining performance and statistics
    Pure functional component - UI = f(state, callbacks)
    """
    # Prepare chart sections
    resource_sections = [
        {"value": chart_data.get("cpu_percent", 35), "color": Colors.CHART_BLUE,
         "label": f"CPU: {chart_data.get('cpu_percent', 35):.0f}%"},
        {"value": chart_data.get("gpu_percent", 0), "color": Colors.SUCCESS,
         "label": f"GPU: {chart_data.get('gpu_percent', 0):.0f}%"},
        {"value": chart_data.get("memory_percent", 34), "color": Colors.CHART_PINK,
         "label": f"Memory: {chart_data.get('memory_percent', 34):.0f}%"},
        {"value": chart_data.get("available_percent", 31), "color": Colors.TEXT_MUTED,
         "label": f"Available: {chart_data.get('available_percent', 31):.0f}%"}
    ]

    block_sections = [
        {"value": chart_data.get("valid_blocks", 145), "color": Colors.SUCCESS,
         "label": f"Valid Blocks: {chart_data.get('valid_blocks', 145)}"},
        {"value": chart_data.get("orphaned_blocks", 3), "color": Colors.CHART_ORANGE,
         "label": f"Orphaned: {chart_data.get('orphaned_blocks', 3)}"},
        {"value": chart_data.get("rejected_blocks", 0), "color": Colors.ERROR,
         "label": f"Rejected: {chart_data.get('rejected_blocks', 0)}"}
    ]

    # Trend data
    hash_rate_data = mining_stats.get("hash_rate_history", [])[-20:] or []
    success_rate_data = mining_stats.get("success_rate_history", [])[-20:] or []
    mining_time_data = mining_stats.get("mining_time_history", [])[-20:] or []

    return ft.Container(
        content=ft.Column(
            controls=[
                # Header
                ft.Row(
                    controls=[
                        ft.Text(
                            "Mining Performance & Statistics",
                            size=Typography.SIZE_TITLE,
                            color=Colors.TEXT_PRIMARY,
                            weight=ft.FontWeight.BOLD
                        ),
                        ft.Container(expand=True),
                        ft.Button(
                            "Refresh Stats",
                            icon=ft.Icons.REFRESH,
                            style=create_button_style(),
                            on_click=lambda _: on_refresh()
                        )
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN
                ),
                ft.Container(height=Spacing.XL),

                ft.Row(
                    vertical_alignment=ft.CrossAxisAlignment.START,
                    controls=[
                        ft.Container(expand=True,
                                     content=ft.GridView(
                                         runs_count=2,
                                         child_aspect_ratio=2.0,
                                         controls=[
                                             StatsCard(
                                                 icon=ft.Icons.GRID_VIEW,
                                                 icon_color=Colors.CHART_BLUE,
                                                 label="Blocks Mined",
                                                 value=str(node_status.get("blocks_mined", 0)),
                                                 value_color=Colors.CHART_BLUE
                                             ),
                                             StatsCard(
                                                 icon=ft.Icons.CHECK_CIRCLE,
                                                 icon_color=Colors.SUCCESS,
                                                 label="Success Rate",
                                                 value=f"{mining_stats.get('success_rate', 0):.0f}%",
                                                 value_color=Colors.CHART_GREEN
                                             ),
                                             StatsCard(
                                                 icon=ft.Icons.FLASH_ON,
                                                 icon_color=Colors.WARNING,
                                                 label="Hash Rate",
                                                 value=f"{mining_stats.get('hash_rate', 0):.0f} H/s",
                                                 value_color=Colors.CHART_ORANGE
                                             ),
                                             StatsCard(
                                                 icon=ft.Icons.SCHEDULE,
                                                 icon_color=Colors.SUCCESS,
                                                 label="Avg Time",
                                                 value=f"{mining_stats.get('avg_time', 0):.2f}s",
                                                 value_color=Colors.SUCCESS
                                             ),
                                             StatsCard(
                                                 icon=ft.Icons.BAR_CHART,
                                                 icon_color=Colors.CHART_PURPLE,
                                                 label="Total Attempts",
                                                 value=str(mining_stats.get("total_attempts", 0)),
                                                 value_color=Colors.CHART_PURPLE
                                             ),
                                             StatsCard(
                                                 icon=ft.Icons.EMOJI_EVENTS,
                                                 icon_color=Colors.CHART_YELLOW,
                                                 label="Total Reward",
                                                 value=f"{node_status.get('total_reward', 0):.2f} LUN",
                                                 value_color=Colors.CHART_YELLOW
                                             ),
                                         ]
                                     )),
                        ft.Container(expand=True, content=DonutChart(title="Resource Usage Distribution",
                                                                     sections=resource_sections), ),
                        ft.Container(expand=True,
                                     content=DonutChart(title="Block Distribution", sections=block_sections))
                    ]
                ),
                ft.Container(height=Spacing.XL),

                # System metrics
                ft.Row(
                    controls=[
                        metric_card(
                            icon=ft.Icons.MEMORY,
                            label="CPU Usage",
                            value=f"{mining_stats.get('cpu_usage', 0):.0f}%",
                            percentage=mining_stats.get("cpu_usage", 0),
                            color=Colors.CHART_BLUE
                        ),
                        metric_card(
                            icon=ft.Icons.STORAGE,
                            label="Memory Usage",
                            value=f"{mining_stats.get('memory_usage', 0):.0f}%",
                            percentage=mining_stats.get("memory_usage", 0),
                            color=Colors.CHART_PINK
                        ),
                        metric_card(
                            icon=ft.Icons.COMPUTER,
                            label="GPU Usage",
                            value=f"{mining_stats.get('gpu_usage', 0):.0f}%",
                            percentage=mining_stats.get("gpu_usage", 0),
                            color=Colors.SUCCESS
                        ),
                        metric_card(
                            icon=ft.Icons.WIFI,
                            label="Network Latency",
                            value=f"{mining_stats.get('network_latency', 0)}ms",
                            percentage=min(mining_stats.get("network_latency", 0) / 10, 100),
                            color=Colors.CHART_YELLOW
                        )
                    ],
                    spacing=Spacing.LG,
                    expand=True
                )
            ],
            spacing=0,
            scroll=ft.ScrollMode.AUTO,
            expand=True
        ),
        bgcolor=Colors.BG_DARK,
        padding=Spacing.XL,
        expand=True
    )
