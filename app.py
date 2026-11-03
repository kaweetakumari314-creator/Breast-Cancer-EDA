"""Interactive dashboard for the Breast Cancer EDA project."""
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(page_title="Breast Cancer EDA Dashboard", page_icon="🩺", layout="wide")

# Consistent palette used across the dashboard.
COLORS = {"Alive": "#168C83", "Dead": "#D95757", "Positive": "#168C83", "Negative": "#8B79C6"}
EXPECTED_COLUMNS = [
    "Age", "Race", "Marital Status", "T Stage", "N Stage", "6th Stage",
    "differentiate", "Grade", "A Stage", "Tumor Size", "Estrogen Status",
    "Progesterone Status", "Regional Node Examined", "Reginol Node Positive",
    "Survival Months", "Status",
]

st.markdown("""
<style>
.block-container {padding-top: 1.5rem; padding-bottom: 2rem;}
[data-testid="stMetric"] {background:#f4f7fb; border:1px solid #e5eaf2; padding:16px 18px; border-radius:14px;}
[data-testid="stMetricLabel"] {color:#526174;}
[data-testid="stMetricValue"] {color:#15253b;}
</style>
""", unsafe_allow_html=True)


def find_dataset():
    """Look for the project's CSV beside this app or in its subfolders."""
    base = Path(__file__).resolve().parent
    preferred = [base / "Breast_Cancer.csv", base / "Breast_cancer.csv"]
    for path in preferred:
        if path.exists():
            return path
    candidates = sorted(p for p in base.rglob("*.csv") if p.name.lower() == "breast_cancer.csv")
    if candidates:
        return candidates[0]
    candidates = sorted(base.rglob("*.csv"))
    return candidates[0] if len(candidates) == 1 else None


def load_data(uploaded_file):
    """Read the real project CSV and check that it matches the notebook schema."""
    if uploaded_file is not None:
        data = pd.read_csv(uploaded_file)
    else:
        path = find_dataset()
        if path is None:
            return None, None
        data = pd.read_csv(path)
    data.columns = data.columns.str.strip()
    missing = [column for column in EXPECTED_COLUMNS if column not in data.columns]
    if missing:
        st.error("The selected CSV does not match the notebook's columns. Missing: " + ", ".join(missing))
        st.stop()
    # The notebook removes duplicate records before its main analysis.
    data = data.drop_duplicates().copy()
    for column in ["Age", "Tumor Size", "Regional Node Examined", "Reginol Node Positive", "Survival Months", "Grade"]:
        data[column] = pd.to_numeric(data[column], errors="coerce")
    data = data.dropna(subset=["Age", "Tumor Size", "Regional Node Examined", "Reginol Node Positive", "Survival Months"])
    data["Age Group"] = pd.cut(
        data["Age"], bins=[0, 39, 49, 59, 69, float("inf")],
        labels=["Under 40", "40–49", "50–59", "60–69", "70+"],
    )
    return data, path if uploaded_file is None else None


st.sidebar.title("🩺 Breast Cancer EDA")
st.sidebar.caption("Interactive view of the analysis in your notebook")
upload = st.sidebar.file_uploader("Use project CSV (optional upload)", type="csv")
df, dataset_path = load_data(upload)
if df is None:
    st.title("Breast Cancer EDA Dashboard")
    st.warning("I couldn't find the dataset CSV. The notebook references `/content/Breast_Cancer.csv`, but its saved outputs contain previews only.")
    st.markdown("Place the original **Breast_Cancer.csv** beside `app.py` (or inside this project folder), or upload it above. The file must contain the same 16 columns used by the notebook.")
    st.stop()

st.sidebar.caption(f"Loaded {len(df):,} unique patient records" + (f" · {dataset_path.name}" if dataset_path else " · uploaded CSV"))
if st.sidebar.button("Reset filters", use_container_width=True):
    st.session_state["age_filter"] = (int(df["Age"].min()), int(df["Age"].max()))
    for key in ["race_filter", "marital_filter", "stage_filter", "grade_filter", "estrogen_filter", "progesterone_filter", "status_filter"]:
        st.session_state[key] = []
    st.rerun()

st.sidebar.subheader("Filters")
age_min, age_max = int(df["Age"].min()), int(df["Age"].max())
if "age_filter" not in st.session_state:
    st.session_state["age_filter"] = (age_min, age_max)
age_range = st.sidebar.slider("Age", age_min, age_max, key="age_filter")

def multi_filter(label, column, key):
    values = sorted(df[column].dropna().astype(str).unique().tolist())
    return st.sidebar.multiselect(label, values, default=[], key=key, help="Leave empty to include all values.")

