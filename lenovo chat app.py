import streamlit as st
import sqlite3
import json
import datetime
import pandas as pd
import time
import socket

# --- PAGE CONFIGURATION (Must be first) ---
st.set_page_config(
    page_title="Lenovo QA Manager Pro", 
    page_icon="🔴", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CUSTOM CSS STYLING (FIXED DARK MODE) ---
st.markdown("""
<style>
    /* Global Dark Theme */
    [data-testid="stAppViewContainer"] {
        background-color: #0e0e0e;
        color: #f0f0f0;
    }
    
    /* Sidebar Styling */
    section[data-testid="stSidebar"] {
        background-color: #050505;
        border-right: 1px solid #222;
    }
    section[data-testid="stSidebar"] h1, section[data-testid="stSidebar"] h2, section[data-testid="stSidebar"] h3 {
        color: #E2231A !important;
    }
    
    /* Inputs */
    .stTextInput input, .stSelectbox div[data-baseweb="select"] > div {
        background-color: #1a1a1a !important;
        color: white !important;
        border: 1px solid #333 !important;
    }
    
    /* Chat Bubbles */
    .stChatMessage {
        background-color: #1a1a1a;
        border: 1px solid #333;
    }
    
    /* Buttons */
    .stButton > button {
        background-color: #E2231A;
        color: white;
        border: none;
        font-weight: bold;
    }
    .stButton > button:hover {
        background-color: #ff3b30;
    }

    /* Result Boxes */
    .grade-container {
        padding: 15px;
        border-radius: 8px;
        margin-bottom: 10px;
        border-left: 5px solid;
    }
    .grade-pass { background-color: #0a1f0a; border-color: #2e7d32; color: #a5d6a7; }
    .grade-fail { background-color: #1f0a0a; border-color: #c62828; color: #ef9a9a; }
    .grade-score { font-size: 2.5em; font-weight: bold; text-align: center; margin: 10px 0; }

</style>
""", unsafe_allow_html=True)

# --- CONSTANTS ---
DB_FILE = "qa_database.db"

DEFAULT_KEYWORDS = {
    "greetings": ['hello', 'hi', 'welcome', 'good morning', 'good afternoon', 'my name is', 'assist you', 'chatting with'],
    "empathy": ['sorry', 'apologize', 'understand', 'frustrating', 'regret', 'trouble', 'hear that', 'realize', 'inconvenience'],
    "hold": ['hold', 'moment', 'check', 'bear with me', 'researching', 'consult', 'accessing'],
    "discovery": ['?', 'what', 'how', 'need', 'looking for', 'usage', 'budget', 'preference', 'primary use'],
    "closing": ['anything else', 'further', 'assist', 'help you with', 'questions'],
    "prof_closing": ['thank', 'bye', 'wonderful day', 'take care', 'appreciate', 'choosing lenovo'],
    "warranty": ['warranty', 'care', 'support', 'protection', 'repair', 'onsite', 'depot', 'adp'],
    "csat": ['survey', 'feedback', 'rate', 'experience', 'satisfaction'],
    "cx_critical": ['shut up', 'idiot', 'stupid', 'dumb', 'waste of time', 'hate you'],
    "comp_critical": ['credit card', 'cvv', 'card number', 'expiry', 'password', 'ssn'],
    "biz_critical": ['fake price', 'unauthorized discount']
}

DEFAULT_SCORECARD = [
    {"id": "greet", "name": "Opening: Greet & Intro", "weight": 5.0, "keywords": "greetings"},
    {"id": "empathy", "name": "Comm: Empathy", "weight": 10.0, "keywords": "empathy"},
    {"id": "discovery", "name": "Sales: Discovery Questions", "weight": 15.0, "keywords": "discovery"},
    {"id": "hold", "name": "Comm: Hold Etiquette", "weight": 5.0, "keywords": "hold"},
    {"id": "warranty", "name": "Sales: Warranty Pitch", "weight": 10.0, "keywords": "warranty"},
    {"id": "closing", "name": "Closing: Addressed Query", "weight": 5.0, "keywords": "closing"},
    {"id": "end_prof", "name": "Closing: Professional End", "weight": 5.0, "keywords": "prof_closing"},
    {"id": "csat", "name": "Closing: CSAT Request", "weight": 5.0, "keywords": "csat"}
]

COACHING_TIPS = {
    "greet": "Start with: 'Thank you for contacting Lenovo, my name is...'",
    "empathy": "Say: 'I apologize for the inconvenience' or 'I understand your frustration'.",
    "discovery": "Ask open-ended questions (Who, What, Where, Why) to understand needs.",
    "hold": "Ask permission: 'May I place you on a brief hold while I check that?'",
    "warranty": "Always offer Warranty Upgrades or Accidental Damage Protection.",
    "closing": "Ask: 'Is there anything else I can assist you with today?'",
    "end_prof": "End with: 'Thank you for choosing Lenovo. Have a wonderful day!'",
    "csat": "Don't forget to invite the customer to take the satisfaction survey."
}

# --- DATABASE ---
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS rooms (id INTEGER PRIMARY KEY AUTOINCREMENT, host TEXT, agent TEXT, status TEXT, created_at TIMESTAMP)''')
    c.execute('''CREATE TABLE IF NOT EXISTS messages (id INTEGER PRIMARY KEY AUTOINCREMENT, room_id INTEGER, sender TEXT, role TEXT, text TEXT, timestamp TIMESTAMP)''')
    c.execute('''CREATE TABLE IF NOT EXISTS config (key TEXT PRIMARY KEY, value TEXT)''')
    c.execute("SELECT * FROM config WHERE key='scorecard'")
    if not c.fetchone():
        c.execute("INSERT INTO config (key, value) VALUES (?, ?)", ('scorecard', json.dumps(DEFAULT_SCORECARD)))
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
    c.execute("INSERT INTO rooms (host, agent, status, created_at) VALUES (?, ?, ?, ?)", (host, 'Waiting...', 'Active', datetime.datetime.now()))
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

def send_msg(rid, sender, role, text):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT INTO messages (room_id, sender, role, text, timestamp) VALUES (?, ?, ?, ?, ?)", (rid, sender, role, text, datetime.datetime.now()))
    conn.commit()
    conn.close()

def get_msgs(rid):
    try:
        conn = sqlite3.connect(DB_FILE)
        df = pd.read_sql_query("SELECT * FROM messages WHERE room_id = ? ORDER BY id ASC", conn, params=(rid,))
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

# --- GRADING ENGINE ---
def grade_chat(msgs, sc):
    if msgs.empty: return 0, {}, None, []
    
    agent_text = " ".join(msgs[msgs['role']=='Agent']['text'].astype(str).str.lower().tolist())
    
    score, max_s = 0, 0
    breakdown = {}
    crit = None
    tips = []

    # Criticals
    for k in ['cx_critical', 'comp_critical', 'biz_critical']:
        for w in DEFAULT_KEYWORDS[k]:
            if w in agent_text:
                crit = f"Critical Fail: Found '{w}'"
                if k in COACHING_TIPS: tips.append(COACHING_TIPS[k])
                break
        if crit: break
    
    if not crit:
        for item in sc:
            w = float(item['weight'])
            max_s += w
            passed = False
            kw_key = item.get('keywords', '')
            kws = DEFAULT_KEYWORDS.get(kw_key, [])
            
            if item['id'] == 'discovery':
                if agent_text.count('?') >= 2 or sum(1 for k in kws if k in agent_text) >= 2: passed = True
            elif item['id'] == 'hold':
                passed = True # Assume N/A or Pass
            elif kws:
                if any(k in agent_text for k in kws): passed = True
            else:
                passed = True # Default pass for subjective
            
            if passed:
                score += w
                breakdown[item['name']] = "PASS"
            else:
                breakdown[item['name']] = "FAIL"
                if item['id'] in COACHING_TIPS: tips.append(COACHING_TIPS[item['id']])

    final = 0 if crit else int((score/max_s)*100) if max_s > 0 else 0
    return final, breakdown, crit, tips

# --- UI FRAGMENTS (Modern Streamlit) ---
@st.fragment(run_every=0.5)
def render_live_chat(rid):
    """Refreshes chat messages every 0.5 seconds automatically."""
    msgs = get_msgs(rid)
    if msgs.empty:
        st.markdown("<div style='text-align: center; color: #666; margin-top: 50px;'>No messages yet. Start typing!</div>", unsafe_allow_html=True)
    else:
        for _, m in msgs.iterrows():
            with st.chat_message(m['role'], avatar="👤" if m['role']=='Agent' else "👔"):
                st.write(f"**{m['sender']}**: {m['text']}")

# --- APP LAYOUT ---
if 'user' not in st.session_state: st.session_state['user'] = None

# SIDEBAR
with st.sidebar:
    st.title("🔴 Lenovo QA")
    st.caption(f"Network: http://{get_ip()}:8501")
    
    if st.session_state['user']:
        st.write(f"Logged in as: **{st.session_state['user']}** ({st.session_state['role']})")
        if st.button("Logout", use_container_width=True):
            st.session_state['user'] = None
            st.rerun()
        
        st.divider()
        st.subheader("Rooms")
        if st.session_state['role'] == "Manager":
            if st.button("➕ Create Room", use_container_width=True):
                rid = create_room(st.session_state['user'])
                st.session_state['active_room'] = rid
                st.rerun()
        
        if st.button("🔄 Refresh Rooms", use_container_width=True): st.rerun()
        
        rooms = get_rooms()
        if not rooms.empty:
            for _, r in rooms.iterrows():
                label = f"#{r['id']} {r['host']}"
                if r['agent'] != 'Waiting...': label += f" vs {r['agent']}"
                if st.button(label, key=f"r_{r['id']}", use_container_width=True):
                    st.session_state['active_room'] = r['id']
                    if st.session_state['role'] == 'Agent' and r['agent'] == 'Waiting...':
                        join_room(r['id'], st.session_state['user'])
                    st.rerun()

# MAIN AREA
if not st.session_state['user']:
    c1, c2, c3 = st.columns([1,2,1])
    with c2:
        st.header("Login")
        with st.form("login_form"):
            name = st.text_input("Name")
            role = st.selectbox("Role", ["Manager", "Agent"])
            if st.form_submit_button("Start", use_container_width=True):
                if name:
                    st.session_state['user'] = name
                    st.session_state['role'] = role
                    init_db()
                    st.rerun()
else:
    if 'active_room' in st.session_state:
        rid = st.session_state['active_room']
        col_chat, col_tools = st.columns([2, 1])
        
        with col_chat:
            st.subheader(f"Chat Room #{rid}")
            container = st.container(height=600)
            with container:
                render_live_chat(rid)
            
            # Input outside fragment to avoid focus loss
            if prompt := st.chat_input("Message..."):
                send_msg(rid, st.session_state['user'], st.session_state['role'], prompt)
                st.rerun()
        
        with col_tools:
            st.subheader("Tools")
            if st.session_state['role'] == 'Manager':
                tab1, tab2 = st.tabs(["Grading", "Setup"])
                with tab1:
                    if st.button("Run Analysis", use_container_width=True):
                        msgs = get_msgs(rid)
                        sc = get_config('scorecard')
                        score, bd, crit, tips = grade_chat(msgs, sc)
                        
                        if crit:
                            st.markdown(f"<div class='grade-container grade-fail'><div class='grade-score'>0%</div><div style='text-align:center'>{crit}</div></div>", unsafe_allow_html=True)
                        else:
                            cls = "grade-pass" if score >= 85 else "grade-fail"
                            st.markdown(f"<div class='grade-container {cls}'><div class='grade-score'>{score}%</div></div>", unsafe_allow_html=True)
                        
                        if tips:
                            st.warning("Coaching Tips:")
                            for t in tips: st.markdown(f"- {t}")
                        
                        st.write("Breakdown:")
                        for k, v in bd.items():
                            c = "grade-pass" if v == "PASS" else "grade-fail"
                            st.markdown(f"<div class='grade-container {c}' style='padding:8px; margin-bottom:5px;'>{k}: <b>{v}</b></div>", unsafe_allow_html=True)
                
                with tab2:
                    st.info("Scorecard Config")
                    curr = get_config('scorecard')
                    new_sc = []
                    for i in curr:
                        with st.expander(i['name']):
                            w = st.number_input("Weight", value=float(i['weight']), key=f"w_{i['id']}")
                            n = st.text_input("Name", value=i['name'], key=f"n_{i['id']}")
                            i['weight'] = w
                            i['name'] = n
                            new_sc.append(i)
                    if st.button("Save Config", use_container_width=True):
                        update_config('scorecard', new_sc)
                        st.success("Saved")
            else:
                st.info("Agent Mode Active")
                st.markdown("Focus on the chat. Your manager will grade the conversation.")
    else:
        st.info("Select a room to begin.")
