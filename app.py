import streamlit as st
import requests
from bs4 import BeautifulSoup
from duckduckgo_search import DDGS
from urllib.parse import urlparse
from difflib import SequenceMatcher
import io
import re
from collections import defaultdict

# Impor modul AI yang sudah dipisahkan
from gemini import penulis_profesional_ai, jawab_pertanyaan_chat

from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from docx import Document

# ==========================================
# 1. SEMANTIC RETRIEVAL & SOURCE INTELLIGENCE
# ==========================================
def expand_semantic_keywords(kata_kunci):
    kunci_lower = kata_kunci.lower()
    expanded_set = set([kunci_lower])
    semantic_synonyms = {
        "mobil listrik": ["electric vehicle", "ev", "battery electric vehicle", "bev", "kendaraan listrik"],
        "electric vehicle": ["mobil listrik", "ev", "kendaraan listrik"],
        "pppk": ["pegawai pemerintah dengan perjanjian kerja", "asn", "pegawai honorer", "aparatur sipil negara"],
        "pppk paruh waktu": ["pegawai pemerintah dengan perjanjian kerja", "paruh waktu", "paruh-waktu", "asn paruh waktu"],
        "kesehatan": ["health", "medis", "medical", "klinis", "clinical"],
        "pendidikan": ["education", "sekolah", "school", "kurikulum", "learning"],
        "ekonomi": ["economy", "financial", "keuangan", "bisnis", "market", "pasar"],
        "energi terbarukan": ["renewable energy", "green energy", "clean energy", "energi hijau"],
        "sejarah": ["history", "historis", "kronologi", "asal-usul", "era", "dynasty"],
        "runtuh": ["keruntuhan", "kejatuhan", "collapse", "destroy", "bubar", "akhir"]
    }
    for key, synonyms in semantic_synonyms.items():
        if key in kunci_lower:
            for syn in synonyms:
                expanded_set.add(syn)
    for word in kunci_lower.split():
        if len(word) > 2:
            expanded_set.add(word)
    return list(expanded_set)

def hitung_source_intelligence_score(url, soup_obj, teks_artikel):
    parsed_url = urlparse(url)
    domain = parsed_url.netloc.lower()
    skor_dasar = 50
    if parsed_url.scheme == "https":
        skor_dasar += 10
    if ".go.id" in domain:
        skor_dasar += 25
    elif ".ac.id" in domain or ".edu" in domain:
        skor_dasar += 23
    elif "wikipedia.org" in domain:
        skor_dasar += 20
    elif any(d in domain for d in ["kompas.com", "detik.com", "tempo.co", "antaranews.com", "liputan6.com", "cnnindonesia.com", "katadata.co.id", "bbc.com", "reuters.com"]):
        skor_dasar += 20
    elif any(d in domain for d in ["medium.com", "kompasiana.com", "blogspot.com", "wordpress.com"]):
        skor_dasar -= 15
    else:
        skor_dasar += 10
        
    if len(teks_artikel) > 1000:
        skor_dasar += 10
    elif len(teks_artikel) > 500:
        skor_dasar += 5
    else:
        skor_dasar -= 5
        
    trust_score = max(10, min(skor_dasar, 99))
    if trust_score >= 85:
        label_kualitas = f"🟢 Sangat Kredibel (Trust Score: {trust_score})"
    elif trust_score >= 70:
        label_kualitas = f"🔵 Kredibel & Terverifikasi (Trust Score: {trust_score})"
    elif trust_score >= 50:
        label_kualitas = f"🟡 Cukup / Standar (Trust Score: {trust_score})"
    else:
        label_kualitas = f"🔴 Rendah / Blog (Trust Score: {trust_score})"
    return trust_score, label_kualitas

def cari_sumber_mentah(kata_kunci):
    try:
        links = []
        with DDGS() as ddgs:
            results = [r for r in ddgs.text(kata_kunci, region="id-id", max_results=10)]
            for r in results:
                links.append({'url': r['href'], 'title': r.get('title', 'Sumber Web'), 'snippet': r.get('body', '')})
        return links
    except Exception as e:
        st.error(f"Terjadi kesalahan saat mencari: {e}")
        return []

def hitung_kemiripan(teks1, teks2):
    return SequenceMatcher(None, teks1.lower(), teks2.lower()).ratio()

