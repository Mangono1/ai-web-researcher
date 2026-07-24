import streamlit as st
from google import genai

# Daftar model Gemini dengan mekanisme Fallback Otomatis
DAFTAR_MODEL_GEMINI = [
    'gemini-2.5-flash',
    'gemini-2.0-flash',
    'gemini-1.5-flash',
    'gemini-3.1-flash-lite'
]

def panggil_gemini(prompt_teks):
    """Fungsi pusat pemanggilan Gemini AI dengan sistem fallback otomatis."""
    try:
        api_key = st.secrets["GEMINI_API_KEY"]
        client = genai.Client(api_key=api_key)
        
        for nama_model in DAFTAR_MODEL_GEMINI:
            try:
                response = client.models.generate_content(
                    model=nama_model,
                    contents=prompt_teks
                )
                if response and response.text:
                    return response.text, nama_model
            except Exception:
                continue
                
        return "⚠️ Semua model Gemini sedang tidak tersedia atau kuota habis.", None
    except KeyError:
        return "⚠️ GEMINI_API_KEY belum diatur di Streamlit Secrets.", None
    except Exception as e:
        return f"Terjadi kesalahan koneksi AI: {e}", None

def dapatkan_sinonim_ai(kata_kunci):
    """
    Dynamic AI Semantic Expander:
    Meminta Gemini memberikan sinonim atau kepanjangan dari kata kunci secara otomatis.
    """
    prompt = f"Berikan maksimal 5 sinonim, kepanjangan, atau istilah yang sangat erat kaitannya dengan '{kata_kunci}'. Pisahkan dengan koma. Hanya berikan kata-katanya saja tanpa penjelasan apapun."
    teks, _ = panggil_gemini(prompt)
    if teks and not "⚠️" in teks:
        # Bersihkan hasil dan masukkan ke dalam list
        return [s.strip().lower() for s in teks.split(',')]
    return []

def penulis_profesional_ai(planner_blueprint, causal_chains, timeline_global, global_entities, global_triples, topik, confidence):
    prompt = f"""
    Kamu adalah Penulis Profesional. Python telah menjalankan Question Planner Engine (Agen Perencanaan Berpikir) yang memecah topik '{topik}' ke dalam sub-pertanyaan multidimensi beserta klaim terarahnya.
    Berdasarkan cetak biru perencanaan Python (Confidence Score: {confidence}%), susun laporan riset yang sangat mendalam, terstruktur, dan tuntas dalam Bahasa Indonesia dengan format:

    1. **CETAK BIRU PERENCANAAN PIKIRAN (QUESTION PLANNER BLUEPRINT)**: Sajikan analisis sub-dimensi yang telah disiapkan Python.

    2. **POHON SEBAB-AKIBAT (CAUSAL CHAINS)**: Rantai kausal terverifikasi.

    3. **KNOWLEDGE GRAPH & ENTITAS UTAMA**: 
       - Tokoh: {', '.join(global_entities.get('Tokoh', []))}
       - Lokasi: {', '.join(global_entities.get('Lokasi', []))}
       - Organisasi: {', '.join(global_entities.get('Organisasi', []))}
       - Tanggal / Tahun: {', '.join(global_entities.get('Tanggal', []))}

    4. **KRONOLOGI WAKTU**: Rangkaian waktu peristiwa.

    5. **RINGKASAN EKSEKUTIF & JAWABAN ANALITIS UTAMA**: Rangkai seluruh sub-pertanyaan dan bukti di atas menjadi laporan profesional yang menjawab tuntas inti pertanyaan pengguna.
    """
    return panggil_gemini(prompt)

def jawab_pertanyaan_chat(user_prompt, planner_blueprint, causal_chains, timeline_global, laporan_utama):
    bp_p = ""
    for bp in planner_blueprint:
        bp_p += f"[{bp['domain']}]: " + "; ".join([c[1] for c in bp['matched_claims']]) + "\n"
        
    prompt = f"""
    Kamu adalah asisten riset cerdas berbekal Question Planner Engine. Jawab pertanyaan pengguna secara analitis berdasarkan cetak biru sub-pertanyaan Python:
    
    CETAK BIRU PERENCANAAN:
    {bp_p}
    
    LAPORAN UTAMA:
    {laporan_utama}
    
    PERTANYAAN:
    {user_prompt}
    """
    teks_jawaban, _ = panggil_gemini(prompt)
    return teks_jawaban
