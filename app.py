from math import log10

import pandas as pd
import streamlit as st

from analysis import VALID_SENTIMENTS, load_data


st.set_page_config(
    page_title="Analisis Google Play Store",
    page_icon="📊",
    layout="wide",
)


@st.cache_data
def get_data() -> tuple[pd.DataFrame, pd.DataFrame, dict[str, int]]:
    return load_data()


st.title("Analisis Pengalaman Pengguna Google Play Store")
st.caption(
    "Jelajahi kualitas listing aplikasi dan persepsi dari ulasan pengguna. "
    "Semua metrik dihitung dari dataset yang tersedia."
)

try:
    apps_all, reviews_all, audit = get_data()
except (FileNotFoundError, ValueError, pd.errors.ParserError) as error:
    st.error(f"Data tidak dapat dimuat: {error}")
    st.stop()

with st.sidebar:
    st.header("Filter data")
    categories = sorted(apps_all["Category"].dropna().unique().tolist())
    selected_categories = st.multiselect(
        "Kategori aplikasi", categories, help="Kosongkan untuk memilih semua kategori."
    )
    rating_values = apps_all["Rating"].dropna()
    if rating_values.empty:
        rating_range = None
        st.caption("Filter rating tidak tersedia karena tidak ada rating valid.")
    else:
        minimum = float(rating_values.min())
        maximum = float(rating_values.max())
        rating_range = st.slider(
            "Rentang rating", min_value=0.0, max_value=5.0,
            value=(minimum, maximum), step=0.1,
        )
    if "Type" in apps_all.columns:
        available_types = sorted(apps_all["Type"].dropna().unique().tolist())
        selected_types = st.multiselect(
            "Tipe aplikasi", available_types,
            help="Kosongkan untuk menyertakan semua tipe.",
        )
    else:
        selected_types = []
    selected_sentiments = st.multiselect(
        "Sentimen ulasan", sorted(VALID_SENTIMENTS),
        help="Kosongkan untuk menyertakan semua sentimen.",
    )

apps = apps_all.copy()
if selected_categories:
    apps = apps.loc[apps["Category"].isin(selected_categories)]
if selected_types:
    apps = apps.loc[apps["Type"].isin(selected_types)]
if rating_range is not None:
    full_rating_range = (
        not rating_values.empty
        and rating_range[0] <= float(rating_values.min())
        and rating_range[1] >= float(rating_values.max())
    )
    if not full_rating_range:
        apps = apps.loc[apps["Rating"].between(rating_range[0], rating_range[1])]

selected_app_names = set(apps["App"].dropna())
reviews = reviews_all.loc[reviews_all["App"].isin(selected_app_names)].copy()
if selected_sentiments:
    reviews = reviews.loc[reviews["Sentiment"].isin(selected_sentiments)]

with st.container(border=True):
    st.subheader("Ringkasan utama")
    metric_columns = st.columns(4)
    metric_columns[0].metric("Aplikasi unik ditampilkan", f"{apps['App'].nunique():,}")
    average_rating = apps["Rating"].mean()
    metric_columns[1].metric(
        "Rata-rata rating", f"{average_rating:.2f} / 5" if pd.notna(average_rating) else "—"
    )
    metric_columns[2].metric("Kategori ditampilkan", f"{apps['Category'].nunique():,}")
    metric_columns[3].metric("Ulasan yang dianalisis", f"{len(reviews):,}")
    st.caption(
        "Aplikasi dihitung berdasarkan nama unik setelah membuang baris duplikat "
        "persis dan memilih record paling lengkap per nama. Rating kosong/tidak valid "
        "tidak masuk rata-rata. Ulasan dihitung setelah membuang duplikat, teks kosong, "
        "dan label sentimen yang hilang; hanya ulasan dengan nama aplikasi yang cocok "
        "persis dengan hasil filter aplikasi yang dihitung."
    )

active_filters = []
if selected_categories:
    active_filters.append(f"{len(selected_categories)} kategori")
if rating_range is not None and (
    rating_range[0] > (float(rating_values.min()) if not rating_values.empty else 0)
    or rating_range[1] < (float(rating_values.max()) if not rating_values.empty else 5)
):
    active_filters.append(f"rating {rating_range[0]:.1f}–{rating_range[1]:.1f}")
if selected_types:
    active_filters.append(f"{len(selected_types)} tipe")
if selected_sentiments:
    active_filters.append(f"{len(selected_sentiments)} sentimen")
st.info(
    f"Filter aktif: {', '.join(active_filters) if active_filters else 'tidak ada'}. "
    f"Menampilkan {len(apps):,} record aplikasi dan {len(reviews):,} ulasan."
)

if apps.empty:
    st.warning("Tidak ada aplikasi yang sesuai dengan filter. Ubah atau hapus filter.")
