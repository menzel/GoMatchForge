"""
MatchForge — Go League Matchmaking
====================================
Google Sheets layout expected:
  Sheet 1 "Players":  name | timezone | rank | status 
  Sheet 2 "Games":    player1 | player2 | winner | url | week_date | week | year

Configure via .streamlit/secrets.toml:
  [gcp_service_account]
  type = "service_account"
  project_id = "..."
  private_key_id = "..."
  private_key = "..."
  client_email = "..."
  client_id = "..."
  auth_uri = "..."
  token_uri = "..."
  auth_provider_x509_cert_url = "..."
  client_x509_cert_url = "..."

  [sheets]
  spreadsheet_id = "YOUR_SPREADSHEET_ID"
"""

import streamlit as st
import pandas as pd
import numpy as np
import itertools
import json
from datetime import datetime, timezone, timedelta
import time


# ─── Page Config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="MatchForge · Go League",
    page_icon="⚫",
    layout="wide",
)

# ─── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Bebas+Neue&family=DM+Mono:wght@400;500&family=DM+Sans:wght@300;400;500&display=swap');
:root {
    --bg:#0a0a0f; --surface:#13131a; --surface2:#1c1c28;
    --accent:#e8ff47; --accent2:#ff6b35;
    --text:#e8e8f0; --muted:#6b6b80; --border:#2a2a38;
    --good:#47ffb0; --warn:#ffcc47; --bad:#ff4757;
    --kyu:#a78bfa; --dan:#fbbf24;
}
html,body,[class*="css"]{ background:var(--bg); color:var(--text); font-family:'DM Sans',sans-serif; }
.stApp{ background:var(--bg); }
h1{ font-family:'Bebas Neue',sans-serif; font-size:4rem!important; letter-spacing:4px; color:var(--accent)!important; line-height:1!important; }
h2{ font-family:'Bebas Neue',sans-serif; font-size:2.2rem!important; letter-spacing:2px; color:var(--text)!important; }
h3{ font-family:'DM Mono',monospace; font-size:1rem!important; color:var(--accent2)!important; text-transform:uppercase; letter-spacing:1px; }
.hero-sub{ font-family:'DM Mono',monospace; color:var(--muted); font-size:.85rem; letter-spacing:2px; text-transform:uppercase; margin-top:-1rem; margin-bottom:2rem; }
.metric-card{ background:var(--surface); border:1px solid var(--border); border-radius:4px; padding:1.2rem 1.5rem; border-left:3px solid var(--accent); }
.metric-card .label{ font-family:'DM Mono',monospace; font-size:.7rem; color:var(--muted); text-transform:uppercase; letter-spacing:1.5px; }
.metric-card .value{ font-family:'Bebas Neue',sans-serif; font-size:2.5rem; color:var(--accent); line-height:1.1; }
.section-divider{ border:none; border-top:1px solid var(--border); margin:2rem 0; }
.match-card{ background:var(--surface2); border:1px solid var(--border); border-radius:6px; padding:0.2rem 0.2rem; margin-bottom:.75rem; }
.match-card.best{ border-color:var(--accent); background:rgba(232,255,71,.04); }
.match-card.has-winner{ border-color:var(--good); }
.match-top{ display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:.5rem; }
.match-players{ display:flex; align-items:center; }
.match-player{ font-family:'DM Mono',monospace; font-weight:500; font-size:1rem; }
.match-player.winner{ color:var(--good); }
.match-player.loser{ color:var(--muted); text-decoration:line-through; }
.vs{ color:var(--muted); font-family:'Bebas Neue',sans-serif; font-size:1.4rem; margin:0 .8rem; }
.penalty-badge{ font-family:'DM Mono',monospace; font-size:.8rem; padding:.3rem .8rem; border-radius:100px; font-weight:500; }
.penalty-0{ background:rgba(71,255,176,.15); color:var(--good); }
.penalty-low{ background:rgba(255,204,71,.15); color:var(--warn); }
.penalty-high{ background:rgba(255,71,87,.15); color:var(--bad); }
.match-meta{ margin-top:.5rem; display:flex; gap:1rem; align-items:center; flex-wrap:wrap; }
.match-url{ font-family:'DM Mono',monospace; font-size:.75rem; color:var(--accent); text-decoration:none; }
.match-url:hover{ text-decoration:underline; }
.winner-badge{ font-family:'DM Mono',monospace; font-size:.75rem; padding:.2rem .6rem; background:rgba(71,255,176,.15); color:var(--good); border-radius:100px; }
.pending-badge{ font-family:'DM Mono',monospace; font-size:.75rem; padding:.2rem .6rem; background:rgba(107,107,128,.2); color:var(--muted); border-radius:100px; }
.week-header{ font-family:'Bebas Neue',sans-serif; font-size:1.5rem; letter-spacing:2px; color:var(--accent2); border-bottom:1px solid var(--border); padding-bottom:.4rem; margin:1.5rem 0 .8rem; }
.rank-kyu{ font-family:'DM Mono',monospace; font-size:.75rem; padding:.15rem .5rem; border-radius:4px; background:rgba(167,139,250,.15); color:var(--kyu); }
.rank-dan{ font-family:'DM Mono',monospace; font-size:.75rem; padding:.15rem .5rem; border-radius:4px; background:rgba(251,191,36,.15); color:var(--dan); }
[data-testid="stDataFrame"]{ border:1px solid var(--border); border-radius:6px; }
[data-testid="stSidebar"]{ background:var(--surface); border-right:1px solid var(--border); }
.stButton>button{ background:#939393; color:#0a0a0f; border:none; font-family:'Bebas Neue',sans-serif; font-size:1.1rem; letter-spacing:2px; padding:.6rem 2rem; border-radius:3px; transition:opacity .2s; width:100%; }
.stButton>button:hover{ opacity:.85; }
.info-box{ background:var(--surface2); border:1px solid var(--border); border-left:3px solid var(--accent2); border-radius:4px; padding:.9rem 1.2rem; font-family:'DM Mono',monospace; font-size:.8rem; color:var(--muted); margin-bottom:1rem; }
.gs-badge{ display:inline-block; font-family:'DM Mono',monospace; font-size:.7rem; padding:.2rem .6rem; border-radius:100px; margin-left:.5rem; }
.gs-ok{ background:rgba(71,255,176,.15); color:var(--good); }
.gs-err{ background:rgba(255,71,87,.15); color:var(--bad); }
.gs-off{ background:rgba(107,107,128,.2); color:var(--muted); }
</style>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# GO RANK SYSTEM
# ═══════════════════════════════════════════════════════════════════════════════
KYU_RANKS = [f"{k}k" for k in range(30, 0, -1)]
DAN_RANKS = [f"{d}d" for d in range(1, 10)]
ALL_RANKS = KYU_RANKS + DAN_RANKS  # 30k(idx0,val1) … 9d(idx38,val39)

def won_games(player: dict,hist) -> int:
  return len(hist[hist['winner'] == player['name']])
  
# ═══════════════════════════════════════════════════════════════════════════════

def rank_to_int(player: dict,hist: dict,cap=True) -> int:

  r = player['rank']
  if cap:
    return max(10,ALL_RANKS.index(str(r)) + 1) +  won_games(player,hist)/2
  else:
    return (ALL_RANKS.index(str(r)) + 1) + won_games(player,hist)/2

def rank_display(r: str) -> str:
    css = "rank-dan" if str(r).endswith("d") else "rank-kyu"
    return f"<span class='{css}'>{r}</span>"


# ═══════════════════════════════════════════════════════════════════════════════
# GOOGLE SHEETS LAYER
# ═══════════════════════════════════════════════════════════════════════════════
PLAYERS_SHEET = "Players"
GAMES_SHEET   = "Games"

PLAYERS_COLS = ["name", "timezone", "rank", "status", "timezone_matters"]
GAMES_COLS   = ["player1", "player2", "winner", "url", "week_date", "week", "year"]


def _get_gspread_client():
    """Return an authorised gspread client using service account from secrets."""
    try:
        import gspread
        from google.oauth2.service_account import Credentials
    except ImportError:
        return None, "gspread / google-auth not installed. Run: pip install gspread google-auth"

    try:
        creds_dict = dict(st.secrets["gcp_service_account"])
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ]
        creds  = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        client = gspread.authorize(creds)
        return client, None
    except KeyError:
        return None, "No [gcp_service_account] found in .streamlit/secrets.toml"
    except Exception as e:
        return None, str(e)


