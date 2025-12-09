"""
Luna Node - Entry Point for True Declarative UI with Hooks

This uses Flet's declarative approach with @ft.component and hooks:
- ft.use_state() for state management
- ft.use_effect() for side effects
- UI = f(state) paradigm

The old entry point (main_old.py) remains untouched.
"""
import flet as ft
# Import the main function from your app module
from gui.v1.app import main as app_main

# This is the entry point that `flet run` will execute
def main(page: ft.Page):
    app_main(page)

# This block allows you to still run the app with `python main.py`
if __name__ == "__main__":
    ft.run(main)