races = multi_filter("Race", "Race", "race_filter")
marital = multi_filter("Marital Status", "Marital Status", "marital_filter")
stages = multi_filter("Cancer Stage (6th Stage)", "6th Stage", "stage_filter")
grades = multi_filter("Grade", "Grade", "grade_filter")
estrogen = multi_filter("Estrogen Status", "Estrogen Status", "estrogen_filter")
progesterone = multi_filter("Progesterone Status", "Progesterone Status", "progesterone_filter")
statuses = multi_filter("Survival Status", "Status", "status_filter")

filtered = df[df["Age"].between(age_range[0], age_range[1])].copy()
for column, selected in [("Race", races), ("Marital Status", marital), ("6th Stage", stages), ("Grade", grades), ("Estrogen Status", estrogen), ("Progesterone Status", progesterone), ("Status", statuses)]:
    if selected:
        filtered = filtered[filtered[column].astype(str).isin(selected)]

st.title("Breast Cancer Patient Analysis")
st.caption("A filtered, interactive dashboard based on the dataset and analysis in your EDA notebook.")
if filtered.empty:
    st.info("No patients match the selected filters. Adjust the sidebar filters to see results.")
    st.stop()

pages = ["Overview", "Patient Demographics", "Cancer Stage", "Tumor Analysis", "Survival Analysis", "Bivariate & Multivariate"]
page = st.sidebar.radio("Navigate", pages, label_visibility="collapsed")


def chart(fig, height=390):
    fig.update_layout(height=height, margin=dict(l=12, r=12, t=55, b=12), template="plotly_white", font=dict(family="Arial", color="#26364a"))
    st.plotly_chart(fig, use_container_width=True)


def count_bar(column, title, horizontal=False):
    counts = filtered[column].astype(str).value_counts().rename_axis(column).reset_index(name="Patients")
    fig = px.bar(counts, x="Patients" if horizontal else column, y=column if horizontal else "Patients", color=column,
                 title=title, text="Patients", color_discrete_sequence=px.colors.qualitative.Safe)
    if horizontal:
        fig.update_layout(showlegend=False)
    return fig

if page == "Overview":
    st.subheader("At a glance")
    cols = st.columns(6)
    metrics = [
        ("Patients", f"{len(filtered):,}"),
        ("Average age", f"{filtered['Age'].mean():.1f} yrs"),
        ("Avg. tumor size", f"{filtered['Tumor Size'].mean():.1f}"),
        ("Avg. survival", f"{filtered['Survival Months'].mean():.1f} mo"),
        ("Alive", f"{(filtered['Status'] == 'Alive').sum():,}"),
        ("Dead", f"{(filtered['Status'] == 'Dead').sum():,}"),
    ]
    for col, (label, value) in zip(cols, metrics): col.metric(label, value)
    left, right = st.columns(2)
    with left: chart(count_bar("Status", "Survival status"))
    with right: chart(count_bar("6th Stage", "Patients by cancer stage"))
    st.caption("All values reflect the current sidebar filters. Duplicate rows are removed, as in the notebook.")

elif page == "Patient Demographics":
    st.subheader("Who is represented in the dataset?")
    c1, c2 = st.columns(2)
    with c1: chart(px.histogram(filtered, x="Age", nbins=20, color="Status", color_discrete_map=COLORS, title="Age distribution", barmode="overlay", opacity=.78))
    with c2: chart(count_bar("Race", "Race distribution"))
    c3, c4 = st.columns(2)
    with c3: chart(count_bar("Marital Status", "Marital status distribution"))
    with c4:
        age_status = filtered.groupby(["Age Group", "Status"], observed=False).size().reset_index(name="Patients")
        chart(px.bar(age_status, x="Age Group", y="Patients", color="Status", barmode="group", color_discrete_map=COLORS, title="Age groups by survival status"))

elif page == "Cancer Stage":
    st.subheader("Cancer stage profile")
    cols = st.columns(4)
    for col, field, title in zip(cols, ["6th Stage", "T Stage", "N Stage", "A Stage"], ["6th Stage", "T Stage", "N Stage", "A Stage"]):
        with col: chart(count_bar(field, f"{title} distribution"), 340)
    st.markdown("#### Cancer stage versus survival status")
    stage_status = filtered.groupby(["6th Stage", "Status"]).size().reset_index(name="Patients")
    chart(px.bar(stage_status, x="6th Stage", y="Patients", color="Status", barmode="group", color_discrete_map=COLORS, title="Patient counts by stage and status"))