def filter_relevansi_dan_duplikat(sumber_mentah, kata_kunci):
    expanded_keywords = expand_semantic_keywords(kata_kunci)
    sumber_terfilter = []
    for item in sumber_mentah:
        teks_gabungan = (item['title'] + " " + item['snippet']).lower()
        if not expanded_keywords or any(k in teks_gabungan for k in expanded_keywords):
            if not any(hitung_kemiripan(item['title'], unik['title']) >= 0.6 for unik in sumber_terfilter):
                sumber_terfilter.append(item)
    return sumber_terfilter[:5]

# ==========================================
# 2. PYTHON RESEARCH ENGINES (ROBUST & SAFE)
# ==========================================
def pecah_menjadi_atomic_claims(kalimat):
    titik_pecah = re.split(r',|\bsetelah\b|\bsebelum\b|\bdimana\b|\bketika\b|\bserta\b|\bdan juga\b', kalimat)
    atomic_list = []
    for bagian in titik_pecah:
        bersih = bagian.strip(" .")
        if len(bersih) > 12:
            atomic_list.append(bersih[0].upper() + bersih[1:])
    return atomic_list if atomic_list else [kalimat.strip(".")]

def parsing_causal_relations(kalimat):
    causal_chains = []
    kalimat_lower = kalimat.lower()
    for marker in ["menyebabkan", "mengakibatkan", "berdampak pada", "karena", "akibat", "memicu", "berkontribusi pada"]:
        if marker in kalimat_lower:
            parts = kalimat_lower.split(marker)
            if len(parts) == 2:
                sebab, akibat = parts[0].strip(" ,.").title(), parts[1].strip(" ,.").title()
                if 3 < len(sebab) < 45 and 3 < len(akibat) < 45:
                    causal_chains.append((sebab, marker, akibat))
    return causal_chains

def parsing_temporal_lanjutan(kalimat):
    events = []
    kalimat_lower = kalimat.lower()
    for y in re.findall(r'\b(1[0-9]{3}|20[0-9]{2})\b', kalimat):
        events.append((int(y), f"Tahun {y}: {kalimat.strip()}"))
    for a in re.findall(r'abad\s*(?:ke-)?([0-9ivxlc]+)', kalimat_lower):
        num_val = int(a) if a.isdigit() else {'iv': 4, 'v': 5, 'vi': 6, 'vii': 7, 'viii': 8, 'ix': 9, 'x': 10, 'xi': 11, 'xii': 12, 'xiii': 13, 'xiv': 14, 'xv': 15, 'xvi': 16, 'xvii': 17, 'xviii': 18, 'xix': 19, 'xx': 20}.get(a, 5)
        events.append(((num_val - 1) * 100, f"Abad ke-{num_val}: {kalimat.strip()}"))
    return events

def ekstrak_knowledge_graph_python(teks_full):
    triples = []
    for kal in [k.strip() for k in teks_full.split('.') if len(k.strip()) > 20]:
        kal_lower = kal.lower()
        for verb in ["memimpin", "didirikan oleh", "dibangun oleh", "terletak di", "berpusat di", "dipimpin oleh", "mencapai", "menaklukkan", "berdiri pada", "merupakan", "adalah"]:
            if verb in kal_lower:
                parts = kal_lower.split(verb)
                if len(parts) == 2:
                    subjek, objek = parts[0].strip().title(), parts[1].strip(". ").title()
                    if 2 < len(subjek) < 30 and 2 < len(objek) < 30:
                        triples.append((subjek, verb, objek))
                        break
    return list(set(triples))[:10]

def ekstrak_entitas_python(teks_full):
    tokoh, lokasi, organisasi, tanggal = set(), set(), set(), set()
    for y in re.findall(r'\b(1[0-9]{3}|20[0-9]{2})\b', teks_full):
        tanggal.add(str(y))
    for w in re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', teks_full):
        if w not in {"Dan", "Yang", "Dari", "Dalam", "Pada", "Dengan", "Untuk", "Sebagai", "Oleh", "Adalah", "Namun", "Selain", "Ketika", "Setelah", "Sebelum", "Karena", "Sehingga"} and len(w) > 3:
            w_lower = w.lower()
            if any(org in w_lower for org in ["kerajaan", "republik", "pt", "cv", "universitas", "badan"]):
                organisasi.add(w)
            elif any(loc in w_lower for loc in ["kota", "kabupaten", "provinsi", "pulau", "candi", "majapahit", "borobudur", "indonesia"]):
                lokasi.add(w)
            else:
                tokoh.add(w)
    return {"Tokoh": list(tokoh)[:6], "Lokasi": list(lokasi)[:6], "Organisasi": list(organisasi)[:6], "Tanggal": sorted(list(tanggal))}

