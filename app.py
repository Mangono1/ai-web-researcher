import streamlit as st
import wikipedia
from google import genai

# Atur bahasa Wikipedia ke Bahasa Indonesia
wikipedia.set_lang("id")

# ==========================================
# 1. FUNGSI PENCARIAN WIKIPEDIA
# ==========================================
def cari_di_wikipedia(kata_kunci):
    try:
        # Cari halaman berdasarkan kata kunci (ambil 2 teratas)
        hasil_pencarian = wikipedia.search(kata_kunci, results=2)
        
        if not hasil_pencarian:
            return None, "Topik tidak ditemukan di Wikipedia."
            
        # Ambil halaman pertama yang paling relevan
        halaman = wikipedia.page(hasil_pencarian[0])
        
        # Ambil isi teks artikelnya (ambil maksimal 4000 karakter agar pas untuk AI)
        teks_artikel = halaman.content[:4000]
        url_artikel = halaman.url
        
        return {
            "title": halaman.title,
            "url": url_artikel,
            "text": teks_artikel
        }, None
    except wikipedia.exceptions.DisambiguationError as e:
        return None, f"Kata kunci terlalu luas. Pilihan lain: {e.options[:5]}"
    except Exception as e:
        return None, f"Terjadi kesalahan: {e}"

# ==========================================
# 2. FUNGSI PERANGKUM AI (GEMINI)
# ==========================================
def rangkum_dengan_ai(teks_kumpul, judul, topik):
    try:
        api_key = st.secrets["GEMINI_API_KEY"]
        client = genai.Client(api_key=api_key)
        
        prompt = f"""
        Kamu adalah asisten riset. Berdasarkan artikel ensiklopedia Wikipedia berjudul '{judul}' mengenai '{topik}', 
        buatkan ringkasan yang mendalam, terstruktur dengan baik, dan mudah dipahami dalam Bahasa Indonesia 
        menggunakan poin-poin yang rapi.

        ISI WIKIPEDIA:
        {teks_kumpul}
        """
        
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt
        )
        return response.text
    except KeyError:
        return "⚠️ GEMINI_API_KEY belum diatur di Streamlit Secrets."
    except Exception as e:
        return f"Terjadi kesalahan saat memanggil AI: {e}"

# ==========================================
# 3. TAMPILAN ANTARMUKA STREAMLIT
# ==========================================
st.set_page_config(page_title="Wikipedia AI Researcher", page_icon="📚")

st.title("📚 Asisten Riset Wikipedia & AI")
st.caption("Pencarian Ensiklopedia Bersih + Ringkasan Pintar Gemini")

query = st.text_input("Masukkan topik yang ingin dicari (contoh: Sejarah Majapahit, BUMDes, dll):")

if st.button("Cari & Rangkum dari Wikipedia"):
    if query.strip():
        with st.status("Sedang memproses...", expanded=True) as status:
            st.write("🔍 Mencari artikel di Wikipedia...")
            data_wiki, error = cari_di_wikipedia(query)
            
            if error:
                status.update(label="Gagal menemukan data.", state="error")
                st.error(error)
                st.stop()
                
            st.write(f"✅ Menemukan artikel: **{data_wiki['title']}**")
            st.link_button("🔗 Buka Sumber Asli di Wikipedia", data_wiki['url'])
            
            st.write("🧠 Merangkum isi ensiklopedia dengan Gemini AI...")
            ringkasan_ai = rangkum_dengan_ai(data_wiki['text'], data_wiki['title'], query)
            
            status.update(label="Selesai!", state="complete", expanded=False)
            
        st.subheader(f"💡 Hasil Ringkasan: {data_wiki['title']}")
        st.markdown(ringkasan_ai)
        
        with st.expander("Lihat Teks Asli dari Wikipedia"):
            st.text_area("Teks Mentah Wikipedia:", value=data_wiki['text'], height=300)
    else:
        st.warning("Ketikkan topik pencarian terlebih dahulu!")
