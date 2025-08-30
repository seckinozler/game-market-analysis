#!/usr/bin/env python
# coding: utf-8

# # Preliminary Analysis of the Gaming Market (with RAWG API)
# 
# ## 🎯 Objective
# 
# Before developing a new game, we aim to understand the market by examining the breakdown of games by **genre**, **platform**, **developer**, and **publisher**, as well as their quality distribution.  
# 
# In this scope:
# 
# - **Time analysis:** Average Metacritic scores by year and distribution of 84+ games, pandemic impact, and shifts in the top segment.  
# - **Genre analysis:** Average quality by genre, player interest (ratings_count & added), and the balance between quality and interest.  
# - **Developer analysis:** Developers with the highest output, their 84+ game ratios, and strategies to avoid competition (particularly Nintendo’s dominance).  
# - **Publisher analysis:** Segmentation by a 40% threshold (high volume & high success, accessible but lower success, prestigious niche partners). Potential partnership opportunities for indie developers.  
# - **Store analysis:** Number of games released on stores, 84+ ratios, and evaluation of porting workload. Strategic recommendations for release sequencing.  
# - **Additional analyses:** Community interest and popularity trends of games based on ratings_count and added metrics.  
# - **Unforgettables:** For enthusiasts, a listing of Metacritic 95+ games (34 titles).  
# 
# **Overall goal:**  
# To make informed **genre–platform–partner–timing** decisions for a new game, considering not only quality (Metacritic) but also **player interest, publisher strategies, and store dynamics**.
# 
# ## Data Source
# - **RAWG Video Games Database API**
# - This study was conducted solely for **learning and portfolio** purposes.
# - **Data extraction date:** August 2025
# 
# ## Collected Data
# - **Total records:** 5,000 games
# - **Selection criteria:** Top 5,000 games sorted by Metacritic score (descending). The lowest included score is 68.
# - **Extraction strategy:**
#   1) **List endpoint:** `GET /api/games`  
#      Parameters:  
#      - `ordering = -metacritic`  
#      - `page_size = 40`  
#      - `page = 1..n` (iterated until 5,000 records retrieved)  
#   2) **Detail enrichment:** For each game `GET /api/games/{id}`  
#      - Added developer, publisher, genre, and store data.
# 
# ## Final Columns
# - `rawg_id`, `name`, `released`, `metacritic_x`, `ratings_count`, `added`, `platforms`, `developers`, `publishers`, `genres`, `stores`
# 
# > Notes:
# > - For some very old/broken records, the detail endpoint occasionally returned **502**; these records have empty detail fields.  
# > - All analyses and visualizations were conducted on this 5,000-record dataset.  

# # 0. RAWG API Connection Test (Smoke Test)
# 
# In this step, I verified that the API key is working and that we can properly access the `/api/games` endpoint.
# 
# ## What did I do?
# - **Endpoint:** `GET https://api.rawg.io/api/games`
# - **Parameters:**
#   - `ordering = -metacritic`  → sort starting from the highest Metacritic
#   - `page_size = 3`           → quick check without consuming the quota (3 records)
#   - `page = 1`                → first page
# - **Expected output:**
#   - `status: 200`
#   - JSON top-level key includes `results`
#   - First 3 games contain `name`, `metacritic`, `ratings_count`
# 
# ## Why this step?
# - To quickly confirm if the API key and endpoint access are **valid**
# - To **check** the JSON schema (top-level keys)
# - To run a **quick validation** before moving to the large extraction (5,000 records)

# In[105]:


import requests

# RAWG API anahtarını tanımlıyoruz
RAWG_KEY = "762732b1ace74b74b4afac1190285ebb"

# Çekmek istediğimiz endpoint: Oyun listesi
url = "https://api.rawg.io/api/games"

# Parametreler:
# - key: API anahtarımız
# - page_size: Kaç oyun gelsin (3 ile test amaçlı sınırlıyoruz)
# - ordering: "-metacritic" → Metacritic puanına göre azalan sıralama
params = {
    "key": RAWG_KEY,
    "page_size": 3,       # sadece 3 oyun gelsin
    "ordering": "-metacritic"
}

# API isteğini gönderiyoruz (15 sn timeout ile)
r = requests.get(url, params=params, timeout=15)
print("status:", r.status_code)  # HTTP durum kodunu yazdır (200 → başarılı)

# JSON verisini alıyoruz
data = r.json()

# Gelen cevaptaki en üst seviyedeki anahtarları yazdırıyoruz (ör. "results", "count", "next" vb.)
print("üst anahtarlar:", list(data.keys()))

# "results" listesindeki oyunları tek tek yazdır
for g in data.get("results", []):
    # Her oyun için isim, metacritic puanı ve ratings_count (kaç kişinin oyladığı) gösterilir
    print(g.get("name"), "| metacritic:", g.get("metacritic"), "| ratings_count:", g.get("ratings_count")) 


# # 1. Data Collection and Preparation
# 
# ## 1.1 List Endpoint (10 Sample Games)
# - In the initial test, 10 games were retrieved from the list endpoint.
# - Extracted fields: `rawg_id, name, released, metacritic_x, ratings_count, added, platforms`
# - At this step, only the **list response** was used (summary information).
# 
# ## 1.2 Detail Endpoint (Enrichment)
# - For each game, `GET /api/games/{id}` was called.
# - Additional fields included: `developers, publishers, genres, stores`
# - This way, a **complete profile** was created for each game.
# 
# ## 1.3 Merging
# - The list table and detail table were merged via `rawg_id`.
# - Result: Each row corresponds to one game and contains the following columns:
#   - `rawg_id`, `name`, `released`, `metacritic_x`, `ratings_count`, `added`,
#   - `platforms`, `developers`, `publishers`, `genres`, `stores`
# 
# > At the end of this step, a small sample set (10 games) was created.  
# > In the next step, the same process was scaled up to **5,000 games**.

# In[13]:


import requests, pandas as pd, time

# 1) İlk 10 oyunu liste endpointinden çek
BASE = "https://api.rawg.io/api/games"
params = {"key": RAWG_KEY, "ordering": "-metacritic", "page_size": 10, "page": 1}
r = requests.get(BASE, params=params, timeout=20)
r.raise_for_status()
data = r.json()

rows = []
for g in data["results"]:
    rows.append({
        "rawg_id": g["id"],
        "name": g.get("name"),
        "released": g.get("released"),
        "metacritic_x": g.get("metacritic"),   # liste yanıtından gelen metacritic
        "ratings_count": g.get("ratings_count"),
        "added": g.get("added"),
        "platforms": ", ".join([p["platform"]["name"] for p in (g.get("platforms") or [])])
    })

df_list = pd.DataFrame(rows)

# 2) Detaylardan developers, publishers, genres, stores ekle
def fetch_game_details(rawg_id: int, key: str) -> dict:
    url = f"https://api.rawg.io/api/games/{rawg_id}"
    r = requests.get(url, params={"key": key}, timeout=30)
    r.raise_for_status()
    d = r.json()

    def join_names(lst, key="name"):
        return ", ".join([x.get(key) for x in (lst or []) if x.get(key)]) if lst else None

    stores = None
    if d.get("stores"):
        stores = ", ".join([(s.get("store") or {}).get("name") for s in d["stores"] if s.get("store")])

    return {
        "rawg_id": d["id"],
        "developers": join_names(d.get("developers")),
        "publishers": join_names(d.get("publishers")),
        "genres": join_names(d.get("genres")),
        "stores": stores
    }

