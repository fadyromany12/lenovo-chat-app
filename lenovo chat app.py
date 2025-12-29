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
    page_title="Lenovo Chat App", 
    page_icon="🔴", 
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'Get Help': None,
        'Report a bug': None,
        'About': None
    }
)

# --- CUSTOM CSS STYLING (FUTURISTIC UI) ---
st.markdown("""
<style>
    /* IMPORT FUTURISTIC FONTS */
    @import url('https://fonts.googleapis.com/css2?family=Rajdhani:wght@400;600;700&family=Roboto+Mono:wght@300;400;500&display=swap');

    /* --- GLOBAL HIDES --- */
    #MainMenu, footer, header, .stDeployButton, [data-testid="stToolbar"], [data-testid="stHeader"] {
        visibility: hidden;
        display: none;
    }

    /* --- MAIN APP CONTAINER --- */
    [data-testid="stAppViewContainer"] {
        background-color: #050505;
        background-image: 
            radial-gradient(circle at 10% 20%, rgba(226, 35, 26, 0.05) 0%, transparent 20%),
            radial-gradient(circle at 90% 80%, rgba(20, 20, 20, 1) 0%, transparent 50%);
        color: #e0e0e0;
        font-family: 'Roboto Mono', monospace;
    }

    /* --- TYPOGRAPHY --- */
    h1, h2, h3, h4, .stMarkdown h1, .stMarkdown h2, .stMarkdown h3 {
        font-family: 'Rajdhani', sans-serif !important;
        text-transform: uppercase;
        letter-spacing: 2px;
        color: #fff;
        text-shadow: 0 0 10px rgba(226, 35, 26, 0.3);
    }

    /* --- SIDEBAR (CONTROL PANEL LOOK) --- */
    section[data-testid="stSidebar"] {
        background-color: rgba(10, 10, 10, 0.85);
        border-right: 1px solid #333;
        backdrop-filter: blur(10px);
        box-shadow: 5px 0 20px rgba(0,0,0,0.5);
    }
    section[data-testid="stSidebar"] hr {
        border-color: #333;
    }

    /* --- INPUT FIELDS (TERMINAL STYLE) --- */
    .stTextInput input, .stSelectbox div[data-baseweb="select"] > div {
        background-color: rgba(20, 20, 20, 0.8) !important;
        color: #00ffcc !important; /* Cyber Cyan Text */
        border: 1px solid #333 !important;
        border-radius: 0px !important; /* Sharp edges */
        font-family: 'Roboto Mono', monospace;
        transition: all 0.3s;
    }
    .stTextInput input:focus, .stSelectbox div[data-baseweb="select"] > div:focus-within {
        border-color: #E2231A !important;
        box-shadow: 0 0 10px rgba(226, 35, 26, 0.4);
    }

    /* --- BUTTONS (HOLOGRAPHIC & ANIMATED) --- */
    .stButton > button {
        background: transparent;
        border: 1px solid #E2231A;
        color: #E2231A;
        font-family: 'Rajdhani', sans-serif;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 2px;
        border-radius: 0px;
        padding: 0.6rem 1.2rem;
        transition: all 0.3s ease;
        position: relative;
        overflow: hidden;
        /* Sci-fi cut corner shape */
        clip-path: polygon(10% 0, 100% 0, 100% 70%, 90% 100%, 0 100%, 0 30%);
    }
    
    /* Hover Glow Effect */
    .stButton > button:hover {
        background: #E2231A;
        color: #000;
        box-shadow: 0 0 25px rgba(226, 35, 26, 0.6);
        transform: translateY(-2px);
    }
    
    /* Scanline Animation on Buttons */
    .stButton > button::after {
        content: '';
        position: absolute;
        top: 0; left: -100%;
        width: 100%; height: 100%;
        background: linear-gradient(90deg, transparent, rgba(255,255,255,0.2), transparent);
        transition: 0.5s;
    }
    .stButton > button:hover::after {
        left: 100%;
    }

    /* --- CHAT INTERFACE (GLASS) --- */
    .stChatMessage {
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(255, 255, 255, 0.05);
        backdrop-filter: blur(5px);
        border-radius: 4px;
        border-left: 3px solid #444;
        animation: slideIn 0.4s ease-out;
        transition: all 0.2s;
    }
    .stChatMessage:hover {
        border-left-color: #E2231A;
        background: rgba(255, 255, 255, 0.05);
        transform: translateX(5px);
    }
    div[data-testid="stChatMessageAvatar"] {
        background: linear-gradient(135deg, #111, #333);
        border: 1px solid #E2231A;
        border-radius: 0px; /* Square avatars */
    }

    /* --- GRADING HUD --- */
    .grade-container {
        background: rgba(0, 0, 0, 0.6);
        border: 1px solid #333;
        padding: 15px;
        margin-bottom: 10px;
        border-radius: 4px;
        position: relative;
        overflow: hidden;
        animation: fadeIn 0.6s ease-out;
    }
    .grade-pass {
        border-left: 4px solid #00ffcc;
        box-shadow: -5px 0 15px rgba(0, 255, 204, 0.1);
    }
    .grade-fail {
        border-left: 4px solid #ff3b30;
        box-shadow: -5px 0 15px rgba(255, 59, 48, 0.1);
    }
    .grade-score {
        font-family: 'Rajdhani', sans-serif;
        font-size: 4em;
        font-weight: 800;
        text-align: center;
        margin: 10px 0;
        text-shadow: 0 0 20px currentColor;
    }

    /* --- TIMERS --- */
    .timer-badge {
        font-family: 'Roboto Mono', monospace;
        font-weight: bold;
        text-align: center;
        padding: 10px;
        border: 1px solid #333;
        background: rgba(0,0,0,0.5);
        margin-bottom: 15px;
        letter-spacing: 1px;
    }
    .timer-ok { border-color: #00ffcc; color: #00ffcc; box-shadow: 0 0 10px rgba(0,255,204,0.2); }
    .timer-warn { border-color: #ffcc00; color: #ffcc00; }
    .timer-crit { border-color: #ff3b30; color: #ff3b30; animation: pulse 1.5s infinite; }
    .timer-wait { border-color: #555; color: #888; font-style: italic; }

    /* --- ANIMATIONS --- */
    @keyframes slideIn {
        from { opacity: 0; transform: translateX(-20px); }
        to { opacity: 1; transform: translateX(0); }
    }
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(10px); }
        to { opacity: 1; transform: translateY(0); }
    }
    @keyframes pulse {
        0% { box-shadow: 0 0 0 0 rgba(255, 59, 48, 0.4); }
        70% { box-shadow: 0 0 0 10px rgba(255, 59, 48, 0); }
        100% { box-shadow: 0 0 0 0 rgba(255, 59, 48, 0); }
    }

    /* Scrollbar */
    ::-webkit-scrollbar { width: 8px; background: #050505; }
    ::-webkit-scrollbar-thumb { background: #333; border: 1px solid #000; }
    ::-webkit-scrollbar-thumb:hover { background: #E2231A; }

</style>
""", unsafe_allow_html=True)