else:
    st.subheader("Visualisasi")
    left, right = st.columns(2)
    with left:
        st.markdown("**Distribusi rating aplikasi**")
        ratings = apps["Rating"].dropna()
        if ratings.empty:
            st.info("Tidak ada rating valid pada hasil filter.")
        else:
            st.bar_chart(
                ratings.value_counts(bins=10, sort=False).rename_axis("Rentang rating")
            )
    with right:
        st.markdown("**Jumlah aplikasi per kategori**")
        category_counts = apps["Category"].value_counts().head(15).sort_values()
        if category_counts.empty:
            st.info("Tidak ada kategori valid pada hasil filter.")
        else:
            st.bar_chart(category_counts)

    left, right = st.columns(2)
    with left:
        st.markdown("**Rating dan jumlah ulasan per aplikasi**")
        relation = apps.dropna(subset=["Rating", "Reviews"]).copy()
        if relation.empty:
            st.info("Belum ada pasangan rating dan jumlah ulasan yang valid.")
        else:
            relation = relation.loc[relation["Reviews"] > 0]
            if relation.empty:
                st.info("Jumlah ulasan harus lebih dari nol untuk skala log.")
            else:
                relation["Log jumlah ulasan"] = relation["Reviews"].map(log10)
                st.scatter_chart(
                    relation, x="Log jumlah ulasan", y="Rating",
                    x_label="Log10 jumlah ulasan", y_label="Rating (0-5)",
                )
        if len(relation) >= 2:
            corr = relation[["Rating", "Reviews"]].corr(method="spearman").iloc[0, 1]
            if pd.notna(corr):
                st.caption(
                    f"Korelasi peringkat Spearman pada aplikasi yang terlihat: {corr:.2f}. "
                    "Korelasi tidak menunjukkan hubungan sebab-akibat."
                )
    with right:
        st.markdown("**Rating dan batas bawah instalasi**")
        rating_installs = apps.dropna(subset=["Rating", "Installs"])
        rating_installs = rating_installs.loc[rating_installs["Installs"] > 0]
        if rating_installs.empty:
            st.info("Belum ada pasangan rating dan instalasi yang valid.")
        else:
            rating_installs["Log instalasi"] = rating_installs["Installs"].map(log10)
            st.scatter_chart(
                rating_installs, x="Log instalasi", y="Rating",
                x_label="Log10 batas bawah instalasi", y_label="Rating (0-5)",
            )

    left, right = st.columns(2)
    with left:
        st.markdown("**Rata-rata rating per kategori**")
        top_categories = apps["Category"].value_counts().head(12).index
        category_ratings = (
            apps.loc[apps["Category"].isin(top_categories)]
            .groupby("Category")["Rating"]
            .mean()
            .dropna()
            .sort_values()
        )
        if category_ratings.empty:
            st.info("Belum ada rating kategori yang valid pada filter ini.")
        else:
            st.bar_chart(category_ratings, y_label="Rating rata-rata (0-5)")
    with right:
        st.markdown("**Distribusi sentimen ulasan**")
        if reviews.empty:
            st.info("Tidak ada ulasan yang cocok dengan filter aplikasi dan sentimen.")
        else:
            st.bar_chart(reviews["Sentiment"].value_counts().reindex(
                ["Positive", "Neutral", "Negative"], fill_value=0
            ))

    st.markdown("**Jumlah ulasan dan batas bawah instalasi**")
    review_installs = apps.dropna(subset=["Reviews", "Installs"])
    review_installs = review_installs.loc[
        (review_installs["Reviews"] > 0) & (review_installs["Installs"] > 0)
    ].copy()
    if review_installs.empty:
        st.info("Belum ada pasangan jumlah ulasan dan instalasi yang valid.")
    else:
        review_installs["Log jumlah ulasan"] = review_installs["Reviews"].map(log10)
        review_installs["Log instalasi"] = review_installs["Installs"].map(log10)
        st.scatter_chart(
            review_installs, x="Log jumlah ulasan", y="Log instalasi",
            x_label="Log10 jumlah ulasan",
            y_label="Log10 batas bawah instalasi",
        )

    st.subheader("Insight dari data yang sedang ditampilkan")
    insight_columns = st.columns(2)
    category_counts = apps["Category"].value_counts()
    if category_counts.empty:
        insight_columns[0].write("Belum ada kategori yang dapat diringkas.")
    else:
        leader = category_counts.index[0]
        insight_columns[0].write(
            f"Kategori dengan aplikasi terbanyak adalah **{leader}** "
            f"({category_counts.iloc[0]:,} aplikasi)."
        )
    sentiment_counts = reviews["Sentiment"].value_counts()
    if sentiment_counts.empty:
        insight_columns[1].write("Belum ada ulasan berlabel untuk diringkas.")
    else:
        leading_sentiment = sentiment_counts.idxmax()
        percentage = sentiment_counts.max() / sentiment_counts.sum() * 100
        insight_columns[1].write(
            f"Sentimen terbanyak adalah **{leading_sentiment}** "
            f"({sentiment_counts.max():,} dari {sentiment_counts.sum():,}; "
            f"{percentage:.1f}%). Ini deskripsi distribusi, bukan sebab kualitas aplikasi."
        )

st.subheader("Data aplikasi")
st.caption(
    "Tabel mengikuti filter kategori, rating, dan tipe. Kolom dapat diurutkan "
    "dengan mengklik judulnya; pencarian berdasarkan nama aplikasi tersedia."
)
search = st.text_input("Cari nama aplikasi", placeholder="Ketik nama aplikasi...")
table = apps.copy()
if search.strip():
    table = table.loc[table["App"].str.contains(search.strip(), case=False, na=False)]
page_size = st.selectbox("Baris per halaman", [10, 25, 50, 100], index=1)
total_pages = max(1, (len(table) + page_size - 1) // page_size)
page_number = st.number_input(
    "Halaman", min_value=1, max_value=total_pages, value=1, step=1
)
start = (int(page_number) - 1) * page_size
st.dataframe(
    table.iloc[start:start + page_size],
    use_container_width=True,
    hide_index=True,
)
st.caption(
    f"Baris {start + 1 if len(table) else 0:,}–{min(start + page_size, len(table)):,} "
    f"dari {len(table):,} hasil pencarian."
)
st.caption(
    f"Sumber data mentah: {audit['apps_raw_rows']:,} baris aplikasi dan "
    f"{audit['reviews_raw_rows']:,} baris ulasan. Setelah pembersihan, "
    f"{audit['review_app_names_unmatched']:,} nama aplikasi ulasan tidak memiliki "
    "kecocokan persis dan tidak dihitung pada metrik yang mengaitkan aplikasi."
)
