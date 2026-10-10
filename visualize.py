# visualize.py
import plotly.express as px
import pandas as pd

def create_tier_chart(tier_summary: pd.DataFrame):
    fig_tier = px.bar(
        tier_summary, 
        x="tier", 
        y="points", 
        text_auto=True,
        labels={"tier": "Leaderboard Tier", "points": "Total Points"}
    )
    return fig_tier

def create_decay_chart(df: pd.DataFrame):
    decay_df = df.sort_values("rank")
    fig_decay = px.line(
        decay_df, 
        x="rank", 
        y="points", 
        markers=True,
        labels={"rank": "Leaderboard Rank", "points": "Points"},
        hover_data=["hunter"]
    )
    fig_decay.update_traces(line_color="#2ca02c", marker=dict(size=5))
    return fig_decay