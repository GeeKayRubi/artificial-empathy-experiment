import pandas as pd
from pathlib import Path


PARTICIPANT_LEVEL_COLS = ["participant_id", "age_range", "gender", "education",  "preferred_bot", "bot_more_helpful", "most_comfortable_bot","emotionally_supported_bot", "future_bot_choice","previous_chatbot_use", "chatbot_use_comments",
]



def build_wide(input_csv: str, output_csv: str) -> None:
    df = pd.read_csv(input_csv, encoding="utf-8", low_memory=False)
    df["session_number"] = pd.to_numeric(df["session_number"], errors="coerce").astype("Int64")


    pl_cols = [c for c in PARTICIPANT_LEVEL_COLS if c in df.columns and c != "participant_id"]
    df_pl = (df[["participant_id"] + pl_cols]
             .drop_duplicates(subset=["participant_id"])
             .set_index("participant_id"))
    
    exclude = set(PARTICIPANT_LEVEL_COLS) | {"participant_id", "session_number"}
    session_vars = [c for c in df.columns if c not in exclude]

    df_wide = df.pivot(index="participant_id", columns="session_number", values=session_vars)
    df_wide.columns = [f"{var}_S{int(s)}" for var, s in df_wide.columns]
    df_wide = df_wide.sort_index()

    out = df_pl.join(df_wide, how="left").reset_index()
    try:
        out["participant_id"] = pd.to_numeric(out["participant_id"], errors="raise")
        out = out.sort_values("participant_id")
    except Exception:
        pass

    Path(output_csv).parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(output_csv, index=False, encoding="utf-8-sig")