# --- CONSTANTS & DICTIONARIES ---
DB_FILE = "qa_database.db"
SOUND_URL = "https://assets.mixkit.co/active_storage/sfx/2869/2869-preview.mp3" # Notification Sound

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
        kw = item['id'] if item['id'] in KEYWORDS else ""
        if item['id'] == 'end_prof': kw = 'profClosing'
        if item['id'] == 'next_steps': kw = 'closing'
        
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
        # Optimization: Fetch only last N messages to prevent lag
        query = f"""
            SELECT * FROM (
                SELECT * FROM messages 
                WHERE room_id = ? 
                ORDER BY id DESC 
                LIMIT {limit}
            ) ORDER BY id ASC
        """
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
    """Checks for Expiry (5min) and Offline (10min) - Agent Only Logic"""
    try:
        conn = sqlite3.connect(DB_FILE)
        
        # 1. Get Room Details
        room_row = conn.execute("SELECT status, last_activity, agent FROM rooms WHERE id = ?", (rid,)).fetchone()
        if not room_row: 
            conn.close()
            return "Unknown", 0, False
            
        status, last_act_str, agent_name = room_row
        
        # 2. If Agent hasn't joined, timer shouldn't start
        if agent_name == 'Waiting...':
            conn.close()
            return status, 0, False

        # 3. Get Last Message Sender Role
        msg_row = conn.execute("SELECT role FROM messages WHERE room_id = ? ORDER BY id DESC LIMIT 1", (rid,)).fetchone()
        last_role = msg_row[0] if msg_row else None
        
        is_agent_turn = (last_role != 'Agent')

        if not last_act_str: 
            conn.close()
            return status, 0, is_agent_turn

        try:
            last_act = pd.to_datetime(last_act_str).to_pydatetime()
        except:
            last_act = datetime.datetime.now()

        now = datetime.datetime.now()
        diff = (now - last_act).total_seconds()

        # 4. Status Update Logic (Only if it's Agent's turn)
        new_status = status
        if status == 'Active' and is_agent_turn:
            if diff > 600: # 10 mins offline
                new_status = 'Offline'
            elif diff > 300: # 5 min expiry
                new_status = 'Expired'
            
            if new_status != status:
                conn.execute("UPDATE rooms SET status = ? WHERE id = ?", (new_status, rid))
                conn.commit()
        
        conn.close()
        return new_status, diff, is_agent_turn
    except Exception as e:
        print(e)
        return "Error", 0, False