def _get_spreadsheet(client):
    try:
        sid = st.secrets["sheets"]["spreadsheet_id"]
        return client.open_by_key(sid), None
    except KeyError:
        return None, "No [sheets] spreadsheet_id in secrets.toml"
    except Exception as e:
        return None, str(e)


def gs_load_players(client) -> tuple[pd.DataFrame | None, str | None]:
    sh, err = _get_spreadsheet(client)
    if err: return None, err
    try:
        ws   = sh.worksheet(PLAYERS_SHEET)
        data = ws.get_all_records()
        if not data:
            return pd.DataFrame(columns=PLAYERS_COLS), None
        df = pd.DataFrame(data)
        # Coerce types
        df["timezone"] = pd.to_numeric(df["timezone"], errors="coerce").fillna(0).astype(int)
        for col in ["name", "rank", "status"]:
            if col not in df.columns: df[col] = ""
        return df[PLAYERS_COLS], None
    except Exception as e:
        return None, str(e)


def gs_load_games(client) -> tuple[pd.DataFrame | None, str | None]:
    sh, err = _get_spreadsheet(client)
    if err: return None, err
    try:
        ws   = sh.worksheet(GAMES_SHEET)
        data = ws.get_all_records()
        if not data:
            return pd.DataFrame(columns=GAMES_COLS), None
        df = pd.DataFrame(data)
        for col in GAMES_COLS:
            if col not in df.columns: df[col] = ""
        df["week"] = pd.to_numeric(df["week"], errors="coerce").fillna(0).astype(int)
        df["year"] = pd.to_numeric(df["year"], errors="coerce").fillna(0).astype(int)
        return df[GAMES_COLS], None
    except Exception as e:
        return None, str(e)


