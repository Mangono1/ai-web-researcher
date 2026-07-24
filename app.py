import streamlit as st
import requests
from bs4 import BeautifulSoup
from duckduckgo_search import DDGS

# ==========================================
# 1. FUNGSI PENCARIAN DUCKDUCKGO (TANPA API KEY)
# ==========================================
def cari_di_web(kata_kunci):
    try:
        links = []
        # Menggunakan DuckDuckGo Search secara langsung
        with DDGS() as ddgs:
            results = [r for r in ddgs.text(kata_kunci, region="id-id", max_results=3)]
            for r in results:
                links.append(r['href'])
        return links
    except Exception as e:
        st.error(f"Terjadi kesalahan saat mencari: {e}")
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
st.set_page_config(page_title="Asisten Riset Web", page_icon="🔍")

st.title("🔍 Asisten Riset Otomatis")
st.caption("Pencarian Web Otomatis + Ekstraksi Teks (Tanpa API Key!)")

# Form Input
query = st.text_input("Masukkan topik atau pertanyaan pencarian:")

if st.button("Mulai Cari & Ekstrak"):
    if query.strip():
        with st.status("Sedang memproses...", expanded=True) as status:
            st.write("🔍 Mencari referensi terbaik di internet...")
            links = cari_di_web(query)
            
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
        # Ambil teks paragraf yang panjangnya lebih dari 30 karakter
        paragraf = [p.get_text() for p in soup.find_all('p') if len(p.get_text().strip()) > 30]
        teks_bersih = " ".join(" ".join(paragraf).split())
        return teks_bersih
    except Exception:
        return ""

# ==========================================
# 3. TAMPILAN ANTARMUKA STREAMLIT
# ==========================================
st.set_page_config(page_title="Asisten Riset Web", page_icon="🔍")

st.title("🔍 Asisten Riset Otomatis")
st.caption("Pencarian Web Otomatis + Ekstraksi Teks (Tanpa API Key!)")

# Form Input
query = st.text_input("Masukkan topik atau pertanyaan pencarian:")

if st.button("Mulai Cari & Ekstrak"):
    if query.strip():
        with st.status("Sedang memproses...", expanded=True) as status:
            st.write("🔍 Mencari referensi terbaik di internet...")
            links = cari_di_web(query)
            
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
st.set_page_config(page_title="Asisten Riset Serper AI", page_icon="🔍")

st.title("🔍 Asisten Riset Otomatis")
st.caption("Didukung oleh Serper.dev & Python Web Scraping")

# Mengambil Kunci Rahasia Serper dari Streamlit Secrets
try:
    SERPER_API_KEY = st.secrets["SERPER_API_KEY"]
except KeyError:
    st.error("⚠️ 'SERPER_API_KEY' belum diatur di Streamlit Secrets!")
    st.info("Masukkan SERPER_API_KEY pada menu Advanced Settings -> Secrets di Streamlit Cloud.")
    st.stop()

# Form Input
query = st.text_input("Masukkan topik atau pertanyaan pencarian:")

if st.button("Mulai Cari & Ekstrak"):
    if query.strip():
        with st.status("Sedang memproses...", expanded=True) as status:
            st.write("🔍 Mencari referensi terbaik via Serper.dev...")
            links = cari_di_google(query, SERPER_API_KEY)
            
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
