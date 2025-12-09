from dataclasses import dataclass

import flet as ft
from .components.navbar import NavBar
from .pages.stats_page import StatsPage
from .theme import Colors, Layout


@dataclass
class NavBarState(ft.Observable):
    current_page: str

    def select(self, page):
        self.current_page = page
        print(self.current_page)


@ft.component
def App():
    navbar_state, _ = ft.use_state(NavBarState(current_page="stats"))
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
                                    bgcolor=Colors.WARNING,
                                    content=StatsPage()
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