def gs_write_players(client, df: pd.DataFrame) -> str | None:
    sh, err = _get_spreadsheet(client)
    if err: return err
    try:
        ws = sh.worksheet(PLAYERS_SHEET)
        ws.clear()
        rows = [PLAYERS_COLS] + df[PLAYERS_COLS].fillna("").astype(str).values.tolist()
        ws.update(rows, value_input_option="RAW")
        return None
    except Exception as e:
        return str(e)


def gs_append_games(client, new_rows: pd.DataFrame) -> str | None:
    """Append new game rows to the Games sheet (preserves existing data)."""
    sh, err = _get_spreadsheet(client)
    if err: return err
    try:
        ws = sh.worksheet(GAMES_SHEET)
        # Ensure header exists
        existing = ws.get_all_values()
        if not existing:
            ws.append_row(GAMES_COLS)
        rows = new_rows[GAMES_COLS].fillna("").astype(str).values.tolist()
        for row in rows:
            ws.append_row(row, value_input_option="RAW")
        return None
    except Exception as e:
        return str(e)


def gs_update_game_row(client, games_df: pd.DataFrame, row_index_in_df: int) -> str | None:
    """Update a single game row in the sheet (row_index_in_df is 0-based DataFrame index)."""
    sh, err = _get_spreadsheet(client)
    if err: return err
    try:
        ws          = sh.worksheet(GAMES_SHEET)
        # Sheet row = header(1) + 1-based offset → +2
        sheet_row   = row_index_in_df + 2
        row_data    = games_df.loc[row_index_in_df, GAMES_COLS].fillna("").astype(str).tolist()
        ws.update(f"A{sheet_row}", [row_data], value_input_option="RAW")
        return None
    except Exception as e:
        return str(e)


def gs_write_all_games(client, df: pd.DataFrame) -> str | None:
    """Full overwrite of Games sheet."""
    sh, err = _get_spreadsheet(client)
    if err: return err
    try:
        ws   = sh.worksheet(GAMES_SHEET)
        ws.clear()
        rows = [GAMES_COLS] + df[GAMES_COLS].fillna("").astype(str).values.tolist()
        ws.update(rows, value_input_option="RAW")
        return None
    except Exception as e:
        return str(e)


# ═══════════════════════════════════════════════════════════════════════════════
# DATE / WEEK HELPERS
# ═══════════════════════════════════════════════════════════════════════════════
def now_utc() -> datetime:
    return datetime.now(timezone.utc)

def iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%d")

def week_num(dt: datetime) -> int:
    return int(dt.strftime("%W"))   # ISO week Mon-based; Sun league → week of the Sunday

def current_sunday() -> datetime:
    n = now_utc()
    return n - timedelta(days=(n.weekday() + 1) % 7)

def next_sunday_noon() -> datetime:
    n   = now_utc()
    off = (6 - n.weekday()) % 7
    if off == 0 and n.hour >= 12: off = 7
    s   = n + timedelta(days=off)
    return s.replace(hour=12, minute=0, second=0, microsecond=0)

def week_label_from_date(date_str: str) -> str:
    try:
        d = datetime.strptime(date_str, "%Y-%m-%d")
        return d.strftime("Week of %B %d, %Y")
    except Exception:
        return date_str


# ═══════════════════════════════════════════════════════════════════════════════
# MATCHMAKING CORE
# ═══════════════════════════════════════════════════════════════════════════════
def prev_plays(p1: str, p2: str, hist: pd.DataFrame) -> int:
    if hist.empty: return 0
    return int(((hist.player1==p1)&(hist.player2==p2)|
                (hist.player1==p2)&(hist.player2==p1)).sum())