def proses_peneliti_python(url, kata_kunci, source_id):
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        response = requests.get(url, headers=headers, timeout=7)
        soup = BeautifulSoup(response.text, 'html.parser')
        for elemen in soup(['script', 'style', 'header', 'footer', 'nav', 'aside', 'form']):
            elemen.decompose()
            
        paragraf = [p.get_text().strip() for p in soup.find_all('p') if len(p.get_text().strip()) > 30]
        
        # PERBAIKAN UTAMA BUG 3: Selama teks berhasil diambil, proses dan selamatkan semuanya!
        if not paragraf:
            return "", [], [], {}, [], [], 50, "Cukup"
            
        teks_full = " ".join(paragraf)
        trust_score, label = hitung_source_intelligence_score(url, soup, teks_full)
        entities = ekstrak_entitas_python(teks_full)
        triples = ekstrak_knowledge_graph_python(teks_full)
        
        expanded_kw = expand_semantic_keywords(kata_kunci)
        claims, events, causal_list = [], [], []
        
        for p in paragraf:
            for kal in [k.strip() for k in p.split('.') if len(k.strip()) > 20]:
                kal_lower = kal.lower()
                ada_keyword = any(kw in kal_lower for kw in expanded_kw)
                ada_angka = bool(re.search(r'\b(1[0-9]{3}|20[0-9]{2})\b', kal))
                
                if ada_keyword or ada_angka:
                    for ac in pecah_menjadi_atomic_claims(kal):
                        if ac not in claims:
                            claims.append(ac)
                            
                events.extend(parsing_temporal_lanjutan(kal))
                causal_list.extend(parsing_causal_relations(kal))
                
        # Safe fallback: Jika claims kosong, ambil langsung paragraf awal sebagai klaim aman
        if not claims and paragraf:
            for p in paragraf[:5]:
                for ac in pecah_menjadi_atomic_claims(p):
                    if ac not in claims:
                        claims.append(ac)
                        
        return ". ".join(claims[:12]) + ".", claims[:12], sorted(list(set(events)), key=lambda x: x[0]), entities, triples, list(set(causal_list)), trust_score, label
    except Exception:
        return "", [], [], {}, [], [], 50, "Cukup"

def build_question_planner_blueprint(query, sumber_data_lengkap):
    sub_questions = [
        {"domain": "Kebijakan & Regulasi", "keyword": ["regulasi", "kebijakan", "aturan", "pemerintah", "keputusan", "pppk", "pegawai"]},
        {"domain": "Status & Gaji", "keyword": ["status", "gaji", "pendapatan", "honor", "formasi", "pengangkatan"]},
        {"domain": "Ketentuan Waktu & Teknis", "keyword": ["waktu", "jam", "kerja", "paruh", "ketentuan", "teknis"]},
        {"domain": "Dampak & Formasi", "keyword": ["dampak", "formasi", "kebutuhan", "seleksi", "pelamar"]}
    ]
    blueprint = []
    for sq in sub_questions:
        matched_claims = []
        for item in sumber_data_lengkap:
            for claim in item['claims']:
                if any(kw in claim.lower() for kw in sq['keyword']):
                    matched_claims.append((item['id'], claim))
        blueprint.append({'domain': sq['domain'], 'matched_claims': matched_claims[:3]})
    return blueprint

def hitung_statistik_riset(sumber_data):
    if not sumber_data:
        return 0, 0, 0, 0
    rata_trust = sum(i['trust_score'] for i in sumber_data) / len(sumber_data)
    confidence = int(round((rata_trust * 0.4) + (min(len(sumber_data) / 5.0, 1.0) * 30) + 30))
    consensus = int(round(min(rata_trust * 0.98, 98)))
    return confidence, rata_trust, len(sumber_data), consensus