detail_rows = []
for i, rid in enumerate(df_list["rawg_id"].tolist(), start=1):
    detail_rows.append(fetch_game_details(int(rid), RAWG_KEY))
    if i % 3 == 0 or i == len(df_list):
        print(f"detay alındı: {i}/{len(df_list)}")
    time.sleep(0.2)

df_details = pd.DataFrame(detail_rows)

# 3) Birleştir
df_final = df_list.merge(df_details, on="rawg_id", how="left")

# 4) Son tablo
print("Satır:", len(df_final), "| Sütun:", len(df_final.columns))
df_final.head(10)


# # 2. Large Extraction: 5,000 Games (Ordering = Metacritic ↓)
# 
# In this step, I scaled up the sample study and pulled **5,000 games** from the RAWG API.  
# The goal is to build a broader dataset that represents the market and enables more solid analyses of genres/platforms/developers.
# 
# ## 2.1 Method (List → Detail → Merge)
# 1) **List endpoint**: `GET /api/games`  
#    - `ordering = -metacritic`  → starting from the highest Metacritic  
#    - `page_size = 40`          → maximum records per page  
#    - `page = 1..n`             → keep paginating as long as “next” exists  
#    - Loop stops once target (`TARGET = 5000`) is reached.  
#    - Fields extracted from the list:  
#      `rawg_id, name, released, metacritic_x, ratings_count, added, platforms`
# 
# 2) **Detail endpoint**: `GET /api/games/{id}`  
#    - Individual call for each game.  
#    - Additional fields: `developers, publishers, genres, stores`  
#    - Each game thus became “enriched.”
# 
# 3) **Merging**  
#    - List + Detail tables were **left merged** via `rawg_id`.  
#    - Final table (11 columns):  
#      `rawg_id, name, released, metacritic_x, ratings_count, added, platforms, developers, publishers, genres, stores`
# 
# ## 2.2 Rate Limiting and Error Handling
# - A **small delay** was added between requests (`time.sleep(0.25)`) → to be kind to the API.  
# - For some old/incomplete records, the server returned **502 (Bad Gateway)**.  
#   - In those cases, detail fields were left **empty**, and the flow continued.  
#   - (Retry/backoff could be added if desired.)
# 
# ## 2.3 Output
# - Total row count: **≈ 5,000**
# - Saved file: `data/rawg_5000_games.csv` (archived as CSV in the project)  
# - This dataset was later used for market snapshot, time trends, and genre/developer/platform analyses.
# 
# > Note: This work is solely for **learning and portfolio** purposes; data source is **RAWG API**.

# In[17]:


import requests, pandas as pd, time, os
from datetime import datetime

RAWG_BASE = "https://api.rawg.io/api/games"
TARGET = 5000          # hedef oyun sayısı
PAGE_SIZE = 40
ORDERING = "-metacritic"
RATE_SLEEP_LIST = 0.25     # liste çağrıları arası bekleme (sn)
RATE_SLEEP_DETAIL = 0.25   # detay çağrıları arası bekleme (sn)

# ---------- 1) LISTE: temel alanlar ----------
rows = []
page = 1
print(">> Liste çekimi başlıyor...")
while len(rows) < TARGET:
    params = {
        "key": RAWG_KEY,
        "page_size": PAGE_SIZE,
        "page": page,
        "ordering": ORDERING
    }
    r = requests.get(RAWG_BASE, params=params, timeout=30)
    r.raise_for_status()
    data = r.json()

    for g in data.get("results", []):
        rows.append({
            "rawg_id": g.get("id"),
            "name": g.get("name"),
            "released": g.get("released"),
            "metacritic_x": g.get("metacritic"),
            "ratings_count": g.get("ratings_count"),
            "added": g.get("added"),
            "platforms": ", ".join([p["platform"]["name"] for p in (g.get("platforms") or [])])
        })
        if len(rows) >= TARGET:
            break

    if not data.get("next"):
        print(">> Sayfa bitti (next yok).")
        break
    page += 1
    if page % 5 == 0:
        print(f"  - İşlenen sayfa: {page}, toplanan satır: {len(rows)}")
    time.sleep(RATE_SLEEP_LIST)

df_list = pd.DataFrame(rows).drop_duplicates(subset=["rawg_id"]).reset_index(drop=True)
print(">> Liste tamamlandı. Satır:", len(df_list))

# ---------- 2) DETAY: developers, publishers, genres, stores ----------
def fetch_game_details(rawg_id: int, key: str) -> dict:
    url = f"https://api.rawg.io/api/games/{rawg_id}"
    r = requests.get(url, params={"key": key}, timeout=30)
    r.raise_for_status()
    d = r.json()

    def join_names(lst, key="name"):
        return ", ".join([x.get(key) for x in (lst or []) if isinstance(x, dict) and x.get(key)]) if lst else None

    stores = None
    if d.get("stores"):
        stores = ", ".join([(s.get("store") or {}).get("name") for s in d["stores"] if (s.get("store") or {}).get("name")])

    return {
        "rawg_id": d.get("id"),
        "developers": join_names(d.get("developers")),
        "publishers": join_names(d.get("publishers")),
        "genres": join_names(d.get("genres")),
        "stores": stores
    }

detail_rows = []
print(">> Detay çekimi başlıyor...")
for i, rid in enumerate(df_list["rawg_id"].tolist(), start=1):
    try:
        detail_rows.append(fetch_game_details(int(rid), RAWG_KEY))
    except Exception as e:
        # hata olursa boş kayıt koyup devam edelim
        detail_rows.append({"rawg_id": int(rid), "developers": None, "publishers": None, "genres": None, "stores": None})
        print(f"  ! detay hatası (id={rid}): {type(e).__name__} - {e}")
    if i % 100 == 0 or i == len(df_list):
        print(f"  - Detay ilerleme: {i}/{len(df_list)}")
    time.sleep(RATE_SLEEP_DETAIL)

df_details = pd.DataFrame(detail_rows)

# ---------- 3) MERGE ----------
df_final = df_list.merge(df_details, on="rawg_id", how="left")
print(">> Birleştirildi. Boyut:", df_final.shape)

# ---------- 4) KAYDET ----------
os.makedirs("data", exist_ok=True)
stamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
out_csv = f"data/rawg_{len(df_final)}_games_{stamp}.csv"
df_final.to_csv(out_csv, index=False)
print(">> Kaydedildi:", out_csv)

# ---------- 5) ÖZET ----------
print("\nÖrnek satırlar:")
display(df_final.head(5))
print("\nSütunlar:", list(df_final.columns))


# # 2.4 Data Saving and Cleaning
# 
# ## Saving as CSV
# - The final `df_final` table was written to disk in **CSV** format:  
#   `rawg_5000_games.csv`
# - The file was made accessible via a downloadable link in Jupyter (`FileLink`).
# 
# ## Date Format Adjustment
# - In some rows, the `released` column was returned as a string.  
# - Converted to **datetime** type using Pandas `to_datetime(..., errors="coerce")`.  
#   - Invalid/empty values were marked as `NaT`.  
# - This step was necessary for use in time-series analyses (`.dt.year`, etc.).
# 
# > At the end of this step, the dataset was both **archived** and **ready for analysis**.

# In[18]:


df_final.to_csv("rawg_5000_games.csv", index=False)


# In[19]:


