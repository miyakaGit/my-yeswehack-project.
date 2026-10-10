# analysis.py
import pandas as pd

def get_tier(rank: int) -> str:
    if rank <= 10:
        return "Top 10 (Ranks 1–10)"
    elif rank <= 50:
        return "Tier 2 (Ranks 11–50)"
    else:
        return "Tier 3 (Ranks 51–100)"

def calculate_tier_distribution(df: pd.DataFrame) -> pd.DataFrame:
    tier_df = df.copy()
    tier_df["tier"] = tier_df["rank"].apply(get_tier)
    tier_summary = tier_df.groupby("tier")["points"].sum().reset_index()
    tier_order = ["Top 10 (Ranks 1–10)", "Tier 2 (Ranks 11–50)", "Tier 3 (Ranks 51–100)"]
    tier_summary["tier"] = pd.Categorical(tier_summary["tier"], categories=tier_order, ordered=True)
    return tier_summary.sort_values("tier")

def make_findings(df: pd.DataFrame) -> list[str]:
    if df.empty:
        return ["No observations can be generated because no ranking rows were collected."]

    data = df.copy()
    data["rank"] = pd.to_numeric(data["rank"], errors="coerce")
    data["points"] = pd.to_numeric(data["points"], errors="coerce")
    data = data.dropna(subset=["rank", "points", "hunter", "period"])
    findings = []

    leaders = data.sort_values(["rank", "points"], ascending=[True, False]).groupby("period", sort=False).first()
    for period, row in leaders.iterrows():
        findings.append(
            f"Leadership — {period}: {row['hunter']} is ranked #{int(row['rank'])} "
            f"with {int(row['points']):,} points in this collected snapshot."
        )

    for period, group in data.groupby("period", sort=False):
        ordered = group.sort_values(["points", "rank"], ascending=[False, True])
        total = ordered["points"].sum()
        if len(ordered) >= 3 and total > 0:
            share = ordered.head(3)["points"].sum() / total * 100
            findings.append(
                f"Points concentration — {period}: the top three collected hunters account for "
                f"{share:.1f}% of points among {len(ordered)} collected rows."
            )
    return findings