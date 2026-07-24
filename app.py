import streamlit as st
import requests
from bs4 import BeautifulSoup
from duckduckgo_search import DDGS
from google import genai

# ==========================================
# 1. FUNGSI PENCARIAN DUCKDUCKGO
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
# 2. FUNGSI EKSTRAKSI TEKS WEB
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
# 3. FUNGSI PERANGKUM AI (DENGAN CADANGAN OTOMATIS)
# ==========================================
def rangkum_dengan_ai(teks_kumpul, topik):
    try:
        api_key = st.secrets["GEMINI_API_KEY"]
        client = genai.Client(api_key=api_key)
        
        prompt = f"""
        Kamu adalah asisten riset yang profesional. Berdasarkan teks referensi dari web di bawah ini tentang topik '{topik}', 
        buatkan ringkasan komprehensif, terstruktur, dan mudah dipahami dalam Bahasa Indonesia. 
        Gunakan poin-poin penting agar informatif.

        TEKS REFERENSI:
        {teks_kumpul[:4000]}
        """
        
        # Coba model pertama: gemini-2.5-flash
        try:
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt
            )
            return response.text
        except Exception as e_utama:
            # Jika 2.5 gagal, otomatis pindah ke jalur cadangan: gemini-3.1-flash-lite
            st.warning(f"Model utama (2.5-flash) sedang kendala, beralih ke cadangan (3.1-flash-lite)...")
            response_cadangan = client.models.generate_content(
                model='gemini-3.1-flash-lite',
                contents=prompt
            )
            return response_cadangan.text

    except KeyError:
        return "⚠️ GEMINI_API_KEY belum diatur di Streamlit Secrets."
    except Exception as e:
        return f"Terjadi kesalahan total pada AI: {e}"

# ==========================================
# 4. TAMPILAN ANTARMUKA STREAMLIT
# ==========================================
st.set_page_config(page_title="Asisten Riset AI", page_icon="🤖")

st.title("🤖 Asisten Riset & Perangkum AI")
st.caption("Pencarian Web + Ekstraksi + Sistem Cadangan Pintar Gemini")

query = st.text_input("Masukkan topik atau pertanyaan riset:")

if st.button("Mulai Riset & Rangkum"):
    if query.strip():
        with st.status("Sedang memproses riset...", expanded=True) as status:
            st.write("🔍 Mencari referensi di internet...")
            links = cari_di_web(query)
            
            if not links:
                status.update(label="Tidak ada hasil ditemukan.", state="error")
                st.stop()
                
            st.write(f"✅ Menemukan {len(links)} sumber web.")
            
            hasil_ekstraksi = ""
            for idx, link in enumerate(links, 1):
                st.write(f"📥 Mengekstrak artikel {idx}: {link}")
                teks = ambil_teks_artikel(link)
                if teks:
                    hasil_ekstraksi += f"Sumber: {link}\n{teks}\n\n"
            
            st.write("🧠 Menganalisis dan merangkum dengan Gemini AI...")
            ringkasan_ai = rangkum_dengan_ai(hasil_ekstraksi, query)
            
            status.update(label="Riset selesai!", state="complete", expanded=False)
            
        if hasil_ekstraksi:
            st.subheader("💡 Hasil Ringkasan AI")
            st.markdown(ringkasan_ai)
            
            with st.expander("Lihat Teks Mentah dari Web"):
                st.text_area("Sumber Mentah:", value=hasil_ekstraksi, height=300)
        else:
            st.warning("Gagal mengambil teks dari artikel yang ditemukan.")
    else:
        st.warning("Ketikkan topik pencarian terlebih dahulu!")
