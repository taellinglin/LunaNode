import flet as ft

from gui.v1.components.navbar import AppPage
from gui.v1.pages import StatsPage
from gui.v1.theme import Colors

# Initialize state for StatsPage
node_status = {
    "blocks_mined": 145,
    "total_reward": 2.40,
    "status": "Running",
    "network_height": 0,
    "difficulty": 1,
    "connection": "connected",
    "uptime": "00:00:26"
}

mining_stats = {
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
}

chart_data = {
    "cpu_percent": 35,
    "gpu_percent": 0,
    "memory_percent": 34,
    "available_percent": 31,
    "valid_blocks": 145,
    "orphaned_blocks": 3,
    "rejected_blocks": 0
}

def handle_refresh():
    # Placeholder for refresh logic
    print("Refreshing stats...")

@ft.component
def MainContent(current_page: AppPage):
    match current_page:
        case AppPage.MINING:
            return ft.Text('Mining', color=Colors.TEXT_PRIMARY)
        case AppPage.BILLS:
            return ft.Text('Bills', color=Colors.TEXT_PRIMARY)
        case AppPage.STATS:
            return StatsPage(
                node_status=node_status,
                mining_stats=mining_stats,
                chart_data=chart_data,
                on_refresh=handle_refresh
            )
        case AppPage.SETTINGS:
            return ft.Text('Settings', color=Colors.TEXT_PRIMARY)
        case AppPage.LOG:
            return ft.Text('Log', color=Colors.TEXT_PRIMARY)