from IPython.display import FileLink
FileLink("rawg_5000_games.csv")


# In[21]:


df_final["released"] = pd.to_datetime(df_final["released"], errors="coerce")


# # 3. Time Trends — Average Metacritic by Year
# 
# **Why?**  
# Since our data extraction criterion is Metacritic score, the first step is to examine how the average score has evolved by year.  
# This analysis provides a baseline reference for the question: *“If a new game is released today, what is the current quality benchmark in the market?”*
# 
# **Method (summary):**
# - Converted `released` date to `datetime` type (`errors="coerce"`).
# - Extracted `year = released.dt.year` for each game.
# - Grouped by year and calculated the average of `metacritic_x`.
# 
# **Chart interpretation (expected insights):**
# - The overall upward/downward trend of average Metacritic scores over the years.  
# - Peak and drop years (e.g., generation transitions, platform booms).  
# - Potential impacts of disruptions in the trend (e.g., 2007–2012 console transitions, pandemic period).  
# 
# > Note: Records with missing `released` values were excluded. Therefore, some very old or incomplete entries may not be reflected in the chart.

# In[127]:


# "released" kolonunu datetime formatına çeviriyoruz
# errors="coerce" → hatalı tarihleri NaT (eksik değer) yapar
df_final["released"] = pd.to_datetime(df_final["released"], errors="coerce")

import matplotlib.pyplot as plt

# Yıllara göre ortalama Metacritic hesaplama
df_year = (
    df_final
    .dropna(subset=["released","metacritic_x"])   # eksik tarih veya metacritic olan satırları at
    .assign(year=lambda d: d["released"].dt.year) # tarih kolonundan sadece yılı çıkar
    .groupby("year", as_index=False)["metacritic_x"].mean()  # yıl bazında ortalama metacritic al
)

# Çizgi grafik çizimi
plt.figure(figsize=(12,6))  # grafik boyutu
plt.plot(df_year["year"], df_year["metacritic_x"], marker="o")  # yıllar x ekseni, ortalama metacritic y ekseni
plt.title("Yıllara Göre Ortalama Metacritic")  # başlık
plt.xlabel("Yıl")                             # x ekseni etiketi
plt.ylabel("Ortalama Metacritic")             # y ekseni etiketi
plt.grid(True, alpha=0.4)                     # grid çizgileri (alpha=0.4 → şeffaflık)
plt.show()                                    # grafiği göster


# ### Commentary — Average Metacritic by Year
# 
# The chart shows the average Metacritic scores of games released between 1985–2024.  
# 
# **Key findings:**
# - **Mid-1990s – early 2000s:** Average Metacritic scores were very high (84–86 range). This was the era when the console market expanded and many “legendary” games were released.  
# - **Post-2005:** Average scores stabilized in the 78–80 range. In other words, overall game quality became **more balanced and closer to the mean**.  
# - **2015–2021:** Nearly flat trend (around 77–79) over a long period. This indicates that the quality benchmark in the gaming industry had plateaued.  
# - **Sudden rise after 2023:** Average scores climbed back to 82–83.  
#   A major reason may be that **large-scale titles developed during the 2020 pandemic but delayed** started to release around 2023. The extended development cycles could have improved quality.  
#   However, since our dataset is **selected by Metacritic ranking**, we should keep in mind there may be a slight bias here.  
# 
# **Conclusion:**  
# For someone planning to develop a new game, this chart conveys the following message:  
# - Since 2005, industry-wide average quality has been **stabilized in the 78–80 band**.  
# - Although there has been a recent improvement, achieving a “high Metacritic” score still means **crossing the 84+ threshold**, which remains very challenging.  
# - A new game aiming to be competitive should reasonably target **84 or higher**.

# ## 3.1 Number of “High-Quality Games” by Year (Metacritic ≥ 84)
# 
# **Why?**  
# Since the Top-5000 dataset was selected based on Metacritic, the “total number of games per year” may not represent the entire market.  
# Therefore, we set a threshold of **84** and count how many games per year scored **84+**.  
# This allows us to compare the **density of high-quality titles** more fairly across different periods.
# 
# **Method (summary):**
# - Extracted `released → year` (records with missing dates excluded).  
# - Applied filter `metacritic_x ≥ 84`.  
# - Grouped by year + counted.  
# - Labeled each bar in the chart with its count.  
# 
# > Note: Since the dataset consists of the “top 5000,” this metric reflects the **concentration of high-quality games**, not the full market volume.

# In[110]:


import matplotlib.pyplot as plt

THRESH = 84  #  Baraj değerimiz (Metacritic 84 ve üzeri oyunları alacağız)

# Veri hazırlığı
df_ge = (
    df_final
    .dropna(subset=["released","metacritic_x"])     # geçersiz tarih veya metacritic verilerini at
    .assign(year=lambda d: d["released"].dt.year)   # yıl bilgisi ekle
    .query("metacritic_x >= @THRESH")               # sadece 84+ oyunları filtrele
    .groupby("year", as_index=False)                # yıl bazında grupla
    .size()                                         # oyun sayısını hesapla
    .rename(columns={"size": f"count_ge_{THRESH}"}) # kolon adını anlamlı yap (count_ge_84)
)

# Çubuk grafik çizimi
plt.figure(figsize=(12,6))
bars = plt.bar(df_ge["year"], df_ge[f"count_ge_{THRESH}"])   # yıl → x, oyun sayısı → y
plt.title(f"Yıllara Göre Metacritic ≥ {THRESH} Oyun Sayısı (Top-5000 örneklem)")
plt.xlabel("Yıl")
plt.ylabel("Oyun Sayısı")

# Çubukların üstüne değer etiketleri ekle
for b, v in zip(bars, df_ge[f"count_ge_{THRESH}"]):
    plt.text(b.get_x()+b.get_width()/2, b.get_height()+0.5, str(int(v)),
             ha="center", va="bottom")

plt.tight_layout()   # kenarlarda taşma olmasın
plt.show()           # grafiği göster


# ### Commentary — Number of Games with Metacritic ≥ 84 by Year
# 
# The chart shows the **number of games per year with a Metacritic score of 84 or higher** (based on the top-5000 sample).
# 
# **Key findings:**
# - **2000–2010 period:** On average, 40–50 high-scoring games were released per year; this was the most consistent era of quality game production.  
# - **2016–2017 peak:** 63 games in 2016 and 73 in 2017 scored 84+, marking the highest concentration of quality in the dataset.  
# - **Post-2018 decline:** From 2018 onwards, the count dropped significantly; there was a sharp decline between 2021–2023 (only 10 games in 2023).  
# - **Possible reason:** Many projects were delayed during the pandemic starting in 2020, which reduced releases in 2021–2023.  
#   In the coming years, we may see a rebound as projects developed during 2020–2023 get released.  
# 
# **Conclusion:**  
# The industry **peaked in terms of quality in the mid-2010s**, but in recent years the number of highly-rated games has decreased.  
# For a new game, this could create a “gap” in the market — a high-quality release may stand out more in a period with lower competition.
# 
# ---
# 
# ### Commentary — Pandemic Effect
# 
# We previously observed that the pandemic **increased average Metacritic scores**.  
# However, when we analyze the 84+ threshold, we see that the **number of top-segment games decreased** in the same period.  
# 
# This result shows us:  
# - Overall, the industry experienced a **general quality increase**,  
# - But the **concentration in the top tier** has diminished.  
# - In other words, the standard deviation narrowed, with games clustering more in the **upper-mid range**.  
# 
# Therefore, a game scoring **84+ will attract even more attention** in today’s market.  
# This reinforces our earlier conclusion that the 84 threshold is a meaningful benchmark.
# 
# ---
# 
# ### Note — 2024 and Beyond
# 
# In the chart, 2024 appears with only **1 game**, and 2025 has no data.  
# This is because the dataset was **extracted in August 2025**.  
# - Since 2024 is not yet complete, many games have not been released or scored.  
# - For 2025, although some games are listed, they are not yet scored and thus excluded from this analysis.  
# 
# Therefore, data for 2024 and beyond is **not reliable due to partial-year effects**.  
# It is more accurate to focus interpretations on 2023 and earlier.

