import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
from sqlalchemy.orm import Session
from database.database import engine, SessionLocal
from database.models import Base, PlayerInfo

CSV_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "merged_fbref_transfermarkt.csv")

COLUMN_RENAMES = {
    "nation_": "nation",
    "pos_": "position",
    "age_": "age",
    "born_": "born",
    "Playing Time_MP": "playing_time_mp",
    "Playing Time_Starts": "playing_time_starts",
    "Playing Time_Min": "playing_time_min",
    "Playing Time_90s": "playing_time_90s",
    "Performance_Gls": "performance_gls",
    "Performance_Ast": "performance_ast",
    "Performance_G+A": "performance_g_plus_a",
    "Performance_G-PK": "performance_g_minus_pk",
    "Performance_PK": "performance_pk",
    "Performance_PKatt": "performance_pkatt",
    "Performance_CrdY": "performance_crdy",
    "Performance_CrdR": "performance_crdr",
    "Per 90 Minutes_Gls": "per90_gls",
    "Per 90 Minutes_Ast": "per90_ast",
    "Per 90 Minutes_G+A": "per90_g_plus_a",
    "Per 90 Minutes_G-PK": "per90_g_minus_pk",
    "Per 90 Minutes_G+A-PK": "per90_g_plus_a_minus_pk",
    "market_value_in_eur": "market_value_eur",
    "tm_player_id": "tm_player_id",
    "tm_club": "tm_club",
}

def load_csv(path: str) -> pd.DataFrame:
    df = pd.read_csv(path, encoding="utf-8")
    df = df.rename(columns=COLUMN_RENAMES)
    df = df[list(COLUMN_RENAMES.values()) + ["league", "season", "team", "player_name", "player_name_clean", "team_clean", "transfermarkt_match", "match_score"]]
    df = df.where(pd.notnull(df), None)
    return df


def create_table():
    Base.metadata.create_all(bind=engine)


def import_player_info():
    create_table()
    df = load_csv(CSV_PATH)

    with SessionLocal() as session:
        session.query(PlayerInfo).delete()
        session.commit()

        records = df.to_dict(orient="records")
        for record in records:
            session.add(PlayerInfo(**record))
        session.commit()

    print(f"Imported {len(records)} rows into player_info")


if __name__ == "__main__":
    import_player_info()