elif page == "Tumor Analysis":
    st.subheader("Tumor size and regional lymph nodes")
    c1, c2 = st.columns(2)
    with c1: chart(px.histogram(filtered, x="Tumor Size", nbins=25, title="Tumor size distribution", labels={"Tumor Size":"Tumor size"}))
    with c2: chart(px.scatter(filtered, x="Tumor Size", y="Survival Months", color="Status", color_discrete_map=COLORS, opacity=.65, hover_data=["Age", "6th Stage", "Grade"], title="Tumor size versus survival months", labels={"Tumor Size":"Tumor size", "Survival Months":"Survival months"}))
    c3, c4 = st.columns(2)
    with c3: chart(px.box(filtered, x="6th Stage", y="Tumor Size", color="6th Stage", points="outliers", title="Tumor size by cancer stage"))
    with c4:
        nodes = filtered[["Regional Node Examined", "Reginol Node Positive"]].melt(var_name="Node measure", value_name="Node count")
        nodes["Node measure"] = nodes["Node measure"].replace({"Regional Node Examined":"Examined", "Reginol Node Positive":"Positive"})
        chart(px.box(nodes, x="Node measure", y="Node count", color="Node measure", title="Regional nodes examined and positive"))

elif page == "Survival Analysis":
    st.subheader("Survival patterns")
    c1, c2 = st.columns(2)
    with c1: chart(px.histogram(filtered, x="Survival Months", nbins=25, color="Status", color_discrete_map=COLORS, barmode="overlay", opacity=.75, title="Survival months distribution"))
    with c2: chart(px.box(filtered, x="6th Stage", y="Survival Months", color="6th Stage", points="outliers", title="Survival months by cancer stage"))
    c3, c4 = st.columns(2)
    with c3: chart(px.box(filtered, x="Age Group", y="Survival Months", color="Age Group", points="outliers", title="Survival months by age group"))
    with c4:
        hormone = filtered.melt(id_vars=["Survival Months"], value_vars=["Estrogen Status", "Progesterone Status"], var_name="Hormone", value_name="Result")
        hormone["Hormone"] = hormone["Hormone"].replace({"Estrogen Status":"Estrogen", "Progesterone Status":"Progesterone"})
        chart(px.box(hormone, x="Hormone", y="Survival Months", color="Result", color_discrete_map=COLORS, title="Survival months by hormone status"))
    chart(count_bar("Status", "Survival status distribution"))

else:
    st.subheader("Explore relationships between patient measures")
    c1, c2 = st.columns(2)
    with c1:
        x_metric = st.selectbox("Scatter plot horizontal axis", ["Age", "Tumor Size", "Regional Node Examined", "Reginol Node Positive", "Survival Months"])
    with c2:
        y_options = [item for item in ["Survival Months", "Tumor Size", "Age", "Regional Node Examined", "Reginol Node Positive"] if item != x_metric]
        y_metric = st.selectbox("Scatter plot vertical axis", y_options)
    chart(px.scatter(filtered, x=x_metric, y=y_metric, color="Status", color_discrete_map=COLORS, opacity=.65, hover_data=["6th Stage", "Grade", "Estrogen Status", "Progesterone Status"], title=f"{x_metric} versus {y_metric}"))
    c3, c4 = st.columns(2)
    with c3: chart(px.box(filtered, x="6th Stage", y="Survival Months", color="Status", color_discrete_map=COLORS, title="Survival months by stage and status"))
    with c4:
        numeric_columns = ["Age", "Tumor Size", "Regional Node Examined", "Reginol Node Positive", "Survival Months"]
        corr = filtered[numeric_columns].corr()
        chart(px.imshow(corr, text_auto=".2f", color_continuous_scale="RdBu_r", zmin=-1, zmax=1, title="Correlation heatmap of patient metrics"))
    st.markdown("#### Average survival by stage and estrogen status")
    pivot = filtered.pivot_table(index="6th Stage", columns="Estrogen Status", values="Survival Months", aggfunc="mean")
    chart(px.imshow(pivot, text_auto=".1f", color_continuous_scale="YlGnBu", aspect="auto", labels=dict(color="Months"), title="Mean survival months"))
    st.markdown("#### Marital status and race")
    demographic_matrix = pd.crosstab(filtered["Marital Status"], filtered["Race"])
    chart(px.imshow(demographic_matrix, text_auto=True, color_continuous_scale="BuPu", aspect="auto", labels=dict(color="Patients"), title="Patient count by marital status and race"))

with st.expander("About the data and notebook coverage"):
    st.write("This dashboard follows the notebook's 16-column Breast Cancer dataset, removes duplicate rows as the notebook does, and recreates its demographic, stage, tumor, survival, hormone-status, and multivariate relationship analyses. The notebook's survival-month outlier-cleaned dataset is retained as a separate notebook analysis; dashboard summaries use the full deduplicated dataset so filters and KPIs describe the same patient set.")
