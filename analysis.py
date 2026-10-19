from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns


ROOT_DIR = Path(__file__).resolve().parent
DATA_DIR = ROOT_DIR / "data"
OUTPUT_DIR = ROOT_DIR / "output"
APP_FILE = DATA_DIR / "googleplaystore.csv"
REVIEW_FILE = DATA_DIR / "googleplaystore_user_reviews.csv"
VALID_SENTIMENTS = {"Positive", "Negative", "Neutral"}
REQUIRED_APP_COLUMNS = {"App", "Category", "Rating", "Reviews", "Installs", "Type"}
REQUIRED_REVIEW_COLUMNS = {"App", "Translated_Review", "Sentiment"}


def _require_columns(frame: pd.DataFrame, required: set[str], filename: Path) -> None:
    missing = sorted(required.difference(frame.columns))
    if missing:
        raise ValueError(
            f"Kolom wajib tidak ditemukan pada {filename.name}: {', '.join(missing)}"
        )


def _parse_count(values: pd.Series, allow_plus: bool = False) -> pd.Series:
    cleaned = values.astype("string").str.strip()
    if allow_plus:
        cleaned = cleaned.str.replace(r"\+$", "", regex=True)
    cleaned = cleaned.str.replace(",", "", regex=False)
    cleaned = cleaned.where(cleaned.str.fullmatch(r"\d+(?:\.\d+)?", na=False))
    return pd.to_numeric(cleaned, errors="coerce")


def _parse_size_mb(values: pd.Series) -> pd.Series:
    parts = values.astype("string").str.strip().str.lower().str.extract(
        r"^(\d+(?:\.\d+)?)\s*([kmg]?)$"
    )
    amount = pd.to_numeric(parts[0], errors="coerce")
    multiplier = parts[1].map({"k": 1 / 1024, "m": 1, "g": 1024, "": 1})
    return amount * multiplier


def load_data() -> tuple[pd.DataFrame, pd.DataFrame, dict[str, int]]:
    """Load and clean source data without modifying either CSV."""
    if not APP_FILE.is_file() or not REVIEW_FILE.is_file():
        missing_files = [
            path.name for path in (APP_FILE, REVIEW_FILE) if not path.is_file()
        ]
        raise FileNotFoundError(
            f"File dataset tidak ditemukan di folder data/: {', '.join(missing_files)}"
        )

    apps_raw = pd.read_csv(APP_FILE)
    reviews_raw = pd.read_csv(REVIEW_FILE)
    _require_columns(apps_raw, REQUIRED_APP_COLUMNS, APP_FILE)
    _require_columns(reviews_raw, REQUIRED_REVIEW_COLUMNS, REVIEW_FILE)

    audit = {
        "apps_raw_rows": len(apps_raw),
        "reviews_raw_rows": len(reviews_raw),
        "apps_exact_duplicates": int(apps_raw.duplicated().sum()),
        "reviews_exact_duplicates": int(reviews_raw.duplicated().sum()),
        "reviews_missing_text": int(reviews_raw["Translated_Review"].isna().sum()),
        "reviews_missing_sentiment": int(reviews_raw["Sentiment"].isna().sum()),
    }

    apps = apps_raw.drop_duplicates().copy()
    apps["App"] = apps["App"].astype("string").str.strip()
    apps["Category"] = apps["Category"].astype("string").str.strip()
    apps["Category"] = apps["Category"].where(
        apps["Category"].str.fullmatch(r"[A-Z_]+", na=False)
    )
    apps["Rating"] = pd.to_numeric(apps["Rating"], errors="coerce")
    apps["Rating"] = apps["Rating"].where(apps["Rating"].between(0, 5))
    apps["Reviews"] = _parse_count(apps["Reviews"])
    apps["Installs"] = _parse_count(apps["Installs"], allow_plus=True)
    if "Size" in apps.columns:
        apps["Size_MB"] = _parse_size_mb(apps["Size"])
    if "Price" in apps.columns:
        price = apps["Price"].astype("string").str.replace("$", "", regex=False)
        apps["Price"] = pd.to_numeric(price, errors="coerce")
    if "Type" in apps.columns:
        apps["Type"] = apps["Type"].where(apps["Type"].isin(["Free", "Paid"]))

    quality_columns = [
        column
        for column in ("Category", "Rating", "Reviews", "Installs", "Type")
        if column in apps.columns
    ]
    apps["_completeness"] = apps[quality_columns].notna().sum(axis=1)
    audit["apps_duplicate_names"] = int(apps.duplicated(subset=["App"]).sum())
    audit["apps_invalid_ratings"] = int(
        pd.to_numeric(apps_raw["Rating"], errors="coerce").gt(5).sum()
    )
    apps = (
        apps.sort_values("_completeness", ascending=False, kind="stable")
        .drop_duplicates(subset=["App"], keep="first")
        .drop(columns="_completeness")
        .reset_index(drop=True)
    )
    audit["apps_clean_rows"] = len(apps)
    audit["apps_missing_category_after_cleaning"] = int(apps["Category"].isna().sum())

    reviews = reviews_raw.drop_duplicates().copy()
    reviews["App"] = reviews["App"].astype("string").str.strip()
    reviews["Translated_Review"] = reviews["Translated_Review"].astype("string").str.strip()
    reviews["Sentiment"] = reviews["Sentiment"].astype("string").str.strip()
    reviews["Sentiment"] = reviews["Sentiment"].where(
        reviews["Sentiment"].isin(VALID_SENTIMENTS)
    )
    reviews = reviews.dropna(subset=["App", "Translated_Review", "Sentiment"])
    reviews = reviews.loc[reviews["Translated_Review"].ne("")].reset_index(drop=True)
    for column in ("Sentiment_Polarity", "Sentiment_Subjectivity"):
        if column in reviews.columns:
            reviews[column] = pd.to_numeric(reviews[column], errors="coerce")
    audit["reviews_analyzable_rows"] = len(reviews)
    audit["review_app_names_matched"] = int(
        reviews["App"].isin(set(apps["App"].dropna())).sum()
    )
    audit["review_app_names_unmatched"] = int(
        reviews.loc[~reviews["App"].isin(set(apps["App"].dropna())), "App"].nunique()
    )
    return apps, reviews, audit