# ### Transition to Genre Analysis
# 
# In the previous steps, we established our target **Metacritic threshold (84+)**.  
# Now, we shift focus to game genres.  
# The goal is to identify which genres generally achieve higher average scores, and in which genres the likelihood of entering the 84+ segment is greater.

# ## 3.2 Genre Analysis — Average Quality and Top-Tier Potential
# 
# One of the most strategic decisions in game development is choosing which **genre** to focus on.  
# Therefore, by analyzing the genres in our dataset, we compare:  
# 
# - The **average Metacritic scores** of genres (overall quality level),  
# - The **proportion of games reaching 84+** within each genre (potential for producing top-tier titles).  
# 
# **Goal:** To reveal which genres provide higher average quality and which ones offer a greater chance of achieving top-level success.

# In[120]:


# 1 satır 2 kolon (yan yana grafikler) olacak şekilde figür hazırlıyoruz
fig, axes = plt.subplots(1, 2, figsize=(16, 6))

# --- Ortalama Metacritic ---
# Türlere göre ortalama Metacritic puanını en yüksekten sıralayıp ilk 15'i alıyoruz
top_mean = agg.sort_values("mean_mc", ascending=False).head(15)

# Yatay bar grafiği (barh) çizdiriyoruz, ters çevirerek üstten alta doğru sıralama yapıyoruz
bars = axes[0].barh(top_mean["genre"][::-1], top_mean["mean_mc"][::-1])

# Grafik başlığı, eksen adı ve sınırları
axes[0].set_title("Türlere Göre Ortalama Metacritic (Top 15)")
axes[0].set_xlabel("Ortalama Metacritic")
axes[0].set_xlim(77, 80)  # daha net görünüm için 77–80 aralığı zoom

# Barların üzerine sayısal değer (ortalama Metacritic) yazdırıyoruz
for b in bars:
    axes[0].text(b.get_width()+0.02, b.get_y()+b.get_height()/2,
                 f"{b.get_width():.1f}", va="center", fontsize=8)

# --- 84+ Oranı ---
# Türlere göre 84 ve üzeri puan alan oyunların oranını hesaplayıp en yüksek ilk 15'i alıyoruz
top_rate = agg.sort_values("rate_ge84", ascending=False).head(15)

# Yatay bar grafiği (barh) çizdiriyoruz
bars = axes[1].barh(top_rate["genre"][::-1], top_rate["rate_ge84"][::-1])

# Grafik başlığı ve eksen etiketi
axes[1].set_title("Türlere Göre 84+ Oranı (Top 15)")
axes[1].set_xlabel("84+ Oranı (%)")

# Barların üzerine oran değerini yüzde formatında yazdırıyoruz
for b in bars:
    axes[1].text(b.get_width()+0.3, b.get_y()+b.get_height()/2,
                 f"{b.get_width():.1f}%", va="center", fontsize=8)

# Grafiklerin taşmaması ve hizalı görünmesi için
plt.tight_layout()
plt.show()


# ### Commentary — Metacritic Analysis by Genre
# 
# In the first chart (left), the **average Metacritic scores** of genres are compared.  
# Here, we see that *Educational, Platformer, and Card* genres stand out, reaching an average of 79+ points compared to others.  
# However, since the differences cluster in a narrow range (77–80), overall quality is relatively balanced across genres.  
# 
# In the second chart (right), the **proportion of games reaching the 84+ segment** is shown.  
# This metric better reflects a genre’s potential to produce “top-tier” games.  
# - *Card (31%), Platformer (29%), Shooter (27%)* genres managed to bring roughly one-third of their titles into the 84+ range.  
# - In contrast, genres like *Adventure (17%) and Family (18.9%)* have a lower probability of reaching the top tier.  
# 
# **Conclusion:**  
# - While average scores are close across genres, those with higher **84+ ratios** (Card, Platformer, Shooter) may offer more strategic opportunities for new game development.  
# - This analysis highlights the importance of looking not only at “average quality” but also at the **likelihood of achieving top-tier success**.

# ## 3.3 Genre Analysis — Engagement / Popularity (ratings_count & added)
# 
# While Metacritic reflects quality, we measure **player interest** using two RAWG metrics:
# - **`ratings_count`**: How many people rated the game → *engagement intensity*  
# - **`added`**: How many people added it to their collection/wishlist → *popularity/interest*  
# 
# **Method:**
# - Exploded games by genre and calculated the **median** `ratings_count` and **median** `added` for each genre (to avoid distortion from outliers).  
# - Listed the top 15 genres separately for each metric.  
# 
# > Note: The number of samples per genre is not equal; genres with only a few games may appear inflated. This is why we used the median.

# In[121]:


import pandas as pd
import matplotlib.pyplot as plt

# Hariç tutulacak türler
EXCLUDE_GENRES = {"Indie"}   # Oyun tarzlarına göre baktığımız için, indie olan bir oyun mesala metroidvania da olabildiği için indie yi tür olarak almıyoruz.

# genres + ilgi metrikleri için uzun form (Indie hariç)
rows = []
src = df_final.dropna(subset=["genres"])
for _, row in src.iterrows():
    g_list = [g.strip() for g in row["genres"].split(",") if g.strip()]
    rc = row.get("ratings_count")
    ad = row.get("added")
    for g in g_list:
        if g in EXCLUDE_GENRES:
            continue
        rows.append({
            "genre": g,
            "ratings_count": float(rc) if pd.notna(rc) else None,
            "added": float(ad) if pd.notna(ad) else None
        })

gpop = pd.DataFrame(rows)

# Tür bazında medyan ilgi metrikleri (ve örnek sayısı)
agg_pop = (
    gpop.groupby("genre", as_index=False)
        .agg(n=("ratings_count","size"),
             median_ratings=("ratings_count","median"),
             median_added=("added","median"))
        .fillna(0)
)

top_ratings = agg_pop.sort_values("median_ratings", ascending=False).head(15)
top_added   = agg_pop.sort_values("median_added",   ascending=False).head(15)

fig, axes = plt.subplots(1, 2, figsize=(18, 7))

# Sol: ratings_count (medyan)
bars1 = axes[0].barh(top_ratings["genre"][::-1], top_ratings["median_ratings"][::-1])
axes[0].set_title("Türlere Göre Medyan Ratings Count — İlk 15 (Indie hariç)")
axes[0].set_xlabel("Medyan ratings_count")
for b in bars1:
    axes[0].text(b.get_width()*1.01, b.get_y()+b.get_height()/2,
                 f"{b.get_width():.0f}", va="center", fontsize=9)

