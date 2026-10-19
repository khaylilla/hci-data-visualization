# Analisis Pengalaman Pengguna Aplikasi Google Play Store melalui Data Visualization dan Dashboard Interaktif

Proyek ini menggunakan analisis data dan visualisasi untuk membantu pengguna
menjelajahi karakteristik aplikasi Android pada dataset Google Play Store serta
distribusi sentimen pada ulasan yang tersedia. Dashboard dirancang dengan
prinsip HCI agar ringkasan mudah dipindai, filter mudah dikenali, dan keterbatasan
data terlihat oleh pengguna.

## Dataset dan batasan sumber

Letakkan kedua file CSV yang diberikan di folder `data/`:

- `googleplaystore.csv`: berisi kolom `App`, `Category`, `Rating`, `Reviews`,
  `Size`, `Installs`, `Type`, `Price`, `Content Rating`, `Genres`,
  `Last Updated`, `Current Ver`, dan `Android Ver`.
- `googleplaystore_user_reviews.csv`: berisi `App`, `Translated_Review`,
  `Sentiment`, `Sentiment_Polarity`, dan `Sentiment_Subjectivity`.

Sumber asal atau URL dataset tidak tercantum pada file yang tersedia di proyek
ini, sehingga README ini tidak mengasumsikan sumber eksternal tertentu. Dataset
asli tidak diubah oleh program.

Pemeriksaan CSV yang disediakan menemukan 10.841 baris aplikasi dan 64.295 baris
ulasan. Pada aplikasi, `Rating` memiliki 1.474 nilai kosong dan ditemukan 483
duplikasi baris persis. Pada ulasan, teks memiliki 26.868 nilai kosong,
`Sentiment` memiliki 26.863 nilai kosong, dan ditemukan 33.616 duplikasi baris
persis. Satu record aplikasi memiliki kategori `1.9`, rating `19`, dan nilai
kolom lain yang menunjukkan data tidak konsisten; nilai kategori/rating yang
tidak valid tidak digunakan dalam analisis kategori/rating. Rincian aktual
setelah pembersihan dicetak dan disimpan ke `output/ringkasan_analisis.txt`
ketika analisis dijalankan.

Hasil aktual dari aturan pembersihan yang diterapkan: 9.660 aplikasi unik dan
33 kategori valid; 8.196 aplikasi memiliki rating valid dengan rata-rata 4,173
dari 5. Kategori `FAMILY` memiliki jumlah aplikasi terbanyak (1.832). Sebanyak
29.692 ulasan memiliki teks dan label sentimen valid setelah deduplikasi;
28.250 baris ulasan tersebut cocok persis dengan nama aplikasi. Sentimennya
terdiri dari 19.015 positif, 6.321 negatif, dan 4.356 netral. Korelasi Spearman
rating dengan jumlah ulasan sebesar 0,12; ini hanya hubungan statistik
deskriptif, bukan bukti sebab-akibat. Korelasi Spearman rating dengan batas
bawah instalasi sebesar 0,027, sedangkan jumlah ulasan dengan batas bawah
instalasi sebesar 0,968. Karena instalasi disediakan dalam rentang berakhiran
`+`, angka instalasi tersebut adalah estimasi batas bawah. Nilai ringkasan
dicetak ulang dari data setiap kali `analysis.py` dijalankan.

## Teknologi

- Python
- Pandas
- Matplotlib dan Seaborn
- Streamlit

## Struktur folder

```text
hci-data-visualization/
├── data/
│   ├── googleplaystore.csv
│   └── googleplaystore_user_reviews.csv
├── output/                         # profil data, ringkasan, dan grafik PNG
├── analysis.py
├── app.py
├── requirements.txt
├── README.md
└── .gitignore
```

## Instalasi

Jalankan perintah dari folder proyek:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

## Menjalankan analisis dan dashboard

Jalankan analisis pembersihan, ringkasan, dan ekspor visualisasi:

```powershell
python analysis.py
```

Jalankan dashboard:

```powershell
streamlit run app.py
```

