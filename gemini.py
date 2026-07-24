BUG 1 (Paling besar)
Di sini
expanded_keywords = expand_semantic_keywords(kata_kunci)

if any(k in teks_gabungan for k in expanded_keywords):
Masalahnya adalah
PPPK Paruh Waktu
AI mungkin menghasilkan
pegawai pemerintah

ASN

pegawai kontrak
Tetapi artikel hanya menulis
PPPK
Tidak ada
pegawai pemerintah
Akibatnya
False
langsung dibuang.
Saya lebih suka pakai sistem skor.
Misalnya
match = 0

for kw in expanded_keywords:

    if kw in teks:
        match += 1

if match >=1:
    lolos
atau
ranking berdasarkan jumlah keyword
lebih bagus.