# Sağ: added (medyan)
bars2 = axes[1].barh(top_added["genre"][::-1], top_added["median_added"][::-1])
axes[1].set_title("Türlere Göre Medyan Added — İlk 15 (Indie hariç)")
axes[1].set_xlabel("Medyan added")
for b in bars2:
    axes[1].text(b.get_width()*1.01, b.get_y()+b.get_height()/2,
                 f"{b.get_width():.0f}", va="center", fontsize=9)

plt.tight_layout()
plt.show()


# ### Commentary — Balance of Success and Player Interest by Genre
# 
# When comparing our analyses, we see that some genres deliver **high quality (Metacritic scores)**, while others attract more **player interest** (ratings count and added).
# 
# - **Platformer & Educational:**  
#   They achieve high success on Metacritic (top averages), yet lag behind in player interest.  
#   → These are **genres loved by critics but struggling to reach broad audiences**.  
# 
# - **Shooter & Card:**  
#   Ranked high both in Metacritic scores and player engagement.  
#   → These genres are strong candidates in terms of **both success and popularity**.  
# 
# - **Massively Multiplayer:**  
#   Metacritic performance is average, but this genre shows the **highest player engagement (added/ratings)**.  
#   → Highly demanded by players, though difficult to achieve high critical scores.  
#   → Big potential, but also highly competitive.  
# 
# - **Family & Action:**  
#   High player engagement, but Metacritic success remains around average.  
#   → These genres may **reach large audiences but face challenges earning high critic scores**.  
# 
# **Takeaway:**  
# - If the priority is **high ratings** (crossing the 84+ threshold): *Card, Shooter, Platformer*.  
# - If the priority is **player interest and broad reach**: *Shooter, Massively Multiplayer, Action*.  
# - For a balanced strategy: **Shooter** stands out, as it scores highly on both metrics.

# ## 3.4 Developer Analysis — Competition and Top-Tier Success
# 
# In addition to a game’s quality, the past performance of its developer is also critical for strategic decisions.  
# Therefore, by examining the developers in our dataset, we evaluate:  
# 
# - **How many games they released** within the Top-5000 sample (competition intensity),  
# - **How many of those games achieved Metacritic ≥ 84** (top-tier success).  
# 
# **Goal:** To **map the competition** and answer the question:  
# “Which studios both release many games and consistently exceed the quality threshold?”

# In[122]:


import pandas as pd
import matplotlib.pyplot as plt
from collections import Counter

THRESH = 84

# 1) Developer'ları explode ederek satırlaştır
rows = []
for _, row in df_final.dropna(subset=["developers", "metacritic_x"]).iterrows():
    for d in row["developers"].split(","):
        dev = d.strip()
        if dev:
            rows.append({"developer": dev, "metacritic": float(row["metacritic_x"])})

devdf = pd.DataFrame(rows)

# 2) Metrikler: toplam oyun sayısı, 84+ sayısı, 84+ oranı
agg = (
    devdf
    .assign(ge84=lambda d: (d["metacritic"] >= THRESH).astype(int))
    .groupby("developer", as_index=False)
    .agg(n_total=("metacritic","size"),
         n_ge84=("ge84","sum"))
)
agg["rate_ge84"] = (agg["n_ge84"] / agg["n_total"] * 100).round(1)

# 3) Görselleştirme: Top 15 (rekabet & elit başarı)
top_by_total = agg.sort_values("n_total", ascending=False).head(15)
top_by_ge84  = agg.sort_values("n_ge84",  ascending=False).head(15)

fig, axes = plt.subplots(1, 2, figsize=(18, 7))

# Sol: en çok oyun çıkaran 15 developer (rekabet yoğunluğu)
bars1 = axes[0].barh(top_by_total["developer"][::-1], top_by_total["n_total"][::-1])
axes[0].set_title("En Çok Oyun Çıkaran 15 Developer (Top-5000 içinde)")
axes[0].set_xlabel("Oyun Sayısı")
for b in bars1:
    axes[0].text(b.get_width()+0.5, b.get_y()+b.get_height()/2, int(b.get_width()), va="center", fontsize=9)

# Sağ: 84+ sayısına göre en güçlü 15 developer (elit başarı)
bars2 = axes[1].barh(top_by_ge84["developer"][::-1], top_by_ge84["n_ge84"][::-1])
axes[1].set_title(f"Metacritic ≥ {THRESH} Alan Oyun Sayısı — İlk 15 Developer")
axes[1].set_xlabel("84+ Oyun Sayısı")
for b in bars2:
    axes[1].text(b.get_width()+0.3, b.get_y()+b.get_height()/2, int(b.get_width()), va="center", fontsize=9)

plt.tight_layout()
plt.show()


# ### Commentary — Developer Competition and Timing
# 
# The chart on the left shows the studios with the **most games released** within the Top-5000 sample (overall production power).  
# The chart on the right ranks studios by the **number of games scoring Metacritic ≥ 84** (top-tier success).
# 
# **Interpretation:**
# - **Nintendo, Sony Interactive Entertainment, and Square Enix** appear at the top of both lists. These studios not only produce **frequently** but also have the capacity to deliver **highly rated** games.  
# - Therefore, releasing our game during the same window as their major launches could **negatively impact visibility**.  
#   > Strategy: Target a **relatively quiet release window** that avoids overlapping with major Nintendo/Sony launches.
# 
# **Note:** This analysis is based on the Top-5000 sample (ranked by Metacritic) and thus represents the **upper-quality segment** rather than the entire market. Still, it provides a strong signal for making “noise-free timing” decisions.
# 
# **Takeaway:** For a game aiming at the 84+ threshold, avoiding periods of heavy competition and choosing a **quieter release window** can improve visibility and increase both press and player attention.
# 
# ---
# 
# **Future Analysis:**
# 
# Nintendo, Sony Interactive Entertainment, and Square Enix dominate both lists. These studios release games frequently and have strong capacity for high-scoring titles.  
# 
# Nintendo’s unique success: In the left chart, Nintendo is on par with competitors (Sony, Square Enix, EA, Ubisoft, Capcom) in terms of total game production. Yet in the right chart, Nintendo nearly **doubles its rivals** in the number of 84+ games.  
# Moreover, Nintendo’s approach to design and development (with its strong focus on quality) offers a valuable model worth studying.  
# 
# > 🔮 **Future Analysis Note:** The factors behind Nintendo’s ability to consistently surpass the 84+ barrier could be examined in detail later. Insights from such an analysis may directly inform strategies when developing a new game.

# ## 3.5 — Monthly Release Density of 84+ Games for the Top 3 Developers
# 
# The chart shows, regardless of year, **which months saw the highest concentration of 84+ game releases** for **Nintendo, Sony Interactive Entertainment, and Square Enix**.
# 
# **Key findings:**
# - **Nintendo:** Peaks in November. Strong holiday-season launches stand out. July also shows high density.  
# - **Sony Interactive Entertainment:** Has the most balanced distribution, with release density increasing especially in **March–April** and **September–November**.  
# - **Square Enix:** Stands out in March and July, indicating important mid-summer launches.  
# 
# **Strategic takeaway:**  
# - November and December are the most competitive months due to major studio launches.  
# - For smaller or mid-scale games, it may be more advantageous to **avoid these crowded months** and instead target quieter windows (e.g., May, June, August).  
# 
# > 🔮 **Future Analysis Note:** This analysis is limited to the “top 3 developers.” In the future, other major studios (Ubisoft, Capcom, EA) could be included to build a broader **“release timing competition map.”**

