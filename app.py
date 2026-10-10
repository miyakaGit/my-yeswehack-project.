# app.py
from dataclasses import asdict
import pandas as pd
import streamlit as st

from scraper import PERIODS, collect_period
from analysis import calculate_tier_distribution, make_findings
from visualize import create_tier_chart, create_decay_chart

st.set_page_config(page_title="YesWeHack Ranking Explorer", page_icon="🛡️", layout="wide")

# Custom UI Styling for better readability and underlined links
st.markdown("""
<style>
    .reportview-container { background: #f0f2f6 }
    .stTable, div[data-testid="stDataFrame"] { border-radius: 8px; }
</style>
""", unsafe_allow_html=True)

st.title("🛡️ YesWeHack Ranking Explorer")
st.caption("Data Collection, Tiers Analysis, and Interactive Leaderboard Dashboard (Top 100 Hunters)")

with st.sidebar:
    st.header("Collection Settings")
    selected_periods = st.multiselect("Ranking periods", list(PERIODS), default=["All time", "Q1 2026"])
    # Set default max_pages to 4 to capture 100 researchers (25 per page)
    max_pages = st.slider("Maximum pages per period", 1, 10, 4)
    delay = st.slider("Delay between pages (sec)", 0.5, 3.0, 1.0)
    run = st.button("Collect & Analyze Top 100", type="primary", use_container_width=True)

if "ranking_data" not in st.session_state:
    st.session_state.ranking_data = pd.DataFrame()
    st.session_state.logs = []

if run:
    if not selected_periods:
        st.warning("Please select at least one period.")
    else:
        collected, logs = [], []
        progress = st.progress(0, text="Scraping top 100 leaderboard snapshots...")
        for i, period in enumerate(selected_periods, start=1):
            with st.spinner(f"Fetching {period}..."):
                rows, period_logs = collect_period(period, PERIODS[period], max_pages, delay)
            collected.extend(asdict(row) for row in rows)
            logs.extend(period_logs)
            progress.progress(i / len(selected_periods), text=f"Finished {period}")
        st.session_state.ranking_data = pd.DataFrame(collected)
        st.session_state.logs = logs
        if st.session_state.ranking_data.empty:
            st.error("No ranking rows parsed. Check connection or site structure.")
        else:
            st.success(f"Successfully collected {len(st.session_state.ranking_data):,} records covering up to the Top 100!")

df = st.session_state.ranking_data.copy()
if not df.empty:
    tab1, tab2, tab3, tab4 = st.tabs(["📊 Dashboard", "🏆 Leaderboard Table (Top 100)", "🔎 Key Findings", "📄 Export & Logs"])
    
    with tab1:
        st.subheader("Analytical Visualizations")
        left, right = st.columns(2)
        with left:
            st.markdown("**Point Distribution by Tier (Top 100 Breakdown)**")
            tier_summary = calculate_tier_distribution(df)
            st.plotly_chart(create_tier_chart(tier_summary), use_container_width=True)
        with right:
            st.markdown("**Leaderboard Point Decay Curve**")
            st.plotly_chart(create_decay_chart(df), use_container_width=True)

    with tab2:
        st.subheader("Elite Hunters Leaderboard (Top 100)")
        st.markdown("Hunters with a public profile have clickable alias links. Private profiles display as plain text.")
        
        chosen_period = st.selectbox("Filter by Period", ["All periods"] + list(df["period"].drop_duplicates()))
        display_df = df if chosen_period == "All periods" else df[df["period"] == chosen_period]
        
        # Safe fallback if columns are missing from an older session state
        for col, default_val in [("impact_score", 0.0), ("reports_count", 0)]:
            if col not in display_df.columns:
                display_df[col] = default_val

        table_view = display_df[["rank", "hunter", "points", "impact_score", "reports_count", "profile_url"]].copy()
        
        st.dataframe(
            table_view,
            use_container_width=True,
            hide_index=True,
            column_config={
                "rank": st.column_config.NumberColumn("Rank", format="#%d"),
                "hunter": st.column_config.TextColumn("Hunter Alias"),
                "points": st.column_config.NumberColumn("Points", format="%d pts"),
                "impact_score": st.column_config.NumberColumn("Impact Score", format="%.2f"),
                "reports_count": st.column_config.NumberColumn("Reports", format="%d"),
                "profile_url": st.column_config.LinkColumn("Public Profile", display_text="Open Profile")
            }
        )

    with tab3:
            st.subheader("Insights & Findings")
            for i, finding in enumerate(make_findings(df), 1):
                st.markdown(f"**Observation {i}.** {finding}")
            
            # Simple descriptive text of the statistics (from summary notes)
            st.markdown("---")
            st.markdown("### Key Statistics for the Top 100")
            
            # Calculate these from the dataframe (or pass from analysis.py if available)
            total_points = df['points'].sum()
            top_3_points = df.nlargest(3, 'points')['points'].sum()
            top_3_conc = (top_3_points / total_points) * 100 if total_points > 0 else 0
            mean_val = df['points'].mean()
            median_val = df['points'].median()
            
            st.write(f"- **Total Hunters:** Exactly 100")
            st.write(f"- **Top 3 Points Concentration:** {top_3_conc:.1f}%")
            st.write(f"- **Points Mean (Average):** {mean_val:.2f} pts")
            st.write(f"- **Points Median (Middle):** {median_val:.2f} pts")
            
            st.markdown("---")
            # Keep a limited, point-focused table view of df.describe() for easy reference
            st.markdown("### Detailed Points Summary")
            st.dataframe(df[['points', 'rank']].describe(), use_container_width=True)

    with tab4:
        st.download_button("Download Dataset as CSV", df.to_csv(index=False).encode("utf-8"), "yeswehack_top100_rankings.csv", "text/csv")
        st.subheader("Collection Logs")
        st.code("\n".join(st.session_state.logs) or "No logs available.")
else:
    st.info("👈 Open the sidebar, select your preferred ranking periods, ensure **Maximum pages per period** is set to **4**, and click **Collect & Analyze Top 100**.")