# --- GRADING ENGINE ---
def auto_grade_chat(msgs, sc):
    """Initial Auto-Grading using Keywords/Regex"""
    if msgs.empty: return {}, None, []
    
    agent_msgs = msgs[msgs['role']=='Agent']
    agent_text = " ".join(agent_msgs['text'].astype(str).str.lower().tolist())
    
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
                if any(p in agent_text for p in KEYWORDS['products']): passed = True
            elif cid == 'objection':
                if any(o in agent_text for o in KEYWORDS['objection']): passed = True
            else:
                kw_key = item.get('keywords', '')
                kws = KEYWORDS.get(kw_key, [])
                if kws and any(k in agent_text for k in kws): passed = True
                elif not kws: passed = True # Default pass for subjective
            
            breakdown[item['name']] = "PASS" if passed else "FAIL"
            if not passed:
                 tips.append(f"{item['name']}: Try using words like {', '.join(KEYWORDS.get(cid, ['...'])[:3])}")

    return breakdown, crit, tips

def calculate_final_score(breakdown, crit, sc):
    """Calculates score from breakdown dictionary (Auto or Manual)"""
    if crit: return 0
    
    score = 0
    max_score = 0
    
    for item in sc:
        w = float(item['weight'])
        max_score += w
        if breakdown.get(item['name']) == "PASS":
            score += w
            
    return int((score / max_score) * 100) if max_score > 0 else 0

