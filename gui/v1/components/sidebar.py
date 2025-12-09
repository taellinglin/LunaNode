"""
Sidebar Component - Declarative with hooks
"""
import flet as ft
from ..theme import Colors, Spacing, Typography, Layout, create_button_style

@ft.component
def sidebar(
    node_status: dict,
    mining_stats: dict,
    on_start_mining,
    on_stop_mining,
    on_sync_network,
    on_mine_single
):
    """
    Left sidebar with node status, quick actions, and mining stats
    Pure functional component - UI = f(state, callbacks)
    """
    # Node status section
    status_items = [
        ("Status:", node_status.get("status", "Stopped"),
         Colors.SUCCESS if node_status.get("is_running") else Colors.TEXT_SECONDARY),
        ("Network Height:", str(node_status.get("network_height", 0)), Colors.TEXT_PRIMARY),
        ("Difficulty:", str(node_status.get("difficulty", 1)), Colors.TEXT_PRIMARY),
        ("Blocks Mined:", str(node_status.get("blocks_mined", 0)), Colors.TEXT_PRIMARY),
        ("Total Reward:", f"{node_status.get('total_reward', 0):.2f} LUN", Colors.TEXT_PRIMARY),
        ("Connection:", node_status.get("connection", "disconnected"),
         Colors.SUCCESS if node_status.get("connection") == "connected" else Colors.TEXT_SECONDARY),
        ("Uptime:", node_status.get("uptime", "00:00:00"), Colors.TEXT_PRIMARY),
    ]

    status_rows = [
        ft.Row(
            controls=[
                ft.Text(label, size=Typography.SIZE_XS, color=Colors.TEXT_SECONDARY, width=100),
                ft.Text(value, size=Typography.SIZE_XS, color=color, weight=ft.FontWeight.W_500)
            ],
            spacing=Spacing.SM
        )
        for label, value, color in status_items
    ]

    # Current hash display
    current_hash = mining_stats.get("current_hash", "")
    hash_display = current_hash[:16] + "..." if len(current_hash) > 16 else current_hash or "N/A"

    return ft.Container(
        content=ft.Column(
            controls=[
                # Header
                ft.Row(
                    controls=[
                        ft.IconButton(
                            icon="",
                            icon_color=Colors.TEXT_PRIMARY,
                            icon_size=20
                        ),
                        ft.Container(
                            content=ft.Row(
                                controls=[
                                    ft.Container(
                                        width=12,
                                        height=12,
                                        bgcolor=Colors.PRIMARY,
                                        border_radius=6
                                    ),
                                    ft.Text(
                                        "Luna Node",
                                        size=Typography.SIZE_LG,
                                        color=Colors.TEXT_PRIMARY,
                                        weight=ft.FontWeight.BOLD
                                    )
                                ],
                                spacing=Spacing.SM
                            ),
                            expand=True
                        )
                    ],
                    spacing=0
                ),
                ft.Container(height=Spacing.XL),

                # Node Status
                ft.Column(
                    controls=[
                        ft.Row(
                            controls=[
                                ft.Container(
                                    width=12,
                                    height=12,
                                    bgcolor=Colors.PRIMARY,
                                    border_radius=6
                                ),
                                ft.Text(
                                    "Node Status",
                                    size=Typography.SIZE_MD,
                                    color=Colors.TEXT_PRIMARY,
                                    weight=ft.FontWeight.W_500
                                )
                            ],
                            spacing=Spacing.SM
                        ),
                        ft.Container(height=Spacing.MD),
                        *status_rows
                    ],
                    spacing=Spacing.SM
                ),
                ft.Container(height=Spacing.XL),

                # Quick Actions
                ft.Column(
                    controls=[
                        ft.Text(
                            "Quick Actions",
                            size=Typography.SIZE_MD,
                            color=Colors.TEXT_PRIMARY,
                            weight=ft.FontWeight.W_500
                        ),
                        ft.Container(height=Spacing.MD),
                        ft.ElevatedButton(
                            content=ft.Text("Start Mining", size=Typography.SIZE_SM),
                            style=create_button_style(),
                            width=Layout.SIDEBAR_WIDTH - (Spacing.LG * 2),
                            on_click=lambda _: on_start_mining()
                        ),
                        ft.ElevatedButton(
                            content=ft.Text("Stop Mining", size=Typography.SIZE_SM),
                            style=create_button_style(),
                            width=Layout.SIDEBAR_WIDTH - (Spacing.LG * 2),
                            on_click=lambda _: on_stop_mining()
                        ),
                        ft.ElevatedButton(
                            content=ft.Text("Sync Network", size=Typography.SIZE_SM),
                            style=create_button_style(),
                            width=Layout.SIDEBAR_WIDTH - (Spacing.LG * 2),
                            on_click=lambda _: on_sync_network()
                        ),
                        ft.ElevatedButton(
                            content=ft.Text("Mine Single Block", size=Typography.SIZE_SM),
                            style=create_button_style(),
                            width=Layout.SIDEBAR_WIDTH - (Spacing.LG * 2),
                            on_click=lambda _: on_mine_single()
                        ),
                    ],
                    spacing=Spacing.SM
                ),
                ft.Container(height=Spacing.XL),

                # Mining Stats
                ft.Column(
                    controls=[
                        ft.Text(
                            "Mining Stats",
                            size=Typography.SIZE_MD,
                            color=Colors.TEXT_PRIMARY,
                            weight=ft.FontWeight.W_500
                        ),
                        ft.Container(height=Spacing.MD),
                        ft.Row(
                            controls=[
                                ft.Text("Hash Rate:", size=Typography.SIZE_XS, color=Colors.TEXT_SECONDARY),
                                ft.Text(
                                    f"{mining_stats.get('hash_rate', 0):.0f} H/s",
                                    size=Typography.SIZE_XS,
                                    color=Colors.TEXT_PRIMARY
                                )
                            ],
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN
                        ),
                        ft.Column(
                            controls=[
                                ft.Text("Current Hash:", size=Typography.SIZE_XS, color=Colors.TEXT_SECONDARY),
                                ft.Text(hash_display, size=Typography.SIZE_XS, color=Colors.TEXT_PRIMARY)
                            ],
                            spacing=Spacing.XS
                        ),
                        ft.Column(
                            controls=[
                                ft.Row(
                                    controls=[
                                        ft.Text("Nonce:", size=Typography.SIZE_XS, color=Colors.TEXT_SECONDARY),
                                        ft.Text(
                                            str(mining_stats.get("nonce", 0)),
                                            size=Typography.SIZE_XS,
                                            color=Colors.TEXT_PRIMARY
                                        )
                                    ],
                                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN
                                ),
                                ft.ProgressBar(
                                    value=0.5,
                                    color=Colors.PRIMARY,
                                    bgcolor=Colors.BG_DARK,
                                    height=4
                                )
                            ],
                            spacing=Spacing.XS
                        )
                    ],
                    spacing=Spacing.SM
                )
            ],
            spacing=0,
            scroll=ft.ScrollMode.AUTO
        ),
        width=Layout.SIDEBAR_WIDTH,
        bgcolor=Colors.BG_SIDEBAR,
        padding=Spacing.LG,
        expand=True
    )
