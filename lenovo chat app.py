import streamlit as st
import sqlite3
import json
import datetime
import pandas as pd
import time
import socket
import re  # Added for Regex support

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
    
    /* Timer Badges */
    .timer-badge {
        font-weight: bold;
        padding: 5px 10px;
        border-radius: 4px;
        display: inline-block;
    }
    .timer-ok { color: #4caf50; background: rgba(76, 175, 80, 0.1); border: 1px solid #4caf50; }
    .timer-warn { color: #ff9800; background: rgba(255, 152, 0, 0.1); border: 1px solid #ff9800; }
    .timer-crit { color: #f44336; background: rgba(244, 67, 54, 0.1); border: 1px solid #f44336; }

</style>
""", unsafe_allow_html=True)

# --- CONSTANTS & DICTIONARIES ---
DB_FILE = "qa_database.db"

# 1. SMART DICTIONARIES
SENTIMENT_DICT = {
    'negative': {
        'high': ['angry', 'upset', 'ridiculous', 'useless', 'manager', 'sue', 'lawyer', 'complaint', 'fail', 'waste', 'broken', 'worst', 'liar'],
        'medium': ['slow', 'waiting', 'wrong', 'cancel', 'disappointed', 'hard', 'difficult', 'confusing']
    },
    'positive': {
        'high': ['perfect', 'amazing', 'great', 'love', 'excellent', 'star', 'best'],
        'medium': ['thanks', 'thank', 'helpful', 'appreciate', 'good', 'clear', 'solved', 'working']
    }
}

SALES_TRIGGERS = {
    'inquiry': ['price', 'cost', 'much', 'quote', 'specs', 'difference', 'better', 'recommend'],
    'objection': ['expensive', 'cheaper', 'competitor', 'think about it', 'budget'],
    'closing': ['buy', 'purchase', 'order', 'cart', 'card', 'payment', 'link', 'send me']
}

# 2. ADVANCED PATTERN MATCHING
INTENT_REGEX = {
    'greeting': r'\b(hi|hello|morning|afternoon|welcome|assist)\b',
    'closing': r'\b(thank|bye|goodbye|help you with|anything else|wonderful day)\b',
    'question': r'\?|\b(what|how|when|why|where|can i|could you)\b',
    'problem': r'\b(not working|broken|issue|error|damage|slow|fail|blue screen|boot|charge)\b',
    'instruction': r'\b(click|link|visit|go to|steps|setting|select|press|type)\b',
    'warranty': r'\b(warranty|repair|onsite|depot|coverage|entitlement)\b',
    'sales_pitch': r'\b(features|benefits|design|performance|powerful|exclusive|offer|deal)\b',
    'sales_close': r'\b(secure this|proceed|ready to|cart|checkout|order now)\b',
    'empathy': r'\b(sorry|apologize|understand|regret|frustrating|bear with me)\b',
    'confirmation': r'\b(yes|correct|ok|sure|right|will do|absolutely)\b'
}

# 3. KEYWORDS
KEYWORDS = {
    "greetings": [
        'hello', 'hi', 'welcome', 'good morning', 'good afternoon', 'good evening', 
        'thank you for contacting', 'thanks for contacting', 'how can i help', 'my name is',
        'chatting with', 'pleasure to meet', 'reaching out', 'assist you today'
    ],
    "empathy": [
        'sorry', 'apologize', 'understand', 'regret', 'unfortunate', 'frustrating', 
        'bear with me', 'my apologies', 'sorry for the inconvenience', 'i assure you',
        'totally understand', 'hear that', 'must be difficult', 'resolve this', 
        'on the same page', 'make this right', 'trouble you are facing', 'i realize'
    ],
    "hold": [
        'hold', 'moment', 'check', 'bear with me', 'allow me to check', 'look into this', 
        'researching', 'brief hold', 'few minutes', 'consult', 'pull up', 'accessing', 
        'give me a second', 'quick check', 'grabbing that info', 'double check'
    ],
    "warranty": [
        'warranty', 'care', 'support', 'accessory', 'guarantee', 'repair', 'depot', 
        'onsite', 'accidental', 'damage', 'protection', 'sealed battery', 'keep your drive', 
        'adp', 'premier', 'upgrade warranty', 'warranty status', 'entitlement', 
        'base warranty', 'smart performance', 'extended'
    ],
    # NEW: Sales Specific Products & Terms
    "products": [
        'thinkpad', 'legion', 'yoga', 'ideapad', 'thinkbook', 'loq', 'monitor', 'dock', 
        'workstation', 'p series', 'x1 carbon', 't series', 'gaming', 'specs', 'specification',
        'ram', 'ssd', 'processor', 'intel', 'amd', 'ryzen', 'nvidia', 'rtx', 'graphics',
        'screen', 'display', 'oled', 'ips', 'battery life', 'weight'
    ],
    # NEW: Pricing & Closing Terms
    "sales": [
        'price', 'quote', 'cost', 'discount', 'offer', 'deal', 'cart', 'buy', 'purchase',
        'order', 'checkout', 'finance', 'save', 'promotion', 'coupon', 'code', 'total',
        'tax', 'shipping', 'delivery', 'stock', 'available', 'ready to ship'
    ],
    "accessories": [
        'mouse', 'keyboard', 'monitor', 'dock', 'charger', 'adapter', 'headset', 'bag', 
        'case', 'sleeve', 'cable', 'hub', 'webcam', 'stylus', 'pen', 'privacy filter', 
        'backpack', 'stand', 'speaker', 'hard drive', 'ssd', 'ram', 'memory', 'power bank'
    ],
    "closing": [
        'anything else', 'further', 'assist you', 'other questions', 'help you with',
        'additional questions', 'support you', 'else i can do', 'proceed with', 
        'ready to', 'secure this'
    ],
    "profClosing": [
        'thank', 'bye', 'wonderful day', 'great day', 'rest of your day', 'take care', 
        'goodbye', 'appreciate your business', 'thanks for choosing', 'thanks for shopping'
    ],
    "csat": [
        'survey', 'feedback', 'short survey', 'rate', 'experience', 'email', 
        'satisfaction', 'how i did', 'valued feedback', 'fill out'
    ],
    "discovery": [
        '?', 'what', 'how', 'need', 'looking for', 'intend to use', 'purpose', 
        'usage', 'budget', 'preference', 'screen size', 'processor', 'storage', 
        'primary use', 'work', 'school', 'gaming', 'editing', 'business', 'student',
        'heavy', 'light', 'travel', 'desktop'
    ],
    # NEW: Objection Handling / reassurance
    "objection": [
        'compare', 'difference', 'better', 'value', 'benefit', 'reason', 'why',
        'advantage', 'competitor', 'cheaper', 'expensive', 'investment', 'quality',
        'review', 'performance', 'durable', 'reliable'
    ],
    "cxCritical": [
        'shut up', 'idiot', 'stupid', 'dumb', 'hate you', 'don\'t care', 'whatever', 
        'ridiculous', 'liar', 'waste of time', 'bullshit', 'damn'
    ],
    "compCritical": [
        'credit card', 'cvv', 'card number', 'expiry', 'social security', 'ssn', 
        'password', 'login credentials', 'pwd'
    ]
}

# 4. HIERARCHICAL SCORECARD (Flattened for DB compatibility but logic preserved)
SCORECARD_STRUCTURE = {
    "Opening": [
        { "id": "greet", "text": "Opening: Greet & Intro", "weight": 2.0 },
        { "id": "confirm", "text": "Opening: Confirm Name/Reason", "weight": 3.0 }
    ],
    "Communication": [
        { "id": "listening", "text": "Comm: Active Listening", "weight": 5.0 },
        { "id": "clear", "text": "Comm: Clear Language", "weight": 5.0 },
        { "id": "empathy", "text": "Comm: Empathy", "weight": 5.0 },
        { "id": "tone", "text": "Comm: Tone", "weight": 2.0 },
        { "id": "hold", "text": "Comm: Hold Etiquette", "weight": 3.0 }
    ],
    "Solution/Sales": [
        { "id": "discovery", "text": "Sales: Discovery Questions", "weight": 7.5 },
        { "id": "product", "text": "Sales: Product Knowledge", "weight": 7.5 },
        { "id": "solution", "text": "Sales: Right Solution", "weight": 7.5 },
        { "id": "objection", "text": "Sales: Objection Handling", "weight": 7.5 },
        { "id": "warranty", "text": "Sales: Warranty/Accessories", "weight": 15.0 }
    ],
    "Process": [
        { "id": "next_steps", "text": "Process: Next Steps", "weight": 5.0 },
        { "id": "compliance", "text": "Process: Compliance", "weight": 10.0 }
    ],
    "Closing": [
        { "id": "transfer", "text": "Closing: Transfer", "weight": 2.0 },
        { "id": "disposition", "text": "Closing: Disposition", "weight": 4.0 },
        { "id": "addressed", "text": "Closing: Query Addressed", "weight": 2.0 },
        { "id": "end_prof", "text": "Closing: Professional End", "weight": 2.0 },
        { "id": "csat", "text": "Closing: CSAT Statement", "weight": 5.0 }
    ]
}

# Flatten for DB
DEFAULT_SCORECARD = []
for cat, items in SCORECARD_STRUCTURE.items():
    for item in items:
        # Map keyword keys based on ID for simplicity in grading engine
        kw = item['id'] if item['id'] in KEYWORDS else ""
        if item['id'] == 'end_prof': kw = 'profClosing'
        if item['id'] == 'next_steps': kw = 'closing' # Fallback
        
        DEFAULT_SCORECARD.append({
            "id": item['id'],
            "name": item['text'],
            "weight": item['weight'],
            "keywords": kw,
            "category": cat
        })

CRITICAL_DEFINITIONS = {
    "CX Critical": ["Rude attitude or sarcasm.", "Providing misleading information.", "Chat Dumping."],
    "Business Critical": ["Stacking discounts.", "Unauthorized prices.", "Misrepresenting specs."],
    "Compliance Critical": ["PCI DSS: Asking for Credit Card info.", "GDPR: Sharing personal data."]
}

# --- DATABASE ---
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS rooms (id INTEGER PRIMARY KEY AUTOINCREMENT, host TEXT, agent TEXT, status TEXT, created_at TIMESTAMP, last_activity TIMESTAMP)''')
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

def send_msg(rid, sender, role, text):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    now = datetime.datetime.now()
    c.execute("INSERT INTO messages (room_id, sender, role, text, timestamp) VALUES (?, ?, ?, ?, ?)", (rid, sender, role, text, now))
    c.execute("UPDATE rooms SET last_activity = ? WHERE id = ?", (now, rid))
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

def check_room_status(rid):
    """Checks for Expiry (30s) and Offline (5min)"""
    try:
        conn = sqlite3.connect(DB_FILE)
        row = conn.execute("SELECT status, last_activity FROM rooms WHERE id = ?", (rid,)).fetchone()
        conn.close()
        
        if not row: return "Unknown", 0
        
        status, last_act_str = row
        if not last_act_str: return status, 0

        # Handle various timestamp formats safely
        try:
            last_act = pd.to_datetime(last_act_str).to_pydatetime()
        except:
            last_act = datetime.datetime.now()

        now = datetime.datetime.now()
        diff = (now - last_act).total_seconds()

        # Logic
        new_status = status
        if status == 'Active':
            if diff > 300: # 5 mins
                new_status = 'Offline'
            elif diff > 30: # 30 sec
                new_status = 'Expired'
            
            if new_status != status:
                conn = sqlite3.connect(DB_FILE)
                conn.execute("UPDATE rooms SET status = ? WHERE id = ?", (new_status, rid))
                conn.commit()
                conn.close()
        
        return new_status, diff
    except Exception as e:
        print(e)
        return "Error", 0

# --- GRADING ENGINE ---
def grade_chat(msgs, sc):
    if msgs.empty: return 0, {}, None, []
    
    agent_msgs = msgs[msgs['role']=='Agent']
    agent_text = " ".join(agent_msgs['text'].astype(str).str.lower().tolist())
    
    score, max_s = 0, 0
    breakdown = {}
    crit = None
    tips = []

    # 1. Criticals
    for kw_list in [KEYWORDS['cxCritical'], KEYWORDS['compCritical']]:
        for w in kw_list:
            if w in agent_text:
                crit = f"Critical Fail: Found '{w}'"
                break
        if crit: break
    
    if not crit:
        # 2. Scorecard Logic with Regex & Keywords
        for item in sc:
            w = float(item['weight'])
            max_s += w
            passed = False
            
            cid = item['id']
            
            # Smart Logic
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
                # Check for product keywords
                if any(p in agent_text for p in KEYWORDS['products']): passed = True
            elif cid == 'objection':
                # Check for objection handling words
                if any(o in agent_text for o in KEYWORDS['objection']): passed = True
            else:
                # Fallback to simple keyword match if provided
                kw_key = item.get('keywords', '')
                kws = KEYWORDS.get(kw_key, [])
                if kws and any(k in agent_text for k in kws): passed = True
                elif not kws: passed = True # Default pass for subjective if no keywords
            
            if passed:
                score += w
                breakdown[item['name']] = "PASS"
            else:
                breakdown[item['name']] = "FAIL"
                tips.append(f"{item['name']}: Try using words like {', '.join(KEYWORDS.get(cid, ['...'])[:3])}")

    final = 0 if crit else int((score/max_s)*100) if max_s > 0 else 0
    return final, breakdown, crit, tips

# --- UI FRAGMENTS (Modern Streamlit) ---
@st.fragment(run_every=0.5)
def render_live_chat(rid):
    """Refreshes chat messages & checks timer every 0.5 seconds."""
    
    # 1. Check Timer
    status, diff = check_room_status(rid)
    
    # Timer Display
    if status == 'Active':
        if diff < 30:
            st.markdown(f"<div class='timer-badge timer-ok'>⏱️ Reply Time: {int(diff)}s / 30s</div>", unsafe_allow_html=True)
        else:
            st.markdown(f"<div class='timer-badge timer-crit'>⚠️ OVERTIME: {int(diff)}s</div>", unsafe_allow_html=True)
    elif status == 'Expired':
        st.markdown(f"<div class='timer-badge timer-crit'>💀 CHAT EXPIRED (No Reply > 30s)</div>", unsafe_allow_html=True)
    elif status == 'Offline':
        st.markdown(f"<div class='timer-badge timer-warn'>💤 OFFLINE (Inactive > 5m)</div>", unsafe_allow_html=True)

    # 2. Render Messages
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
                # Status Icon Logic
                icon = "🟢"
                if r['status'] == 'Expired': icon = "💀"
                elif r['status'] == 'Offline': icon = "💤"
                
                label = f"{icon} #{r['id']} {r['host']}"
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
            
            # Input outside fragment
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
