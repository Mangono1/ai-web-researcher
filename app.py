import streamlit as st
import requests
from bs4 import BeautifulSoup

# ==========================================
# 1. FUNGSI PENCARIAN GOOGLE (CUSTOM SEARCH API)
# ==========================================
def cari_di_google(kata_kunci, api_key, cx_id):
    url = "https://customsearch.googleapis.com/customsearch/v1"
    params = {
        'q': kata_kunci,
        'key': api_key,
        'cx': cx_id,
        'num': 3  # Mengambil 3 hasil teratas
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            items = data.get('items', [])
            links = [item['link'] for item in items]
            return links
        else:
            st.error(f"Gagal mengambil dari Google CSE API (Status Code: {response.status_code})")
            st.write(response.json())
            return []
    except Exception as e:
        st.error(f"Terjadi kesalahan koneksi API: {e}")
        return []

# ==========================================
# 2. FUNGSI EKSTRAKSI TEKS WEB (BEAUTIFULSOUP)
# ==========================================
def ambil_teks_artikel(url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    try:
        response = requests.get(url, headers=headers, timeout=8)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Buang elemen HTML non-artikel/sampah
        for elemen in soup(['script', 'style', 'header', 'footer', 'nav', 'aside', 'form']):
            elemen.decompose()
            
        # Ambil teks paragraf yang panjangnya lebih dari 30 karakter
        paragraf = [p.get_text() for p in soup.find_all('p') if len(p.get_text().strip()) > 30]
        teks_bersih = " ".join(" ".join(paragraf).split())
        return teks_bersih
    except Exception:
        return ""

# ==========================================
# 3. TAMPILAN ANTARMUKA STREAMLIT
# ==========================================
st.set_page_config(page_title="Asisten Riset Google", page_icon="🔍")

st.title("🔍 Asisten Riset Otomatis")
st.caption("Integrasi Google Custom Search Engine + Ekstraksi Teks Python")

# Mengambil Kunci Rahasia dari Streamlit Secrets
try:
    GOOGLE_API_KEY = st.secrets["GOOGLE_API_KEY"]
    GOOGLE_CX_ID = st.secrets["GOOGLE_CX_ID"]
except KeyError:
    st.error("⚠️ API Key / CX ID belum diatur di Streamlit Secrets!")
    st.info("Masukkan GOOGLE_API_KEY dan GOOGLE_CX_ID pada menu Advanced Settings -> Secrets di Streamlit Cloud.")
    st.stop()

# Form Input
query = st.text_input("Masukkan topik atau pertanyaan pencarian:")

if st.button("Mulai Cari & Ekstrak"):
    if query.strip():
        with st.status("Sedang memproses...", expanded=True) as status:
            st.write("🔍 Menghubungi Google Custom Search Engine...")
            links = cari_di_google(query, GOOGLE_API_KEY, GOOGLE_CX_ID)
            
            if not links:
                status.update(label="Tidak ada hasil ditemukan.", state="error")
                st.stop()
                
            st.write(f"✅ Berhasil menemukan {len(links)} URL artikel.")
            
            hasil_ekstraksi = ""
            for idx, link in enumerate(links, 1):
                st.write(f"📥 Mengambil isi teks dari artikel {idx}: {link}")
                teks = ambil_teks_artikel(link)
                if teks:
                    hasil_ekstraksi += f"=== SUMBER {idx}: {link} ===\n"
                    hasil_ekstraksi += f"{teks[:1200]}...\n\n"
            
            status.update(label="Proses ekstraksi selesai!", state="complete", expanded=False)
            
        if hasil_ekstraksi:
            st.subheader("📑 Hasil Ekstraksi Teks")
            st.text_area("Teks bersih yang siap diringkas:", value=hasil_ekstraksi, height=350)
        else:
            st.warning("Gagal mengambil teks dari artikel yang ditemukan.")
    else:
        st.warning("Ketikkan topik pencarian terlebih dahulu!")
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    try:
        response = requests.get(url, headers=headers, timeout=8)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Buang elemen HTML non-artikel/sampah
        for elemen in soup(['script', 'style', 'header', 'footer', 'nav', 'aside', 'form']):
            elemen.decompose()
            
        # Ambil teks paragraf yang panjangnya lebih dari 30 karakter
        paragraf = [p.get_text() for p in soup.find_all('p') if len(p.get_text().strip()) > 30]
        teks_bersih = " ".join(" ".join(paragraf).split())
        return teks_bersih
    except Exception:
        return ""

# ==========================================
# 3. TAMPILAN ANTARMUKA STREAMLIT
# ==========================================
st.set_page_config(page_title="Asisten Riset Google", page_icon="🔍")

st.title("🔍 Asisten Riset Otomatis")
st.caption("Integrasi Google Custom Search Engine + Ekstraksi Teks Python")

# Mengambil Kunci Rahasia dari Streamlit Secrets
try:
    GOOGLE_API_KEY = st.secrets["GOOGLE_API_KEY"]
    GOOGLE_CX_ID = st.secrets["GOOGLE_CX_ID"]
except KeyError:
    st.error("⚠️ API Key / CX ID belum diatur di Streamlit Secrets!")
    st.info("Masukkan GOOGLE_API_KEY dan GOOGLE_CX_ID pada menu Advanced Settings -> Secrets di Streamlit Cloud.")
    st.stop()

# Form Input
query = st.text_input("Masukkan topik atau pertanyaan pencarian:")

if st.button("Mulai Cari & Ekstrak"):
    if query.strip():
        with st.status("Sedang memproses...", expanded=True) as status:
            st.write("🔍 Menghubungi Google Custom Search Engine...")
            links = cari_di_google(query, GOOGLE_API_KEY, GOOGLE_CX_ID)
            
            if not links:
                status.update(label="Tidak ada hasil ditemukan.", state="error")
                st.stop()
                
            st.write(f"✅ Berhasil menemukan {len(links)} URL artikel.")
            
            hasil_ekstraksi = ""
            for idx, link in enumerate(links, 1):
                st.write(f"📥 Mengambil isi teks dari artikel {idx}: {link}")
                teks = ambil_teks_artikel(link)
                if teks:
                    hasil_ekstraksi += f"=== SUMBER {idx}: {link} ===\n"
                    hasil_ekstraksi += f"{teks[:1200]}...\n\n"
            
            status.update(label="Proses ekstraksi selesai!", state="complete", expanded=False)
            
        if hasil_ekstraksi:
            st.subheader("📑 Hasil Ekstraksi Teks")
            st.text_area("Teks bersih yang siap diringkas:", value=hasil_ekstraksi, height=350)
        else:
            st.warning("Gagal mengambil teks dari artikel yang ditemukan.")
    else:
        st.warning("Ketikkan topik pencarian terlebih dahulu!")
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