# In[69]:


import calendar
import matplotlib.pyplot as plt

# Ay numarasını çıkar
m = (df_top3
     .assign(month=lambda d: d["year_month"].dt.month)
     .groupby(["developer","month"]).size()
     .reset_index(name="count"))

fig, ax = plt.subplots(figsize=(14,6))
for dev in top3:
    s = m[m["developer"] == dev].set_index("month")["count"].reindex(range(1,13), fill_value=0)
    ax.plot(range(1,13), s.values, marker="o", label=dev)

ax.set_title("İlk 3 Developer — Ay Bazında 84+ Çıkış Yoğunluğu (Yıllardan Bağımsız)")
ax.set_xlabel("Ay")
ax.set_ylabel("84+ Oyun Sayısı")
ax.set_xticks(range(1,13))
ax.set_xticklabels(list(calendar.month_abbr)[1:])  # Jan, Feb, ...

ax.legend(bbox_to_anchor=(1.02,1), loc="upper left")
plt.tight_layout()
plt.show()


# ## 3.6 Publisher Analizi — Partnerlik Fırsatları (Hacim vs. 84+ Başarı)
# 
# Indie bir geliştirici için doğru **publisher** ile ortaklık; görünürlük, platform ilişkileri ve pazarlama gücü açısından kritik olabilir.  
# Bu bölümde publisher’ları iki metrikle yan yana inceliyoruz:
# 
# - **Hacim (Top-5000 içinde çıkardıkları oyun sayısı)** → ağ genişliği / dağıtım gücü
# - **Başarı (Metacritic ≥ 84 alan oyun sayısı)** → üst düzey kaliteyi pazara çıkarma kapasitesi
# 
# Amaç:  
# - “Çok oyun çıkarıp 84+’ı düşük olan” publisher’lar → **yüksek hacim, daha erişilebilir partner** (niş ama fırsat).  
# - “Hem hacmi hem 84+’ı yüksek” publisher’lar → **güçlü ama rekabetçi partner**.  
# - “Hacmi düşük ama 84+’ı yüksek” publisher’lar → **seçici, prestijli niş partner**.
# 
# > Not: Bu analiz Top-5000 (Metacritic’e göre sıralı) örneklemi temel alır; pazarın tamamını değil, üst kalite kesitini temsil eder.

# In[123]:


import pandas as pd
import matplotlib.pyplot as plt

THRESH = 84

# 1) Publisher'ları explode ederek tablo oluştur
rows = []
src = df_final.dropna(subset=["publishers", "metacritic_x"])
for _, row in src.iterrows():
    score = float(row["metacritic_x"])
    for p in row["publishers"].split(","):
        pub = p.strip()
        if pub:
            rows.append({"publisher": pub, "metacritic": score})

pubdf = pd.DataFrame(rows)

# 2) Hacim (n_total), 84+ sayısı (n_ge84), oran
agg_pub = (
    pubdf
    .assign(ge84=lambda d: (d["metacritic"] >= THRESH).astype(int))
    .groupby("publisher", as_index=False)
    .agg(n_total=("metacritic", "size"),
         n_ge84=("ge84", "sum"))
)
agg_pub["rate_ge84"] = (agg_pub["n_ge84"] / agg_pub["n_total"] * 100).round(1)

# 3) Görselleştirme — Top 15 (hacim ve 84+ sayısı)
top_total = agg_pub.sort_values("n_total", ascending=False).head(15)
top_ge84  = agg_pub.sort_values("n_ge84",  ascending=False).head(15)

fig, axes = plt.subplots(1, 2, figsize=(18, 7))

# Sol: En çok oyun çıkaran 15 publisher
bars1 = axes[0].barh(top_total["publisher"][::-1], top_total["n_total"][::-1])
axes[0].set_title("En Çok Oyun Çıkaran 15 Publisher (Top-5000 içinde)")
axes[0].set_xlabel("Oyun Sayısı")
for b in bars1:
    axes[0].text(b.get_width()+0.5, b.get_y()+b.get_height()/2,
                 int(b.get_width()), va="center", fontsize=9)

# Sağ: Metacritic ≥ 84 alan oyun sayısına göre 15 publisher
bars2 = axes[1].barh(top_ge84["publisher"][::-1], top_ge84["n_ge84"][::-1])
axes[1].set_title(f"Metacritic ≥ {THRESH} Alan Oyun Sayısı — İlk 15 Publisher")
axes[1].set_xlabel("84+ Oyun Sayısı")
for b in bars2:
    axes[1].text(b.get_width()+0.3, b.get_y()+b.get_height()/2,
                 int(b.get_width()), va="center", fontsize=9)

plt.tight_layout()
plt.show()


# In[128]:


# Publisher bazında toplam oyun ve 84+ oyun sayısı + oran
pub_stats = (
    df_final.groupby("publishers")
    .agg(
        total_games=("rawg_id", "count"),
        high84_games=("rawg_id", lambda idx: (df_final.loc[idx.index, "metacritic_x"] >= 84).sum())
    )
    .reset_index()
)

# Oran (%)
pub_stats["high84_ratio"] = (pub_stats["high84_games"] / pub_stats["total_games"] * 100).round(1)

# En çok oyun çıkaran 15 publisher
top15_publishers = (
    pub_stats.sort_values("total_games", ascending=False)
    .head(15)
    .reset_index(drop=True)
)

# --- 40 barajına göre renklendirme ---
def highlight_groups_40(row):
    # 🟥 Yüksek hacim & düşük başarı
    if row["total_games"] > 100 and row["high84_ratio"] < 40:
        return ["background-color: #fdd"] * len(row)      # kırmızımsı
    # 🟩 Yüksek hacim & yüksek başarı
    elif row["total_games"] > 100 and row["high84_ratio"] >= 40:
        return ["background-color: #dfd"] * len(row)      # yeşilimsi
    # 🟦 Düşük hacim & yüksek başarı
    elif row["total_games"] <= 100 and row["high84_ratio"] >= 40:
        return ["background-color: #ddf"] * len(row)      # mavimsi
    # ⚪ Düşük hacim & düşük başarı
    else:
        return ["background-color: #eee"] * len(row)      # gri

styled = top15_publishers.style.apply(highlight_groups_40, axis=1)
styled