def penalty(p1d: dict, p2d: dict, hist: pd.DataFrame) -> int:
    tz = abs(p1d["timezone"] - p2d["timezone"])
    tz = tz*p1d['timezone_matters']*p2d['timezone_matters']
    tp = 4 if tz>10 else (1.5 if tz>4 else 0)

    rp = abs(rank_to_int(p1d,hist) - rank_to_int(p2d,hist))
    #rp = rp*8 if rp>=5 else (2*rp if rp > 1 else rp)
    rpm = [0,0,2,4,rp*8]
    rp = rpm[min(int(round(rp)),4)]

    hp = prev_plays(p1d["name"], p2d["name"], hist)

    return tp + rp + 2*hp

def build_matrix(users: pd.DataFrame, hist: pd.DataFrame) -> pd.DataFrame:
    act   = users[users.status=="active"].reset_index(drop=True)
    names = act.name.tolist()
    mat   = pd.DataFrame(np.nan, index=names, columns=names)
    for i,j in itertools.combinations(range(len(names)),2):
        p = penalty(act.iloc[i].to_dict(), act.iloc[j].to_dict(), hist)
        mat.loc[names[i],names[j]] = p
        mat.loc[names[j],names[i]] = p
    return mat

def all_combos(users: pd.DataFrame, hist: pd.DataFrame) -> pd.DataFrame:
    act  = users[users.status=="active"].reset_index(drop=True)
    rows = []
    for i,j in itertools.combinations(range(len(act)),2):
        p1,p2 = act.iloc[i].to_dict(), act.iloc[j].to_dict()
        pen   = penalty(p1,p2,hist)
        rows.append({
            "Player 1":p1["name"],"Rank 1":p1["rank"],
            "Player 2":p2["name"],"Rank 2":p2["rank"],
            "TZ Diff":abs(p1["timezone"]-p2["timezone"]),
            "Rank Diff":abs(rank_to_int(p1,hist)-rank_to_int(p2,hist)),
            "Prev Games":prev_plays(p1["name"],p2["name"],hist),
            "Penalty":pen,
        })
    return pd.DataFrame(rows).sort_values("Penalty").reset_index(drop=True)


def _build_cost_matrix(players: list[dict], hist: pd.DataFrame) -> np.ndarray:
    """Square symmetric cost matrix for a list of player dicts."""
    n   = len(players)
    mat = np.zeros((n, n), dtype=float)
    for i in range(n):
        for j in range(n):
            if i != j:
                mat[i, j] = penalty(players[i], players[j], hist)
    return mat


def optimal_matchups(users: pd.DataFrame, hist: pd.DataFrame) -> tuple[list, str | None]:
    """
    Globally optimal minimum-penalty matching using the Blossom V algorithm
    (NetworkX implementation), which correctly handles general (non-bipartite)
    graphs where every player can be matched with any other player.

    linear_sum_assignment (Hungarian) solves bipartite assignment — it treats
    rows and columns as two distinct sets, so player A in row 2 and player A
    in column 2 are considered different nodes. This means it can legally
    "match A with A" or double-count players. Blossom works on a true
    undirected graph and is the correct algorithm for this problem.

    For odd player counts: each player is tried as the bye candidate, Blossom
    is solved on the remaining even pool, and the configuration with the
    lowest total penalty wins.

    Returns (matches: list[dict], bye_player: str | None)
    """
    import networkx as nx

    act     = users[users.status == "active"].reset_index(drop=True)
    players = act.to_dict("records")
    n       = len(players)

    if n < 2:
        return [], None

    def _solve_with_pool(pool: list[dict]) -> tuple[list, float]:
        """Run min-weight perfect matching on an even-sized pool."""
        G = nx.Graph()
        G.add_nodes_from(range(len(pool)))

        for i, j in itertools.combinations(range(len(pool)), 2):
            pen = penalty(pool[i], pool[j], hist)
            # NetworkX max_weight_matching maximises, so negate penalty.
            # Use a large constant minus penalty so weights stay positive.
            G.add_edge(i, j, weight=1000 - pen)

        matching = nx.max_weight_matching(G, maxcardinality=True, weight="weight")

        pairs, total = [], 0.0
        for i, j in matching:
            p1, p2 = pool[i], pool[j]
            pen    = penalty(p1, p2, hist)
            total += pen
            pairs.append({
                "Player 1":  p1["name"],  "Rank 1": p1["rank"],
                "Player 2":  p2["name"],  "Rank 2": p2["rank"],
                "TZ Diff":   abs(p1["timezone"] - p2["timezone"]),
                "Rank Diff": abs(rank_to_int(p1,hist) - rank_to_int(p2,hist)),
                "Prev Games": prev_plays(p1["name"], p2["name"], hist),
                "Penalty":   int(pen),
            })
        return pairs, total

    if n % 2 == 0:
        matches, _ = _solve_with_pool(players)
        return matches, None

    # Odd: try every player as bye, keep lowest-total assignment
    best_matches, best_total, best_bye = [], float("inf"), None
    for bye_idx in range(n):
        pool           = [p for i, p in enumerate(players) if i != bye_idx]
        pairs, total   = _solve_with_pool(pool)
        if total < best_total:
            best_total, best_matches, best_bye = total, pairs, players[bye_idx]["name"]

    return best_matches, best_bye

