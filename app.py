import streamlit as st
import requests
import datetime
import time
import pandas as pd
import streamlit.components.v1 as components

st.set_page_config(page_title="Stanley 戰略指揮部", page_icon="🛡️", layout="wide")

st.title("🛡️ 流動性雷達 (7日戰略趨勢版)")
st.caption("當前執行進度：已於 28 元減碼第二部分 | 目標：2031 優雅退休")

tz_tw = datetime.timezone(datetime.timedelta(hours=8))
now = datetime.datetime.now(tz_tw)

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'
}

@st.cache_data(ttl=7200)
def fetch_past_7_days(now_dt):
    history_records = []
    current_check = now_dt
    loop_count = 0 
    
    while len(history_records) < 7 and loop_count < 15:
        if current_check.weekday() in [5, 6]:
            current_check -= datetime.timedelta(days=1)
            continue
            
        loop_count += 1
        date_str = current_check.strftime("%Y%m%d")
        roc_year = int(date_str[:4]) - 1911
        target_roc_date = f"{roc_year}/{date_str[4:6]}/{date_str[6:8]}"
        
        m_url = f"https://www.twse.com.tw/exchangeReport/FMTQIK?response=json&date={date_str}"
        d_url = f"https://www.twse.com.tw/exchangeReport/TWTB4U?response=json&date={date_str}&selectType=All"
        
        try:
            m_res = requests.get(m_url, headers=headers, timeout=5).json()
            time.sleep(1.0)
            d_res = requests.get(d_url, headers=headers, timeout=5).json()
            
            if 'data' in m_res and ('data' in d_res or 'tables' in d_res):
                m_idx = 2
                for idx, f_item in enumerate(m_res.get('fields', [])):
                    if '成交金額' in f_item: m_idx = idx; break
                
                total_market_val = None
                for row in m_res['data']:
                    if row[0].strip() == target_roc_date:
                        total_market_val = float(str(row[m_idx]).replace(',', '').strip())
                        break
                
                if total_market_val is None:
                    total_market_val = float(str(m_res['data'][-1][m_idx]).replace(',', '').strip())
                
                ratio = 0.0
                parsed_success = False
                
                if 'tables' in d_res:
                    for table in d_res['tables']:
                        fields = table.get('fields', [])
                        t_data = table.get('data', [])
                        if not t_data: continue
                        if any('總買進' in f for f in fields):
                            b_idx, r_idx = -1, -1
                            for idx, f in enumerate(fields):
                                if '買進' in f and ('比重' in f or '占' in f or '%' in f): r_idx = idx
                                elif '買進' in f and '金額' in f: b_idx = idx
                            
                            row = t_data[0]
                            if r_idx != -1 and r_idx < len(row):
                                ratio = float(str(row[r_idx]).replace(',', '').strip())
                                parsed_success = True; break
                                
                if not parsed_success and 'data' in d_res:
                    d_idx = 4
                    for idx, f in enumerate(d_res.get('fields', [])):
                        if '買進' in f and '金額' in f: d_idx = idx; break
                    for row in d_res['data']:
                        if row and len(row) > d_idx and ('合' in str(row[0]) or '總' in str(row[0])):
                            ratio = (float(str(row[d_idx]).replace(',', '').strip()) / total_market_val) * 100
                            parsed_success = True; break
                
                if parsed_success and ratio > 0:
                    display_date = f"{date_str[4:6]}/{date_str[6:8]}"
                    history_records.append({
                        "📋 日期": display_date,
                        "大盤成交量(億)": round(total_market_val / 1e8, 1),
                        "當沖佔比(%)": round(ratio, 2)
                    })
        except Exception: pass
        current_check -= datetime.timedelta(days=1)
        time.sleep(0.3)
        
    return pd.DataFrame(history_records)[::-1].reset_index(drop=True)

df_history = fetch_past_7_days(now)