# ### Yorum — Publisher Analizi (40% Başarı Barajı ile)
# 
# Tablo, **publisher’ların çıkardıkları toplam oyun sayısı**, bunlardan **kaçının Metacritic ≥ 84 aldığı** ve oranlarını göstermektedir.  
# Renkler üç farklı stratejik grubu ifade etmektedir:  
# 
# - 🟩 **Yüksek hacim & yüksek başarı**  
#   - Örnek: **Nintendo (46.8%)**, **Sony Computer Entertainment (42.6%)**  
#   - Çok sayıda oyun çıkarıp aynı zamanda yüksek başarı oranına ulaşabiliyorlar.  
#   - Bu firmalarla partnerlik yapmak **prestijli ama zorlayıcı** olabilir; rekabet yüksek, kabul süreçleri seçici.  
# 
# - 🟥 **Yüksek hacim & düşük başarı**  
#   - Örnek: **Electronic Arts (30.4%)**, **Ubisoft (20.4%)**, **SEGA (24.8%)**, **Capcom (28.8%)**, **Square Enix (28.7%)**  
#   - Çok sayıda oyun çıkarıyorlar ancak 84+ oranı görece düşük.  
#   - Indie geliştiriciler için **erişilebilir partnerlik fırsatları** sunabilir; oyun kalabalık havuzda kaybolma riski taşıyabilir ama yayıncı desteği daha ulaşılabilir.  
# 
# - 🟦 **Düşük hacim & yüksek başarı**  
#   - Örnek: **Microsoft Studios (42.4%)**  
#   - Daha az oyun çıkarıyorlar ancak başarı oranı yüksek.  
#   - Partnerlik daha **niş ve seçici**, fakat **yüksek prestij** potansiyeli taşıyor.  
# 
# - ⚪ **Düşük hacim & düşük başarı**  
#   - Örnek: **Bandai Namco Entertainment, Atlus, Devolver Digital, Warner Bros. Interactive**  
#   - Oran da hacim de düşük.  
#   - Partnerlik halinde büyük bir prestij sağlamaz ama belirli niş pazarlarda faydalı olabilir.  
# 
# ---
# 
# ### Çıkarım — Indie Geliştirici için Partnerlik
# - Eğer **yüksek görünürlük ve prestij** hedefleniyorsa → 🟩 grubundaki publisher’lar tercih edilmeli.  
# - Eğer **erişilebilirlik ve hızlı partnerlik** öncelikliyse → 🟥 grubundaki publisher’lar daha mantıklı olabilir.  
# - Uzun vadede ise 🟦 grubundaki az ama başarılı publisher’lar, **kalite odaklı çıkış** için kritik fırsatlar sunabilir.  
# 
# 👉 Bu analiz, indie geliştiricinin **hangi publisher tipi ile iş birliği yapmasının stratejik olarak uygun olacağını** netleştirmeyi amaçlıyor.  

# ## 3.7. Store Analizi — Oyunların Çıkış Yaptığı Platformlar
# 
# Publisher analizinden sonra şimdi odağımızı **oyunların hangi dijital mağazalarda (store) yayınlandığına** çeviriyoruz.  
# Amacımız, indie bir geliştirici olarak oyunumuzu çıkarmak için **en doğru mağaza partnerini** seçmek.
# 
# ### Analiz Adımları:
# 1. Her store’da toplam kaç oyun yayınlanmış?  
# 2. Bu oyunlardan kaç tanesi **Metacritic ≥ 84** barajını aşmış?  
# 3. Oranları karşılaştırarak hangi store’ların **prestijli ama zorlayıcı**, hangilerinin **erişilebilir ama rekabetçi** olduğunu belirlemek.  
# 
# Bu analiz, indie bir oyun için doğru mağaza seçimi stratejisine ışık tutacaktır.
# 

# In[85]:


import matplotlib.pyplot as plt

# İlk 10 store (hacme göre)
top_stores = df_store_stats.head(10)

fig, axes = plt.subplots(1, 2, figsize=(18, 7))

# Sol grafik — toplam oyun sayısı
bars1 = axes[0].barh(top_stores["store"][::-1], top_stores["total_games"][::-1])
axes[0].set_title("En Çok Oyun Yayınlanan 10 Store (Top-5000 içinde)")
axes[0].set_xlabel("Oyun Sayısı")
for b in bars1:
    axes[0].text(b.get_width()+5, b.get_y()+b.get_height()/2,
                 int(b.get_width()), va="center", fontsize=9)

# Sağ grafik — 84+ oyun sayısı
bars2 = axes[1].barh(top_stores["store"][::-1], top_stores["high84_games"][::-1])
axes[1].set_title("Metacritic ≥ 84 Alan Oyun Sayısı — İlk 10 Store")
axes[1].set_xlabel("84+ Oyun Sayısı")
for b in bars2:
    axes[1].text(b.get_width()+1, b.get_y()+b.get_height()/2,
                 int(b.get_width()), va="center", fontsize=9)

plt.tight_layout()
plt.show()


# In[125]:


from collections import Counter
import pandas as pd

# --- Mapping: farklı isimleri ortak gruba çevir ---
store_mapping = {
    "Xbox 360 Store": "Xbox Store",
    "Xbox One Store": "Xbox Store",
    "Xbox Series S/X Store": "Xbox Store",
    "PlayStation 3 Store": "PlayStation Store",
    "PlayStation 4 Store": "PlayStation Store",
    "PlayStation 5 Store": "PlayStation Store"
}

def normalize_store(name):
    return store_mapping.get(name, name)

# --- 1) Tüm oyunlarda store sayıları ---
all_stores = []
for s in df_final["stores"].dropna():
    for st in s.split(","):
        all_stores.append(normalize_store(st.strip()))

store_counts_all = Counter(all_stores)
df_stores_all = pd.DataFrame(store_counts_all.items(), columns=["store", "total_games"])

# --- 2) Sadece 84+ oyunlar ---
all_stores_84 = []
for s in df_final.loc[df_final["metacritic_x"] >= 84, "stores"].dropna():
    for st in s.split(","):
        all_stores_84.append(normalize_store(st.strip()))

store_counts_84 = Counter(all_stores_84)
df_stores_84 = pd.DataFrame(store_counts_84.items(), columns=["store", "high84_games"])

# --- 3) Birleştir ve oran hesapla ---
df_store_stats = (
    df_stores_all.merge(df_stores_84, on="store", how="left")
    .fillna(0)
    .assign(
        high84_games=lambda d: d["high84_games"].astype(int),
        high84_ratio=lambda d: (d["high84_games"] / d["total_games"] * 100).round(1)
    )
    .sort_values("total_games", ascending=False)
    .reset_index(drop=True)
)

# --- 4) İlk 10 store'u tablo olarak göster ---
top10_stores = df_store_stats.head(10).reset_index(drop=True)
top10_stores


# ### Yorum — Store Seçimi ve Portlama Stratejisi  
# 
# **Tablodan öne çıkanlar:**  
# - **Steam (3054 oyun, %17.9)**: En geniş oyun kütüphanesine sahip, indie oyunların ilk çıkış noktası. Ancak 84+ oranı görece düşük; kalabalık ortamda kaybolma riski yüksek.  
# - **PlayStation Store (1965 oyun, %20.6)**: Daha seçici bir ortam, kalite oranı Steam’den daha iyi. Ancak portlama iş yükü yüksek, sertifikasyon süreçleri uzun.  
# - **Xbox Store (1884 oyun, %23.3)**: 84+ oranı güçlü, özellikle Game Pass entegrasyonu görünürlük sağlar. Portlama iş yükü PlayStation’a benzer ama partnerlik fırsatları daha esnek.  
# - **Nintendo Store (1269 oyun, %22.8)**: Özellikle indie platformer/metroidvania türleri için en uygun pazar. 84+ oranı yüksek, kitlesi sadık. Portlama orta zorlukta ama getirisi tür uyumuna göre çok yüksek.  
# - **GOG (1265 oyun, %16.7)**: DRM’siz yapısı ve sadık PC oyuncusu kitlesi var. Ancak 84+ oranı düşük, satış hacmi sınırlı.  
# - **App Store & Google Play (%25 civarı)**: Yüksek kalite oranı göze çarpıyor, fakat tamamen farklı iş modeli (F2P, mikro ödemeler). Oyunun türüne göre uygun olmayabilir.  
# - **Epic Games (%20.9)**: Daha küçük kütüphane ama düşük komisyon (%12). Özellikle indie için cazip. Görünürlük fırsatı Epic anlaşmalarına bağlı.  
# - **itch.io (%20.5)**: En düşük oyun sayısına sahip. Gelir küçük ama geliştirici özgürlüğü yüksek; topluluk bazlı test için uygun.  
# 
# ---
# 
# ### Çıkarım  
# - **Başlangıç noktası (low risk, high reach):** Steam + Epic Games → düşük iş yükü, geniş erişim.  
# - **İkinci dalga (prestij + tür uyumu):** Nintendo Store → metroidvania/platformer gibi türlerde stratejik avantaj.  
# - **Stratejik partnerlik:** Xbox Store (Game Pass anlaşmaları) → yüksek görünürlük sağlar.  
# - **Uzun vadeli hedef:** PlayStation Store → prestijli ama yüksek portlama maliyeti nedeniyle publisher desteği ile düşünülmeli.  
# 
# ---
# 
# 📌 **Özet:**  
# İş yükü / getiriyi dengelemek için, **önce PC (Steam/Epic)** çıkışı → sonra **Nintendo veya Xbox** → en son **PlayStation (publisher partnerliğiyle)** doğru sıralama olacaktır.  
# 

