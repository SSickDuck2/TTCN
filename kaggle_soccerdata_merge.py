import os
import pandas as pd
import time
import random
from typing import Any
from soccerdata import FBref
from thefuzz import fuzz, process
from unidecode import unidecode


# ============================================================================
# Configuration: Teams by League
# ============================================================================

TEAMS_BY_LEAGUE = {
    "ENG-Premier League": [
        "Arsenal", "Manchester City", "Manchester United", "Aston Villa", "Liverpool",
        "Chelsea", "Brentford", "Everton", "Brighton", "Sunderland",
        "Bournemouth", "Fulham", "Crystal Palace", "Newcastle United", "Leeds United",
        "Nottingham Forest", "West Ham United", "Tottenham Hotspur", "Burnley", "Wolverhampton Wanderers"
    ],
    "FR-Ligue 1": [
        "Paris Saint-Germain", "Lens", "Lille", "Olympique Marseille", "Olympique Lyon",
        "Stade Rennes", "AS Monaco", "RC Strasbourg", "FC Lorient", "Toulouse",
        "Stade Brest", "Paris FC", "Angers", "Le Havre", "Nice",
        "Auxerre", "Nantes", "FC Metz"
    ],
    "ES-La Liga": [
        "Barcelona", "Real Madrid", "Villarreal", "Atletico Madrid", "Real Betis",
        "Celta Vigo", "Real Sociedad", "Getafe", "Osasuna", "Espanyol",
        "Girona", "Athletic Bilbao", "Rayo Vallecano", "Valencia", "Mallorca",
        "Sevilla", "Deportivo Alaves", "Elche", "Levante", "Real Oviedo"
    ],
    "IT-Serie A": [
        "Inter Milan", "Napoli", "AC Milan", "Juventus", "Como",
        "Roma", "Atalanta", "Bologna", "Lazio", "Udinese",
        "Sassuolo", "Torino", "Genoa", "Parma", "Fiorentina",
        "Cagliari", "Cremonese", "Lecce", "Hellas Verona", "Pisa"
    ],
    "DE-Bundesliga": [
        "Bayern Munich", "Borussia Dortmund", "VfB Stuttgart", "RB Leipzig", "Bayer Leverkusen",
        "TSG Hoffenheim", "Eintracht Frankfurt", "SC Freiburg", "Mainz 05", "FC Augsburg",
        "Union Berlin", "Hamburger SV", "FC Cologne", "Borussia Monchengladbach", "Werder Bremen",
        "FC St. Pauli", "VfL Wolfsburg", "1. FC Heidenheim"
    ]
}

# Map league codes to soccerdata friendly names
LEAGUE_MAP = {
    "ENG-Premier League": "ENG-Premier League",
    "FR-Ligue 1": "FRA-Ligue 1",
    "ES-La Liga": "ESP-La Liga",
    "IT-Serie A": "ITA-Serie A",
    "DE-Bundesliga": "GER-Bundesliga"
}

# Map league codes to Transfermarkt domestic competition IDs
LEAGUE_TM_ID = {
    "ENG-Premier League": "GB1",
    "FR-Ligue 1": "FR1",
    "ES-La Liga": "ES1",
    "IT-Serie A": "IT1",
    "DE-Bundesliga": "GR1"
}

LEAGUE_ID_TO_CODE = {v: k for k, v in LEAGUE_TM_ID.items()}


def normalize_name(value: Any) -> str:
    """Normalize player and club names for fuzzy matching."""
    return unidecode(str(value or "")).lower().strip()


def infer_league_id_from_club(club_name: str) -> str:
    """Infer league ID from a club name using configured major league team lists."""
    club_name_clean = normalize_name(club_name)
    if not club_name_clean:
        return ""

    for league_code, teams in TEAMS_BY_LEAGUE.items():
        for team in teams:
            team_clean = normalize_name(team)
            if team_clean and (team_clean in club_name_clean or club_name_clean in team_clean):
                return LEAGUE_TM_ID.get(league_code, "")

    return ""

# ============================================================================
# Load Transfermarkt Data from CSVs
# ============================================================================