def best_matchups(users: pd.DataFrame, hist: pd.DataFrame) -> list:
    print(users)
    print(hist)
    combos = all_combos(users, hist)
    used, matches = set(), []
    for _,r in combos.iterrows():
        if r["Player 1"] not in used and r["Player 2"] not in used:
            matches.append(r.to_dict())
            used.add(r["Player 1"]); used.add(r["Player 2"])
    return matches

def apply_inactivity(users, hist):
    users = users.copy()
    cutoff = iso(now_utc() - timedelta(days=7))
    
    if hist.empty:
        # No history at all → nobody gets penalized, everyone stays as-is
        return users
    
    # Players who have ever played
    ever_played = set(hist.player1) | set(hist.player2)
    # Players who played recently (last 7 days)
    recent = hist[hist.week_date >= cutoff]
    recent_players = set(recent.player1) | set(recent.player2)
    
    def update(row):
        if row["name"] not in ever_played:
            return row["status"]          # never played → keep current status (active by default)
        if row["name"] not in recent_players:
            return "inactive"             # played before but not recently → inactive
        return row["status"]              # played recently → unchanged
    
    users["status"] = users.apply(update, axis=1)
    return users

def pcc(p: int) -> str:
    return "penalty-0" if p==0 else ("penalty-low" if p<=3 else "penalty-high")


# ═══════════════════════════════════════════════════════════════════════════════
# FALLBACK DEFAULT DATA (shown when no Sheets connection)
# ═══════════════════════════════════════════════════════════════════════════════
_n = now_utc()
_ls = _n - timedelta(days=(_n.weekday()+1)%7)
_ps = _ls - timedelta(days=7)

DEFAULT_USERS = pd.DataFrame([
    {"name":"Alice",   "timezone": 0, "rank":"5k",  "status":"active", "timezone_matters": 1, "key": "lama"},
    {"name":"Bob",     "timezone": 3, "rank":"3k",  "status":"active", "timezone_matters": 1, "key": "tree"},
    {"name":"Carlos",  "timezone": 8, "rank":"1d",  "status":"active", "timezone_matters": 0, "key": "house"}
])

DEFAULT_GAMES = pd.DataFrame([
    {"player1":"Alice","player2":"Bob",   "winner":"Alice","url":"https://online-go.com/game/1001","week_date":iso(_ps),"week":week_num(_ps),"year":_ps.year},
    {"player1":"Carlos","player2":"Alice","winner":"Alice","url":"https://online-go.com/game/1002","week_date":iso(_ps),"week":week_num(_ps),"year":_ps.year}
])


# ═══════════════════════════════════════════════════════════════════════════════
# SESSION STATE — load from Sheets on first run
# ═══════════════════════════════════════════════════════════════════════════════
if "gs_client" not in st.session_state:
    client, err = _get_gspread_client()
    st.session_state.gs_client    = client
    st.session_state.gs_init_err  = err
    st.session_state.gs_connected = (client is not None and err is None)

if "gs_loaded" not in st.session_state:
    st.session_state.gs_loaded = False

if not st.session_state.gs_loaded:
    if st.session_state.gs_connected:
        players_df, p_err = gs_load_players(st.session_state.gs_client)
        games_df,   g_err = gs_load_games(st.session_state.gs_client)
        load_errors = [e for e in [p_err, g_err] if e]
        if not load_errors and players_df is not None and games_df is not None:
            st.session_state.users   = players_df
            st.session_state.history = games_df
            st.session_state.gs_load_status = "ok"
        else:
            st.session_state.users   = DEFAULT_USERS.copy()
            st.session_state.history = DEFAULT_GAMES.copy()
            st.session_state.gs_load_status = "error: " + "; ".join(load_errors)
    else:
        st.session_state.users   = DEFAULT_USERS.copy()
        st.session_state.history = DEFAULT_GAMES.copy()
        st.session_state.gs_load_status = "offline"
    st.session_state.gs_loaded = True

if "scheduled_weeks" not in st.session_state:
    if not st.session_state.history.empty:
        st.session_state.scheduled_weeks = set(
            st.session_state.history["week_date"].unique().tolist()
        )
    else:
        st.session_state.scheduled_weeks = set()