def _save_data_profile() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    profile_rows = []
    for label, path in (("applications", APP_FILE), ("reviews", REVIEW_FILE)):
        frame = pd.read_csv(path)
        for column in frame.columns:
            non_null = frame[column].dropna()
            example = str(non_null.iloc[0])[:100] if not non_null.empty else ""
            profile_rows.append(
                {
                    "dataset": label,
                    "column": column,
                    "dtype": str(frame[column].dtype),
                    "rows": len(frame),
                    "missing": int(frame[column].isna().sum()),
                    "missing_percent": round(
                        float(frame[column].isna().mean() * 100), 2
                    ),
                    "unique_non_missing": int(frame[column].nunique(dropna=True)),
                    "example": example,
                }
            )
    pd.DataFrame(profile_rows).to_csv(
        OUTPUT_DIR / "data_profile.csv", index=False, encoding="utf-8"
    )


def _save_figures(apps: pd.DataFrame, reviews: pd.DataFrame) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    sns.set_theme(style="whitegrid", palette="colorblind")

    rated = apps.dropna(subset=["Rating"])
    fig, ax = plt.subplots(figsize=(9, 5))
    sns.histplot(rated["Rating"], bins=20, binrange=(0, 5), color="#2878B5", ax=ax)
    ax.set(xlim=(0, 5), xlabel="Rating (0-5)", ylabel="Jumlah aplikasi",
           title="Distribusi rating aplikasi")
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "distribusi_rating.png", dpi=160)
    plt.close(fig)

    category_counts = apps["Category"].value_counts().head(10).sort_values()
    fig, ax = plt.subplots(figsize=(10, 6))
    category_counts.plot.barh(ax=ax, color="#2878B5")
    ax.set(xlabel="Jumlah aplikasi unik", ylabel="Kategori",
           title="10 kategori dengan aplikasi terbanyak")
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "top_10_kategori.png", dpi=160)
    plt.close(fig)

    rated_categories = (
        rated.dropna(subset=["Category"])
        .groupby("Category")["Rating"]
        .count()
        .sort_values(ascending=False)
        .head(12)
        .index
    )
    category_ratings = rated.loc[rated["Category"].isin(rated_categories)]
    fig, ax = plt.subplots(figsize=(12, 6))
    sns.boxplot(data=category_ratings, x="Rating", y="Category", color="#76B7B2", ax=ax)
    ax.set(xlim=(0, 5), xlabel="Rating (0-5)", ylabel="Kategori",
           title="Sebaran rating pada 12 kategori dengan data rating terbanyak")
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "rating_per_kategori.png", dpi=160)
    plt.close(fig)

    relationship = rated.dropna(subset=["Reviews"])
    fig, ax = plt.subplots(figsize=(9, 5))
    if not relationship.empty:
        sns.scatterplot(
            data=relationship, x="Reviews", y="Rating", alpha=0.35,
            s=24, color="#2878B5", edgecolor=None, ax=ax,
        )
        ax.set_xscale("log")
    ax.set(xlabel="Jumlah ulasan (skala log)", ylabel="Rating (0-5)",
           title="Hubungan rating dan jumlah ulasan")
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "rating_dan_ulasan.png", dpi=160)
    plt.close(fig)

    rated_installs = apps.dropna(subset=["Rating", "Installs"])
    fig, ax = plt.subplots(figsize=(9, 5))
    rated_installs = rated_installs.loc[rated_installs["Installs"] > 0]
    if not rated_installs.empty:
        sns.scatterplot(
            data=rated_installs, x="Installs", y="Rating", alpha=0.35,
            s=24, color="#2A9D8F", edgecolor=None, ax=ax,
        )
        ax.set_xscale("log")
    ax.set(xlabel="Batas bawah instalasi (skala log)", ylabel="Rating (0-5)",
           title="Hubungan rating dan batas bawah instalasi")
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "rating_dan_instalasi.png", dpi=160)
    plt.close(fig)

    review_install = apps.dropna(subset=["Reviews", "Installs"])
    review_install = review_install.loc[
        (review_install["Reviews"] > 0) & (review_install["Installs"] > 0)
    ]
    fig, ax = plt.subplots(figsize=(9, 5))
    if not review_install.empty:
        sns.scatterplot(
            data=review_install, x="Reviews", y="Installs", alpha=0.35,
            s=24, color="#F28E2B", edgecolor=None, ax=ax,
        )
        ax.set_xscale("log")
        ax.set_yscale("log")
    ax.set(xlabel="Jumlah ulasan (skala log)",
           ylabel="Batas bawah instalasi (skala log)",
           title="Hubungan jumlah ulasan dan batas bawah instalasi")
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "ulasan_dan_instalasi.png", dpi=160)
    plt.close(fig)

    sentiment_counts = reviews["Sentiment"].value_counts().reindex(
        ["Positive", "Neutral", "Negative"], fill_value=0
    )
    fig, ax = plt.subplots(figsize=(8, 5))
    sentiment_counts.plot.bar(ax=ax, color=["#2A9D8F", "#E9C46A", "#E76F51"])
    ax.set(xlabel="Sentimen", ylabel="Jumlah ulasan",
           title="Distribusi sentimen ulasan yang dapat dianalisis")
    ax.tick_params(axis="x", rotation=0)
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "distribusi_sentimen.png", dpi=160)
    plt.close(fig)

    installs_by_category = (
        apps.dropna(subset=["Category", "Installs"])
        .groupby("Category")["Installs"]
        .sum()
        .nlargest(10)
        .sort_values()
    )
    fig, ax = plt.subplots(figsize=(10, 6))
    installs_by_category.plot.barh(ax=ax, color="#F28E2B")
    ax.set(xlabel="Akumulasi batas bawah instalasi", ylabel="Kategori",
           title="10 kategori dengan akumulasi estimasi instalasi tertinggi")
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "instalasi_per_kategori.png", dpi=160)
    plt.close(fig)


