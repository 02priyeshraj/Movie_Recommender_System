import pickle
import streamlit as st
import requests
import os
import gdown
from dotenv import load_dotenv

# -------------------------------
# Load environment variables
# -------------------------------
# Load .env locally (Streamlit Cloud will just skip if no file)
if os.path.exists(".env"):
    load_dotenv()

# Prefer .env (local) else fallback to Streamlit Secrets
TMDB_API_KEY = os.getenv("TMDB_API_KEY") or st.secrets.get("TMDB_API_KEY")

if not TMDB_API_KEY:
    st.error("❌ TMDB_API_KEY not found in either .env or Streamlit Secrets.")
    st.stop()

# -------------------------------
# File Config
# -------------------------------
MOVIE_LIST_PATH = "movie_list.pkl"
SIMILARITY_PATH = "similarity.pkl"

# Direct Google Drive links (converted from your shared links)
MOVIE_LIST_URL = "https://drive.google.com/uc?id=1aCq5M2VGk4nV3l41U-8nOtyitnUVv9He"
SIMILARITY_URL = "https://drive.google.com/uc?id=1iGnGesL-2wSPB4bQstgYoVR944-aZiUS"

# -------------------------------
# Ensure required data files exist
# -------------------------------
def download_data():
    """Download .pkl files if they don't exist"""
    os.makedirs(".", exist_ok=True)

    if not os.path.exists(MOVIE_LIST_PATH):
        with st.spinner("📦 Downloading movie_list.pkl (first time only)..."):
            gdown.download(MOVIE_LIST_URL, MOVIE_LIST_PATH, quiet=False)
        st.success("✅ movie_list.pkl downloaded!")

    if not os.path.exists(SIMILARITY_PATH):
        with st.spinner("📦 Downloading similarity.pkl (first time only)..."):
            gdown.download(SIMILARITY_URL, SIMILARITY_PATH, quiet=False)
        st.success("✅ similarity.pkl downloaded!")

# -------------------------------
# Data Loader (cached)
# -------------------------------
@st.cache_resource
def load_data():
    """Load pickled data and ensure correct format"""
    download_data()
    movies = pickle.load(open(MOVIE_LIST_PATH, "rb"))
    similarity = pickle.load(open(SIMILARITY_PATH, "rb"))

    # ✅ Ensure movies is a DataFrame
    import pandas as pd
    if not isinstance(movies, pd.DataFrame):
        try:
            movies = pd.DataFrame(movies)
        except Exception as e:
            st.error(f"❌ Could not convert movies.pkl to DataFrame: {e}")
            st.stop()

    # ✅ Ensure columns are correct
    expected_cols = {"movie_id", "title", "tags"}
    if not expected_cols.issubset(set(movies.columns)):
        st.warning(f"⚠️ Unexpected columns found: {movies.columns.tolist()}")
    return movies, similarity


# -------------------------------
# Function to fetch movie poster
# -------------------------------
def fetch_poster(movie_id):
    url = f"https://api.themoviedb.org/3/movie/{movie_id}?api_key={TMDB_API_KEY}&language=en-US"
    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        data = response.json()
        poster_path = data.get("poster_path")
        if poster_path:
            return f"https://image.tmdb.org/t/p/w500/{poster_path}"
    except Exception:
        return None
    return None

# -------------------------------
# Recommendation Function
# -------------------------------
def recommend(movie, movies, similarity):
    index = movies[movies["title"] == movie].index[0]
    distances = sorted(list(enumerate(similarity[index])), reverse=True, key=lambda x: x[1])

    recommended_movie_names = []
    recommended_movie_posters = []

    for i in distances[1:30]:  # Fetch more to ensure valid posters
        movie_id = movies.iloc[i[0]].movie_id
        poster_url = fetch_poster(movie_id)
        if poster_url:
            recommended_movie_posters.append(poster_url)
            recommended_movie_names.append(movies.iloc[i[0]].title)
        if len(recommended_movie_names) >= 9:
            break

    return recommended_movie_names, recommended_movie_posters

# -------------------------------
# Streamlit UI Config
# -------------------------------
st.set_page_config(page_title="Movie Recommender 🎬", layout="wide")

# Custom Styling
st.markdown(
    """
    <style>
    body {
        background-color: #0d0d0d;
        color: #ffffff;
    }
    .main {
        background-color: #111111;
        padding: 20px;
        border-radius: 12px;
    }
    h1 {
        text-align: center;
        color: #ffcc00;
        font-family: 'Trebuchet MS', sans-serif;
    }
    .stSelectbox label {
        font-size: 18px;
        font-weight: bold;
        color: #ffcc00;
    }
    .movie-title {
        text-align: center;
        font-size: 16px;
        font-weight: 600;
        color: #ffffff;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# -------------------------------
# Header
# -------------------------------
st.markdown("<h1>🎬 Movie Recommender System</h1>", unsafe_allow_html=True)

# -------------------------------
# Load Data
# -------------------------------
movies, similarity = load_data()


# -------------------------------
# Dropdown & Recommendation UI
# -------------------------------
movie_list = movies["title"].values
selected_movie = st.selectbox("🎥 Select a Movie:", movie_list)

if st.button("🔍 Show Recommendation"):
    recommended_movie_names, recommended_movie_posters = recommend(selected_movie, movies, similarity)

    st.markdown("## 🍿 Recommended Movies for You")
    st.write("---")

    for i in range(0, len(recommended_movie_names), 3):
        cols = st.columns(3, gap="large")
        for j in range(3):
            if i + j < len(recommended_movie_names):
                with cols[j]:
                    st.image(
                        recommended_movie_posters[i + j],
                        use_container_width=True,
                        caption=f"⭐ {recommended_movie_names[i + j]}"
                    )
