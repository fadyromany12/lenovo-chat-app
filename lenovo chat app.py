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
    page_icon="💬", 
    layout="wide",
    initial_sidebar_state="expanded",
    # Hide default menu items
    menu_items={
        'Get Help': None,
        'Report a bug': None,
        'About': None
    }
)

# --- CUSTOM CSS STYLING (FORCED DARK MODE & ANIMATIONS) ---
st.markdown("""
<style>
    /* --- HIDE STREAMLIT UI ELEMENTS --- */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .stDeployButton {display:none;}
    [data-testid="stToolbar"] {visibility: hidden;}
    [data-testid="stHeader"] {visibility: hidden;}
    
    /* Global Dark Theme Enforcement */
    [data-testid="stAppViewContainer"] {
        background-color: #121212;
        color: #e0e0e0;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }

    /* Animations */
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(10px); }
        to { opacity: 1; transform: translateY(0); }
    }
    
    @keyframes pulse {
        0% { box-shadow: 0 0 0 0 rgba(226, 35, 26, 0.4); }
        70% { box-shadow: 0 0 0 10px rgba(226, 35, 26, 0); }
        100% { box-shadow: 0 0 0 0 rgba(226, 35, 26, 0); }
    }

    /* Sidebar Styling */
    section[data-testid="stSidebar"] {
        background-color: #050505;
        border-right: 1px solid #333;
    }
    section[data-testid="stSidebar"] h1, section[data-testid="stSidebar"] h2, section[data-testid="stSidebar"] h3 {
        color: #E2231A !important;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    
    /* Input Fields */
    .stTextInput input, .stSelectbox div[data-baseweb="select"] > div {
        background-color: #1e1e1e !important;
        color: white !important;
        border: 1px solid #444 !important;
        border-radius: 6px;
        transition: border-color 0.3s;
    }
    .stTextInput input:focus, .stSelectbox div[data-baseweb="select"] > div:focus-within {
        border-color: #E2231A !important;
    }
    
    /* Chat Bubbles */
    .stChatMessage {
        background-color: #1e1e1e;
        border: 1px solid #333;
        border-radius: 12px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.2);
        animation: fadeIn 0.4s ease-out;
        transition: transform 0.2s;
    }
    .stChatMessage:hover {
        transform: scale(1.01);
        border-color: #444;
    }
    div[data-testid="stChatMessageAvatar"] {
        background-color: #E2231A;
        border-radius: 50%;
    }
    
    /* Buttons */
    .stButton > button {
        background: linear-gradient(135deg, #E2231A 0%, #D11006 100%);
        color: white;
        border: none;
        border-radius: 6px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        padding: 0.5rem 1rem;
        transition: all 0.3s ease;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
    }
    .stButton > button:hover {
        background: linear-gradient(135deg, #ff4d4d 0%, #E2231A 100%);
        transform: translateY(-2px);
        box-shadow: 0 6px 12px rgba(226, 35, 26, 0.4);
    }
    .stButton > button:active {
        transform: translateY(0);
    }

    /* Result Boxes */
    .grade-container {
        padding: 15px;
        border-radius: 8px;
        margin-bottom: 12px;
        border-left: 5px solid;
        background-color: #1a1a1a;
        animation: fadeIn 0.5s ease-out;
    }
    .grade-pass { border-color: #2e7d32; background: linear-gradient(90deg, rgba(46,125,50,0.1) 0%, rgba(0,0,0,0) 100%); color: #a5d6a7; }
    .grade-fail { border-color: #c62828; background: linear-gradient(90deg, rgba(198,40,40,0.1) 0%, rgba(0,0,0,0) 100%); color: #ef9a9a; }
    .grade-score { font-size: 3em; font-weight: 800; text-align: center; margin: 15px 0; text-shadow: 0 2px 4px rgba(0,0,0,0.5); }
    
    /* Timer Badges */
    .timer-badge {
        font-weight: bold;
        padding: 8px 16px;
        border-radius: 20px;
        display: block;
        text-align: center;
        width: 100%;
        margin-bottom: 15px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.2);
        animation: fadeIn 0.3s;
        font-size: 1.1em;
    }
    .timer-ok { color: #4caf50; background: rgba(76, 175, 80, 0.15); border: 1px solid #4caf50; }
    .timer-warn { color: #ff9800; background: rgba(255, 152, 0, 0.15); border: 1px solid #ff9800; }
    .timer-crit { color: #f44336; background: rgba(244, 67, 54, 0.15); border: 1px solid #f44336; animation: pulse 2s infinite; }
    .timer-wait { color: #aaa; background: rgba(255, 255, 255, 0.08); border: 1px solid #555; }

    /* Custom Scrollbar */
    ::-webkit-scrollbar {
        width: 10px;
        background: #0e0e0e;
    }
    ::-webkit-scrollbar-thumb {
        background: #333;
        border-radius: 5px;
    }
    ::-webkit-scrollbar-thumb:hover {
        background: #555;
    }

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
                st.markdown(f"<div class='timer-badge timer-ok'>⏱️ Reply Time: {int(diff)}s / 300s</div>", unsafe_allow_html=True)
            else:
                st.markdown(f"<div class='timer-badge timer-crit'>⚠️ OVERTIME: {int(diff)}s</div>", unsafe_allow_html=True)
        else:
            st.markdown(f"<div class='timer-badge timer-wait'>⏳ Customer Typing...</div>", unsafe_allow_html=True)
            
    elif status == 'Expired':
        st.markdown(f"<div class='timer-badge timer-crit'>💀 CHAT EXPIRED (Agent No Reply > 5m)</div>", unsafe_allow_html=True)
    elif status == 'Offline':
        st.markdown(f"<div class='timer-badge timer-warn'>💤 OFFLINE (Inactive > 10m)</div>", unsafe_allow_html=True)

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
            st.markdown("<div style='text-align: center; color: #666; margin-top: 50px;'>No messages yet. Start typing!</div>", unsafe_allow_html=True)
        else:
            for _, m in msgs.iterrows():
                with st.chat_message(m['role'], avatar="👤" if m['role']=='Agent' else "👔"):
                    st.write(f"**{m['sender']}**: {m['text']}")

# --- APP LAYOUT ---
if 'user' not in st.session_state: st.session_state['user'] = None
if 'manual_grading' not in st.session_state: st.session_state['manual_grading'] = {} # Store grading state

# SIDEBAR
with st.sidebar:
    st.title("Lenovo Chat App")
    st.caption(f"Network: http://{get_ip()}:8501")
    
    if st.session_state['user']:
        st.write(f"Logged in as: **{st.session_state['user']}** ({st.session_state['role']})")
        if st.button("Logout", use_container_width=True):
            st.session_state['user'] = None
            st.session_state['active_room'] = None
            st.rerun()
        
        st.divider()
        st.subheader("Rooms")
        if st.session_state['role'] == "Manager":
            if st.button("➕ Create Room", use_container_width=True):
                rid = create_room(st.session_state['user'])
                st.session_state['active_room'] = rid
                st.session_state['manual_grading'] = {} # Reset grading on new room
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
                         if st.button("🗑️", key=f"del_{r['id']}"):
                             delete_room(r['id'])
                             if st.session_state.get('active_room') == r['id']:
                                 st.session_state['active_room'] = None
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
    if 'active_room' in st.session_state and st.session_state['active_room']:
        rid = st.session_state['active_room']
        col_chat, col_tools = st.columns([2, 1])
        
        with col_chat:
            st.subheader(f"Chat Room #{rid}")
            
            # CALL THE FRAGMENT (Handles Timer + Messages)
            render_live_updates(rid)
            
            # Input outside fragment
            if prompt := st.chat_input("Message..."):
                send_msg(rid, st.session_state['user'], st.session_state['role'], prompt)
                st.rerun()
        
        with col_tools:
            st.subheader("Tools")
            if st.session_state['role'] == 'Manager':
                tab1, tab2 = st.tabs(["Grading", "Setup"])
                with tab1:
                    msgs = get_msgs(rid, limit=1000) # Fetch full history for grading
                    sc = get_config('scorecard')
                    
                    # 1. RUN AUTO ANALYSIS
                    if st.button("Run Auto-Analysis", use_container_width=True):
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
                            st.markdown(f"<div class='grade-container grade-fail'><div class='grade-score'>0%</div><div style='text-align:center'>{crit}</div></div>", unsafe_allow_html=True)
                        else:
                            cls = "grade-pass" if current_score >= 85 else "grade-fail"
                            st.markdown(f"<div class='grade-container {cls}'><div class='grade-score'>{current_score}%</div></div>", unsafe_allow_html=True)
                        
                        st.write("---")
                        st.write("### Grading Breakdown (Editable)")
                        
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
                            label="📥 Export Chat & Report",
                            data=report_text,
                            file_name=f"Lenovo_Chat_Report_{rid}.txt",
                            mime="text/plain",
                            use_container_width=True
                        )

                    else:
                        st.info("Click 'Run Auto-Analysis' to start grading.")
                
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