def run_analysis() -> dict[str, object]:
    apps, reviews, audit = load_data()
    _save_data_profile()
    _save_figures(apps, reviews)

    category_counts = apps["Category"].value_counts()
    sentiment_counts = reviews["Sentiment"].value_counts()
    top_category = (
        {"category": str(category_counts.index[0]), "apps": int(category_counts.iloc[0])}
        if not category_counts.empty else None
    )
    sentiment_total = int(sentiment_counts.sum())
    sentiment_share = (
        {
            str(label): round(int(count) / sentiment_total * 100, 2)
            for label, count in sentiment_counts.items()
        }
        if sentiment_total else {}
    )
    correlation_frame = apps[["Rating", "Reviews", "Installs"]].corr(
        method="spearman"
    )
    pairwise_correlations = {
        "rating_reviews": correlation_frame.loc["Rating", "Reviews"],
        "rating_installs": correlation_frame.loc["Rating", "Installs"],
        "reviews_installs": correlation_frame.loc["Reviews", "Installs"],
    }
    pairwise_correlations = {
        key: round(float(value), 3) if pd.notna(value) else None
        for key, value in pairwise_correlations.items()
    }
    summary: dict[str, object] = {
        "audit": audit,
        "unique_apps": int(apps["App"].nunique()),
        "app_records": len(apps),
        "category_count": int(apps["Category"].nunique()),
        "mean_rating": (
            round(float(apps["Rating"].mean()), 3)
            if apps["Rating"].notna().any() else None
        ),
        "rated_app_count": int(apps["Rating"].notna().sum()),
        "analyzable_review_count": len(reviews),
        "matched_analyzable_review_count": audit["review_app_names_matched"],
        "top_category": top_category,
        "sentiment_counts": {str(k): int(v) for k, v in sentiment_counts.items()},
        "sentiment_share_percent": sentiment_share,
        "spearman_correlations": pairwise_correlations,
        "install_values_available": int(apps["Installs"].notna().sum()),
        "size_values_available": int(apps["Size_MB"].notna().sum()),
    }

    report_lines = [
        "Ringkasan analisis Google Play Store",
        "",
        f"Baris aplikasi mentah: {audit['apps_raw_rows']:,}",
        f"Duplikasi baris aplikasi persis: {audit['apps_exact_duplicates']:,}",
        f"Nama aplikasi berulang setelah deduplikasi persis: {audit['apps_duplicate_names']:,}",
        f"Record aplikasi unik yang dianalisis: {summary['app_records']:,}",
        f"Kategori valid: {summary['category_count']:,}",
        f"Aplikasi dengan rating valid: {summary['rated_app_count']:,}",
        f"Rata-rata rating valid (0-5): {summary['mean_rating']}",
        f"Rating di luar rentang yang ditemukan: {audit['apps_invalid_ratings']:,}",
        f"Baris ulasan mentah: {audit['reviews_raw_rows']:,}",
        f"Ulasan dengan teks dan label sentimen valid: {len(reviews):,}",
        f"Duplikasi baris ulasan persis: {audit['reviews_exact_duplicates']:,}",
        f"Ulasan valid dengan nama aplikasi cocok persis: {audit['review_app_names_matched']:,}",
        f"Nama aplikasi ulasan yang tidak cocok: {audit['review_app_names_unmatched']:,}",
        f"Kategori dengan aplikasi terbanyak: {top_category}",
        f"Distribusi sentimen: {summary['sentiment_counts']}",
        f"Korelasi Spearman berpasangan: {summary['spearman_correlations']}",
        f"Nilai ukuran aplikasi yang dapat dikonversi ke MB: {summary['size_values_available']:,}",
        "",
        "Installs berakhiran '+' ditafsirkan sebagai batas bawah; total kategori adalah",
        "penjumlahan batas bawah, bukan jumlah instalasi aktual yang presisi.",
        "Profil kolom dan grafik PNG tersimpan di folder output/.",
    ]
    (OUTPUT_DIR / "ringkasan_analisis.txt").write_text(
        "\n".join(report_lines), encoding="utf-8"
    )
    print("\n".join(report_lines))
    return summary


if __name__ == "__main__":
    run_analysis()