# ═══════════════════════════════════════════════════════════════════════════════
# CONVENIENCE REFERENCES
# ═══════════════════════════════════════════════════════════════════════════════
def gs_status_badge() -> str:
    s = st.session_state.gs_load_status
    if s == "ok":      return "<span class='gs-badge gs-ok'>● Sheets connected</span>"
    if s == "offline": return "<span class='gs-badge gs-off'>● Sheets offline (demo data)</span>"
    return                    "<span class='gs-badge gs-err'>● Sheets error</span>"

def push_players():
    """Write current users to Sheets if connected."""
    if st.session_state.gs_connected:
        err = gs_write_players(st.session_state.gs_client, st.session_state.users)
        if err: st.warning(f"Sheets sync warning (players): {err}")

def push_all_games():
    """Full overwrite of Games sheet."""
    if st.session_state.gs_connected:
        err = gs_write_all_games(st.session_state.gs_client, st.session_state.history)
        if err: st.warning(f"Sheets sync warning (games): {err}")

def append_games_to_sheet(new_df: pd.DataFrame):
    if st.session_state.gs_connected:
        err = gs_append_games(st.session_state.gs_client, new_df)
        if err: st.warning(f"Sheets sync warning (append games): {err}")

def update_game_row_in_sheet(idx: int):
    if st.session_state.gs_connected:
        err = gs_update_game_row(
            st.session_state.gs_client, st.session_state.history, idx
        )
        if err: st.warning(f"Sheets sync warning (update game): {err}")


# ═══════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ═══════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown(f"## ⚫ MatchForge {gs_status_badge()}", unsafe_allow_html=True)
    st.markdown("<div class='hero-sub'>Go League Manager</div>", unsafe_allow_html=True)
    st.markdown("---")

    def check_key(key,players):
        print(key)
        print(players)
        print(users)
        return False

    # ── Log game result
    st.markdown("### Log Game Result")
    hist = st.session_state.history
    pending_idx = hist[hist["winner"] == ""].index.tolist() if not hist.empty else []

    if pending_idx:
        pending_df  = hist.loc[pending_idx]
        game_labels = [
            f"{r.player1} vs {r.player2} (W{int(r.week)}/{int(r.year)})"
            for _, r in pending_df.iterrows()
        ]
      # Outside the form — reacts immediately when game changes
        game_sel = st.selectbox("Pending game", game_labels, key="pending_game_sel")
        sel_idx  = pending_idx[game_labels.index(game_sel)]
        sel_row  = hist.loc[sel_idx]

        with st.form("log_result", clear_on_submit=True):
            winner_in = st.selectbox("Winner", [sel_row.player1, sel_row.player2])
            url_in    = st.text_input("Game URL", value=sel_row.url)
            key_in    = st.text_input("Player key", value=sel_row.url)

            if not check_key(key_in,[sel_row.player1, sel_row.player2]):
                st.error("Invalid key",[sel_row.player1, sel_row.player2])

            r_sub     = st.form_submit_button("SAVE RESULT",type="primary")
            if r_sub:
                if winner_in != "(pending)":
                    st.session_state.history.at[sel_idx, "winner"] = winner_in
                    for pn in [sel_row.player1, sel_row.player2]:
                        mask = st.session_state.users["name"] == pn
                       # st.session_state.users.loc[mask, "last_active"] = sel_row.week_date
                    push_players()
                if url_in:
                    st.session_state.history.at[sel_idx, "url"] = url_in
                update_game_row_in_sheet(sel_idx)
                st.success("Result saved!")
                st.rerun()
    else:
        st.info("No pending games.")

    st.markdown("---")
  
      # ── Add Player
    #st.markdown("### Add Player")
    #with st.form("add_player", clear_on_submit=True):
    #    name_in = st.text_input("Name")
    #    tz_in   = st.number_input("Timezone (UTC offset)", min_value=-12, max_value=14, value=0)
    #    rank_in = st.selectbox("Go Rank", ALL_RANKS, index=ALL_RANKS.index("5k"))
    #    ap_sub  = st.form_submit_button("ADD PLAYER")
    #    if ap_sub and name_in.strip():
    #        today = iso(now_utc())
    #        new_p = pd.DataFrame([{
    #            "name": name_in.strip(), "timezone": tz_in,
    #            "rank": rank_in, "status": "active",
    #        }])
    #        st.session_state.users = pd.concat(
    #            [st.session_state.users, new_p], ignore_index=True
    #        )
    #        push_players()
    #        st.success(f"Added {name_in.strip()} ({rank_in})!")
    #        st.rerun()


    # ── Run pairing
    # ADMIN PANEL
    #with st.form("pairing", clear_on_submit=True):

    st.markdown("### Admin")
    
    pw = st.text_input("Password", type="password")
    
    if st.button("▶ RUN PAIRING", type='tertiary'):
        sun    = current_sunday()
        wk     = iso(sun)
        wnum   = week_num(sun)
        wyear  = sun.year

        if pw != st.secrets["sheets"]["password"]:
          time.sleep(1)
          st.write("Wrong password")
        else:
            # 1. Inactivity pass
            st.session_state.users = apply_inactivity(
                st.session_state.users, st.session_state.history
            )
            push_players()

            # 2. Generate matches
            matches, bye = optimal_matchups(st.session_state.users, st.session_state.history)
            if matches:
                new_rows = pd.DataFrame([{
                    "player1":  m["Player 1"],
                    "player2":  m["Player 2"],
                    "winner":   "",
                    "url":      "",
                    "week_date": wk,
                    "week":     wnum,
                    "year":     wyear,
                } for m in matches])
                st.session_state.history = pd.concat(
                    [st.session_state.history, new_rows], ignore_index=True
                )
                st.session_state.scheduled_weeks.add(wk)
                append_games_to_sheet(new_rows)
                st.success(f"Scheduled {len(matches)} matches for week {wnum}/{wyear}!")
            else:
                st.warning("No active players to pair.")
        st.rerun()

    # ── Reload from Sheets
    if st.session_state.gs_connected:
        if st.button("🔄 RELOAD SHEETS", type='tertiary') and pw == st.secrets["sheets"]["password"]:
            players_df, p_err = gs_load_players(st.session_state.gs_client)
            games_df,   g_err = gs_load_games(st.session_state.gs_client)
            if not p_err and not g_err:
                st.session_state.users   = players_df
                st.session_state.history = games_df
                if not games_df.empty:
                    st.session_state.scheduled_weeks = set(games_df["week_date"].unique().tolist())
                st.session_state.gs_load_status = "ok"
                st.success("Reloaded from Google Sheets!")
            else:
                st.error(f"Reload failed: {p_err or g_err}")
            st.rerun()
    else:
      time.sleep(1)
      st.write("Wrong password")
    st.markdown("---")

    #st.markdown("---")
    #if st.button("RESET TO DEFAULTS"):
    ##    for k in ["users","history","scheduled_weeks","gs_loaded"]:
    #        if k in st.session_state: del st.session_state[k]
    #    st.rerun()


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════
users   = st.session_state.users
history = st.session_state.history
active  = users[users.status == "active"]

