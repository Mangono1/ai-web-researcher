import streamlit as st
import requests
from bs4 import BeautifulSoup
from duckduckgo_search import DDGS
from google import genai

# ==========================================
# 1. FUNGSI PENCARIAN MULTI-SUMBER (WEB)
# ==========================================
def cari_dari_berbagai_sumber(kata_kunci):
    try:
        links = []
        # Mencari tautan dari internet menggunakan DuckDuckGo
        with DDGS() as ddgs:
            results = [r for r in ddgs.text(kata_kunci, region="id-id", max_results=4)]
            for r in results:
                links.append({'url': r['href'], 'title': r.get('title', 'Sumber Web')})
        return links
    except Exception as e:
        st.error(f"Terjadi kesalahan saat mencari: {e}")
        return []

# ==========================================
# 2. FUNGSI EKSTRAKSI TEKS BERSIH
# ==========================================
def ambil_teks_dari_url(url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    try:
        response = requests.get(url, headers=headers, timeout=7)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Buang elemen sampah seperti iklan, navigasi, dan footer
        for elemen in soup(['script', 'style', 'header', 'footer', 'nav', 'aside', 'form']):
            elemen.decompose()
            
        paragraf = [p.get_text() for p in soup.find_all('p') if len(p.get_text().strip()) > 30]
        teks_bersih = " ".join(" ".join(paragraf).split())
        return teks_bersih[:1200] # Batasi panjang teks per artikel agar optimal
    except Exception:
        return ""

# ==========================================
# 3. FUNGSI AI DENGAN MULTI-MODEL CADANGAN
# ==========================================
def analisis_multi_sumber_ai(gabungan_teks, topik):
    try:
        api_key = st.secrets["GEMINI_API_KEY"]
        client = genai.Client(api_key=api_key)
        
        prompt = f"""
        Kamu adalah asisten riset profesional. Berdasarkan beberapa sumber referensi web di bawah ini mengenai topik '{topik}', 
        buatkan laporan riset komprehensif dalam Bahasa Indonesia yang mencakup:
        1. Ringkasan Utama dari berbagai sumber.
        2. Persamaan pandangan antar sumber.
        3. Perbedaan atau sudut pandang unik yang ditemukan.
        Gunakan format poin-poin yang terstruktur rapi.

        SUMBER REFERENSI:
        {gabungan_teks}
        """
        
        # Daftar model prioritas (Model Utama -> Model Cadangan)
        daftar_model = ['gemini-2.5-flash', 'gemini-3.1-flash-lite']
        
        for nama_model in daftar_model:
            try:
                response = client.models.generate_content(
                    model=nama_model,
                    contents=prompt
                )
                if response and response.text:
                    return response.text, nama_model
            except Exception:
                continue
                
        return "Semua model AI sedang sibuk atau kuota habis.", None
    except KeyError:
        return "⚠️ GEMINI_API_KEY belum diatur di Streamlit Secrets.", None
    except Exception as e:
        return f"Terjadi kesalahan: {e}", None

# ==========================================
# 4. TAMPILAN ANTARMUKA STREAMLIT (TAHAP 2)
# ==========================================
st.set_page_config(page_title="Multi-Source AI Researcher", page_icon="🌐")

st.title("🌐 Mesin Riset Multi-Sumber (Tahap 2)")
st.caption("Pencarian Berbagai Situs Web + Analisis Perbandingan AI")

query = st.text_input("Masukkan topik riset (contoh: AI Indonesia, Perkembangan BUMDes, dll):")

if st.button("Mulai Riset Multi-Sumber"):
    if query.strip():
        with st.status("Sedang mengumpulkan data dari internet...", expanded=True) as status:
            st.write("🔍 Mencari referensi dari berbagai situs web...")
            sumber_list = cari_dari_berbagai_sumber(query)
            
            if not sumber_list:
                status.update(label="Tidak ada sumber ditemukan.", state="error")
                st.stop()
                
            st.write(f"✅ Menemukan {len(sumber_list)} sumber web relevan.")
            
            gabungan_teks_total = ""
            sumber_berhasil = []
            
            for idx, item in enumerate(sumber_list, 1):
                st.write(f"📥 Mengekstrak: {item['title']} ({item['url']})")
                teks = ambil_teks_dari_url(item['url'])
                if teks:
                    gabungan_teks_total += f"--- SUMBER {idx}: {item['title']} ({item['url']}) ---\n{teks}\n\n"
                    sumber_berhasil.append(item['url'])
            
            st.write("🧠 Menganalisis persamaan & perbedaan dengan Gemini AI...")
            hasil_analisis, model_pakai = analisis_multi_sumber_ai(gabungan_teks_total, query)
            
            if model_pakai:
                st.write(f"✨ Diproses menggunakan model: `{model_pakai}`")
                
            status.update(label="Riset multi-sumber selesai!", state="complete", expanded=False)
            
        if gabungan_teks_total:
            st.subheader(f"📊 Laporan Riset & Perbandingan: {query}")
            st.markdown(hasil_analisis)
            
            st.markdown("### 🔗 Daftar Referensi Sumber:")
            for url in sumber_berhasil:
                st.markdown(f"- {url}")
                
            with st.expander("Lihat Teks Mentah Gabungan"):
                st.text_area("Teks Sumber:", value=gabungan_teks_total, height=300)
        else:
            st.warning("Gagal mengekstrak isi teks dari situs web yang ditemukan.")
    else:
        st.warning("Ketikkan topik pencarian terlebih dahulu!")
