import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

# --- CONFIGURATION & PATH ---
DATA_PATH = r"C:\Users\michael.sidabutar\Documents\analisis ikpa 2025\rpata\dataset.csv"

st.set_page_config(page_title="Pemantauan RPATA 2025", layout="wide")

# --- SISTEM LOGIN SEDERHANA ---
def check_password():
    """Mengembalikan True jika pengguna memasukkan password yang benar."""
    def password_entered():
        """Memeriksa apakah password yang dimasukkan benar."""
        if st.session_state["password"] == "admin123": # <--- GANTI PASSWORD DI SINI
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # Hapus password dari session state
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        # Tampilan Form Login
        st.markdown("### 🔒 Silakan Login")
        st.text_input("Password", type="password", on_change=password_entered, key="password")
        return False
    elif not st.session_state["password_correct"]:
        # Tampilan jika password salah
        st.markdown("### 🔒 Silakan Login")
        st.text_input("Password", type="password", on_change=password_entered, key="password")
        st.error("😕 Password salah")
        return False
    else:
        # Password benar
        return True

# JALANKAN LOGIN TERLEBIH DAHULU
if check_password():

    # --- CUSTOM CSS ---
    st.markdown("""
        <style>
        .reportview-container .main .block-container { padding-top: 2rem; }
        .stMetric { background-color: #f8f9fa; padding: 15px; border-radius: 10px; border: 1px solid #e9ecef; }
        h3 { margin-top: 25px; border-left: 5px solid #ff4b4b; padding-left: 10px; font-weight: bold; color: #1e3d59; }
        [data-testid="stMetricValue"] { font-size: 1.6rem !important; }
        </style>
        """, unsafe_allow_html=True)

    # --- FUNGSI FORMAT RUPIAH & UNIT INDONESIA ---
    def format_rp(value):
        return f"Rp {value:,.0f}".replace(",", ".")

    def format_unit_id(value):
        if value >= 1_000_000_000_000:
            return f"{value / 1_000_000_000_000:.2f} T"
        elif value >= 1_000_000_000:
            return f"{value / 1_000_000_000:.2f} M"
        elif value >= 1_000_000:
            return f"{value / 1_000_000:.2f} Jt"
        else:
            return f"{value:,.0f}"

    # --- DATA ENGINE ---
    @st.cache_data
    def load_clean_data(path):
        df = pd.read_csv(path)
        df.columns = [c.replace('\n', ' ').strip() for c in df.columns]
        for col in df.columns:
            if "No Kontrak" in col:
                df.rename(columns={col: "No Kontrak"}, inplace=True)
        
        currency_cols = ['Total Nilai Kontrak', 'Nilai Kontrak yang Sudah Dibayarkan', 
                         'Pengisian', 'Belanja_Pembayaran', 'Potongan_Pembayaran', 
                         'Penihilan', 'Saldo']
        for col in currency_cols:
            if col in df.columns:
                df[col] = df[col].replace('Rp', '', regex=True).replace('\.', '', regex=True).replace(',', '.', regex=True).replace('-', '0', regex=True).astype(float)
        
        df['Tgl Kontrak'] = pd.to_datetime(df['Tgl Kontrak'], errors='coerce')
        df['Tgl Kesempatan'] = pd.to_datetime(df['Tanggal Akhir Pemberian Kesempatan'], errors='coerce')
        
        today = datetime.now()
        df['Sisa_Hari'] = (df['Tgl Kesempatan'] - today).dt.days
        return df

    try:
        df = load_clean_data(DATA_PATH)
    except Exception as e:
        st.error(f"Error: {e}")
        st.stop()

    kontrak_kesempatan = df[df['Tgl Kesempatan'].notnull()].copy()

    # --- SIDEBAR LOGOUT (Opsional) ---
    with st.sidebar:
        if st.button("Logout"):
            del st.session_state["password_correct"]
            st.rerun()

    # --- HEADER ---
    st.title("📑 Pemantauan RPATA 2025")

    tab1, tab2 = st.tabs(["📊 Brief Report", "🔍 Rincian"])

    # --- TAB 1: BRIEF REPORT ---
    with tab1:
        st.subheader("📌 Ringkasan Nilai Kontrak Utama")
        ra1, ra2 = st.columns(2)
        with ra1:
            st.metric("Total Jumlah Kontrak", f"{len(df)} Kontrak")
            st.metric("Total Nilai Kontrak", format_rp(df['Total Nilai Kontrak'].sum()))
        with ra2:
            st.metric("Total Nama Supplier", f"{df['Nama Supplier'].nunique()} Vendor")

        st.subheader("💰 Status Pencadangan (RPATA)")
        rb1, rb2 = st.columns([1, 2])
        with rb1:
            st.metric("Total Nilai Dicadangkan (Pengisian)", format_rp(df['Pengisian'].sum()))
            st.metric("Realisasi Pembayaran (Belanja)", format_rp(df['Belanja_Pembayaran'].sum()))
            st.metric("Total Sisa Cadangan (Saldo)", format_rp(df['Saldo'].sum()))
            st.metric("Total Tidak Terbayar (Penihilan)", format_rp(df['Penihilan'].sum()))
        with rb2:
            labels = ['Belanja (Dibayar)', 'Saldo (Sisa)', 'Penihilan']
            values = [df['Belanja_Pembayaran'].sum(), df['Saldo'].sum(), df['Penihilan'].sum()]
            fig_rpata = px.pie(names=labels, values=values, title="Proporsi Pemanfaatan Dana Cadangan (RPATA)",
                               color_discrete_sequence=px.colors.sequential.RdBu)
            st.plotly_chart(fig_rpata, use_container_width=True)

        st.divider()

        # --- COMPARISON PER KPPN ---
        st.subheader("⚖️ Perbandingan Antar KPPN")
        kppn_metrics = df.groupby('KPPN').agg({'No': 'count', 'Belanja_Pembayaran': 'sum', 'Saldo': 'sum', 'Total Nilai Kontrak': 'sum'}).reset_index().rename(columns={'No': 'Total Kontrak'})
        kppn_melted = kppn_metrics.melt(id_vars='KPPN', value_vars=['Belanja_Pembayaran', 'Saldo'], var_name='Status', value_name='Nilai')
        fig_stack = px.bar(kppn_melted, x='KPPN', y='Nilai', color='Status', title="Monitoring Pembayaran: Realisasi vs Sisa Saldo per KPPN", color_discrete_map={'Belanja_Pembayaran': '#1f77b4', 'Saldo': '#ff4b4b'})
        st.plotly_chart(fig_stack, use_container_width=True)

        # --- ANALISIS SATKER TERAKTIF & TERBESAR ---
        st.divider()
        st.subheader("🏢 Analisis Satker Teraktif & Saldo Terbesar")
        
        st.write("#### 🔝 Top 10 Satker dengan Kontrak Terbanyak")
        top_satker_cnt = df.groupby(['Satker', 'KPPN']).size().reset_index(name='Jumlah Kontrak').sort_values('Jumlah Kontrak', ascending=False).head(10)
        sc1, sc2 = st.columns([2, 1])
        with sc1:
            fig_cnt = px.bar(top_satker_cnt, x='Jumlah Kontrak', y='Satker', orientation='h', text='Jumlah Kontrak', color='Jumlah Kontrak', color_continuous_scale='Blues')
            fig_cnt.update_layout(yaxis={'categoryorder':'total ascending'})
            st.plotly_chart(fig_cnt, use_container_width=True)
        with sc2:
            st.dataframe(top_satker_cnt, use_container_width=True, hide_index=True)

        st.write("#### 💰 Top 10 Satker dengan Saldo Terbesar")
        top_satker_saldo = df.groupby(['Satker', 'KPPN'])['Saldo'].sum().reset_index().sort_values('Saldo', ascending=False).head(10)
        top_satker_saldo['Label_Saldo'] = top_satker_saldo['Saldo'].apply(format_unit_id)
        
        ss1, ss2 = st.columns([2, 1])
        with ss1:
            fig_sld = px.bar(top_satker_saldo, x='Saldo', y='Satker', orientation='h', text='Label_Saldo', color='Saldo', color_continuous_scale='Reds')
            fig_sld.update_layout(yaxis={'categoryorder':'total ascending'})
            st.plotly_chart(fig_sld, use_container_width=True)
        with ss2:
            top_satker_saldo_view = top_satker_saldo.drop(columns=['Label_Saldo']).copy()
            top_satker_saldo_view['Saldo'] = top_satker_saldo_view['Saldo'].apply(format_rp)
            st.dataframe(top_satker_saldo_view, use_container_width=True, hide_index=True)

        st.divider()

        # --- DAFTAR KONTRAK KESEMPATAN ---
        st.subheader("📅 Daftar Kontrak Dalam Masa Pemberian Kesempatan")
        if not kontrak_kesempatan.empty:
            df_view_kes = kontrak_kesempatan[['KPPN', 'No Kontrak', 'Satker', 'Nama Supplier', 'Tgl Kesempatan', 'Sisa_Hari', 'Saldo']].copy()
            
            def highlight_deadline(row):
                styles = [''] * len(row)
                if row['Sisa_Hari'] <= 7:
                    styles = ['background-color: #ff4b4b; color: white'] * len(row)
                elif row['Sisa_Hari'] <= 14:
                    styles = ['background-color: #ffa500; color: black'] * len(row)
                return styles

            df_view_kes_styled = df_view_kes.sort_values('Sisa_Hari').style.apply(highlight_deadline, axis=1).format({'Saldo': format_rp})
            st.dataframe(df_view_kes_styled, use_container_width=True, hide_index=True)
            st.info("💡 **Keterangan:** Merah (≤ 7 hari), Oranye (≤ 14 hari)")
        else:
            st.info("Tidak ada data kontrak dalam masa pemberian kesempatan.")

    # --- TAB 2: RINCIAN ---
    with tab2:
        st.subheader("🔍 Filter & Rincian Penanggung Jawab")
        list_kppn = sorted(df['KPPN'].unique().tolist())
        selected_kppn = st.selectbox("Pilih KPPN Penanggung Jawab:", ["Semua KPPN"] + list_kppn)

        df_filtered = df if selected_kppn == "Semua KPPN" else df[df['KPPN'] == selected_kppn]
        df_unpaid = df_filtered[df_filtered['Saldo'] > 0].copy()

        st.subheader(f"🚩 Rincian Kontrak dengan Saldo Aktif ({selected_kppn})")
        if not df_unpaid.empty:
            df_unpaid_view = df_unpaid[['No Kontrak', 'Satker', 'Nama Supplier', 'Saldo', 'Tgl Kontrak']].copy()
            df_unpaid_view['Tgl Kontrak'] = df_unpaid_view['Tgl Kontrak'].dt.strftime('%d-%m-%Y')
            df_unpaid_view['Saldo'] = df_unpaid_view['Saldo'].apply(format_rp)
            st.dataframe(df_unpaid_view, use_container_width=True, hide_index=True)
        else:
            st.success("Tidak ada saldo aktif.")

        st.divider()

        # --- SUPPLIER INSIGHTS ---
        st.subheader("🏆 Analisis Supplier (Top 10 Global)")
        cl, cr = st.columns(2)
        
        with cl:
            st.write("**Top 10 Supplier (Saldo Terbanyak):**")
            t_val = df.groupby('Nama Supplier')['Saldo'].sum().sort_values(ascending=False).head(10).reset_index()
            t_val['Label_Saldo'] = t_val['Saldo'].apply(format_unit_id)
            fig_sup_val = px.bar(t_val, x='Saldo', y='Nama Supplier', orientation='h', text='Label_Saldo', color='Saldo', color_continuous_scale='Viridis')
            fig_sup_val.update_layout(yaxis={'categoryorder':'total ascending'}, showlegend=False)
            st.plotly_chart(fig_sup_val, use_container_width=True)
            
            t_val_table = t_val.drop(columns=['Label_Saldo']).copy()
            t_val_table['Saldo'] = t_val_table['Saldo'].apply(format_rp)
            st.dataframe(t_val_table, use_container_width=True, hide_index=True)

        with cr:
            st.write("**Top 10 Supplier (Kontrak Terbanyak):**")
            t_cnt = df.groupby('Nama Supplier').size().reset_index(name='Jumlah Kontrak').sort_values('Jumlah Kontrak', ascending=False).head(10)
            fig_sup_cnt = px.bar(t_cnt, x='Jumlah Kontrak', y='Nama Supplier', orientation='h', text='Jumlah Kontrak', color='Jumlah Kontrak', color_continuous_scale='Plasma')
            fig_sup_cnt.update_layout(yaxis={'categoryorder':'total ascending'}, showlegend=False)
            st.plotly_chart(fig_sup_cnt, use_container_width=True)
            st.dataframe(t_cnt, use_container_width=True, hide_index=True)

