import io
import csv
import numpy as np
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path
import io
from datetime import datetime
from zoneinfo import ZoneInfo
import matplotlib.ticker as ticker
import matplotlib.font_manager as fm
from matplotlib import rcParams
from matplotlib.font_manager import FontProperties

from trade_analyzer import StockTradeAnalyzer


analyzer = StockTradeAnalyzer()

# --- Streamlit 主程式 ---

# 🔵 CSS 調小字體
st.markdown("""
    <style>
    div[data-testid="stDataFrame"] div { 
        font-size: 12px;
    }
    div[data-testid="stTable"] div {
        font-size: 12px;
    }
    div[data-baseweb="select"] {
        max-height: 300px;
        overflow-y: auto;
    }
    </style>
""", unsafe_allow_html=True)

# --- 頁面標題 ---
st.title("買賣日報表彙總分析")
st.caption("每日籌碼可至 https://bsr.twse.com.tw/bshtm/ 下載")

taiwan_today = datetime.now(ZoneInfo("Asia/Taipei")).date()
selected_date = st.date_input("選擇報表日期", value=taiwan_today)
date_str = selected_date.strftime("%Y-%m-%d")
st.caption(f"📅 目前報表日期為：{date_str}")

# --- 上傳CSV ---
uploaded_file = st.file_uploader("上傳CSV檔案", type=["csv"])
if uploaded_file is not None:
    df2 = analyzer.csv2df(uploaded_file)
    df_raw = analyzer.df2clean(df2)
    df = analyzer.df2calculate(df_raw)
    
    if df is not None:
        st.success("檔案已整理完成！")

        # 🔵 篩選功能
        st.subheader("原始資料篩選區")

        # 價格範圍（手動輸入）
        min_price_raw = float(df_raw['價格'].min())
        max_price_raw = float(df_raw['價格'].max())

        col1, col2 = st.columns(2)
        with col1:
            price_min_raw = st.number_input(
                "原始資料 - 輸入最小價格",
                min_value=min_price_raw,
                max_value=max_price_raw,
                value=min_price_raw,
                step=0.5,
                format="%.2f",
                key="price_min_raw"
            )
        with col2:
            price_max_raw = st.number_input(
                "原始資料 - 輸入最大價格",
                min_value=min_price_raw,
                max_value=max_price_raw,
                value=max_price_raw,
                step=0.5,
                format="%.2f",
                key="price_max_raw"
            )

        # 券商名稱選擇（可搜尋且加捲軸）
        all_brokers_raw = df_raw['券商'].dropna().unique().tolist()
        selected_brokers_raw = st.multiselect(
            "原始資料 - 選擇券商（可複選）",
            options=all_brokers_raw,
            key="brokers_raw"
        )

        # 🔵 原始資料篩選（用 df_raw）
        df_raw_filtered = df_raw[
            (df_raw['價格'] >= price_min_raw) & 
            (df_raw['價格'] <= price_max_raw)
        ]
        if selected_brokers_raw:
            df_raw_filtered = df_raw_filtered[df_raw_filtered['券商'].isin(selected_brokers_raw)]

        # --- 顯示原始資料 ---
        st.subheader("原始資料")
        st.dataframe(df_raw_filtered, use_container_width=True)

        # CSV 下載按鈕（原本的）
        csv_raw_filtered = df_raw_filtered.to_csv(index=False).encode('utf-8-sig')
        st.download_button(
            label="下載原始資料 CSV",
            data=csv_raw_filtered,
            file_name=f'原始資料_{date_str}.csv',
            mime='text/csv'
        )
        st.divider()


        # --- 彙整資料篩選區 ---
        st.subheader("彙整資料篩選區")

        min_price_agg = float(df['買入價'].min())
        max_price_agg = float(df['買入價'].max())

        col1, col2 = st.columns(2)
        with col1:
            price_min_agg = st.number_input(
                "彙整資料 - 輸入最小價格",
                min_value=min_price_agg,
                max_value=max_price_agg,
                value=min_price_agg,
                step=0.5,
                format="%.2f",
                key="price_min_agg"
            )
        with col2:
            price_max_agg = st.number_input(
                "彙整資料 - 輸入最大價格",
                min_value=min_price_agg,
                max_value=max_price_agg,
                value=max_price_agg,
                step=0.5,
                format="%.2f",
                key="price_max_agg"
            )

        all_brokers_agg = df['券商'].dropna().unique().tolist()
        selected_brokers_agg = st.multiselect(
            "彙整資料 - 選擇券商（可複選）",
            options=all_brokers_agg,
            key="brokers_agg"
        )

        df_filtered = df[
            (df['買入價'] >= price_min_agg) & 
            (df['買入價'] <= price_max_agg)
        ]
        if selected_brokers_agg:
            df_filtered = df_filtered[df_filtered['券商'].isin(selected_brokers_agg)]

        st.subheader("彙整資料")
        st.dataframe(df_filtered, use_container_width=True)
        
        # CSV 下載按鈕（原本的）
        csv_filtered = df_filtered.to_csv(index=False).encode('utf-8-sig')
        st.download_button(
            label="下載彙整資料 CSV",
            data=csv_filtered,
            file_name=f'彙整資料_{date_str}.csv',
            mime='text/csv'
        )

        st.divider()



        # --- Top20 報表 + 下載 ---

        ## 📈 買超前20名
        st.subheader("📈 買超前20名")
        df_buy = analyzer.top20_buy(df)  # 這裡是你原本的邏輯
        st.table(df_buy.style.format({
            "買入價": "{:.1f}",
            "賣出價": "{:.1f}",
            "買入(張)": "{:.0f}",
            "賣出(張)": "{:.0f}",
            "淨買入(張)": "{:.0f}"
        }))

        # CSV 下載
        csv_buy = df_buy.to_csv(index=False).encode('utf-8-sig')
        st.download_button(
            label="下載買超前20名 CSV",
            data=csv_buy,
            file_name=f'買超前20名_{date_str}.csv',
            mime='text/csv'
        )

        # PNG 下載
        png_buf_buy = analyzer.df_to_png_bytes(df_buy, "買超前20名", date_str)
        st.download_button(
            label="下載買超前20名 PNG",
            data=png_buf_buy,
            file_name=f'買超前20名_{date_str}.png',
            mime='image/png'
        )

        st.divider()


        ## 📉 賣超前20名
        st.subheader("📉 賣超前20名")
        df_sell = analyzer.top20_sell(df)  # 這裡是你原本的邏輯
        st.table(df_sell.style.format({
            "買入價": "{:.1f}",
            "賣出價": "{:.1f}",
            "買入(張)": "{:.0f}",
            "賣出(張)": "{:.0f}",
            "淨賣出(張)": "{:.0f}"
        }))

        # CSV 下載
        csv_sell = df_sell.to_csv(index=False).encode('utf-8-sig')
        st.download_button(
            label="下載賣超前20名 CSV",
            data=csv_sell,
            file_name=f'賣超前20名_{date_str}.csv',
            mime='text/csv'
        )

        # PNG 下載
        png_buf_sell = analyzer.df_to_png_bytes(df_sell, "賣超前20名", date_str)
        st.download_button(
            label="下載賣超前20名 PNG",
            data=png_buf_sell,
            file_name=f'賣超前20名_{date_str}.png',
            mime='image/png'
        )

        st.divider()


        ## ⚡ 當沖前20名
        st.subheader("⚡ 當沖前20名")
        df_intraday = analyzer.top20_intraday(df)  # 這裡是你原本的邏輯
        st.table(df_intraday.style.format({
            "買入(張)": "{:.0f}",
            "賣出(張)": "{:.0f}",
            "當沖量(張)": "{:.0f}",
            "買入價": "{:.1f}",
            "賣出價": "{:.1f}",
            "當沖盈虧(萬)": "{:.1f}"
        }))

        # CSV 下載
        csv_intraday = df_intraday.to_csv(index=False).encode('utf-8-sig')
        st.download_button(
            label="下載當沖前20名 CSV",
            data=csv_intraday,
            file_name=f'當沖前20名_{date_str}.csv',
            mime='text/csv'
        )

        # PNG 下載
        png_buf_intraday = analyzer.df_to_png_bytes(df_intraday, "當沖前20名", date_str)
        st.download_button(
            label="下載當沖前20名 PNG",
            data=png_buf_intraday,
            file_name=f'當沖前20名_{date_str}.png',
            mime='image/png'
        )

        st.divider()
        

        ## 圖片

        st.subheader("🚀 買賣超對照圖")
        fig = analyzer.create_visualization(df_buy, df_sell, date_str)

        # 將圖形儲存到 BytesIO
        buf = io.BytesIO()
        fig.savefig(buf, format='png', dpi=300, bbox_inches='tight', facecolor=fig.get_facecolor())
        buf.seek(0)

        # 顯示圖片
        st.image(buf, caption="📷 買賣超對照圖", use_container_width=True)

        # 下載按鈕
        st.download_button(
            label="下載買賣超對照圖 PNG",
            data=buf,
            file_name=f"買賣超對照圖_{date_str}.png",
            mime="image/png"
        )
