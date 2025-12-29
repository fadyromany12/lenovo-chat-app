import streamlit as st
import sqlite3
import json
import datetime
import pandas as pd
import time
import socket
import re

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="Lenovo Chat App", 
    page_icon="🔴", 
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={'Get Help': None, 'Report a bug': None, 'About': None}
)

# --- CUSTOM CSS (FUTURISTIC UI) ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Rajdhani:wght@400;600;700&family=Roboto+Mono:wght@300;400;500&display=swap');

    /* HIDES */
    #MainMenu, footer, header, .stDeployButton, [data-testid="stToolbar"], [data-testid="stHeader"] { display: none; }

    /* APP CONTAINER */
    [data-testid="stAppViewContainer"] {
        background-color: #050505;
        background-image: 
            linear-gradient(rgba(18, 18, 18, 0.95), rgba(18, 18, 18, 0.95)),
            url("https://www.transparenttextures.com/patterns/carbon-fibre.png");
        color: #e0e0e0;
        font-family: 'Roboto Mono', monospace;
    }

    /* TYPOGRAPHY */
    h1, h2, h3, h4 {
        font-family: 'Rajdhani', sans-serif !important;
        text-transform: uppercase;
        letter-spacing: 2px;
        color: #fff;
        text-shadow: 0 0 10px rgba(226, 35, 26, 0.5);
    }

    /* SIDEBAR */
    section[data-testid="stSidebar"] {
        background-color: #080808;
        border-right: 1px solid #333;
    }

    /* CHAT BUBBLES */
    .stChatMessage {
        background: rgba(30, 30, 30, 0.6);
        border: 1px solid #333;
        backdrop-filter: blur(5px);
        border-radius: 4px;
        border-left: 3px solid #555;
        animation: slideIn 0.3s ease-out;
    }
    div[data-testid="stChatMessageAvatar"] {
        background-color: #E2231A;
        border-radius: 2px;
    }

    /* BUTTONS */
    .stButton > button {
        background: linear-gradient(135deg, #E2231A 0%, #8a0e09 100%);
        color: white;
        border: none;
        font-family: 'Rajdhani', sans-serif;
        font-weight: 700;
        letter-spacing: 1px;
        clip-path: polygon(10% 0, 100% 0, 100% 70%, 90% 100%, 0 100%, 0 30%);
        transition: all 0.2s;
    }
    .stButton > button:hover {
        transform: scale(1.02);
        box-shadow: 0 0 15px rgba(226, 35, 26, 0.6);
    }

    /* STATUS BADGES */
    .status-badge {
        font-family: 'Rajdhani', sans-serif;
        font-weight: bold;
        padding: 5px 12px;
        border-radius: 2px;
        display: inline-block;
        font-size: 0.9em;
        letter-spacing: 1px;
    }
    .status-online { color: #00ffcc; border: 1px solid #00ffcc; background: rgba(0, 255, 204, 0.1); box-shadow: 0 0 8px rgba(0,255,204,0.2); }
    .status-idle { color: #ffcc00; border: 1px solid #ffcc00; background: rgba(255, 204, 0, 0.1); }
    .status-offline { color: #555; border: 1px solid #555; }

    /* ANIMATIONS */
    @keyframes slideIn { from { opacity: 0; transform: translateX(-10px); } to { opacity: 1; transform: translateX(0); } }
    @keyframes pulse-red { 0% { box-shadow: 0 0 0 0 rgba(226, 35, 26, 0.4); } 70% { box-shadow: 0 0 0 10px rgba(226, 35, 26, 0); } 100% { box-shadow: 0 0 0 0 rgba(226, 35, 26, 0); } }

    /* GRADING UI */
    .grade-box {
        background: #111;
        border: 1px solid #333;
        padding: 10px;
        margin-bottom: 5px;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    .grade-pass { border-left: 4px solid #00ffcc; }
    .grade-fail { border-left: 4px solid #ff3b30; }

</style>
""", unsafe_allow_html=True)

# --- CONSTANTS ---
DB_FILE = "qa_database.db"
# UPDATED SOUNDS
INCOMING_SOUND = "https://assets.mixkit.co/active_storage/sfx/1435/1435-preview.mp3" # Sharp futuristic beep
OUTGOING_SOUND = "https://assets.mixkit.co/active_storage/sfx/2571/2571-preview.mp3" # Keyboard click/send
ALERT_SOUND = "https://assets.mixkit.co/active_storage/sfx/2866/2866-preview.mp3"    # Radar ping (Attention)

# DICTIONARIES
SENTIMENT_DICT = {'negative': {'high': ['angry', 'upset', 'manager', 'sue'], 'medium': ['slow', 'waiting']}, 'positive': {'high': ['perfect', 'amazing'], 'medium': ['thanks', 'good']}}
SALES_TRIGGERS = {'inquiry': ['price', 'quote'], 'objection': ['expensive'], 'closing': ['buy', 'order']}
INTENT_REGEX = {
    'greeting': r'\b(hi|hello|morning|welcome|assist)\b',
    'closing': r'\b(thank|bye|help you with|anything else)\b',
    'question': r'\?|\b(what|how|when|why|can i)\b',
    'empathy': r'\b(sorry|apologize|understand|regret)\b',
    'warranty': r'\b(warranty|repair|support)\b'
}
KEYWORDS = {
    "greetings": ['hello', 'hi', 'welcome', 'good morning', 'my name is', 'assist you'],
    "empathy": ['sorry', 'apologize', 'understand', 'frustrating', 'regret'],
    "hold": ['hold', 'moment', 'check', 'bear with me'],
    "warranty": ['warranty', 'care', 'support', 'protection', 'adp'],
    "products": ['thinkpad', 'legion', 'yoga', 'ideapad', 'specs'],
    "objection": ['compare', 'difference', 'better', 'expensive', 'cheaper'],
    "closing": ['anything else', 'further', 'assist', 'help you with'],
    "profClosing": ['thank', 'bye', 'wonderful day', 'take care', 'choosing lenovo'],
    "csat": ['survey', 'feedback', 'rate', 'satisfaction'],
    "discovery": ['?', 'what', 'how', 'usage', 'budget', 'preference'],
    "cxCritical": ['shut up', 'idiot', 'stupid', 'hate you'],
    "compCritical": ['credit card', 'cvv', 'card number', 'password']
}
DEFAULT_SCORECARD = [
    {"id": "greet", "name": "Opening: Greet", "weight": 2.0, "keywords": "greetings", "category": "Opening"},
    {"id": "confirm", "name": "Opening: Confirm", "weight": 3.0, "keywords": "", "category": "Opening"},
    {"id": "listening", "name": "Comm: Listening", "weight": 5.0, "keywords": "", "category": "Communication"},
    {"id": "empathy", "name": "Comm: Empathy", "weight": 5.0, "keywords": "empathy", "category": "Communication"},
    {"id": "discovery", "name": "Sales: Discovery", "weight": 7.5, "keywords": "discovery", "category": "Sales"},
    {"id": "product", "name": "Sales: Product", "weight": 7.5, "keywords": "products", "category": "Sales"},
    {"id": "warranty", "name": "Sales: Warranty", "weight": 15.0, "keywords": "warranty", "category": "Sales"},
    {"id": "closing", "name": "Closing: Addressed", "weight": 2.0, "keywords": "closing", "category": "Closing"},
    {"id": "end_prof", "name": "Closing: End", "weight": 2.0, "keywords": "profClosing", "category": "Closing"},
    {"id": "csat", "name": "Closing: CSAT", "weight": 5.0, "keywords": "csat", "category": "Closing"}
]

# --- DATABASE ---
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS rooms (id INTEGER PRIMARY KEY AUTOINCREMENT, host TEXT, agent TEXT, status TEXT, created_at TIMESTAMP, last_activity TIMESTAMP)''')
    c.execute('''CREATE TABLE IF NOT EXISTS messages (id INTEGER PRIMARY KEY AUTOINCREMENT, room_id INTEGER, sender TEXT, role TEXT, text TEXT, timestamp TIMESTAMP)''')
    c.execute('''CREATE TABLE IF NOT EXISTS config (key TEXT PRIMARY KEY, value TEXT)''')
    c.execute("SELECT * FROM config WHERE key='scorecard'")
    if not c.fetchone(): c.execute("INSERT INTO config (key, value) VALUES (?, ?)", ('scorecard', json.dumps(DEFAULT_SCORECARD)))
    conn.commit()
    conn.close()

def get_rooms():
    try:
        conn = sqlite3.connect(DB_FILE)
        df = pd.read_sql_query("SELECT * FROM rooms ORDER BY created_at DESC", conn)
        conn.close()
        return df
    except: return pd.DataFrame()

def create_room(host):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    now = datetime.datetime.now()
    c.execute("INSERT INTO rooms (host, agent, status, created_at, last_activity) VALUES (?, ?, ?, ?, ?)", (host, 'Waiting...', 'Active', now, now))
    rid = c.lastrowid
    conn.commit()
    conn.close()
    return rid

def join_room(rid, agent):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("UPDATE rooms SET agent = ? WHERE id = ?", (agent, rid))
    conn.commit()
    conn.close()

def delete_room(rid):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("DELETE FROM rooms WHERE id = ?", (rid,))
    c.execute("DELETE FROM messages WHERE room_id = ?", (rid,))
    conn.commit()
    conn.close()

def send_msg(rid, sender, role, text):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    now = datetime.datetime.now()
    c.execute("INSERT INTO messages (room_id, sender, role, text, timestamp) VALUES (?, ?, ?, ?, ?)", (rid, sender, role, text, now))
    c.execute("UPDATE rooms SET last_activity = ? WHERE id = ?", (now, rid))
    conn.commit()
    conn.close()

def get_msgs(rid, limit=50):
    try:
        conn = sqlite3.connect(DB_FILE)
        query = f"SELECT * FROM (SELECT * FROM messages WHERE room_id = ? ORDER BY id DESC LIMIT {limit}) ORDER BY id ASC"
        df = pd.read_sql_query(query, conn, params=(rid,))
        conn.close()
        return df
    except: return pd.DataFrame()

def get_config(key):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT value FROM config WHERE key=?", (key,))
    row = c.fetchone()
    conn.close()
    return json.loads(row[0]) if row else []

def update_config(key, val):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("REPLACE INTO config (key, value) VALUES (?, ?)", (key, json.dumps(val)))
    conn.commit()
    conn.close()

def get_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except: return "127.0.0.1"

def check_room_status(rid):
    """Checks Expiry, Offline, and 'Last Activity' for Presence"""
    try:
        conn = sqlite3.connect(DB_FILE)
        room_row = conn.execute("SELECT status, last_activity, agent FROM rooms WHERE id = ?", (rid,)).fetchone()
        if not room_row: return "Unknown", 0, False, False
        status, last_act_str, agent_name = room_row
        
        # Get Last Role
        msg_row = conn.execute("SELECT role FROM messages WHERE room_id = ? ORDER BY id DESC LIMIT 1", (rid,)).fetchone()
        last_role = msg_row[0] if msg_row else None
        
        # Determine whose turn it is
        # If I am the Agent, and the last msg was NOT from Agent -> My turn
        # This function returns generic 'is_agent_turn', UI handles specific user role logic
        is_agent_turn = (last_role != 'Agent')
        
        conn.close()

        if not last_act_str: return status, 0, is_agent_turn, False
        try: last_act = pd.to_datetime(last_act_str).to_pydatetime()
        except: last_act = datetime.datetime.now()

        now = datetime.datetime.now()
        diff = (now - last_act).total_seconds()
        
        # Is the other person 'online' (active in last 30s)?
        is_active_recently = diff < 30

        # Auto-Expire Logic (Only changes DB if status changes)
        if status == 'Active' and is_agent_turn:
            new_status = status
            if diff > 600: new_status = 'Offline'
            elif diff > 300: new_status = 'Expired'
            
            if new_status != status:
                c2 = sqlite3.connect(DB_FILE)
                c2.execute("UPDATE rooms SET status = ? WHERE id = ?", (new_status, rid))
                c2.commit()
                c2.close()
                status = new_status

        return status, diff, is_agent_turn, is_active_recently
    except: return "Error", 0, False, False

# --- GRADING ---
def auto_grade_chat(msgs, sc):
    if msgs.empty: return {}, None, []
    agent_msgs = msgs[msgs['role']=='Agent']
    agent_text = " ".join(agent_msgs['text'].astype(str).str.lower().tolist())
    breakdown = {}
    crit = None
    tips = []

    for k in ['cxCritical', 'compCritical']:
        for w in KEYWORDS[k]:
            if w in agent_text:
                crit = f"Critical Fail: {w.upper()}"
                break
        if crit: break
    
    if not crit:
        for item in sc:
            passed = False
            cid = item['id']
            # Logic
            if cid == 'greet':
                if re.search(INTENT_REGEX['greeting'], agent_text): passed = True
            elif cid == 'discovery':
                if re.search(INTENT_REGEX['question'], agent_text) or len(re.findall(r'\?', agent_text)) >= 2: passed = True
            elif cid == 'warranty':
                if re.search(INTENT_REGEX['warranty'], agent_text): passed = True
            elif cid == 'empathy':
                if re.search(INTENT_REGEX['empathy'], agent_text): passed = True
            elif cid == 'end_prof':
                if re.search(INTENT_REGEX['closing'], agent_text): passed = True
            elif cid == 'product':
                if any(p in agent_text for p in KEYWORDS['products']): passed = True
            elif cid == 'objection':
                if any(o in agent_text for o in KEYWORDS['objection']): passed = True
            else:
                kw_key = item.get('keywords', '')
                kws = KEYWORDS.get(kw_key, [])
                if kws and any(k in agent_text for k in kws): passed = True
                elif not kws: passed = True 
            
            breakdown[item['name']] = "PASS" if passed else "FAIL"
            if not passed: tips.append(f"{item['name']}: Use keywords like {', '.join(KEYWORDS.get(cid, ['...'])[:3])}")

    return breakdown, crit, tips

def calculate_final_score(breakdown, crit, sc):
    if crit: return 0
    score, max_score = 0, 0
    for item in sc:
        w = float(item['weight'])
        max_score += w
        if breakdown.get(item['name']) == "PASS": score += w
    return int((score / max_score) * 100) if max_score > 0 else 0

def generate_export(rid, msgs, score, breakdown, crit):
    t = f"LENOVO CHAT LOG #{rid}\nDATE: {datetime.datetime.now()}\nSCORE: {score}%\n"
    if crit: t += f"CRITICAL: {crit}\n"
    t += "-"*30 + "\n"
    for _, m in msgs.iterrows(): t += f"[{m['sender']}]: {m['text']}\n"
    t += "-"*30 + "\nGRADING:\n"
    for k,v in breakdown.items(): t += f"{k}: {v}\n"
    return t

# --- UI FRAGMENTS ---
@st.fragment(run_every=1)
def render_live_updates(rid):
    status, diff, is_agent_turn, is_active = check_room_status(rid)
    
    # 1. HEADER STATUS (PRESENCE)
    if status == 'Active':
        if is_active:
            st.markdown(f"<div class='status-badge status-online'>🟢 TARGET ONLINE</div>", unsafe_allow_html=True)
        else:
            st.markdown(f"<div class='status-badge status-idle'>🟡 IDLE ({int(diff)}s)</div>", unsafe_allow_html=True)
    
    # 2. TURN/TIMER INDICATOR
    current_role = st.session_state.get('role')
    
    # Logic: 
    # If I am Agent AND it is Agent Turn -> MY TURN
    # If I am Manager AND it is NOT Agent Turn (so it's Manager Turn) -> MY TURN
    is_my_turn = (current_role == 'Agent' and is_agent_turn) or (current_role == 'Manager' and not is_agent_turn)

    if status == 'Active':
        if is_agent_turn:
            # Show Timer to everyone, but warn specifically based on turn
            if diff < 300:
                timer_html = f"<div class='timer-badge timer-ok'>⏱️ AGENT REPLY: {int(diff)}s / 300s</div>"
            else:
                timer_html = f"<div class='timer-badge timer-crit'>⚠️ OVERTIME: {int(diff)}s</div>"
            st.markdown(timer_html, unsafe_allow_html=True)
        
        # Turn Indicator
        if is_my_turn:
             st.markdown(f"<div style='color:#00ffcc; margin-top:5px; font-weight:bold; animation: pulse-red 2s infinite;'>⚡ ACTION REQUIRED: YOUR TURN</div>", unsafe_allow_html=True)
        else:
             target = "AGENT" if is_agent_turn else "CUSTOMER"
             st.markdown(f"<div style='color:#888; margin-top:5px; font-style:italic;'>WAITING FOR {target}...</div>", unsafe_allow_html=True)

    elif status == 'Expired':
        st.markdown(f"<div style='color:#ff3b30; font-weight:bold;'>💀 SESSION EXPIRED</div>", unsafe_allow_html=True)

    # 3. CHAT MESSAGES
    with st.container(height=500):
        msgs = get_msgs(rid, limit=50)
        
        # --- SOUND LOGIC ---
        if not msgs.empty:
            latest_id = msgs['id'].max()
            last_key = f"last_msg_id_{rid}"
            if last_key not in st.session_state: st.session_state[last_key] = latest_id
            
            # If new message detected
            if latest_id > st.session_state[last_seen_key := last_key]:
                new_msgs = msgs[msgs['id'] > st.session_state[last_seen_key]]
                current_user = st.session_state.get('user')
                last_sender = new_msgs.iloc[-1]['sender']
                
                if last_sender != current_user:
                    # Incoming Sound + Alert
                    st.markdown(f"""<audio autoplay style="display:none;"><source src="{INCOMING_SOUND}" type="audio/mpeg"></audio>""", unsafe_allow_html=True)
                else:
                    # Outgoing Sound
                    st.markdown(f"""<audio autoplay style="display:none;"><source src="{OUTGOING_SOUND}" type="audio/mpeg"></audio>""", unsafe_allow_html=True)
                
                st.session_state[last_seen_key] = latest_id
        
        # Alert for Turn Switch (If it just became my turn and no new msg to trigger sound)
        # Note: The incoming sound covers this usually, but we can add a specific alert if needed.
        # -------------------

        if msgs.empty:
            st.markdown("<div style='text-align: center; color: #555; margin-top: 50px;'>NO DATA PACKETS FOUND.<br>INITIATE TRANSMISSION.</div>", unsafe_allow_html=True)
        else:
            for _, m in msgs.iterrows():
                with st.chat_message(m['role'], avatar="👤" if m['role']=='Agent' else "👔"):
                    st.write(f"**{m['sender']}**: {m['text']}")

# --- APP LAYOUT ---
if 'user' not in st.session_state: st.session_state['user'] = None
if 'manual_grading' not in st.session_state: st.session_state['manual_grading'] = {}

with st.sidebar:
    st.markdown("<h1>🛑 LENOVO LINK</h1>", unsafe_allow_html=True)
    st.caption(f"SECURE CHANNEL: http://{get_ip()}:8501")
    st.markdown("---")
    if st.session_state['user']:
        st.markdown(f"<h3>👤 {st.session_state['user']}</h3>", unsafe_allow_html=True)
        st.caption(f"RANK: {st.session_state['role'].upper()}")
        if st.button("TERMINATE UPLINK", use_container_width=True):
            st.session_state['user'] = None; st.session_state['active_room'] = None; st.rerun()
        
        st.markdown("---")
        st.markdown("<h3>SIMULATIONS</h3>", unsafe_allow_html=True)
        if st.session_state['role'] == "Manager":
            if st.button("➕ NEW SESSION", use_container_width=True):
                rid = create_room(st.session_state['user'])
                st.session_state['active_room'] = rid
                st.session_state['manual_grading'] = {}
                st.rerun()
        
        if st.button("🔄 SYNC LIST", use_container_width=True): st.rerun()
        
        rooms = get_rooms()
        if not rooms.empty:
            for _, r in rooms.iterrows():
                icon = "🟢"
                if r['status'] == 'Expired': icon = "💀"
                elif r['status'] == 'Offline': icon = "💤"
                label = f"{icon} #{r['id']} {r['host']}"
                if r['agent'] != 'Waiting...': label += f" vs {r['agent']}"
                
                c1, c2 = st.columns([4, 1])
                with c1:
                    if st.button(label, key=f"r_{r['id']}", use_container_width=True):
                        st.session_state['active_room'] = r['id']
                        if st.session_state['role'] == 'Agent' and r['agent'] == 'Waiting...': join_room(r['id'], st.session_state['user'])
                        st.session_state['manual_grading'] = {}
                        st.rerun()
                with c2:
                     if st.session_state['role'] == "Manager":
                         if st.button("✖", key=f"del_{r['id']}"):
                             delete_room(r['id'])
                             if st.session_state.get('active_room') == r['id']: st.session_state['active_room'] = None
                             st.rerun()

if not st.session_state['user']:
    c1, c2, c3 = st.columns([1,2,1])
    with c2:
        st.markdown("<br><br><br><h1 style='text-align: center; font-size: 3em;'>LENOVO LINK</h1><p style='text-align: center; color: #E2231A; letter-spacing: 3px;'>SECURE COMMUNICATION RELAY</p><br>", unsafe_allow_html=True)
        with st.form("login"):
            name = st.text_input("IDENTITY", placeholder="ENTER CREDENTIALS")
            role = st.selectbox("CLEARANCE", ["Manager", "Agent"])
            st.markdown("<br>", unsafe_allow_html=True)
            if st.form_submit_button("ESTABLISH CONNECTION", use_container_width=True):
                if name: st.session_state['user'] = name; st.session_state['role'] = role; init_db(); st.rerun()
else:
    if 'active_room' in st.session_state and st.session_state['active_room']:
        rid = st.session_state['active_room']
        c_chat, c_tools = st.columns([2, 1])
        
        with c_chat:
            st.markdown(f"<h2>CHANNEL #{rid}</h2>", unsafe_allow_html=True)
            render_live_updates(rid)
            if prompt := st.chat_input("TRANSMIT..."):
                send_msg(rid, st.session_state['user'], st.session_state['role'], prompt)
                st.rerun()
        
        with c_tools:
            st.markdown("<h2>COMMANDS</h2>", unsafe_allow_html=True)
            if st.session_state['role'] == 'Manager':
                t1, t2 = st.tabs(["EVALUATION", "SYSTEM"])
                with t1:
                    msgs = get_msgs(rid, 1000)
                    sc = get_config('scorecard')
                    if st.button("INITIATE SCAN", use_container_width=True):
                        bd, crit, tips = auto_grade_chat(msgs, sc)
                        st.session_state['manual_grading'] = bd; st.session_state['crit_fail'] = crit; st.session_state['tips'] = tips
                        st.rerun()
                    
                    if 'manual_grading' in st.session_state and st.session_state['manual_grading']:
                        crit = st.session_state.get('crit_fail')
                        tips = st.session_state.get('tips', [])
                        score = calculate_final_score(st.session_state['manual_grading'], crit, sc)
                        
                        if crit: st.markdown(f"<div style='background:#220000; border:1px solid #ff3b30; color:#ff3b30; padding:10px; text-align:center; font-size:2em; font-weight:bold;'>CRITICAL FAIL<br>{crit}</div>", unsafe_allow_html=True)
                        else:
                            clr = "#00ffcc" if score >= 85 else "#ff3b30"
                            st.markdown(f"<div style='background:rgba(0,0,0,0.5); border:1px solid {clr}; color:{clr}; padding:10px; text-align:center; font-size:3em; font-weight:bold; margin-bottom:10px;'>{score}%</div>", unsafe_allow_html=True)
                        
                        st.write("### BREAKDOWN")
                        for item in sc:
                            name = item['name']
                            val = st.session_state['manual_grading'].get(name, "FAIL")
                            new_val = st.radio(f"{name}", ["PASS", "FAIL"], index=0 if val=="PASS" else 1, horizontal=True, key=f"r_{name}")
                            if new_val != val: st.session_state['manual_grading'][name] = new_val; st.rerun()
                            st.markdown(f"<div class='grade-box {'grade-pass' if val=='PASS' else 'grade-fail'}'><div>{name}</div><div style='font-weight:bold'>{val}</div></div>", unsafe_allow_html=True)
                        
                        st.download_button("DOWNLOAD REPORT", generate_export(rid, msgs, score, st.session_state['manual_grading'], crit), f"Report_{rid}.txt", use_container_width=True)
                with t2:
                    sc = get_config('scorecard')
                    nsc = []
                    for i in sc:
                        with st.expander(i['name']):
                            i['weight'] = st.number_input("Wt", value=float(i['weight']), key=f"w_{i['id']}")
                            i['name'] = st.text_input("Nm", value=i['name'], key=f"n_{i['id']}")
                            nsc.append(i)
                    if st.button("UPDATE PROTOCOL", use_container_width=True): update_config('scorecard', nsc); st.success("UPDATED")
            else:
                st.info("AGENT INTERFACE ONLINE")
                st.markdown("Monitor chat feed. Adhere to support protocols.")
    else:
        st.markdown("<div style='text-align: center; margin-top: 100px; opacity: 0.5;'><h2>AWAITING INPUT</h2><p>SELECT SIMULATION TO ENGAGE</p></div>", unsafe_allow_html=True)