# ==========================================
# 4. EKSPOR DOKUMEN & UI STREAMLIT
# ==========================================
def generate_pdf(topik, skor, consensus, rata_skor, total_sumber, hasil_analisis, sumber_list):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    story = [Paragraph(f"LAPORAN RISET: {topik.upper()}", ParagraphStyle('T', fontSize=16, textColor=colors.HexColor("#1E3A8A"))), Spacer(1, 10)]
    for para in hasil_analisis.split("\n"):
        if para.strip():
            story.append(Paragraph(para, ParagraphStyle('N', fontSize=10, leading=14)))
    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()

def generate_docx(topik, skor, consensus, rata_skor, total_sumber, hasil_analisis, sumber_list):
    doc = Document()
    doc.add_heading(f"Laporan Riset: {topik}", level=1)
    doc.add_paragraph(hasil_analisis)
    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer.getvalue()

st.set_page_config(page_title="AI Researcher - Robust Architecture", page_icon="🛡️")
st.title("🛡️ Mesin Riset Tangguh + Question Planner Engine")
st.caption("Python Menjamin Tidak Ada Sumber yang Terbuang Berdasarkan Keberhasilan Akses Artikel (teks_full)")

query = st.text_input("Masukkan topik riset (contoh: PPPK paruh waktu, Sejarah Majapahit, dll):")

if st.button("Jalankan Riset Tangguh"):
    if query.strip():
        with st.status("Menjalankan Peneliti Python & Gemini AI...", expanded=True) as status:
            st.write("🔍 Mencari sumber relevan...")
            sumber_mentah = cari_sumber_mentah(query)
            if not sumber_mentah:
                status.update(label="Tidak ada sumber ditemukan.", state="error")
                st.stop()
                
            st.write("🧹 Menyaring duplikat & relevansi...")
            sumber_list = filter_relevansi_dan_duplikat(sumber_mentah, query)
            if not sumber_list:
                status.update(label="Tidak ada sumber yang cukup relevan.", state="error")
                st.stop()
                
            sumber_data_lengkap = []
            timeline_global = []
            causal_chains_global = []
            global_entities = {"Tokoh": [], "Lokasi": [], "Organisasi": [], "Tanggal": []}
            global_triples = []
            
            for idx, item in enumerate(sumber_list, 1):
                res = proses_peneliti_python(item['url'], query, idx)
                
                # PERBAIKAN UTAMA BUG 3: Cukup periksa apakah teks artikel berhasil diunduh (res[0] tidak kosong atau ada klaim/entitas)
                if res[0] or res[1] or res[3]:
                    sumber_data_lengkap.append({
                        'id': idx, 'title': item['title'], 'url': item['url'],
                        'trust_score': res[6], 'kualitas': res[7], 'claims': res[1] if res[1] else [item['snippet']]
                    })
                    timeline_global.extend(res[2])
                    global_triples.extend(res[4])
                    causal_chains_global.extend(res[5])
                    for k in global_entities:
                        global_entities[k].extend(res[3].get(k, []))
            
            # Pengaman absolut: Jika karena alasan ekstrem sumber_data_lengkap masih kosong, gunakan snippet mentah
            if not sumber_data_lengkap and sumber_list:
                for idx, item in enumerate(sumber_list, 1):
                    sumber_data_lengkap.append({
                        'id': idx, 'title': item['title'], 'url': item['url'],
                        'trust_score': 60, 'kualitas': "🟡 Standar", 'claims': [item['snippet']]
                    })
            
            for k in global_entities:
                global_entities[k] = sorted(list(set(global_entities[k])))[:8]
            global_triples = list(set(global_triples))
            causal_chains_global = list(set(causal_chains_global))
            
            st.write("🧭 Menyusun Question Planner Blueprint...")
            planner_blueprint = build_question_planner_blueprint(query, sumber_data_lengkap)
            timeline_global = sorted(list(set(timeline_global)), key=lambda x: x[0])
            
            score_akhir, rata_skor_trust, total_sumber, consensus_score = hitung_statistik_riset(sumber_data_lengkap)
            
            st.write("✍️ Memanggil modul gemini.py untuk menyusun laporan...")
            hasil_analisis, model_pakai = penulis_profesional_ai(
                planner_blueprint, causal_chains_global, timeline_global, global_entities, global_triples, query, score_akhir
            )
            
            if model_pakai:
                st.write(f"✨ Berhasil menggunakan model: `{model_pakai}`")
            
            status.update(label="Riset Selesai!", state="complete", expanded=False)
            
        st.session_state['hasil_analisis'] = hasil_analisis
        st.session_state['sumber_data_lengkap'] = sumber_data_lengkap
        st.session_state['planner_blueprint'] = planner_blueprint
        st.session_state['causal_chains_global'] = causal_chains_global
        st.session_state['global_entities'] = global_entities
        st.session_state['timeline_global'] = timeline_global
        st.session_state['global_triples'] = global_triples
        st.session_state['score_akhir'] = score_akhir
        st.session_state['rata_skor_trust'] = rata_skor_trust
        st.session_state['total_sumber'] = total_sumber
        st.session_state['consensus_score'] = consensus_score
        st.session_state['query'] = query
        st.session_state['messages'] = [{"role": "assistant", "content": f"Laporan untuk **{query}** berhasil disusun."}]

