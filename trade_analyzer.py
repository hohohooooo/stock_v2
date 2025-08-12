# trade_analyzer.py
from __future__ import annotations

import io
import csv
from pathlib import Path
from typing import Tuple, Optional

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm


class StockTradeAnalyzer:
    """
    整合：CSV 解析、清整、彙總計算、Top20 報表、PNG 輸出、視覺化
    """

    # ====== 讀檔與清整 ======

    def csv2df(
        self,
        uploaded_file,
        encoding: str = "big5",
        header_row: int = 2,
        data_start_row: int = 3,
    ) -> Optional[pd.DataFrame]:
        """
        讀取原始 CSV（證交所分點日報），將第 header_row 行當標題，其後為資料列。
        """
        try:
            content = uploaded_file.read().decode(encoding)
            sio = io.StringIO(content)

            reader = csv.reader(sio)
            rows = [row for row in reader]
            if not rows:
                return None

            header = rows[header_row]
            data = rows[data_start_row:]
            df = pd.DataFrame(data, columns=header)
            return df
        except Exception as e:
            print(f"讀取檔案失敗: {e}")
            return None

    def df2clean(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        將左右兩區資料欄位整併為統一欄位：券商、價格、買進股數、賣出股數
        """
        left_df = df.iloc[:, [1, 2, 3, 4]].copy()
        left_df.columns = ["券商", "價格", "買進股數", "賣出股數"]
        right_df = df.iloc[:, [7, 8, 9, 10]].copy()
        right_df.columns = ["券商", "價格", "買進股數", "賣出股數"]

        combined_df = pd.concat([left_df, right_df], ignore_index=True)
        combined_df["價格"] = pd.to_numeric(combined_df["價格"], errors="coerce")
        combined_df["買進股數"] = (
            pd.to_numeric(combined_df["買進股數"], errors="coerce").fillna(0).astype(int)
        )
        combined_df["賣出股數"] = (
            pd.to_numeric(combined_df["賣出股數"], errors="coerce").fillna(0).astype(int)
        )

        return combined_df.dropna()

    def df2calculate(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        以券商為單位計算買入/賣出均價、總額、淨買賣、當沖量與當沖盈虧等。
        """
        results = {}

        for broker in df["券商"].unique():
            broker_data = df[df["券商"] == broker]

            # Buy
            buy_data = broker_data[broker_data["買進股數"] > 0]
            total_buy_shares = int(buy_data["買進股數"].sum()) if not buy_data.empty else 0
            if total_buy_shares > 0:
                total_buy_amount = float((buy_data["價格"] * buy_data["買進股數"]).sum())
                avg_buy_price = round(total_buy_amount / total_buy_shares, 2)
            else:
                total_buy_amount = 0.0
                avg_buy_price = 0.0

            # Sell
            sell_data = broker_data[broker_data["賣出股數"] > 0]
            total_sell_shares = int(sell_data["賣出股數"].sum()) if not sell_data.empty else 0
            if total_sell_shares > 0:
                total_sell_amount = float((sell_data["價格"] * sell_data["賣出股數"]).sum())
                avg_sell_price = round(total_sell_amount / total_sell_shares, 2)
            else:
                total_sell_amount = 0.0
                avg_sell_price = 0.0

            # Day trade
            day_trade_volume = min(total_buy_shares, total_sell_shares)
            profit_loss = (avg_sell_price - avg_buy_price) * 1000 if day_trade_volume else 0.0

            # Net
            net_shares = total_buy_shares - total_sell_shares
            if net_shares > 0:
                net_buy_amount = (net_shares * avg_buy_price) / 10000 if avg_buy_price else 0.0
                net_sell_amount = 0.0
            else:
                net_buy_amount = 0.0
                net_sell_amount = (abs(net_shares) * avg_sell_price) / 10000 if avg_sell_price else 0.0

            results[broker] = {
                "券商": broker,
                "買入(張)": round(total_buy_shares/1000,1),
                "買入價": round(avg_buy_price, 1),
                "賣出(張)": round(total_sell_shares/1000,1),
                "賣出價": round(avg_sell_price, 1),
                "當沖量(張)": round(day_trade_volume/1000, 1),
                "總買進金額(萬)": round(total_buy_amount/10000, 1),
                "總賣出金額(萬)": round(total_sell_amount/10000, 1),
                "淨買入(張)": round(net_shares/1000, 1) if net_shares > 0 else 0,
                "淨賣出(張)": round(abs(net_shares)/1000, 1) if net_shares < 0 else 0,
                "淨買額(萬)": int(round(net_buy_amount, 1)),
                "淨賣額(萬)": int(round(net_sell_amount, 1)),
                "當沖盈虧(萬)": profit_loss*day_trade_volume/(10000*1000),
            }

        result_df = pd.DataFrame.from_dict(results, orient="index").reset_index(drop=True)
        return result_df.round(1)

    # ====== Top20 報表 ======

    def top20_buy(self, df: pd.DataFrame, n: int = 20) -> pd.DataFrame:
        df_buy_20 = df.sort_values(by="淨買入(張)", ascending=False).head(n)
        cols = ["券商", "買入(張)", "買入價", "賣出(張)", "賣出價", "淨買入(張)", "淨買額(萬)"]
        out = df_buy_20[cols].reset_index(drop=True)
        out.index = out.index + 1
        out.index.name = "名次"
        out["買入價"] = out["買入價"].round(1)
        out["賣出價"] = out["賣出價"].round(1)
        return out

    def top20_sell(self, df: pd.DataFrame, n: int = 20) -> pd.DataFrame:
        df_sell_20 = df.sort_values(by="淨賣出(張)", ascending=False).head(n)
        cols = ["券商", "買入(張)", "買入價", "賣出(張)", "賣出價", "淨賣出(張)", "淨賣額(萬)"]
        out = df_sell_20[cols].reset_index(drop=True)
        out.index = out.index + 1
        out.index.name = "名次"
        out["買入價"] = out["買入價"].round(1)
        out["賣出價"] = out["賣出價"].round(1)
        return out

    def top20_intraday(self, df: pd.DataFrame, n: int = 20) -> pd.DataFrame:
        df_day_20 = df.sort_values(by="當沖量(張)", ascending=False).head(n)
        cols = ["券商", "買入(張)", "買入價", "賣出(張)", "賣出價", "當沖量(張)", "當沖盈虧(萬)"]
        out = df_day_20[cols].reset_index(drop=True)
        out.index = out.index + 1
        out.index.name = "名次"

        # 四捨五入處理
        out["當沖盈虧(萬)"] = out["當沖盈虧(萬)"].round(1)
        out["買入價"] = out["買入價"].round(1)
        out["賣出價"] = out["賣出價"].round(1)

        return out

    # ====== 文字/數值格式工具 ======

    @staticmethod
    def parse_formatted_number(value) -> float:
        if pd.isna(value):
            return 0.0
        if isinstance(value, (int, float, np.number)):
            return float(value)
        if isinstance(value, str):
            v = value.strip().replace(",", "")
            if v.startswith("(") and v.endswith(")"):
                try:
                    return -float(v[1:-1])
                except ValueError:
                    return 0.0
            if "張" in v and "(" in v and ")" in v:
                try:
                    num_part = v.split("張")[0]
                    return float(num_part) * 1000
                except ValueError:
                    return 0.0
            try:
                return float(v)
            except ValueError:
                return 0.0
        return 0.0

    @staticmethod
    def format_broker_name(name) -> str:
        if not isinstance(name, str):
            return ""
        return "".join(
            ch
            for ch in name
            if ("\u4e00" <= ch <= "\u9fff")
            or ("\u3000" <= ch <= "\u303f")
            or ("\uff00" <= ch <= "\uffef")
            or ch in "()-"
        )

    @classmethod
    def format_volume_int(cls, value) -> str:
        numeric_value = cls.parse_formatted_number(value)
        if pd.isna(numeric_value) or numeric_value == 0:
            return "0"
        return f"{int(round(numeric_value))}"

    @classmethod
    def format_volume_with_price_label(cls, volume_val, price_val) -> Tuple[str, str]:
        """
        回傳 (price_text, volume_text)
        """
        volume_text = cls.format_volume_int(volume_val)
        if pd.isna(price_val) or price_val <= 0:
            price_text = ""
        else:
            price_text = f"({price_val:.1f})"
        return price_text, volume_text

    # ====== 匯出 PNG（表格樣式） ======

    @staticmethod
    def df_to_png_bytes(
        df: pd.DataFrame,
        title: str,
        date: str,
        font_path_regular: str = "fonts/NotoSansCJKtc-Regular.otf",
    ) -> io.BytesIO:
        """
        將 DataFrame 轉為表格風格 PNG 圖片位元流
        """
        df = df.copy()
        df.insert(0, "名次", range(1, len(df) + 1))

        prop = fm.FontProperties(fname=Path(font_path_regular))

        def adjust_column_widths(table, df, total_width=1.0):
            col_widths = []
            for col in df.columns:
                max_len = max([len(str(col))] + [len(str(v)) for v in df[col].values])
                col_widths.append(max_len)
            col_widths = np.array(col_widths, dtype=float)
            col_widths = col_widths / col_widths.sum() * total_width
            for col_idx, width in enumerate(col_widths):
                for row_idx in range(len(df) + 1):
                    cell = table[(row_idx, col_idx)]
                    cell.set_width(width)

        fig, ax = plt.subplots(figsize=(len(df.columns) * 1.8, len(df) * 0.48))
        ax.axis("off")

        ax.text(
            0.01,
            0.98,
            title,
            fontsize=16,
            fontproperties=prop,
            color="#333333",
            ha="left",
            va="top",
            transform=ax.transAxes,
        )
        ax.text(
            0.99,
            0.05,
            date,
            fontsize=12,
            fontproperties=prop,
            color="#666666",
            ha="right",
            va="top",
            transform=ax.transAxes,
        )

        table = ax.table(cellText=df.values, colLabels=df.columns, loc="center", cellLoc="center")

        header_text_color = "#FFFFFF"
        header_bg_color = "#4A6FA5"
        text_color = "#333333"
        even_row_color = "#F7F7F7"
        odd_row_color = "#FFFFFF"
        edge_color = "#DDDDDD"

        for (row, col), cell in table.get_celld().items():
            cell.get_text().set_fontproperties(prop)
            cell.get_text().set_fontsize(10)
            if row == 0:
                cell.set_facecolor(header_bg_color)
                cell.get_text().set_color(header_text_color)
                cell.get_text().set_weight("bold")
            else:
                cell.get_text().set_color(text_color)
                if row % 2 == 0:
                    cell.set_facecolor(even_row_color)
                else:
                    cell.set_facecolor(odd_row_color)
            cell.set_edgecolor(edge_color)

        table.scale(1, 1.8)
        adjust_column_widths(table, df)

        buf = io.BytesIO()
        plt.savefig(buf, format="png", bbox_inches="tight", dpi=150, facecolor="white", pad_inches=0.02)
        buf.seek(0)
        plt.close(fig)
        return buf

    # ====== 視覺化（買賣超對照圖） ======

    @staticmethod
    def _load_font(font_path: str) -> Optional[fm.FontProperties]:
        fp = Path(font_path)
        if fp.exists():
            prop = fm.FontProperties(fname=str(fp))
            # 將 rcParams 的族名設為該字型，確保中文字顯示
            plt.rcParams["font.family"] = prop.get_name()
            return prop
        print("❌ 找不到字型檔案：", font_path)
        return None

    @classmethod
    def create_visualization(
        cls,
        buy_top_raw: pd.DataFrame,
        sell_top_raw: pd.DataFrame,
        date: str,
        n_items: int = 20,
        font_path_bold: str = "fonts/NotoSansCJKtc-Bold.otf",
    ):
        """
        建立左右對照長條圖，回傳 matplotlib Figure（不存檔、不自動 close）。
        """
        font_prop = cls._load_font(font_path_bold)

        if (buy_top_raw is None or buy_top_raw.empty) and (sell_top_raw is None or sell_top_raw.empty):
            raise ValueError("買超與賣超資料皆為空，無法建立圖表。")

        num_buy = min(len(buy_top_raw), n_items)
        num_sell = min(len(sell_top_raw), n_items)
        max_rows = max(num_buy, num_sell)

        # 色彩
        bg_color = "#33373D"
        header_color = "#AEAEAE"
        broker_color = "#FFFFFF"
        buy_color_bar = "#A02C2C"
        sell_color_bar = "#2E7D32"
        buy_price_color = "#E57373"
        sell_price_color = "#66BB6A"
        buy_volume_color = "#FF7A7A"
        sell_volume_color = "#81C784"
        summary_color = "#E0E0E0"

        # 字體大小
        header_fontsize = 19
        broker_fontsize = 18
        value_fontsize = 19
        summary_fontsize = 17
        font_weight = "bold"

        row_height_factor = 0.65
        fig_height = 1.8 + max_rows * row_height_factor + 0.8
        fig, ax = plt.subplots(figsize=(9, fig_height), facecolor=bg_color)
        fig.patch.set_facecolor(bg_color)
        ax.set_facecolor(bg_color)
        ax.set_xticks([])
        ax.set_yticks([])
        for spine in ax.spines.values():
            spine.set_visible(False)
        ax.set_ylim(max_rows + 1.2, -1.5)
        ax.set_xlim(-0.05, 1.05)

        # Header
        header_y = -0.5
        ax.text(
            0.5,
            -1.2,
            date,
            color=header_color,
            fontsize=header_fontsize,
            fontweight=font_weight,
            ha="center",
            va="center",
            fontproperties=font_prop,
        )
        ax.text(0.18, header_y, "買超分點", color=header_color, fontsize=header_fontsize, fontweight=font_weight, ha="center", va="center", fontproperties=font_prop)
        ax.text(0.5, header_y, "買賣超張數(價)", color=header_color, fontsize=header_fontsize, fontweight=font_weight, ha="center", va="center", fontproperties=font_prop)
        ax.text(0.82, header_y, "賣超分點", color=header_color, fontsize=header_fontsize, fontweight=font_weight, ha="center", va="center", fontproperties=font_prop)

        # Max scale
        all_volumes_k = []
        if num_buy > 0:
            all_volumes_k.extend(abs(buy_top_raw["淨買入(張)"].head(num_buy)))
        if num_sell > 0:
            all_volumes_k.extend(abs(sell_top_raw["淨賣出(張)"].head(num_sell)))
        max_abs_volume_k = max(all_volumes_k) if all_volumes_k and max(all_volumes_k) > 0 else 1.0

        # Layout params
        x_buy_broker = 0.01
        x_sell_broker = 0.99
        x_volume_center = 0.5
        center_ref = x_volume_center
        base_offset = 0.015
        fixed_gap_value = 0.08
        bar_max_relative_width = 0.40
        bar_height = 0.7

        # Rows
        for i in range(max_rows):
            y = i + 0.5

            # Buy side
            if i < num_buy:
                broker = cls.format_broker_name(buy_top_raw["券商"].iloc[i])
                volume_val = buy_top_raw["淨買入(張)"].iloc[i]
                price_val = buy_top_raw["買入價"].iloc[i]
                price_text, volume_text = cls.format_volume_with_price_label(volume_val, price_val)

                volume_k = abs(volume_val)
                bar_width = (volume_k / max_abs_volume_k) * bar_max_relative_width if max_abs_volume_k > 0 else 0
                bar_left = center_ref - bar_width

                ax.barh(y, width=bar_width, left=bar_left, height=bar_height, color=buy_color_bar, alpha=0.8, edgecolor=None)
                ax.text(x_buy_broker, y, broker, color=broker_color, fontsize=broker_fontsize, fontweight=font_weight, ha="left", va="center", fontproperties=font_prop)

                x_vol = center_ref - base_offset
                ax.text(x_vol, y, volume_text, color=buy_volume_color, fontsize=value_fontsize, fontweight=font_weight, ha="right", va="center", fontproperties=font_prop)
                if price_text:
                    x_price = x_vol - fixed_gap_value
                    ax.text(x_price, y, price_text, color=buy_price_color, fontsize=value_fontsize, fontweight=font_weight, ha="right", va="center", fontproperties=font_prop)

            # Sell side
            if i < num_sell:
                broker = cls.format_broker_name(sell_top_raw["券商"].iloc[i])
                volume_val = sell_top_raw["淨賣出(張)"].iloc[i]
                price_val = sell_top_raw["賣出價"].iloc[i]
                price_text, volume_text = cls.format_volume_with_price_label(volume_val, price_val)

                volume_k = abs(volume_val)
                bar_width = (volume_k / max_abs_volume_k) * bar_max_relative_width if max_abs_volume_k > 0 else 0
                bar_left = center_ref

                ax.barh(y, width=bar_width, left=bar_left, height=bar_height, color=sell_color_bar, alpha=0.8, edgecolor=None)
                ax.text(x_sell_broker, y, broker, color=broker_color, fontsize=broker_fontsize, fontweight=font_weight, ha="right", va="center", fontproperties=font_prop)

                x_vol = center_ref + base_offset
                ax.text(x_vol, y, volume_text, color=sell_volume_color, fontsize=value_fontsize, fontweight=font_weight, ha="left", va="center", fontproperties=font_prop)
                if price_text:
                    x_price = x_vol + fixed_gap_value
                    ax.text(x_price, y, price_text, color=sell_price_color, fontsize=value_fontsize, fontweight=font_weight, ha="left", va="center", fontproperties=font_prop)

        # Summary
        total_buy_k = buy_top_raw["淨買入(張)"].head(num_buy).sum()  if num_buy > 0 else 0
        total_sell_k = sell_top_raw["淨賣出(張)"].head(num_sell).sum()  if num_sell > 0 else 0
        summary_text = f"Top{n_items} 總買超: {total_buy_k:,.0f} 張       Top{n_items} 總賣超: {total_sell_k:,.0f} 張"
        summary_y = max_rows + 0.9
        ax.text(0.5, summary_y, summary_text, ha="center", va="center", color=summary_color, fontsize=summary_fontsize, fontweight=font_weight, fontproperties=font_prop)

        plt.tight_layout(pad=0.8)
        return fig

    # ====== 其他小工具 ======

    @staticmethod
    def fig_to_png_bytes(fig: plt.Figure, dpi: int = 300) -> io.BytesIO:
        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=dpi, bbox_inches="tight", facecolor=fig.get_facecolor())
        buf.seek(0)
        return buf