if not df_history.empty:
    latest_row = df_history.iloc[-1]
    latest_date = latest_row["📋 日期"]
    total_market_val = latest_row["大盤成交量(億)"]
    ratio = latest_row["當沖佔比(%)"]
    
    st.write(f"📊 最新觀測交易日：**{latest_date}**")
    
    if len(df_history) < 7:
        st.warning(f"⚠️ 提示：因雲端共用 IP 受證交所流控限制，目前成功調取 {len(df_history)} 天數據。")
    
    col1, col2 = st.columns(2)
    with col1:
        st.html(f'<div style="background-color: #ffffff; padding: 18px; border-radius: 10px; border: 1px solid #e2e8f0; text-align: center; box-shadow: 0 2px 4px rgba(0,0,0,0.02);"><p style="color: #64748b; margin: 0; font-size: 14px; font-weight: bold;">最新大盤成交</p><h2 style="color: #1e3a8a; margin: 8px 0 0 0; font-size: 32px; font-weight: 800;">{total_market_val:.0f} 億</h2></div>')
    with col2:
        text_color = "#dc2626" if ratio > 50 else "#16a34a"
        st.html(f'<div style="background-color: #ffffff; padding: 18px; border-radius: 10px; border: 1px solid #e2e8f0; text-align: center; box-shadow: 0 2px 4px rgba(0,0,0,0.02);"><p style="color: #64748b; margin: 0; font-size: 14px; font-weight: bold;">🔥 最新當沖佔比</p><h2 style="color: {text_color}; margin: 8px 0 0 0; font-size: 32px; font-weight: 800;">{ratio:.2f}%</h2></div>')
        
    st.divider()
    
    st.subheader("📈 7日流動性動態趨勢線 (安全向量版)")
    
    ratios = df_history["當沖佔比(%)"].tolist()
    dates = df_history["📋 日期"].tolist()
    
    min_r, max_r = min(ratios) - 2, max(ratios) + 2
    svg_w, svg_h, pad_x, pad_y = 600, 180, 50, 30
    
    denom_x = max(1, len(ratios) - 1)
    denom_y = max(0.1, max_r - min_r)
    
    points = []
    for idx, r in enumerate(ratios):
        x = pad_x + idx * ((svg_w - 2 * pad_x) / denom_x)
        y = svg_h - pad_y - ((r - min_r) / denom_y) * (svg_h - 2 * pad_y)
        points.append(f"{x},{y}")
    
    path_d = "M " + " L ".join(points)
    dots_html = "".join([f'<circle cx="{pad_x + idx * ((svg_w - 2 * pad_x) / denom_x)}" cy="{svg_h - pad_y - ((r - min_r) / denom_y) * (svg_h - 2 * pad_y)}" r="4" fill="#16a34a" stroke="#ffffff" stroke-width="1.5"/>' for idx, r in enumerate(ratios)])
    
    labels_html = ""
    for idx, (r, d) in enumerate(zip(ratios, dates)):
        x = pad_x + idx * ((svg_w - 2 * pad_x) / denom_x)
        y = svg_h - pad_y - ((r - min_r) / denom_y) * (svg_h - 2 * pad_y)
        labels_html += f'<text x="{x}" y="{svg_h - 8}" font-size="10" font-family="sans-serif" text-anchor="middle" fill="#64748b">{d}</text>'
        labels_html += f'<text x="{x}" y="{y - 10}" font-size="10" font-family="sans-serif" font-weight="bold" text-anchor="middle" fill="#1e293b">{r:.1f}%</text>'
    
    y_50 = svg_h - pad_y - ((50 - min_r) / denom_y) * (svg_h - 2 * pad_y)
    alert_line = f'<line x1="{pad_x}" y1="{y_50}" x2="{svg_w-pad_x}" y2="{y_50}" stroke="#ef4444" stroke-width="1" stroke-dasharray="4,4"/>' if min_r <= 50 <= max_r else ""
    alert_text = f'<text x="{svg_w-pad_x+5}" y="{y_50+3}" font-size="9" fill="#ef4444" font-family="sans-serif">50% 警戒線</text>' if min_r <= 50 <= max_r else ""

    components.html(f"""
    <div style="background-color: #ffffff; padding: 15px; border-radius: 10px; border: 1px solid #e2e8f0; box-shadow: 0 2px 4px rgba(0,0,0,0.02); margin: 0; overflow: hidden;">
        <svg width="100%" height="{svg_h}" viewBox="0 0 {svg_w} {svg_h}" preserveAspectRatio="xMidYMid meet">
            <line x1="{pad_x}" y1="{pad_y}" x2="{svg_w-pad_x}" y2="{pad_y}" stroke="#f1f5f9"/>
            <line x1="{pad_x}" y1="{svg_h-pad_y}" x2="{svg_w-pad_x}" y2="{svg_h-pad_y}" stroke="#cbd5e1" stroke-width="1"/>
            {alert_line}{alert_text}
            <path d="{path_d}" fill="none" stroke="#2563eb" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>
            {dots_html}{labels_html}
        </svg>
    </div>
    """, height=210)

    st.divider()

    with st.expander("📋 查看歷史數據明細"):
        st.dataframe(df_history[["📋 日期", "大盤成交量(億)", "當沖佔比(%)"]], use_container_width=True)

    if ratio > 50: st.error(f"🚨 【極端紅色警戒】最新當沖破 50% ！")
    elif ratio > 40: st.warning("⚠️ 【投機升溫】籌碼浮躁，大盤處於高檔震盪。")
    else: st.success("✅ 【籌碼穩定】目前市場結構健康。")

    st.info("💡 Stanley 軍規提醒：\n- 00878 剩餘 2 部分，不到 21% 獲利不動手。\n- 資金已還款存放於理財房貸，信用額度安全。")
else:
    st.error("❌ 證交所目前對雲端共享 IP 實施高度流控封鎖中，請稍微等待快取更新，或重新整理網頁。")