if 'hasil_analisis' in st.session_state:
    st.markdown("---")
    st.subheader("📈 Dashboard Statistik & Kesehatan Riset")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Sumber Unik", st.session_state['total_sumber'])
    with col2:
        st.metric("Avg Trust Score", f"{st.session_state['rata_skor_trust']:.1f}/100")
    with col3:
        st.metric("Konsensus", f"{st.session_state['consensus_score']}%")
    with col4:
        st.metric("Confidence", f"{st.session_state['score_akhir']}%")
    st.progress(st.session_state['score_akhir'] / 100.0)

    st.markdown("---")
    st.subheader("📥 Unduh Laporan")
    col_pdf, col_docx = st.columns(2)
    pdf_bytes = generate_pdf(st.session_state['query'], st.session_state['score_akhir'], st.session_state['consensus_score'], st.session_state['rata_skor_trust'], st.session_state['total_sumber'], st.session_state['hasil_analisis'], st.session_state['sumber_data_lengkap'])
    docx_bytes = generate_docx(st.session_state['query'], st.session_state['score_akhir'], st.session_state['consensus_score'], st.session_state['rata_skor_trust'], st.session_state['total_sumber'], st.session_state['hasil_analisis'], st.session_state['sumber_data_lengkap'])
    
    with col_pdf:
        st.download_button("📄 Unduh PDF", data=pdf_bytes, file_name=f"Riset_{st.session_state['query'].replace(' ', '_')}.pdf", mime="application/pdf")
    with col_docx:
        st.download_button("📝 Unduh Word", data=docx_bytes, file_name=f"Riset_{st.session_state['query'].replace(' ', '_')}.docx", mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document")

    st.markdown("---")
    st.subheader(f"📊 Laporan Riset: {st.session_state['query']}")
    st.markdown(st.session_state['hasil_analisis'])

    with st.expander("🧭 Lihat Cetak Biru Berpikir Python (Question Planner Blueprint)"):
        for bp in st.session_state['planner_blueprint']:
            st.markdown(f"**Dimensi:** `{bp['domain']}`")
            if bp['matched_claims']:
                for src_id, clm in bp['matched_claims']:
                    st.markdown(f"&nbsp;&nbsp;&nbsp;&nbsp;• \"{clm}\" `[{src_id}]`")
            else:
                st.markdown("&nbsp;&nbsp;&nbsp;&nbsp;• *Fakta terintegrasi secara naratif.*")
            st.markdown("---")

    st.markdown("---")
    st.subheader("💬 Tanya Jawab Berbasis Perencanaan Agen")
    for message in st.session_state.get("messages", []):
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if user_prompt := st.chat_input("Tanyakan detail sub-dimensi atau analisis riset..."):
        st.session_state["messages"].append({"role": "user", "content": user_prompt})
        with st.chat_message("user"):
            st.markdown(user_prompt)
        with st.chat_message("assistant"):
            with st.spinner("Menyusun jawaban agen..."):
                jawaban = jawab_pertanyaan_chat(
                    user_prompt, 
                    st.session_state['planner_blueprint'], 
                    st.session_state['causal_chains_global'], 
                    st.session_state['timeline_global'], 
                    st.session_state['hasil_analisis']
                )
                st.markdown(jawaban)
                st.session_state["messages"].append({"role": "assistant", "content": jawaban})

    st.markdown("---")
    st.subheader("📚 Daftar Pustaka & Referensi")
    for item in st.session_state['sumber_data_lengkap']:
        st.markdown(f"**[{item['id']}]** [{item['title']}]({item['url']}) — **Kualitas:** {item['kualitas']}")