def load_transfermarkt_data(db_folder: str) -> pd.DataFrame:
    """Load player and latest valuation data from TransfermarktDB CSV files."""
    print("Loading Transfermarkt data from CSV files...")
    
    try:
        players_df = pd.read_csv(os.path.join(db_folder, "players.csv"))
        valuations_df = pd.read_csv(os.path.join(db_folder, "player_valuations.csv"))
        clubs_df = pd.read_csv(os.path.join(db_folder, "clubs.csv"))
        
        valuations_df["date"] = pd.to_datetime(valuations_df["date"], errors="coerce")
        latest_val = valuations_df.sort_values("date").groupby("player_id", as_index=False).tail(1)
        
        if "market_value_in_eur" in players_df.columns:
            players_df = players_df.drop(columns=["market_value_in_eur"])
        
        merged = players_df.merge(
            latest_val[["player_id", "market_value_in_eur"]],
            on="player_id",
            how="left",
        )
        
        merged = merged.merge(
            clubs_df[["club_id", "name", "domestic_competition_id"]],
            left_on="current_club_id",
            right_on="club_id",
            how="left",
            suffixes=("", "_club"),
        )
        
        merged["player_name_clean"] = merged["name"].apply(normalize_name)
        merged["current_club_name_clean"] = merged["current_club_name"].apply(normalize_name)
        merged["tm_league_id"] = merged["current_club_domestic_competition_id"].astype(str).str.upper().str.strip()
        merged["tm_league_id"] = merged.apply(
            lambda row: row["tm_league_id"]
            if row["tm_league_id"] in LEAGUE_ID_TO_CODE
            else infer_league_id_from_club(row["current_club_name"]),
            axis=1,
        )
        merged["tm_league_name"] = merged["tm_league_id"].map(LEAGUE_ID_TO_CODE).fillna("Unknown")
        
        print(f"  Loaded {len(merged)} players from Transfermarkt data")
        return merged
    except Exception as e:
        print(f"  ERROR loading Transfermarkt: {e}")
        return pd.DataFrame()

# ============================================================================
# Scrape FBRef Data
# ============================================================================

def scrape_fbref_league(league_code: str, season: str = "2025-2026") -> pd.DataFrame:
    """Scrape player stats from FBRef for a specific league and season."""
    print(f"  Fetching {league_code} ({season})...", end=" ")
    
    try:
        fb = FBref(leagues=LEAGUE_MAP[league_code], seasons=season)
        df_stats = fb.read_player_season_stats()
        if isinstance(df_stats.columns, pd.MultiIndex):
            df_stats.columns = [
                "_".join(col).strip() if isinstance(col, tuple) else col
                for col in df_stats.columns
            ]
        df_stats = df_stats.reset_index()
        if "player" in df_stats.columns and "player_name" not in df_stats.columns:
            df_stats = df_stats.rename(columns={"player": "player_name"})
        
        df_stats["league"] = league_code
        df_stats["player_name_clean"] = df_stats["player_name"].astype(str).apply(normalize_name)
        team_col = next((c for c in ["team", "squad", "team_name"] if c in df_stats.columns), None)
        df_stats["team_clean"] = df_stats[team_col].astype(str).apply(normalize_name) if team_col else ""
        print(f"{len(df_stats)} players")
        return df_stats
    except Exception as e:
        print(f"✗ Error: {e}")
        return pd.DataFrame()

def scrape_all_fbref_data(season: str = "2025-2026") -> pd.DataFrame:
    """Scrape FBRef data for all leagues."""
    print(f"\nFetching FBRef data for {len(LEAGUE_MAP)} leagues ({season})...")
    
    all_data = []
    for league_code in LEAGUE_MAP.keys():
        time.sleep(random.uniform(2, 4))  # Delay between requests
        df = scrape_fbref_league(league_code, season)
        if not df.empty:
            all_data.append(df)
    
    return pd.concat(all_data, ignore_index=True) if all_data else pd.DataFrame()

# ============================================================================
# Fuzzy Merge Function
# ============================================================================