def generate_export_text(rid, msgs, score, breakdown, crit):
    """Generates a text report"""
    lines = []
    lines.append(f"LENOVO CHAT REPORT - ROOM #{rid}")
    lines.append("="*40)
    lines.append(f"Date: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"Final Score: {score}%")
    if crit: lines.append(f"CRITICAL FAIL: {crit}")
    lines.append("\n--- CHAT TRANSCRIPT ---")
    for _, m in msgs.iterrows():
        lines.append(f"[{m['timestamp']}] {m['sender']} ({m['role']}): {m['text']}")
    
    lines.append("\n--- GRADING BREAKDOWN ---")
    for k, v in breakdown.items():
        lines.append(f"{k}: {v}")
        
    return "\n".join(lines)

# --- UI FRAGMENTS (Modern Streamlit) ---
@st.fragment(run_every=1)
def render_live_updates(rid):
    """Refreshes chat messages & checks timer every 1 second.
       Handles both Timer (Outside) and Messages (Inside Box)
    """
    
    # 1. Check Status
    status, diff, is_agent_turn = check_room_status(rid)
    
    # 2. Render Timer (VISIBLE OUTSIDE CHAT BOX)
    if status == 'Active':
        if is_agent_turn:
            if diff < 300: # 5 min
                st.markdown(f"<div class='timer-badge timer-ok'>⏱️ REPLY TIME: {int(diff)}s / 300s</div>", unsafe_allow_html=True)
            else:
                st.markdown(f"<div class='timer-badge timer-crit'>⚠️ OVERTIME: {int(diff)}s</div>", unsafe_allow_html=True)
        else:
            st.markdown(f"<div class='timer-badge timer-wait'>⏳ CUSTOMER TYPING...</div>", unsafe_allow_html=True)
            
    elif status == 'Expired':
        st.markdown(f"<div class='timer-badge timer-crit'>💀 CHAT EXPIRED (AGENT TIMEOUT)</div>", unsafe_allow_html=True)
    elif status == 'Offline':
        st.markdown(f"<div class='timer-badge timer-warn'>💤 OFFLINE (SESSION INACTIVE)</div>", unsafe_allow_html=True)

    # 3. Render Messages inside Scrollable Container
    with st.container(height=550):
        msgs = get_msgs(rid, limit=50) # OPTIMIZATION: Limit to 50
        
        # --- NEW MESSAGE SOUND NOTIFICATION ---
        if not msgs.empty:
            latest_id = msgs['id'].max()
            last_seen_key = f"last_msg_id_{rid}"
            
            # Init state if new room
            if last_seen_key not in st.session_state:
                st.session_state[last_seen_key] = latest_id
            
            # Detect new message
            if latest_id > st.session_state[last_seen_key]:
                # Get the new messages
                new_msgs = msgs[msgs['id'] > st.session_state[last_seen_key]]
                
                # Play Sound IF the new message is NOT from me
                current_user = st.session_state.get('user')
                if any(new_msgs['sender'] != current_user):
                    st.markdown(f"""
                        <audio autoplay style="display:none;">
                            <source src="{SOUND_URL}" type="audio/mpeg">
                        </audio>
                    """, unsafe_allow_html=True)
                
                # Update tracker
                st.session_state[last_seen_key] = latest_id
        # --------------------------------------

        if msgs.empty:
            st.markdown("<div style='text-align: center; color: #666; margin-top: 50px; font-style: italic;'>DECRYPTION COMPLETE. NO MESSAGES FOUND.<br>INITIATE PROTOCOL...</div>", unsafe_allow_html=True)
        else:
            for _, m in msgs.iterrows():
                with st.chat_message(m['role'], avatar="👤" if m['role']=='Agent' else "👔"):
                    st.write(f"**{m['sender']}**: {m['text']}")

# --- APP LAYOUT ---
if 'user' not in st.session_state: st.session_state['user'] = None
if 'manual_grading' not in st.session_state: st.session_state['manual_grading'] = {} # Store grading state

# SIDEBAR
with st.sidebar:
    st.markdown("<h1>🛑 LENOVO CHAT</h1>", unsafe_allow_html=True)
    st.caption(f"SECURE LINK: http://{get_ip()}:8501")
    st.markdown("---")
    
    if st.session_state['user']:
        st.markdown(f"<h3>👤 {st.session_state['user']}</h3>", unsafe_allow_html=True)
        st.caption(f"ACCESS LEVEL: {st.session_state['role'].upper()}")
        if st.button("DISCONNECT", use_container_width=True):
            st.session_state['user'] = None
            st.session_state['active_room'] = None
            st.rerun()
        
        st.markdown("---")
        st.markdown("<h3>ACTIVE SIMULATIONS</h3>", unsafe_allow_html=True)
        
        if st.session_state['role'] == "Manager":
            if st.button("➕ INITIATE NEW SIM", use_container_width=True):
                rid = create_room(st.session_state['user'])
                st.session_state['active_room'] = rid
                st.session_state['manual_grading'] = {} # Reset grading on new room
                st.rerun()
        
        if st.button("🔄 REFRESH FEED", use_container_width=True): st.rerun()
        
        rooms = get_rooms()
        if not rooms.empty:
            for _, r in rooms.iterrows():
                # Status Icon Logic
                icon = "🟢"
                if r['status'] == 'Expired': icon = "💀"
                elif r['status'] == 'Offline': icon = "💤"
                
                label = f"{icon} #{r['id']} {r['host']}"
                if r['agent'] != 'Waiting...': label += f" vs {r['agent']}"
                
                c1, c2 = st.columns([4, 1])
                with c1:
                    if st.button(label, key=f"r_{r['id']}", use_container_width=True):
                        st.session_state['active_room'] = r['id']
                        if st.session_state['role'] == 'Agent' and r['agent'] == 'Waiting...':
                            join_room(r['id'], st.session_state['user'])
                        st.session_state['manual_grading'] = {} # Reset
                        st.rerun()
                with c2:
                     # Delete Button for Manager
                     if st.session_state['role'] == "Manager":
                         if st.button("✖", key=f"del_{r['id']}"):
                             delete_room(r['id'])
                             if st.session_state.get('active_room') == r['id']:
                                 st.session_state['active_room'] = None
                             st.rerun()

# MAIN AREA
if not st.session_state['user']:
    c1, c2, c3 = st.columns([1,2,1])
    with c2:
        st.markdown("<br><br><br>", unsafe_allow_html=True)
        st.markdown("<h1 style='text-align: center; font-size: 3em;'>LENOVO CHAT</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: #E2231A; letter-spacing: 3px;'>SECURE SIMULATION ENVIRONMENT</p>", unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        
        with st.form("login_form"):
            name = st.text_input("IDENTIFICATION", placeholder="ENTER NAME")
            role = st.selectbox("CLEARANCE LEVEL", ["Manager", "Agent"])
            st.markdown("<br>", unsafe_allow_html=True)
            if st.form_submit_button("AUTHENTICATE", use_container_width=True):
                if name:
                    st.session_state['user'] = name
                    st.session_state['role'] = role
                    init_db()
                    st.rerun()
else:
    if 'active_room' in st.session_state and st.session_state['active_room']:
        rid = st.session_state['active_room']
        col_chat, col_tools = st.columns([2, 1])
        
        with col_chat:
            st.markdown(f"<h2>CHAT ROOM #{rid}</h2>", unsafe_allow_html=True)
            
            # CALL THE FRAGMENT (Handles Timer + Messages)
            render_live_updates(rid)
            
            # Input outside fragment
            if prompt := st.chat_input("TRANSMIT MESSAGE..."):
                send_msg(rid, st.session_state['user'], st.session_state['role'], prompt)
                st.rerun()
        
        with col_tools:
            st.markdown("<h2>QA TOOLS</h2>", unsafe_allow_html=True)
            if st.session_state['role'] == 'Manager':
                tab1, tab2 = st.tabs(["GRADING", "CONFIG"])
                with tab1:
                    msgs = get_msgs(rid, limit=1000) # Fetch full history for grading
                    sc = get_config('scorecard')
                    
                    # 1. RUN AUTO ANALYSIS
                    if st.button("RUN AUTO-ANALYSIS", use_container_width=True):
                        bd, crit, tips = auto_grade_chat(msgs, sc)
                        st.session_state['manual_grading'] = bd # Init manual with auto
                        st.session_state['crit_fail'] = crit
                        st.session_state['tips'] = tips
                        st.rerun()

                    # 2. MANUAL GRADING FORM
                    if 'manual_grading' in st.session_state and st.session_state['manual_grading']:
                        crit = st.session_state.get('crit_fail')
                        tips = st.session_state.get('tips', [])
                        
                        # Calculate current score based on manual toggles
                        current_score = calculate_final_score(st.session_state['manual_grading'], crit, sc)
                        
                        # Score Display
                        if crit:
                            st.markdown(f"<div class='grade-container grade-fail'><div class='grade-score' style='color:#ff3b30'>0%</div><div style='text-align:center; color:#ff3b30'>{crit}</div></div>", unsafe_allow_html=True)
                        else:
                            cls = "grade-pass" if current_score >= 85 else "grade-fail"
                            color = "#00ffcc" if current_score >= 85 else "#ff3b30"
                            st.markdown(f"<div class='grade-container {cls}'><div class='grade-score' style='color:{color}'>{current_score}%</div></div>", unsafe_allow_html=True)
                        
                        st.write("---")
                        st.markdown("<h4>GRADING MATRIX (EDITABLE)</h4>", unsafe_allow_html=True)
                        
                        # Editable Breakdown
                        for item in sc:
                            name = item['name']
                            current_val = st.session_state['manual_grading'].get(name, "FAIL")
                            
                            # Radio button for manual toggle
                            new_val = st.radio(
                                f"{name} ({item['weight']}%)", 
                                ["PASS", "FAIL"], 
                                index=0 if current_val == "PASS" else 1,
                                horizontal=True,
                                key=f"radio_{name}"
                            )
                            
                            # Update state if changed
                            if new_val != current_val:
                                st.session_state['manual_grading'][name] = new_val
                                st.rerun() # Refresh to update score

                        # Export Button
                        st.write("---")
                        report_text = generate_export_text(rid, msgs, current_score, st.session_state['manual_grading'], crit)
                        st.download_button(
                            label="📥 EXPORT REPORT DATA",
                            data=report_text,
                            file_name=f"Lenovo_Chat_Report_{rid}.txt",
                            mime="text/plain",
                            use_container_width=True
                        )

                    else:
                        st.info("Awaiting Analysis Command...")
                
                with tab2:
                    st.info("System Configuration")
                    curr = get_config('scorecard')
                    new_sc = []
                    for i in curr:
                        with st.expander(i['name']):
                            w = st.number_input("Weight", value=float(i['weight']), key=f"w_{i['id']}")
                            n = st.text_input("Name", value=i['name'], key=f"n_{i['id']}")
                            i['weight'] = w
                            i['name'] = n
                            new_sc.append(i)
                    if st.button("SAVE CONFIGURATION", use_container_width=True):
                        update_config('scorecard', new_sc)
                        st.success("System Updated")
            else:
                st.info("AGENT INTERFACE ACTIVE")
                st.markdown("Awaiting customer input. Maintain protocol.")
    else:
        st.markdown("""
        <div style='text-align: center; margin-top: 100px; opacity: 0.5;'>
            <h2>SYSTEM READY</h2>
            <p>SELECT SIMULATION TO ENGAGE</p>
        </div>
        """, unsafe_allow_html=True)
