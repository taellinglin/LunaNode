import time
from datetime import datetime

import flet as ft


class BillsPage:
    def __init__(self, app):
        self.app = app
        self.bills_content = ft.Column()
        self.bills_table = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("Date", color="#e3f2fd")),
                ft.DataColumn(ft.Text("Type", color="#e3f2fd")),
                ft.DataColumn(ft.Text("Amount", color="#e3f2fd")),
                ft.DataColumn(ft.Text("From", color="#e3f2fd")),
                ft.DataColumn(ft.Text("To", color="#e3f2fd")),
                ft.DataColumn(ft.Text("Status", color="#e3f2fd")),
                ft.DataColumn(ft.Text("Block", color="#e3f2fd")),
            ],
            rows=[],
            vertical_lines=ft.BorderSide(1, "#1e3a5c"),
            horizontal_lines=ft.BorderSide(1, "#1e3a5c"),
            bgcolor="#0f1a2a",
        )

    def create_bills_tab(self):
        """Create bills/transactions management tab"""
        refresh_button = ft.ElevatedButton(
            "🔄 Refresh",
            on_click=lambda e: self.update_bills_content(),
            style=ft.ButtonStyle(
                color="#ffffff",
                bgcolor="#00a1ff",
                padding=ft.padding.symmetric(horizontal=16, vertical=10),
                shape=ft.RoundedRectangleBorder(radius=3)
            ),
            height=38
        )
        
        return ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Text("Mined Bills & Transactions", size=16, color="#e3f2fd"),
                    refresh_button
                ]),
                ft.Container(
                    content=ft.ListView([self.bills_table], expand=True),
                    expand=True,
                    border=ft.border.all(1, "#1e3a5c"),
                    border_radius=3
                )
            ], expand=True),
            padding=10
        )

    def update_bills_content(self):
        """Update bills/transactions content"""
        if not self.app.node:
            return
            
        self.bills_table.rows.clear()
        
        # Get mining rewards from history
        mining_history = self.app.node.get_mining_history()
        mined_bills = []
        
        # Convert mining history to bill format
        for record in mining_history:
            if record.get('status') == 'success':
                bill = {
                    'type': 'mining_reward',
                    'timestamp': record['timestamp'],
                    'amount': 50.0,  # Standard mining reward
                    'from_address': 'network',
                    'to_address': self.app.node.config.miner_address if self.app.node else 'Unknown',
                    'status': 'confirmed',
                    'block_height': record.get('block_index', 'N/A'),
                    'hash': record.get('hash', '')
                }
                mined_bills.append(bill)
        
        # Add any additional transactions from blockchain
        try:
            if self.app.node and self.app.node.miner:
                # Get transactions for our address
                address = self.app.node.config.miner_address
                transactions = self.app.node.miner.blockchain_manager.scan_transactions_for_address(address)
                
                for tx in transactions:
                    bill = {
                        'type': tx.get('type', 'transaction'),
                        'timestamp': tx.get('timestamp', time.time()),
                        'amount': tx.get('amount', 0),
                        'from_address': tx.get('from', 'Unknown'),
                        'to_address': tx.get('to', 'Unknown'),
                        'status': tx.get('status', 'confirmed'),
                        'block_height': tx.get('block_height', 'N/A'),
                        'hash': tx.get('hash', '')
                    }
                    mined_bills.append(bill)
        except Exception as e:
            print(f"Error loading transactions: {e}")
        
        # Sort by timestamp (newest first)
        mined_bills.sort(key=lambda x: x['timestamp'], reverse=True)
        
        # Add to table
        for bill in mined_bills[:50]:  # Show last 50 bills
            timestamp = datetime.fromtimestamp(bill['timestamp']).strftime("%Y-%m-%d %H:%M:%S")
            amount = f"{bill['amount']:.2f} LUN"
            
            # Determine type color and icon
            if bill['type'] == 'mining_reward':
                type_display = "💰 Mining Reward"
                type_color = "#28a745"
            elif bill['type'] == 'reward':
                type_display = "🎁 Block Reward"
                type_color = "#17a2b8"
            else:
                type_display = "🔄 Transaction"
                type_color = "#6c757d"
            
            # Status color
            status_color = "#28a745" if bill['status'] == 'confirmed' else "#ffc107"
            
            row = ft.DataRow(cells=[
                ft.DataCell(ft.Text(timestamp, color="#e3f2fd", size=12)),
                ft.DataCell(ft.Text(type_display, color=type_color, size=12)),
                ft.DataCell(ft.Text(amount, color="#00a1ff", size=12, weight=ft.FontWeight.BOLD)),
                ft.DataCell(ft.Text(bill['from_address'][:12] + "..." if len(bill['from_address']) > 12 else bill['from_address'], 
                                  color="#e3f2fd", size=10)),
                ft.DataCell(ft.Text(bill['to_address'][:12] + "..." if len(bill['to_address']) > 12 else bill['to_address'], 
                                  color="#e3f2fd", size=10)),
                ft.DataCell(ft.Text(bill['status'].capitalize(), color=status_color, size=12)),
                ft.DataCell(ft.Text(f"#{bill['block_height']}", color="#e3f2fd", size=12)),
            ])
            self.bills_table.rows.append(row)
        
        # Show summary
        total_reward = sum(bill['amount'] for bill in mined_bills if bill['type'] in ['mining_reward', 'reward'])
        total_transactions = len(mined_bills)
        
        summary_card = ft.Container(
            content=ft.Row([
                ft.Container(
                    content=ft.Column([
                        ft.Text("Total Mined", size=12, color="#e3f2fd"),
                        ft.Text(f"{total_reward:.2f} LUN", size=16, color="#00a1ff", weight=ft.FontWeight.BOLD),
                    ]),
                    padding=15,
                    bgcolor="#1a2b3c",
                    border_radius=4,
                    expand=True
                ),
                ft.Container(
                    content=ft.Column([
                        ft.Text("Total Bills", size=12, color="#e3f2fd"),
                        ft.Text(str(total_transactions), size=16, color="#00a1ff", weight=ft.FontWeight.BOLD),
                    ]),
                    padding=15,
                    bgcolor="#1a2b3c",
                    border_radius=4,
                    expand=True
                ),
                ft.Container(
                    content=ft.Column([
                        ft.Text("Last Updated", size=12, color="#e3f2fd"),
                        ft.Text(datetime.now().strftime("%H:%M:%S"), size=16, color="#00a1ff", weight=ft.FontWeight.BOLD),
                    ]),
                    padding=15,
                    bgcolor="#1a2b3c",
                    border_radius=4,
                    expand=True
                ),
            ]),
            margin=ft.margin.only(bottom=10)
        )
        
        # Clear and rebuild content
        self.bills_content.controls.clear()
        self.bills_content.controls.extend([
            summary_card,
            self.bills_table
        ])
        
        if self.app.page:
            self.app.page.update()

    def get_bill_details(self, bill_hash: str):
        """Get detailed information about a specific bill"""
        # This would show more details when a bill is clicked
        pass