st.markdown("<h1>Go Match Kango9</h1>", unsafe_allow_html=True)
st.markdown("<div class='hero-sub'>Weekly Go League</div>",
            unsafe_allow_html=True)

# KPIs
c1,c2,c3,c4 = st.columns(4)
played  = len(history[history.winner != ""]) if not history.empty else 0
pending = len(history[history.winner == ""]) if not history.empty else 0
c1.markdown(f"<div class='metric-card'><div class='label'>Active Players</div><div class='value'>{len(active)}</div></div>", unsafe_allow_html=True)
c2.markdown(f"<div class='metric-card'><div class='label'>Total Players</div><div class='value'>{len(users)}</div></div>", unsafe_allow_html=True)
c3.markdown(f"<div class='metric-card'><div class='label'>Games Played</div><div class='value'>{played}</div></div>", unsafe_allow_html=True)
c4.markdown(f"<div class='metric-card' style='border-left-color:var(--warn);'><div class='label'>Pending Results</div><div class='value' style='color:var(--warn)'>{pending}</div></div>", unsafe_allow_html=True)

st.markdown("<hr class='section-divider'>", unsafe_allow_html=True)

tab0,tab4,tab2,tab3= st.tabs([
    "🏆 Weekly Results","👥 Players","📊 Penalty Matrix","🔢 All Combinations"
])