# ## Sonuç ve Öneriler (Özet)
# 
# **Veri kaynağı:** RAWG API – 5.000 oyun (en yüksek Metacritic sıralı).  
# **Filtre / hedef:** 84+ puan barajı (üst segment kalite sinyali).
# 
# ### 1) Zaman Dinamikleri
# - Ortalama Metacritic zaman serisi pandemi sonrası (2020→) toparlanma gösterdi, ancak **84+ oyun sayısı 2016–2017 zirvesinden sonra azaldı.**
# - Yorum: Pazarda **üst segment yoğunluk azalmış**, bu da kaliteli bir oyunun daha görünür olmasına fırsat tanıyor.
# 
# ### 2) Türler (Kalite vs İlgi)
# - **Kalite (84+ oranı / ortalama puan):** **Card, Platformer, Shooter** üst sıralarda.
# - **İlgi (ratings_count & added medyanı):** **Shooter** ve **Massively Multiplayer** çok yüksek; **Card** da üstte.
# - **Denge:** **Shooter** hem kalite hem ilgi tarafında güçlü; **Platformer** kaliteli ama ilgi daha düşük; **Card** iki tarafta da iyi.
# - Öneri: Kaynak kısıtlıysa **Shooter (veya Card)** odağı; daha niş ama prestij hedefliyorsak **Platformer**.
# 
# ### 3) Developer Rekabeti
# - Top üretken stüdyolar ile 84+ çıkaranlar ayrışıyor.  
# - **Nintendo** hem hacim hem 84+’ta zirvede → aynı tarihlere **çıkış çakışmasından kaçın**.  
# - Gelecek çalışma (opsiyonel): Nintendo’nun pattern’leri (takvim/pazarlama/seri yönetimi) incelenip best practice çıkarımı.
# 
# ### 4) Publisher Değerlendirmesi (40% barajıyla segmentasyon)
# - **Yüksek hacim + yüksek başarı (yeşil):** Nintendo, Sony Computer Entertainment vb. → **güçlü ama rekabetçi partner**.
# - **Yüksek hacim + daha düşük başarı (kırmızı):** Ubisoft Ent., SEGA, Capcom vb. → **erişilebilirlik daha yüksek**; doğru proje ile öne çıkma şansı.
# - **Düşük hacim + yüksek başarı (mavi):** Microsoft Studios vb. → **seçici, prestijli niş partner**.
# 
# ### 5) Store Stratejisi (portlama iş yükü dahil)
# - **Başlangıç (low risk / high reach):** **Steam + Epic** (Epic’in %12 komisyon avantajı).  
# - **İkinci dalga (prestij + tür uyumu):** **Nintendo eShop** (özellikle platformer/metroidvania) veya **Xbox (Game Pass)**.  
# - **Uzun vadeli hedef:** **PlayStation Store** (yüksek sertifikasyon/iş yükü → publisher partnerliği ile).  
# - Verisetinde 84+ oranları: Steam %17.9, PS %20.6, Xbox %23.3, Nintendo %22.8, Epic %20.9.
# 
# ### 6) Takvim ve Çıkış
# - Rekabetten kaçınmak için **Nintendo / Sony büyük lansman dönemlerinden kaçın** (önceki grafikteki yoğun aylara bak).  
# - 84+ hedefi için **QA / playtest / demo (Steam Next Fest)** planı kritik.
# 
# ---
# 
# ## Yol Haritası (yapılabilir adımlar)
# 1. **Tür kararı:** Shooter ↔ Card (alternatif: prestij için Platformer).  
# 2. **Hedef metrik:** Metacritic **84+** → tasarım/QA bütçesi ve milestone’ları buna göre ayarla.  
# 3. **Çıkış sırası:** Steam → Epic → (uygunsa) Nintendo / Xbox → PlayStation (publisher ile).  
# 4. **Zamanlama:** Büyük Nintendo/Sony pencerelerinden kaçın; demo + wishlists kampanyası.  
# 5. **Publisher görüşmeleri:** Segment tablomuza göre 2–3 aday listele, vertical fit + referans case iste.  
# 6. **Ek analiz (opsiyonel):** Seçilen tür için **store bazlı performans** (ör. Shooter’ın Switch/PS/Xbox/PC dağılımı) ve **fiyatlandırma/indirim etkisi**.
# 
# ### Sınırlamalar
# - Örneklem top-5000 (Metacritic’e göre) → pazarın tamamını temsil etmeyebilir.  
# - RAWG “genres” alanı heterojen (ör. “Indie” hariç tutularak düzeltildi).  
# - 2024–2025 verileri **erken yıl etkisi** nedeniyle eksik olabilir.
# 
# **Kısa özet:**  
# Kaliteyi (84+) hedefleyen ve popülerlik potansiyeli yüksek, **Shooter/Card** gibi bir türle; **Steam/Epic** çıkışı + **Nintendo/Xbox** ikinci dalga; **PlayStation** publisher’la. Büyük stüdyo lansmanlarından kaçınarak, demo/wishlist stratejisiyle görünürlüğü artır.
# 

# ---
# 
# ## 🎮 Meraklısına — Unutulmazlar
# 
# Her raporun sonunda, oyun dünyasının “zamansız klasikleri”ne de bir selam olsun.  
# Aşağıda **Metacritic puanı 95+ olan oyunlar** listelenmiştir.  
# 
# Bu bölüm analizin bir parçası olmaktan ziyade, **oyun tutkusunu hatırlatmak için** eklenmiştir.  
# Çünkü rakamlar ve istatistikler yolumuzu aydınlatsa da, **oyun geliştirme en nihayetinde bir tutku işidir.**
# 
# ---
# 

# In[99]:


# 95+ oyunları filtrele
top95_games = df_final[df_final["metacritic_x"] >= 95]

# İlgili kolonları seç ve sıralamayı puana göre yap
top95_games = top95_games[["released", "name", "developers", "publishers", "metacritic_x"]] \
    .sort_values("metacritic_x", ascending=False)

# Yılı ayrı bir kolon olarak ekle
top95_games["year"] = top95_games["released"].dt.year

# Kolonları yeniden sırala
top95_games = top95_games[["year", "name", "developers", "publishers", "metacritic_x"]]

# Sonuçları göster
top95_games

