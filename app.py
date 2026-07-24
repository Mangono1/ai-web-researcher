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
        
        for elemen in soup(['script', 'style', 'header', 'footer', 'nav', 'aside', 'form']):
            elemen.decompose()
            
        paragraf = [p.get_text() for p in soup.find_all('p') if len(p.get_text().strip()) > 30]
        teks_bersih = " ".join(" ".join(paragraf).split())
        return teks_bersih[:1200]
    except Exception:
        return ""

# ==========================================
# 3. FUNGSI AI DENGAN FITUR LAPORAN & TIMELINE
# ==========================================
def analisis_dengan_timeline_ai(sumber_data, topik):
    try:
        api_key = st.secrets["GEMINI_API_KEY"]
        client = genai.Client(api_key=api_key)
        
        teks_terstruktur = ""
        for idx, item in enumerate(sumber_data, 1):
            teks_terstruktur += f"[{idx}] Judul: {item['title']} | URL: {item['url']}\nIsi:\n{item['teks']}\n\n"
        
        prompt = f"""
        Kamu adalah asisten riset profesional. Berdasarkan sumber-sumber di bawah ini mengenai topik '{topik}', 
        buatkan dua hal dalam Bahasa Indonesia:
        
        1. **LAPORAN UTAMA DENGAN SITASI**: Rangkuman komprehensif berformat poin-poin dengan menyertakan nomor referensi sumber seperti [1], [2] pada klaim penting.
        2. **KRONOLOGI WAKTU (TIMELINE)**: Ekstrak tahun-tahun penting beserta peristiwa kuncinya dari teks sumber, lalu susun secara berurutan dari masa lampau ke masa kini dengan format visual sederhana (Contoh: **Tahun** — Peristiwa). Jika topik tidak memiliki unsur waktu/sejarah yang jelas, buat ringkasan tonggak pencapaian utamanya.

        SUMBER REFERENSI:
        {teks_terstruktur}
        """
        
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
# 4. TAMPILAN ANTARMUKA STREAMLIT (TAHAP 4)
# ==========================================
st.set_page_config(page_title="AI Research Assistant - Timeline", page_icon="⏳")

st.title("⏳ Mesin Riset + Lini Masa Otomatis (Tahap 4)")
st.caption("Analisis Multi-Sumber, Sitasi Otomatis, dan Kronologi Peristiwa")

query = st.text_input("Masukkan topik riset (contoh: Sejarah Kerajaan Majapahit, Sejarah Internet Indonesia, dll):")

if st.button("Mulai Riset & Buat Timeline"):
    if query.strip():
        with st.status("Sedang mengumpulkan & menganalisis data...", expanded=True) as status:
            st.write("🔍 Mencari sumber terpercaya di internet...")
            sumber_list = cari_dari_berbagai_sumber(query)
            
            if not sumber_list:
                status.update(label="Tidak ada sumber ditemukan.", state="error")
                st.stop()
                
            st.write(f"✅ Menemukan {len(sumber_list)} sumber web.")
            
            sumber_data_lengkap = []
            for idx, item in enumerate(sumber_list, 1):
                st.write(f"📥 Mengekstrak sumber [{idx}]: {item['title']}")
                teks = ambil_teks_dari_url(item['url'])
                if teks:
                    sumber_data_lengkap.append({
                        'id': idx,
                        'title': item['title'],
                        'url': item['url'],
                        'teks': teks
                    })
            
            if not sumber_data_lengkap:
                status.update(label="Gagal mengambil isi teks artikel.", state="error")
                st.stop()
                
            st.write("🧠 Menganalisis laporan dan menyusun linimasa kronologis dengan Gemini AI...")
            hasil_analisis, model_pakai = analisis_dengan_timeline_ai(sumber_data_lengkap, query)
            
            if model_pakai:
                st.write(f"✨ Diproses menggunakan model: `{model_pakai}`")
                
            status.update(label="Riset selesai!", state="complete", expanded=False)
            
        st.subheader(f"📊 Hasil Analisis & Timeline: {query}")
        st.markdown(hasil_analisis)
        
        st.markdown("---")
        st.subheader("📚 Daftar Pustaka / Referensi")
        for item in sumber_data_lengkap:
            st.markdown(f"**[{item['id']}]** [{item['title']}]({item['url']})")
            
        with st.expander("Lihat Data Mentah Sumber"):
            for item in sumber_data_lengkap:
                st.write(f"**Sumber [{item['id']}]**: {item['url']}")
                st.text_area(f"Teks {item['id']}", value=item['teks'], height=150, key=f"raw_{item['id']}")
    else:
        st.warning("Ketikkan topik pencarian terlebih dahulu!")
