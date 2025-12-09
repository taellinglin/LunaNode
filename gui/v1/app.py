from dataclasses import dataclass

import flet as ft
from .components.navbar import NavBar, NavBarTab, tabs
from .pages.stats_page import StatsPage
from .theme import Colors, Layout


@dataclass
class NavBarState(ft.Observable):
    current_page: NavBarTab

    def select(self, page):
        self.current_page = page
        print(self.current_page)


@ft.component
def App():
    navbar_state, _ = ft.use_state(NavBarState(current_page=tabs[2]))

    # Initialize state for StatsPage
    node_status, set_node_status = ft.use_state({
        "blocks_mined": 145,
        "total_reward": 2.40,
        "status": "Running",
        "network_height": 0,
        "difficulty": 1,
        "connection": "connected",
        "uptime": "00:00:26"
    })

    mining_stats, set_mining_stats = ft.use_state({
        "success_rate": 100,
        "hash_rate": 0,
        "avg_time": 0.03,
        "total_attempts": 145,
        "cpu_usage": 35,
        "memory_usage": 34,
        "gpu_usage": 0,
        "network_latency": 164,
        "hash_rate_history": [],
        "success_rate_history": [],
        "mining_time_history": []
    })

    chart_data, set_chart_data = ft.use_state({
        "cpu_percent": 35,
        "gpu_percent": 0,
        "memory_percent": 34,
        "available_percent": 31,
        "valid_blocks": 145,
        "orphaned_blocks": 3,
        "rejected_blocks": 0
    })

    def handle_refresh():
        # Placeholder for refresh logic
        print("Refreshing stats...")

    # The main layout is a Row that will span the full page width.
    return ft.Column(
        expand=True,
        controls=[
            ft.Row(
                # The `expand` property on the Row itself makes it fill the page.
                expand=True,
                controls=[
                    # 1. The Sidebar: A Container with a FIXED width.
                    ft.Container(
                        width=Layout.SIDEBAR_WIDTH,
                        bgcolor=Colors.BG_SIDEBAR,
                        padding=ft.Padding.only(left=20, right=20, top=20),
                        content=ft.Column(
                            expand=True,
                            controls=[
                                ft.Text("Sidebar", color=Colors.TEXT_PRIMARY)
                            ]
                        )
                    ),

                    ft.VerticalDivider(
                        width=1,
                        color=Colors.BORDER
                    ),

                    # 2. The Main Content Area: A Container with `expand=True`.
                    # This control will automatically take up all remaining space in the Row.
                    ft.Container(
                        expand=True,  # This is the key property!
                        bgcolor=Colors.BG_DARK,
                        padding=20,
                        content=ft.Column(
                            expand=True,
                            controls=[
                                NavBar(current_page=navbar_state.current_page,
                                       on_navigate=lambda p: navbar_state.select(p)),
                                ft.Container(
                                    expand=True,
                                    content=StatsPage(
                                        node_status=node_status,
                                        mining_stats=mining_stats,
                                        chart_data=chart_data,
                                        on_refresh=handle_refresh
                                    )
                                )
                            ]
                        )
                    )
                ],
                # Remove spacing between the two controls
                spacing=0
            )
        ]
    )


def main(page: ft.Page):
    page.padding = 0.0
    page.render(App)