# ═══ TAB 0 — Weekly Results ═══════════════════════════════════════════════════
with tab0:
    st.markdown("## Weekly Results")

    if history.empty:
        st.info("No games yet.")
    else:
        # Group by (year, week) descending
        groups = (
            history
            .assign(
                _week=pd.to_numeric(history["week"], errors="coerce").fillna(0).astype(int),
                _year=pd.to_numeric(history["year"], errors="coerce").fillna(0).astype(int),
            )
            .sort_values(["_year","_week"], ascending=False)
            .groupby(["_year","_week"], sort=False)
        )

        for (yr, wk), wgames in groups:
            # Get the week_date for header label
            sample_date = wgames["week_date"].iloc[0] if "week_date" in wgames.columns else ""
            wlabel      = week_label_from_date(str(sample_date)) if sample_date else f"Week {wk}/{yr}"
            n_done      = len(wgames[wgames.winner != ""])
            n_total     = len(wgames)
            prog_col    = "var(--good)" if n_done==n_total else "var(--warn)"

            def get_rank(pn):
                row = users[users.name==pn]
                return row.iloc[0]["rank"] if not row.empty else "?"

            st.markdown(f"""<div class='week-header'>
                {wlabel} &nbsp;
                <span style='font-family:DM Sans,sans-serif;font-size:.85rem;
                    color:{prog_col};font-weight:400;'>
                    W{wk+1} · {yr} · {n_done}/{n_total} completed
                </span>
            </div>""", unsafe_allow_html=True)

            wgames['first_user_rank'] = wgames.apply(lambda x: ALL_RANKS.index(str(get_rank(x.player1))),axis=1) #ignore prev games for sorting 
            wgames = wgames.sort_values(by='first_user_rank',ascending=False)
            print(wgames)

            for _, g in wgames.iterrows():
                p1,p2   = g.player1, g.player2
                winner  = g.winner
                url     = g.url

                r1,r2    = get_rank(p1), get_rank(p2)
                p1_cls   = "winner" if winner==p1 else ("loser" if winner else "")
                p2_cls   = "winner" if winner==p2 else ("loser" if winner else "")
                card_cls = "has-winner" if winner else ""

                winner_html = (
                    f"<span class='winner-badge'>🏆 {winner}</span>" if winner
                    else "<span class='pending-badge'>⏳ Pending</span>"
                )
                url_html = (
                    f"<a class='match-url' href='{url}' target='_blank'>🔗 View game</a>"
                    if url else ""
                )

                st.markdown(f"""
                <div class='match-card {card_cls}'>
                    <div class='match-top'>
                        <div class='match-players'>
                            <span class=''>⚪</span>
                            <span class='match-player {p1_cls}'>{p1}</span>
                            <span style='margin:0 .4rem'>{rank_display(r1)}</span>
                            <span class='vs'>VS</span>
                            <span class=''>⚫</span>
                            <span class='match-player {p2_cls}'>{p2}</span>
                            <span style='margin:0 .4rem'>{rank_display(r2)}</span>
                        </div>
                        <div>{url_html}</div>
                        <div>{winner_html}</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)



# ═══ TAB 2 — Penalty Matrix ═══════════════════════════════════════════════════
with tab2:
    st.markdown("## Penalty Matrix")
    st.markdown("Active players only. Cell = total penalty for that pairing.")
    if len(active) < 2:
        st.warning("Need at least 2 active players.")
    else:
        mat = build_matrix(users, history)
        def cc(v):
            if pd.isna(v): return "background-color:#13131a;color:#2a2a38;"
            vi = int(v)
            if vi==0:    return "background-color:rgba(71,255,176,.12);color:#47ffb0;font-family:DM Mono,monospace;"
            elif vi<=3:  return "background-color:rgba(255,204,71,.12);color:#ffcc47;font-family:DM Mono,monospace;"
            else:        return "background-color:rgba(255,71,87,.12);color:#ff4757;font-family:DM Mono,monospace;"
        st.dataframe(mat.style.applymap(cc).format(precision=0,na_rep="—"), use_container_width=True)
        st.markdown("""<div style='display:flex;gap:1.5rem;margin-top:.5rem;font-family:DM Mono,monospace;font-size:.75rem;'>
            <span style='color:#47ffb0'>■ 0 — Ideal</span>
            <span style='color:#ffcc47'>■ 1–3 — OK</span>
            <span style='color:#ff4757'>■ 4+ — Poor</span>
        </div>""", unsafe_allow_html=True)


# ═══ TAB 3 — All Combinations ═════════════════════════════════════════════════
with tab3:
    st.markdown("## All Possible Combinations")
    if len(active) < 2:
        st.warning("Need at least 2 active players.")
    else:
        cdf = all_combos(users, history)
        def sp(v):
            if v==0:    return "color:#47ffb0;font-family:DM Mono,monospace;font-weight:600;"
            elif v<=3:  return "color:#ffcc47;font-family:DM Mono,monospace;font-weight:600;"
            return             "color:#ff4757;font-family:DM Mono,monospace;font-weight:600;"
        st.dataframe(cdf.style.applymap(sp,subset=["Penalty"]), use_container_width=True, hide_index=True)


# ═══ TAB 4 — Players ══════════════════════════════════════════════════════════
with tab4:
    st.markdown("## Player standings")
    ca, cb = st.columns([3,2])

    with ca:
        du = users.copy(); du.index = range(1,len(du)+1)
        du = du[['name','rank']]
        du['wins'] = du.apply(lambda x: won_games(x,hist),axis=1)
        du['rank_adjusted'] = du.apply(lambda x: rank_to_int(x,hist,cap=False),axis=1)
        du = du.sort_values(by='rank_adjusted',ascending=False)

        st.dataframe(du, use_container_width=True)

    st.markdown("---")

    #main print here
    #st.write(hist)
