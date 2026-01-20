import flet as ft
import os
import threading

# Compatibility shim for older Flet versions without HitTestBehavior
if not hasattr(ft, "HitTestBehavior"):
    class _HitTestBehavior:
        OPAQUE = None
    ft.HitTestBehavior = _HitTestBehavior()
from typing import Dict, List
from datetime import datetime
import time

class BillsPage:
    def __init__(self, app):
        import os
        import json
        self.app = app
        self._prefetching = set()
        self.zoom = 1.0
        try:
            from utils import DataManager
            self.cache_file = os.path.join(DataManager().data_dir, "bills_cache.json")
        except Exception:
            self.cache_file = os.path.join(os.path.dirname(__file__), '../data/bills_cache.json')
        self.bills_cache = self.load_bills_cache()
        cached_transactions = self.bills_cache.get('transactions', [])
        self._cached_transactions = cached_transactions if isinstance(cached_transactions, list) else []
        self._scan_in_progress = False
        self._last_tx_scan_ts = 0.0
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
        # UI部品を先に初期化
        self.bill_tiles = ft.GridView(
            expand=True,
            runs_count=2,
            max_extent=180,
            child_aspect_ratio=16/8,
            spacing=12,
            run_spacing=12,
            controls=[],
            on_scroll=self._on_banknotes_scroll,
        )
        self.tx_cards = ft.Column([], expand=True, spacing=8)
        # その後で内容を更新
        

    def _get_block_for_index(self, block_index: int):
        """Fetch block using lunalib 1.9.2-compatible methods with API fallback."""
        if not self.app or not getattr(self.app, "node", None):
            return None

        # Check local submitted-block cache first
        try:
            from utils import DataManager
            cached_blocks = DataManager().load_blockchain_cache()
            if isinstance(cached_blocks, list):
                for block in cached_blocks:
                    if isinstance(block, dict) and block.get("index") == block_index:
                        return block
        except Exception:
            pass

        manager = getattr(self.app.node, "blockchain_manager", None)
        if manager:
            for method_name in ("get_block", "get_block_by_index", "get_block_by_height"):
                method = getattr(manager, method_name, None)
                if callable(method):
                    try:
                        block = method(block_index)
                        if isinstance(block, dict) and "block" in block and isinstance(block.get("block"), dict):
                            return block.get("block")
                        if isinstance(block, dict):
                            return block
                    except Exception:
                        pass

        try:
            import requests
        except Exception:
            return None

        node_url = "https://bank.linglin.art"
        try:
            node_url = getattr(self.app.node, "config", None).node_url
        except Exception:
            pass

        endpoints = [
            f"{node_url}/blockchain/block/{block_index}",
            f"{node_url}/block/{block_index}",
            f"{node_url}/blockchain/blocks/{block_index}",
            f"{node_url}/blockchain/range?start={block_index}&end={block_index}",
        ]

        for url in endpoints:
            try:
                response = requests.get(url, timeout=10)
                if response.status_code != 200:
                    continue
                data = response.json()

                if isinstance(data, dict) and "block" in data and isinstance(data.get("block"), dict):
                    return data.get("block")

                if isinstance(data, dict) and "blocks" in data and isinstance(data.get("blocks"), list):
                    if data["blocks"]:
                        return data["blocks"][0]

                if isinstance(data, list) and data:
                    return data[0]
            except Exception:
                continue

        return None

    def _get_blocks_for_indices(self, indices: List[int]) -> Dict[int, Dict]:
        results: Dict[int, Dict] = {}
        if not indices:
            return results

        unique_indices = sorted({int(i) for i in indices if isinstance(i, (int, str))})

        # Local cache first
        try:
            from utils import DataManager
            cached_blocks = DataManager().load_blockchain_cache()
            if isinstance(cached_blocks, list):
                for block in cached_blocks:
                    if isinstance(block, dict):
                        idx = block.get("index")
                        if idx in unique_indices:
                            results[idx] = block
        except Exception:
            pass

        missing = [i for i in unique_indices if i not in results]
        if not missing:
            return results

        manager = getattr(self.app.node, "blockchain_manager", None)
        if not manager or not hasattr(manager, "get_blocks_range"):
            return results

        # Build contiguous ranges
        ranges = []
        start = prev = missing[0]
        for idx in missing[1:]:
            if idx == prev + 1:
                prev = idx
            else:
                ranges.append((start, prev))
                start = prev = idx
        ranges.append((start, prev))

        for start, end in ranges:
            try:
                blocks = manager.get_blocks_range(start, end)
                for block in blocks or []:
                    if isinstance(block, dict) and block.get("index") is not None:
                        results[block.get("index")] = block
            except Exception:
                continue

        return results

    def _get_thumbnail_cache_dir(self):
        try:
            from utils import DataManager
            base_dir = DataManager().data_dir
        except Exception:
            base_dir = os.path.join(os.path.dirname(__file__), "..", "data")
        cache_dir = os.path.join(base_dir, "thumbnail_cache")
        os.makedirs(cache_dir, exist_ok=True)
        return cache_dir

    def _prefetch_thumbnail_pair(self, tx_hash: str, front_url: str, back_url: str):
        if tx_hash in self._prefetching:
            return
        self._prefetching.add(tx_hash)

        def _download():
            try:
                import requests
                import time
                cache_dir = self._get_thumbnail_cache_dir()
                front_path = os.path.join(cache_dir, f"{tx_hash}_front.png")
                back_path = os.path.join(cache_dir, f"{tx_hash}_back.png")

                if not os.path.exists(front_path):
                    resp = requests.get(front_url, timeout=15)
                    if resp.ok:
                        with open(front_path, "wb") as f:
                            f.write(resp.content)
                    time.sleep(0.1)

                if not os.path.exists(back_path):
                    resp = requests.get(back_url, timeout=15)
                    if resp.ok:
                        with open(back_path, "wb") as f:
                            f.write(resp.content)
            except Exception:
                pass
            finally:
                self._prefetching.discard(tx_hash)

        import threading
        threading.Thread(target=_download, daemon=True).start()

    def _on_banknotes_scroll(self, e):
        try:
            delta = getattr(e, "delta_y", 0)
        except Exception:
            delta = 0

        if delta == 0:
            return

        step = 0.05
        if delta < 0:
            self.zoom = min(2.0, self.zoom + step)
        else:
            self.zoom = max(0.6, self.zoom - step)

        self.update_bills_content()



    def load_bills_cache(self):
        import os
        import json
        if not os.path.exists(self.cache_file):
            return {'mined_blocks': [], 'thumbnails': {}, 'banknotes': {}}
        try:
            with open(self.cache_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"[DEBUG] Failed to load bills cache: {e}")
            return {'mined_blocks': [], 'thumbnails': {}, 'banknotes': {}}

    def save_bills_cache(self):
        import json
        try:
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.bills_cache, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[DEBUG] Failed to save bills cache: {e}")

    def create_bills_tab(self):
        """Create bills/transactions management tab (split view)"""
        # 上部: PNGサムネイルタイル（16:6アスペクト比）
        # レイアウト（上下分割、各50%）
        return ft.Container(
            content=ft.Column([
                ft.Row([
                    ft.Text("Banknotes", size=16, color="#e3f2fd"),
                ]),
                ft.Divider(height=8, color="#1e3a5c"),
                ft.Row([
                    ft.Container(
                        content=self.bill_tiles,
                        bgcolor="#0f1a2a",
                        border_radius=6,
                        padding=10,
                        expand=True,
                        height=None,
                        width=None,
                    ),
                    # 右側に何も置かない
                ], expand=True),
                ft.Divider(height=12, color="#1e3a5c"),
                ft.Text("Mined Blocks", size=14, color="#e3f2fd"),
                ft.Container(
                    content=self.tx_cards,
                    bgcolor="#0f1a2a",
                    border_radius=6,
                    padding=10,
                    expand=True,
                    width=float('inf'),
                    height=None,
                ),
            ], expand=True),
            padding=10
        )

    def update_bills_content(self, defer_scan: bool = False):
        """Update bills/transactions content (tiles + cards)"""
        txs = []
        # ここでtxやtx_hashは未定義なので何もせず、以降のforループで処理する
        # PNGサムネイルタイル生成: GTX_Genesisトランザクションのハッシュを使う
        if not self.app or not getattr(self.app, 'node', None):
            return
        mining_history = self.app.node.get_mining_history()
        print("[DEBUG] mining_history:", mining_history)
        gtx_hashes = []
        new_blocks = []
        # 既存キャッシュからロード
        cached_blocks = set(self.bills_cache.get('mined_blocks', []))
        cached_thumbnails = self.bills_cache.get('thumbnails', {})
        cached_banknotes = self.bills_cache.get('banknotes', {})
        cached_thumbnail_urls = self.bills_cache.get('thumbnail_urls', {})
        missing_block_indices = []
        # 新規マイニング分だけ取得
        for record in mining_history:
            if record.get('status') == 'success' and record.get('block_index') is not None:
                block_index = record['block_index']
                if block_index in cached_blocks:
                    # 既存キャッシュからGTXハッシュを追加
                    for tx_hash in cached_thumbnails.get(str(block_index), []):
                        gtx_hashes.append(tx_hash)
                else:
                    missing_block_indices.append(block_index)

        if missing_block_indices:
            batch_blocks = self._get_blocks_for_indices(missing_block_indices)
            for block_index in missing_block_indices:
                block = batch_blocks.get(block_index)
                if not block:
                    try:
                        block = self._get_block_for_index(block_index)
                    except Exception as e:
                        print(f"[DEBUG] Failed to get block {block_index}: {e}")
                print(f"[DEBUG] block {block_index}: {block}")
                if block and 'transactions' in block:
                    print(f"[DEBUG] block {block_index} transactions: {block['transactions']}")
                    block_gtx_hashes = []
                    for tx in block['transactions']:
                        if isinstance(tx, dict) and tx.get('type') == 'GTX_Genesis' and tx.get('hash'):
                            gtx_hashes.append(tx['hash'])
                            block_gtx_hashes.append(tx['hash'])
                            # banknote情報もキャッシュ
                            cached_banknotes[tx['hash']] = tx
                            # サムネイルURLをキャッシュ
                            serial_id = tx.get('serial_id') or tx.get('serial_number')
                            img_url_front = f"https://bank.linglin.art/transaction-thumbnail/{tx['hash']}?side=front"
                            if serial_id:
                                img_url_back = f"https://bank.linglin.art/banknote-matching-thumbnail/{serial_id}?side=match"
                            else:
                                img_url_back = f"https://bank.linglin.art/transaction-thumbnail/{tx['hash']}?side=back"
                            cached_thumbnail_urls[tx['hash']] = {
                                "front": f"{img_url_front}&flip=front",
                                "back": f"{img_url_back}&flip=back",
                            }
                    # サムネイルキャッシュ
                    cached_thumbnails[str(block_index)] = block_gtx_hashes
                    new_blocks.append(block_index)
        # キャッシュ更新
        if new_blocks:
            self.bills_cache['mined_blocks'] = list(set(list(cached_blocks) + new_blocks))
            self.bills_cache['thumbnails'] = cached_thumbnails
            self.bills_cache['banknotes'] = cached_banknotes
            self.bills_cache['thumbnail_urls'] = cached_thumbnail_urls
            self.save_bills_cache()
        print(f"[DEBUG] gtx_genesis hashes: {gtx_hashes}")
        # --- キャッシュからのサムネイル・ブロック情報が存在する場合、必ずUIに反映 ---
        # サムネイル描画
        self.bill_tiles.controls.clear()
        zoom = getattr(self, "zoom", 1.0)
        self.bill_tiles.max_extent = int(180 * zoom)
        cached_thumbnails = self.bills_cache.get('thumbnails', {})
        cached_banknotes = self.bills_cache.get('banknotes', {})
        cached_thumbnail_urls = self.bills_cache.get('thumbnail_urls', {})
        cache_dir = self._get_thumbnail_cache_dir()
        tiles = []
        for block_index, tx_hashes in cached_thumbnails.items():
            if not tx_hashes:
                continue  # 空リストはスキップ
            for tx_hash in tx_hashes:
                tx = cached_banknotes.get(tx_hash)
                if not tx:
                    continue  # banknote情報がなければスキップ
                # front/back両方のサムネイルURLを用意
                # frontは常にtransaction-thumbnailで確実に表示し、backはserial_idがあればmatchingを使う
                serial_id = tx.get('serial_id') or tx.get('serial_number')
                cached_urls = cached_thumbnail_urls.get(tx_hash, {})
                front_src = cached_urls.get("front")
                back_src = cached_urls.get("back")
                if not front_src or not back_src:
                    img_url_front = f"https://bank.linglin.art/transaction-thumbnail/{tx_hash}?side=front"
                    if serial_id:
                        img_url_back = f"https://bank.linglin.art/banknote-matching-thumbnail/{serial_id}?side=match"
                    else:
                        img_url_back = f"https://bank.linglin.art/transaction-thumbnail/{tx_hash}?side=back"
                    front_src = f"{img_url_front}&flip=front"
                    back_src = f"{img_url_back}&flip=back"
                    cached_thumbnail_urls[tx_hash] = {"front": front_src, "back": back_src}

                local_front = os.path.join(cache_dir, f"{tx_hash}_front.png")
                local_back = os.path.join(cache_dir, f"{tx_hash}_back.png")
                display_front = local_front if os.path.exists(local_front) else front_src
                display_back = local_back if os.path.exists(local_back) else back_src
                owner = tx.get('issued_to', '')
                amount = tx.get('denomination', '')
                if not tx_hash:
                    continue

                # サムネイル下部にOwner/Amountラベル
                label_row = ft.Container(
                    content=ft.Row([
                        ft.Text(str(owner), size=int(8 * zoom), color="#b0bec5", weight=ft.FontWeight.W_400),
                        ft.Text(f"{amount}", size=int(8 * zoom), color="#ffd600", weight=ft.FontWeight.W_400),
                    ], spacing=4, alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    padding=ft.padding.only(top=2),
                )

                # 単一のImageのsrcを切り替える方法でホバー表示を更新
                img_main = ft.Image(
                    src=display_front,
                    width=int(160 * zoom),
                    height=int(60 * zoom),
                    fit="contain",
                    border_radius=8,
                    gapless_playback=False,
                    error_content=ft.Text("No image", size=8, color="#789")
                )
                content = ft.Column([
                    img_main,
                    label_row
                ], spacing=2)

                if serial_id:
                    fullview_url = f"https://bank.linglin.art/banknote-viewer/{serial_id}"
                else:
                    fullview_url = f"https://bank.linglin.art/transaction/{tx_hash}"

                def set_hover(hovered, img=img_main, front=display_front, back=display_back, _tx_hash=tx_hash):
                    img.src = back if hovered else front
                    img.update()
                    if self.bill_tiles:
                        self.bill_tiles.update()

                def on_hover(e, _tx_hash=tx_hash, front=display_front, back=display_back, _set_hover=set_hover):
                    data = getattr(e, "data", None)
                    data_str = str(data).strip().lower()
                    print(
                        f"[DEBUG] hover: tx={_tx_hash} data={data} front={front} back={back}"
                    )
                    if data_str in ("true", "1", "enter", "over", "hover"):
                        _set_hover(True, front=front, back=back)
                    elif data_str in ("false", "0", "exit", "leave", "out"):
                        _set_hover(False, front=front, back=back)
                    else:
                        # Fallback: treat any hover event as enter
                        _set_hover(True, front=front, back=back)

                def on_tap_open(e, url=fullview_url, _tx_hash=tx_hash):
                    has_page = bool(self.app.page)
                    print(f"[DEBUG] click banknote: tx={_tx_hash} url={url} page={has_page}")
                    try:
                        if self.app.page and hasattr(self.app.page, "launch_url"):
                            self.app.page.launch_url(url)
                        import webbrowser
                        webbrowser.open(url)
                    except Exception as ex:
                        print(f"[DEBUG] click banknote failed: {ex}")

                try:
                    is_mining = bool(self.app and self.app.node and self.app.node.miner and self.app.node.miner.is_mining)
                except Exception:
                    is_mining = False
                if not is_mining:
                    self._prefetch_thumbnail_pair(tx_hash, front_src, back_src)

                img_main.on_hover = on_hover

                tile = ft.Container(
                    content=content,
                    bgcolor="#162a3a",
                    border_radius=8,
                    padding=4,
                    on_click=on_tap_open,
                    on_hover=on_hover,
                    url=fullview_url,
                    ink=True,
                )
                tiles.append(tile)
        self.bill_tiles.controls.extend(tiles)
        self.bill_tiles.scroll = ft.ScrollMode.AUTO
        self.bills_cache['thumbnail_urls'] = cached_thumbnail_urls
        self.save_bills_cache()
        # Mined blocks履歴もキャッシュから
        txs = []
        cached_blocks = self.bills_cache.get('mined_blocks', [])
        mining_history = self.app.node.get_mining_history() if self.app.node else []
        history_by_block = {r.get('block_index'): r for r in mining_history if r.get('status') == 'success'}
        for block_index in cached_blocks:
            info = history_by_block.get(block_index)
            if not info:
                continue
            block_hash = info.get('hash', '')
            nonce = info.get('nonce', '')
            mine_time = info.get('timestamp', 0)
            mining_time = info.get('mining_time', None)
            tx_count = info.get('transactions', None)
            if isinstance(tx_count, list):
                tx_count = len(tx_count)
            elif tx_count is None:
                tx_count = 'N/A'
            else:
                tx_count = str(tx_count)
            method = info.get('method', '').lower()
            tag = None
            if method == 'cuda' or method == 'gpu':
                tag = ft.Container(
                    content=ft.Text("GPU", color="#fff", size=10, weight=ft.FontWeight.BOLD),
                    bgcolor="#28a745", border_radius=4, padding=ft.Padding(4,2,4,2), margin=ft.Margin(right=8)
                )
            elif method == 'cpu':
                tag = ft.Container(
                    content=ft.Text("CPU", color="#fff", size=10, weight=ft.FontWeight.BOLD),
                    bgcolor="#007bff", border_radius=4, padding=ft.Padding(4,2,4,2), margin=ft.Margin(right=8)
                )
            else:
                tag = ft.Container()
            base_url = "https://bank.linglin.art"
            block_url = f"{base_url}/block/{block_index}"
            reward = info.get('reward', None)
            reward_text = ft.Text(f"Reward: {reward}", size=10, color="#ffd600") if reward else None
            block_details = [
                ft.Text(f"Block: {block_index}", size=12, color="#00a1ff", weight=ft.FontWeight.BOLD),
                ft.Text(f"Hash: {block_hash}", size=10, color="#00ff37"),
                ft.Text(f"Nonce: {nonce}", size=10, color="#e3f2fd"),
                ft.Text(f"Mine Time: {datetime.fromtimestamp(mine_time).strftime('%Y-%m-%d %H:%M:%S') if mine_time else ''}", size=10, color="#e3f2fd"),
                ft.Text(f"Tx Count: {tx_count}", size=10, color="#e3f2fd"),
            ]
            if reward_text:
                block_details.append(reward_text)
            def open_block_url(e, url=block_url, _block=block_index):
                has_page = bool(self.app.page)
                print(f"[DEBUG] click view block: block={_block} url={url} page={has_page}")
                try:
                    if self.app.page and hasattr(self.app.page, "launch_url"):
                        self.app.page.launch_url(url)
                    import webbrowser
                    webbrowser.open(url)
                except Exception as ex:
                    print(f"[DEBUG] click view block failed: {ex}")

            view_button = ft.Container(
                content=ft.Text("View Block", color="#ffffff", size=12),
                bgcolor="#00a1ff",
                padding=ft.padding.symmetric(horizontal=12, vertical=6),
                border_radius=2,
                on_click=open_block_url,
                url=block_url,
                ink=True,
            )
            card = ft.Container(
                content=ft.Row([
                    tag,
                    ft.Column(block_details, spacing=2, expand=True),
                    view_button,
                ]),
                bgcolor="#1a2b3c",
                border_radius=6,
                padding=8,
                margin=ft.Margin.only(bottom=4),
                width=float('inf'),
            )
            txs.append(card)
        self.tx_cards.controls = list(txs)
        self.tx_cards.scroll = ft.ScrollMode.AUTO
        if self.app.page:
            self.app.page.update()
        self.tx_cards.controls.clear()
        self.tx_cards.controls.extend(txs)
        self.tx_cards.scroll = ft.ScrollMode.AUTO
        if self.app.page:
            self.app.page.update()
        
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
        
        # Add any additional transactions from blockchain (use cached first, refresh async)
        address = None
        if self.app and self.app.node and self.app.node.miner:
            address = self.app.node.config.miner_address
        transactions = self._cached_transactions
        now = time.time()
        if address and not defer_scan and not self._scan_in_progress and (now - self._last_tx_scan_ts) > 60:
            self._scan_in_progress = True
            self._last_tx_scan_ts = now

            def _scan():
                new_txs = None
                try:
                    new_txs = self.app.node.scan_transactions_for_address_cached(address)
                except Exception as e:
                    print(f"Error loading transactions: {e}")

                def _apply():
                    if isinstance(new_txs, list):
                        self._cached_transactions = new_txs
                        self.bills_cache['transactions'] = new_txs
                        self.save_bills_cache()
                    self._scan_in_progress = False
                    self.update_bills_content(defer_scan=True)

                if self.app and hasattr(self.app, "safe_run_thread"):
                    ok = self.app.safe_run_thread(_apply)
                    if not ok:
                        self._scan_in_progress = False
                else:
                    self._scan_in_progress = False

            threading.Thread(target=_scan, daemon=True).start()

        if isinstance(transactions, list):
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
        
        # Sort by timestamp (newest first)
        mined_bills.sort(key=lambda x: x['timestamp'], reverse=True)
        
        # Add to table
        for bill in mined_bills[:50]:  # Show last 50 bills
            timestamp = datetime.fromtimestamp(bill['timestamp']).strftime("%Y-%m-%d %H:%M:%S")
            amount = f"{bill['amount']:.2f} LKC"
            
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
                        ft.Text(f"{total_reward:.2f} LKC", size=16, color="#00a1ff", weight=ft.FontWeight.BOLD),
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