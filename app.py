import streamlit as st
from duckduckgo_search import DDGS
import trafilatura
from deep_translator import GoogleTranslator
from huggingface_hub import InferenceClient

# Konfigurasi Halaman Streamlit
st.set_page_config(
    page_title="AI Web Research Assistant",
    page_icon="🔍",
    layout="wide"
)

# Inisialisasi Model AI (Mistral-7B via Serverless API)
@st.cache_resource
def get_llm_client():
    return InferenceClient("mistralai/Mistral-7B-Instruct-v0.2")

client = get_llm_client()

# --- FUNGSI UTAMA ---
def search_web(query, max_results=3):
    """Mencari URL berita/artikel dari DuckDuckGo"""
    urls = []
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))
            for r in results:
                urls.append({
                    "title": r.get("title", "Artikel Web"),
                    "url": r.get("href", "")
                })
    except Exception as e:
        st.error(f"Gagal mencari di web: {e}")
    return urls

def scrape_content(url):
    """Mengekstrak teks bersih dari web"""
    try:
        downloaded = trafilatura.fetch_url(url)
        if downloaded:
            text = trafilatura.extract(downloaded)
            return text if text else ""
    except Exception:
        pass
    return ""

def translate_to_id(text):
    """Menerjemahkan teks ke Bahasa Indonesia"""
    if not text:
        return ""
    try:
        chunk = text[:2000]
        return GoogleTranslator(source='auto', target='id').translate(chunk)
    except Exception:
        return text[:2000]

# --- TAMPILAN ANTARMUKA (UI) ---
st.title("🔍 AI Web Research Assistant")
st.caption("Cari informasi terbaru di web, baca berbagai sumber, dan dapatkan ringkasannya secara otomatis.")

query = st.text_input(
    "Topik / Pertanyaan Riset:", 
    placeholder="Contoh: Bagaimana perkembangan teknologi AI tahun 2026?"
)

if st.button("🚀 Cari & Ringkas", type="primary"):
    if not query.strip():
        st.warning("Silakan masukkan topik riset terlebih dahulu.")
    else:
        with st.status("🔍 Sedang mencari dan menganalisis artikel...", expanded=True) as status:
            st.write("1️⃣ Mencari sumber informasi di internet...")
            search_results = search_web(query, max_results=3)

            if not search_results:
                status.update(label="❌ Artikel tidak ditemukan.", state="error")
            else:
                scraped_texts = []
                sources_list = []

                st.write("2️⃣ Membaca dan menerjemahkan isi artikel...")
                for idx, item in enumerate(search_results, 1):
                    url = item['url']
                    title = item['title']
                    content = scrape_content(url)
                    
                    if content:
                        translated_text = translate_to_id(content)
                        scraped_texts.append(f"--- Sumber {idx}: {title} ---\n{translated_text}\n")
                        sources_list.append(f"{idx}. [{title}]({url})")

                if not scraped_texts:
                    status.update(label="❌ Gagal mengekstrak isi teks dari web.", state="error")
                else:
                    st.write("3️⃣ Menyusun ringkasan dengan AI...")
                    combined_context = "\n".join(scraped_texts)[:6000]

                    prompt = f"""<s>[INST] Kamu adalah AI Web Research Assistant profesional. 
Berdasarkan teks artikel di bawah ini, buatlah ringkasan terstruktur dalam Bahasa Indonesia.

Format Balasan:
### 📝 Ringkasan Utama
(Paragraf ringkasan yang padat dan informatif)

### 📌 Poin-Poin Penting
- (Poin penting 1)
- (Poin penting 2)
- (Poin penting 3)

Teks Sumber Artikel:
{combined_context} [/INST]"""

                    try:
                        response = client.text_generation(prompt, max_new_tokens=800, temperature=0.3)
                        status.update(label="✅ Riset Selesai!", state="complete", expanded=False)

                        # Menampilkan Hasil
                        col_summary, col_sources = st.columns([2, 1])

                        with col_summary:
                            st.markdown("### 📊 Hasil Ringkasan AI")
                            st.markdown(response.strip())

                        with col_sources:
                            st.markdown("### 🔗 Sumber Artikel")
                            for src in sources_list:
                                st.markdown(src)

                    except Exception as e:
                        status.update(label=f"❌ Error AI: {e}", state="error")
