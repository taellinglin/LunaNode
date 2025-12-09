"""
Theme and styling constants for Luna Node declarative UI
"""
import flet as ft

# Color Palette
class Colors:
    """Color scheme based on the Figma design"""

    # Backgrounds
    BG_DARK = "#0F1821"  # Main background
    BG_CARD = "#1a1f2e"  # Card/container background
    BG_SIDEBAR = "#0F1821"  # Sidebar background
    BG_HOVER = "#1e2433"  # Hover state

    # Primary & Accents
    PRIMARY = "#00d9ff"  # Cyan accent
    PRIMARY_DARK = "#00a8cc"  # Darker cyan

    # Status Colors
    SUCCESS = "#00ff88"  # Green
    WARNING = "#ff9500"  # Orange
    ERROR = "#ff4d6d"  # Pink/Red
    INFO = "#00d9ff"  # Cyan

    # Chart Colors
    CHART_BLUE = "#0099ff"
    CHART_GREEN = "#00ff88"
    CHART_YELLOW = "#ffaa00"
    CHART_PURPLE = "#9d4edd"
    CHART_PINK = "#ff006e"
    CHART_CYAN = "#00d9ff"
    CHART_ORANGE = "#ff9500"

    # Text Colors
    TEXT_PRIMARY = "#ffffff"
    TEXT_SECONDARY = "#8b95a5"
    TEXT_MUTED = "#4a5568"

    # Border & Divider
    BORDER = "#1e2433"
    DIVIDER = "#1a1f2e"

    # Icon
    NAVBAR_ICON = "#ffffff"


class Spacing:
    """Spacing constants"""
    XS = 4
    SM = 8
    MD = 12
    LG = 16
    XL = 20
    XXL = 24


class Typography:
    """Typography constants"""

    # Font Sizes
    SIZE_XS = 10
    SIZE_SM = 12
    SIZE_MD = 14
    SIZE_LG = 16
    SIZE_XL = 18
    SIZE_XXL = 20
    SIZE_TITLE = 24
    SIZE_HEADING = 28

    # Font Weights
    WEIGHT_REGULAR = "normal"
    WEIGHT_MEDIUM = "w500"
    WEIGHT_BOLD = "bold"


class Layout:
    """Layout constants"""
    SIDEBAR_WIDTH = 220
    NAVBAR_HEIGHT = 60
    CARD_RADIUS = 8
    BUTTON_RADIUS = 6


def create_card_style(bgcolor=None, padding=None, border_radius=None):
    """Create a consistent card container style"""
    return {
        "bgcolor": bgcolor or Colors.BG_CARD,
        "padding": padding or Spacing.LG,
        "border_radius": border_radius or Layout.CARD_RADIUS,
        "border": ft.Border.all(1, Colors.BORDER)
    }


def create_button_style(bgcolor=None, color=None):
    """Create a consistent button style"""
    return ft.ButtonStyle(
        bgcolor={
            ft.ControlState.DEFAULT: bgcolor or Colors.PRIMARY,
            ft.ControlState.HOVERED: Colors.PRIMARY_DARK,
        },
        color={
            ft.ControlState.DEFAULT: color or Colors.TEXT_PRIMARY,
        },
        shape=ft.RoundedRectangleBorder(radius=Layout.BUTTON_RADIUS),
        padding=ft.Padding.symmetric(horizontal=Spacing.LG, vertical=Spacing.MD),
    )
