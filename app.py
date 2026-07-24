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
        hasil_pencarian = wikipedia.search(kata_kunci, results=2)
        if not hasil_pencarian:
            return None, "Topik tidak ditemukan di Wikipedia."
            
        halaman = wikipedia.page(hasil_pencarian[0])
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
# 2. FUNGSI PERANGKUM DENGAN CADANGAN OTOMATIS
# ==========================================
def rangkum_dengan_ai_cadangan(teks_kumpul, judul, topik):
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
        
        # Daftar model prioritas (Model Utama -> Model Cadangan)
        daftar_model = ['gemini-2.5-flash', 'gemini-3.1-flash-lite']
        
        respon_ai = None
        model_digunakan = ""
        
        for nama_model in daftar_model:
            try:
                response = client.models.generate_content(
                    model=nama_model,
                    contents=prompt
                )
                if response and response.text:
                    respon_ai = response.text
                    model_digunakan = nama_model
                    break
            except Exception:
                # Jika model pertama habis kuota / error, lanjut coba model berikutnya
                continue
                
        if respon_ai:
            return respon_ai, model_digunakan
        else:
            return "Semua model AI sedang sibuk atau kuota habis.", None

    except KeyError:
        return "⚠️ GEMINI_API_KEY belum diatur di Streamlit Secrets.", None
    except Exception as e:
        return f"Terjadi kesalahan: {e}", None

# ==========================================
# 3. TAMPILAN ANTARMUKA STREAMLIT
# ==========================================
st.set_page_config(page_title="Wikipedia AI Researcher", page_icon="📚")

st.title("📚 Asisten Riset Wikipedia & AI")
st.caption("Pencarian Ensiklopedia + Multi-Model AI Cadangan Otomatis")

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
            
            st.write("🧠 Menghubungkan ke AI (Mencoba model utama & cadangan)...")
            ringkasan_ai, model_sukses = rangkum_dengan_ai_cadangan(data_wiki['text'], data_wiki['title'], query)
            
            if model_sukses:
                st.write(f"✨ Berhasil merangkum menggunakan model: `{model_sukses}`")
            
            status.update(label="Selesai!", state="complete", expanded=False)
            
        st.subheader(f"💡 Hasil Ringkasan: {data_wiki['title']}")
        st.markdown(ringkasan_ai)
        
        with st.expander("Lihat Teks Asli dari Wikipedia"):
            st.text_area("Teks Mentah Wikipedia:", value=data_wiki['text'], height=300)
    else:
        st.warning("Ketikkan topik pencarian terlebih dahulu!")