`analysis.py` menyimpan grafik PNG, profil kolom mentah, dan ringkasan hasil
terhitung di `output/`. Dashboard membaca data mentah dan membersihkannya
dengan fungsi yang sama sehingga hasil analisis dan dashboard konsisten.
Folder `output/` dibuat otomatis jika belum ada.

## Fitur dashboard

- Kartu metrik: aplikasi unik yang ditampilkan, rata-rata rating valid,
  kategori pada hasil filter, dan ulasan yang dapat dianalisis.
- Filter kategori, rentang rating, tipe aplikasi, dan sentimen.
- Grafik distribusi rating, jumlah aplikasi per kategori, hubungan rating
  dengan jumlah ulasan dan instalasi, rating rata-rata per kategori, serta
  distribusi sentimen.
- Insight deskriptif berdasarkan nilai hasil filter, tanpa klaim sebab-akibat.
- Tabel aplikasi dengan pencarian nama, pengurutan kolom, dan pagination.
- Status filter, jumlah data, serta pesan yang jelas pada hasil kosong.

## Metode dan definisi

- Baris duplikat persis dibuang. Karena beberapa nama aplikasi muncul pada
  beberapa record berbeda, analisis per aplikasi mempertahankan satu record
  terlengkap per nama; jika kelengkapan sama, urutan sumber menjadi pemutus seri.
- Rating dikonversi menjadi numerik; nilai di luar 0–5 diperlakukan sebagai
  tidak valid. Rata-rata rating hanya menghitung rating yang valid.
- `Reviews` dan `Installs` dibersihkan dari koma dan tanda `+`. Nilai instalasi
  adalah batas bawah yang ditunjukkan label sumber, bukan angka instalasi pasti;
  penjumlahan per kategori harus ditafsirkan sebagai akumulasi batas bawah.
- Kolom `Size` mentah dipertahankan; kolom tambahan `Size_MB` mengubah nilai
  dengan satuan `k`, `M`, atau `G` menjadi MB. Nilai seperti
  `Varies with device` atau format tidak dikenal menjadi tidak tersedia.
- Ulasan dianalisis hanya jika teks dan label (`Positive`, `Negative`, atau
  `Neutral`) tersedia setelah deduplikasi. Ulasan dihubungkan ke aplikasi hanya
  menggunakan kecocokan persis pada kolom `App`; nama yang tidak cocok tidak
  dipaksakan untuk digabung.
- Korelasi rating dan jumlah ulasan bersifat deskriptif dan tidak menunjukkan
  hubungan sebab-akibat.

## HCI dan visualisasi data

- **Recognition over recall:** label metrik, judul grafik, satuan, dan petunjuk
  filter ditampilkan langsung.
- **Cognitive load:** ringkasan utama ditempatkan sebelum grafik dan tabel.
- **Gestalt / proximity:** metrik serta visualisasi yang berkaitan dikelompokkan
  berdampingan dengan gaya yang konsisten.
- **Visibility of system status:** filter aktif dan jumlah baris ditampilkan;
  hasil kosong memiliki pesan khusus.
- **Consistency:** istilah, skala rating, warna grafik, dan format angka dibuat
  konsisten.
- **Error prevention:** nilai tidak valid/missing diperlakukan eksplisit dan
  filter kosong tidak menyebabkan aplikasi gagal.
- **Accessibility:** kontras memadai, label menjelaskan makna, dan grafik
  menggunakan judul/sumbu selain warna.
- **Minimalist design:** dekorasi non-informatif dihindari; tabel memakai
  pagination agar tetap responsif.

## Keterbatasan

Data ulasan memiliki banyak baris tanpa teks atau label sentimen. Tidak semua
nama aplikasi dalam data ulasan cocok persis dengan dataset aplikasi. Data
instalasi berupa rentang berakhiran `+`, sehingga hanya dapat dipakai sebagai
perkiraan batas bawah. Hasil analisis juga mencerminkan dataset yang tersedia,
bukan keseluruhan katalog Google Play saat ini.