def fuzzy_merge_players(fbref_df: pd.DataFrame, tm_df: pd.DataFrame, threshold: int = 80) -> pd.DataFrame:
    """Merge FBRef and Transfermarkt data using fuzzy name matching."""
    print("\nPerforming fuzzy merge on player names...")
    
    if fbref_df.empty or tm_df.empty:
        print("  WARNING: One of the dataframes is empty, returning FBRef data only")
        return fbref_df
    
    fbref_df = fbref_df.copy()
    tm_df = tm_df.copy()
    
    fbref_df["player_name_clean"] = fbref_df["player_name"].astype(str).apply(normalize_name)
    fbref_df["team_clean"] = fbref_df.get("team_clean", fbref_df.get("team", fbref_df.get("squad", ""))).astype(str).apply(normalize_name)
    tm_df["player_name_clean"] = tm_df["name"].astype(str).apply(normalize_name)
    tm_df["current_club_name_clean"] = tm_df["current_club_name"].astype(str).apply(normalize_name)
    
    merged_list = []
    
    for _, row in fbref_df.iterrows():
        fb_name = str(row["player_name_clean"]).strip()
        fb_league = str(row.get("league", "")).strip()
        fb_team = str(row.get("team_clean", "")).strip()
        
        row_dict = row.to_dict()
        row_dict["transfermarkt_match"] = None
        row_dict["match_score"] = 0
        row_dict["market_value_in_eur"] = None
        row_dict["tm_player_id"] = None
        row_dict["tm_club"] = None
        
        if not fb_name or len(fb_name) < 3:
            merged_list.append(row_dict)
            continue
        
        candidate_df = tm_df
        league_id = LEAGUE_TM_ID.get(fb_league)
        if league_id and "tm_league_id" in tm_df.columns:
            league_df = tm_df[tm_df["tm_league_id"] == league_id]
            if not league_df.empty:
                candidate_df = league_df
            else:
                fallback_df = tm_df[tm_df["current_club_name_clean"].str.contains(normalize_name(fb_team), na=False)]
                if not fallback_df.empty:
                    candidate_df = fallback_df
        
        if fb_team and not candidate_df.empty:
            club_choices = candidate_df["current_club_name_clean"].dropna().unique().tolist()
            if club_choices:
                club_match = process.extractOne(fb_team, club_choices, scorer=fuzz.token_sort_ratio)
                if club_match and club_match[1] >= 80:
                    candidate_df = candidate_df[candidate_df["current_club_name_clean"] == club_match[0]]
        
        tm_names = candidate_df["player_name_clean"].dropna().unique().tolist()
        if not tm_names:
            candidate_df = tm_df
            tm_names = tm_df["player_name_clean"].dropna().unique().tolist()
        
        matches = process.extract(fb_name, tm_names, scorer=fuzz.token_sort_ratio, limit=1)
        if matches and matches[0][1] >= threshold:
            best_match_name, score = matches[0]
            tm_row = candidate_df[candidate_df["player_name_clean"] == best_match_name].iloc[0]
            row_dict["transfermarkt_match"] = tm_row["name"]
            row_dict["match_score"] = score
            row_dict["market_value_in_eur"] = tm_row.get("market_value_in_eur")
            row_dict["tm_player_id"] = tm_row.get("player_id")
            row_dict["tm_club"] = tm_row.get("current_club_name")
        
        merged_list.append(row_dict)
    
    merged_df = pd.DataFrame(merged_list)
    matched_count = (merged_df["match_score"] >= threshold).sum()
    print(f"  Merged: {matched_count}/{len(fbref_df)} players matched")
    
    return merged_df

# ============================================================================
# Main Execution
# ============================================================================

def main():
    db_folder = r"c:\Users\admin\PycharmProjects\TTCN\TransfermarktDB"
    output_folder = r"c:\Users\admin\PycharmProjects\TTCN"
    
    print("=" * 80)
    print("FBRef + Transfermarkt Merger for 5 Major European Leagues")
    print("=" * 80)
    
    # Load Transfermarkt data from CSVs
    tm_df = load_transfermarkt_data(db_folder)
    
    if tm_df.empty:
        print("ERROR: No Transfermarkt data loaded!")
        return
    
    # Scrape FBRef data for all leagues
    fbref_df = scrape_all_fbref_data(season="2025-2026")
    
    if fbref_df.empty:
        print("ERROR: No FBRef data collected!")
        return
    
    print(f"\nFBRef data collected: {len(fbref_df)} players")
    print(f"Transfermarkt data loaded: {len(tm_df)} players")
    
    # Merge datasets
    merged_df = fuzzy_merge_players(fbref_df, tm_df, threshold=80)
    
    # Save merged data
    output_path = os.path.join(output_folder, "merged_fbref_transfermarkt.csv")
    merged_df.to_csv(output_path, index=False)
    print(f"\nFinal merged data saved to: {output_path}")
    print(f"  Total records: {len(merged_df)}")
    print(f"  Matched with Transfermarkt: {(merged_df['match_score'] >= 80).sum()}")
    
    # Display sample
    print("\nSample of merged data (first 5):")
    sample_cols = ["player_name", "league", "transfermarkt_match", "match_score", 
                   "market_value_in_eur"]
    available_cols = [col for col in sample_cols if col in merged_df.columns]
    print(merged_df[available_cols].head(5).to_string())

if __name__ == "__main__":
    main()
