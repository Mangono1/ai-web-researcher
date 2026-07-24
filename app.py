import streamlit as st
import requests
from bs4 import BeautifulSoup

# --- 1. FUNGSI PENCARIAN GOOGLE CUSTOM SEARCH (CSE) ---
def cari_di_google_cse(kata_kunci, api_key, cx_id):
    url = "https://customsearch.googleapis.com/customsearch/v1"
    params = {
        'q': kata_kunci,
        'key': api_key,
        'cx': cx_id,
    }
    
    response = requests.get(url, params=params)
    
    if response.status_code == 200:
        data = response.json()
        # Mengambil 3 link teratas dari hasil pencarian
        links = [item['link'] for item in data.get('items', [])[:3]]
        return links
    else:
        st.error(f"Error dari Google: {response.status_code} - {response.text}")
        return []

# --- KODE EKSTRAKSI TEKS TETAP SAMA ---
def ambil_teks_artikel(url):
    # ... (Gunakan fungsi ambil_teks_artikel dari kode sebelumnya) ...
    pass
# --- 3. ANTARMUKA STREAMLIT (UI) ---
st.set_page_config(page_title="Pencari & Perangkum AI", page_icon="🔍")

st.title("🔍 Asisten Riset Otomatis")
st.write("Sistem ini akan mencari informasi di Google, mengambil isi artikelnya, dan menyiapkannya untuk diringkas.")

# Mengambil API Key dari Brankas Streamlit (Secrets)
try:
    SERPER_API_KEY = st.secrets["SERPER_API_KEY"]
except KeyError:
    st.error("⚠️ API Key tidak ditemukan! Pastikan sudah mengatur 'SERPER_API_KEY' di Streamlit Secrets.")
    st.stop() # Hentikan program jika API Key tidak ada

# Kotak Input Pengguna
query = st.text_input("Topik apa yang ingin kamu riset hari ini?")

if st.button("Mulai Riset"):
    if query:
        # Menampilkan animasi loading
        with st.status("Memproses permintaanmu...", expanded=True) as status:
            st.write("🔍 Mencari referensi terbaik di Google...")
            daftar_link = cari_di_google(query, SERPER_API_KEY)
            
            if not daftar_link:
                status.update(label="Pencarian gagal atau tidak ada hasil.", state="error")
                st.stop()
                
            st.write(f"✅ Ditemukan {len(daftar_link)} referensi utama.")
            
            kumpulan_teks = ""
            for i, link in enumerate(daftar_link):
                st.write(f"📥 Membaca artikel {i+1}...")
                teks = ambil_teks_artikel(link)
                if teks:
                    # Kita batasi 1000 karakter per artikel agar tidak membebani memori
                    kumpulan_teks += f"Sumber: {link}\n{teks[:1000]}...\n\n"
            
            status.update(label="Ekstraksi selesai!", state="complete", expanded=False)
        
        # Menampilkan Hasil
        st.subheader("📑 Teks yang Berhasil Diekstrak")
        st.text_area("Teks ini siap dikirim ke AI untuk diringkas:", value=kumpulan_teks, height=300)
        
        st.info("💡 Tahap selanjutnya: Menghubungkan teks di atas dengan API Kecerdasan Buatan (AI) untuk membuat ringkasan otomatis.")
        
    else:
        st.warning("Masukkan topik pencarian terlebih dahulu!")
