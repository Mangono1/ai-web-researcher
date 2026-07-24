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
        
        for elemen in soup(['script', 'style', 'header', 'footer', 'nav', 'aside', 'form']):
            elemen.decompose()
            
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
