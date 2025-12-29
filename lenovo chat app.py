import streamlit as st
import sqlite3
import json
import datetime
import pandas as pd
import time
import socket
import re

# Try to import FPDF for PDF generation, handle if missing
try:
    from fpdf import FPDF
    HAS_FPDF = True
except ImportError:
    HAS_FPDF = False

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

    /* --- TIMERS & TYPING --- */
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
    
    .typing-indicator {
        border-color: #00ffcc; 
        color: #00ffcc;
        animation: pulse-green 2s infinite;
        font-style: italic;
    }
    
    /* --- SCENARIO CARD --- */
    .scenario-card {
        background: rgba(226, 35, 26, 0.1);
        border: 1px solid #E2231A;
        padding: 15px;
        margin-bottom: 20px;
        border-radius: 4px;
        color: #fff;
    }
    .scenario-title {
        color: #E2231A;
        font-family: 'Rajdhani', sans-serif;
        font-weight: bold;
        letter-spacing: 2px;
        margin-bottom: 5px;
    }

    /* Scrollbar */
    ::-webkit-scrollbar { width: 8px; background: #050505; }
    ::-webkit-scrollbar-thumb { background: #333; border: 1px solid #000; }
    ::-webkit-scrollbar-thumb:hover { background: #E2231A; }

</style>
""", unsafe_allow_html=True)

# --- CONSTANTS & DICTIONARIES ---
DB_FILE = "qa_database.db"
# Updated Sound URL (Crisp Notification)
SOUND_URL = "https://assets.mixkit.co/active_storage/sfx/2346/2346-preview.mp3" 

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

# 4. HIERARCHICAL SCORECARD
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
    c.execute('''CREATE TABLE IF NOT EXISTS rooms (id INTEGER PRIMARY KEY AUTOINCREMENT, host TEXT, agent TEXT, status TEXT, created_at TIMESTAMP, last_activity TIMESTAMP, scenario TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS messages (id INTEGER PRIMARY KEY AUTOINCREMENT, room_id INTEGER, sender TEXT, role TEXT, text TEXT, timestamp TIMESTAMP)''')
    c.execute('''CREATE TABLE IF NOT EXISTS config (key TEXT PRIMARY KEY, value TEXT)''')
    c.execute("SELECT * FROM config WHERE key='scorecard'")
    if not c.fetchone():
        c.execute("INSERT INTO config (key, value) VALUES (?, ?)", ('scorecard', json.dumps(DEFAULT_SCORECARD)))
    
    # MIGRATION: Ensure 'scenario' column exists for older DB files
    try:
        c.execute("ALTER TABLE rooms ADD COLUMN scenario TEXT")
    except:
        pass # Column likely exists

    conn.commit()
    conn.close()

def get_rooms():
    try:
        conn = sqlite3.connect(DB_FILE)
        df = pd.read_sql_query("SELECT * FROM rooms ORDER BY created_at DESC", conn)
        conn.close()
        return df
    except: return pd.DataFrame()

def create_room(host, scenario=None):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    now = datetime.datetime.now()
    sc_json = json.dumps(scenario) if scenario else None
    c.execute("INSERT INTO rooms (host, agent, status, created_at, last_activity, scenario) VALUES (?, ?, ?, ?, ?, ?)", (host, 'Waiting...', 'Active', now, now, sc_json))
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
    if not text.strip(): return
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

def get_room_details(rid):
    try:
        conn = sqlite3.connect(DB_FILE)
        row = conn.execute("SELECT scenario FROM rooms WHERE id = ?", (rid,)).fetchone()
        conn.close()
        return json.loads(row[0]) if row and row[0] else None
    except: return None

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
        
        # Logic: If last msg was Agent, it's Customer's turn. If last msg was Customer (or None), it's Agent's turn.
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

# --- SENTIMENT ENGINE ---
def calculate_sentiment(text):
    """Returns a score between 0 (Negative) and 100 (Positive). Starts at 50."""
    score = 50
    lower_text = text.lower()
    
    # Check Negative
    for w in SENTIMENT_DICT['negative']['high']:
        if w in lower_text: score -= 15
    for w in SENTIMENT_DICT['negative']['medium']:
        if w in lower_text: score -= 5
        
    # Check Positive
    for w in SENTIMENT_DICT['positive']['high']:
        if w in lower_text: score += 15
    for w in SENTIMENT_DICT['positive']['medium']:
        if w in lower_text: score += 5
        
    return max(0, min(100, score))

def analyze_conversation_sentiment(msgs):
    """Analyzes only the CUSTOMER/MANAGER messages to gauge mood."""
    if msgs.empty: return 50
    # Filter for Customer/Manager messages (assuming Role != Agent)
    cust_msgs = msgs[msgs['role'] != 'Agent']
    if cust_msgs.empty: return 50
    
    # Analyze last 5 messages for "Live" feel
    recent_msgs = cust_msgs.tail(5)
    total_score = 0
    for t in recent_msgs['text']:
        total_score += calculate_sentiment(str(t))
    
    return int(total_score / len(recent_msgs))

# --- PDF GENERATION ---
def generate_pdf_report(rid, msgs, score, breakdown, crit, scenario):
    if not HAS_FPDF:
        return None
        
    class PDF(FPDF):
        def header(self):
            self.set_font('Arial', 'B', 15)
            self.cell(0, 10, f'Lenovo Chat Simulation Report - Room #{rid}', 0, 1, 'C')
            self.ln(5)
            
        def footer(self):
            self.set_y(-15)
            self.set_font('Arial', 'I', 8)
            self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')

    pdf = PDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    
    # 1. Header Info
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, f"Date: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", 0, 1)
    
    if scenario:
        pdf.cell(0, 10, f"Scenario: {scenario.get('name', 'N/A')} - {scenario.get('product', 'N/A')}", 0, 1)
        pdf.set_font("Arial", 'I', 10)
        pdf.multi_cell(0, 5, f"Issue: {scenario.get('issue', 'N/A')}")
        pdf.ln(5)

    # 2. Score
    pdf.set_font("Arial", 'B', 14)
    if crit:
        pdf.set_text_color(255, 0, 0)
        pdf.cell(0, 10, f"FINAL SCORE: 0% (CRITICAL FAIL)", 0, 1)
        pdf.set_font("Arial", size=10)
        pdf.cell(0, 10, f"Reason: {crit}", 0, 1)
    else:
        color = (0, 200, 0) if score >= 85 else (200, 0, 0)
        pdf.set_text_color(*color)
        pdf.cell(0, 10, f"FINAL SCORE: {score}%", 0, 1)
    
    pdf.set_text_color(0, 0, 0)
    pdf.ln(5)
    
    # 3. Grading
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, "Grading Breakdown:", 0, 1)
    pdf.set_font("Arial", size=10)
    for k, v in breakdown.items():
        pdf.cell(0, 6, f"{k}: {v}", 0, 1)
    
    pdf.ln(10)
    
    # 4. Transcript
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, "Chat Transcript:", 0, 1)
    pdf.set_font("Courier", size=9)
    
    for _, m in msgs.iterrows():
        prefix = "AGENT: " if m['role'] == 'Agent' else f"{m['sender'].upper()}: "
        # Clean text
        clean_text = m['text'].encode('latin-1', 'replace').decode('latin-1')
        pdf.multi_cell(0, 5, f"[{m['timestamp']}] {prefix}{clean_text}")
        pdf.ln(1)
        
    return pdf.output(dest='S').encode('latin-1')


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

def generate_export_text(rid, msgs, score, breakdown, crit, scenario):
    """Generates a text report"""
    lines = []
    lines.append(f"LENOVO CHAT REPORT - ROOM #{rid}")
    lines.append("="*40)
    lines.append(f"Date: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    if scenario:
        lines.append(f"SCENARIO: {scenario.get('name')} | {scenario.get('product')}")
        lines.append(f"ISSUE: {scenario.get('issue')}")
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
    """Refreshes chat messages & checks timer every 1 second."""
    
    # 1. Check Status
    status, diff, is_agent_turn = check_room_status(rid)
    user_role = st.session_state.get('role')
    
    # 2. Render Timer/Status Badge (VISIBLE OUTSIDE CHAT BOX)
    if status == 'Active':
        # Logic to show who is typing/waiting
        if is_agent_turn:
            if user_role == 'Agent':
                 # Agent sees: YOUR TURN
                 st.markdown(f"<div class='timer-badge timer-warn'>👉 ACTION REQUIRED: YOUR TURN ({int(diff)}s)</div>", unsafe_allow_html=True)
            else:
                 # Customer/Manager sees: Agent Writing
                 st.markdown(f"<div class='timer-badge typing-indicator'>🔴 AGENT WRITING...</div>", unsafe_allow_html=True)
        else:
            if user_role == 'Agent':
                # Agent sees: Customer Writing
                st.markdown(f"<div class='timer-badge typing-indicator'>👤 CUSTOMER WRITING...</div>", unsafe_allow_html=True)
            else:
                # Customer sees: Waiting for Agent (technically customer turn)
                st.markdown(f"<div class='timer-badge timer-ok'>💬 PLEASE REPLY...</div>", unsafe_allow_html=True)

    elif status == 'Expired':
        st.markdown(f"<div class='timer-badge timer-crit'>💀 CHAT EXPIRED (AGENT TIMEOUT)</div>", unsafe_allow_html=True)
    elif status == 'Offline':
        st.markdown(f"<div class='timer-badge timer-warn'>💤 OFFLINE (SESSION INACTIVE)</div>", unsafe_allow_html=True)

    # 3. Render Messages inside Scrollable Container
    with st.container(height=550):
        msgs = get_msgs(rid, limit=50) 
        
        # --- SCENARIO DISPLAY (AGENT VIEW) ---
        if user_role == 'Agent':
             sc_data = get_room_details(rid)
             if sc_data:
                 st.markdown(f"""
                 <div class='scenario-card'>
                    <div class='scenario-title'>🎯 MISSION BRIEF</div>
                    <b>CUSTOMER:</b> {sc_data.get('name', 'N/A')}<br>
                    <b>DEVICE:</b> {sc_data.get('product', 'N/A')}<br>
                    <b>ISSUE:</b> {sc_data.get('issue', 'N/A')}
                 </div>
                 """, unsafe_allow_html=True)
        # -------------------------------------
        
        # --- NEW MESSAGE SOUND NOTIFICATION ---
        if not msgs.empty:
            latest_id = msgs['id'].max()
            last_seen_key = f"last_msg_id_{rid}"
            
            # Init state if new room
            if last_seen_key not in st.session_state:
                st.session_state[last_seen_key] = latest_id
            
            # Detect new message
            if latest_id > st.session_state[last_seen_key]:
                new_msgs = msgs[msgs['id'] > st.session_state[last_seen_key]]
                current_user = st.session_state.get('user')
                
                # Sound Logic: Only play if NOT muted
                if not st.session_state.get('mute_sounds', False):
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
                # Handle Image "Simulation"
                if "[ATTACHMENT SENT]" in m['text']:
                    with st.chat_message(m['role'], avatar="👤" if m['role']=='Agent' else "👔"):
                        st.markdown(f"**{m['sender']}** sent an attachment:")
                        st.image("https://placehold.co/600x400/1a1a1a/e2231a?text=BROKEN+DEVICE+IMAGE", caption="attachment.jpg")
                else:
                    with st.chat_message(m['role'], avatar="👤" if m['role']=='Agent' else "👔"):
                        st.write(f"**{m['sender']}**: {m['text']}")

# --- APP LAYOUT ---
if 'user' not in st.session_state: st.session_state['user'] = None
if 'manual_grading' not in st.session_state: st.session_state['manual_grading'] = {} 

# SIDEBAR
with st.sidebar:
    st.markdown("<h1>🛑 LENOVO CHAT</h1>", unsafe_allow_html=True)
    st.caption(f"SECURE LINK: http://{get_ip()}:8501")
    st.markdown("---")
    
    # NEW: Mute Toggle
    st.checkbox("🔕 MUTE SOUNDS", key="mute_sounds", help="Disable typing and notification sounds")

    if st.session_state['user']:
        st.markdown(f"<h3>👤 {st.session_state['user']}</h3>", unsafe_allow_html=True)
        st.caption(f"ACCESS LEVEL: {st.session_state['role'].upper()}")
        
        # --- NEW: Live Sentiment Meter ---
        if st.session_state.get('active_room'):
            st.markdown("---")
            st.markdown("<h3>📊 LIVE SENTIMENT</h3>", unsafe_allow_html=True)
            # Need to fetch msgs here or pass it? Better to fetch light version
            current_msgs = get_msgs(st.session_state['active_room'], 20)
            sentiment_score = analyze_conversation_sentiment(current_msgs)
            
            # Color logic
            bar_color = "red"
            if sentiment_score > 40: bar_color = "yellow"
            if sentiment_score > 70: bar_color = "#00ffcc"
            
            st.caption(f"CUSTOMER MOOD: {sentiment_score}/100")
            st.markdown(f"""
            <div style="background-color: #333; width: 100%; height: 10px; border-radius: 5px;">
                <div style="background-color: {bar_color}; width: {sentiment_score}%; height: 100%; border-radius: 5px; transition: width 0.5s;"></div>
            </div>
            """, unsafe_allow_html=True)
        # ---------------------------------
        
        # --- NEW: Quick Actions for Agent ---
        if st.session_state['role'] == "Agent" and st.session_state.get('active_room'):
             st.markdown("---")
             st.markdown("<h3>⚡ QUICK COMMS</h3>", unsafe_allow_html=True)
             c1, c2 = st.columns(2)
             if c1.button("👋 Hello"):
                 send_msg(st.session_state['active_room'], st.session_state['user'], "Agent", "Hello! Thank you for contacting Lenovo Support. My name is " + st.session_state['user'] + ". How can I assist you today?")
                 st.rerun()
             if c2.button("✋ Hold"):
                 send_msg(st.session_state['active_room'], st.session_state['user'], "Agent", "Please bear with me for a moment while I check that information for you.")
                 st.rerun()
             if c1.button("🙏 Sorry"):
                 send_msg(st.session_state['active_room'], st.session_state['user'], "Agent", "I apologize for the inconvenience you are facing.")
                 st.rerun()
             if c2.button("👋 Bye"):
                 send_msg(st.session_state['active_room'], st.session_state['user'], "Agent", "Thank you for choosing Lenovo. Have a wonderful day!")
                 st.rerun()
        # ------------------------------------

        st.markdown("---")
        if st.button("LOGOUT / DISCONNECT", use_container_width=True):
            st.session_state['user'] = None
            st.session_state['active_room'] = None
            st.rerun()
        
        st.markdown("---")
        st.markdown("<h3>ACTIVE SIMULATIONS</h3>", unsafe_allow_html=True)
        
        if st.session_state['role'] == "Manager":
            # --- NEW: Scenario Injection ---
            with st.expander("➕ INITIATE NEW SIM", expanded=False):
                with st.form("new_sim_form"):
                    cust_name = st.text_input("Customer Name", "John Doe")
                    prod_model = st.selectbox("Product", ["ThinkPad X1", "Legion 5 Pro", "Yoga 9i", "IdeaPad 3"])
                    issue_desc = st.text_area("Issue Description", "Blue Screen of Death when launching games.")
                    if st.form_submit_button("LAUNCH SIMULATION"):
                        scenario = {"name": cust_name, "product": prod_model, "issue": issue_desc}
                        rid = create_room(st.session_state['user'], scenario)
                        st.session_state['active_room'] = rid
                        st.session_state['manual_grading'] = {} 
                        st.rerun()
            # -------------------------------
        
        if st.button("🔄 REFRESH FEED", use_container_width=True): st.rerun()
        
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
                        if st.session_state['role'] == 'Agent' and r['agent'] == 'Waiting...':
                            join_room(r['id'], st.session_state['user'])
                        st.session_state['manual_grading'] = {} 
                        st.rerun()
                with c2:
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
            
            # NEW: TYPING SOUNDS JS INJECTION
            mute_str = "true" if st.session_state.get('mute_sounds', False) else "false"
            st.markdown(f"""
            <script>
                // Initialize sound only once if possible, or update mute state
                var typingAudio = new Audio("https://assets.mixkit.co/active_storage/sfx/2364/2364-preview.mp3"); // Clicky sound
                window.muteTyping = {mute_str};
                
                if (!window.typingListenerAttached) {{
                    document.addEventListener('keydown', function(e) {{
                        // Check if typing in text field and not muted
                        if ((e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') && !window.muteTyping) {{
                            // Clone to allow overlapping sounds (fast typing)
                            var sound = typingAudio.cloneNode();
                            sound.volume = 0.1; // Subtle volume
                            sound.play().catch(e => console.log(e));
                        }}
                    }});
                    window.typingListenerAttached = true;
                }}
            </script>
            """, unsafe_allow_html=True)
        
        with col_tools:
            st.markdown("<h2>QA TOOLS</h2>", unsafe_allow_html=True)
            
            # --- NEW: FILE ATTACHMENT SIMULATION (FOR CUSTOMER/MANAGER) ---
            if st.session_state['role'] == 'Manager':
                if st.button("📎 SIMULATE ATTACHMENT", use_container_width=True):
                    send_msg(rid, st.session_state['user'], st.session_state['role'], "[ATTACHMENT SENT]: broken_screen.jpg")
                    st.rerun()
            # --------------------------------------------------------------

            if st.session_state['role'] == 'Manager':
                tab1, tab2 = st.tabs(["GRADING", "CONFIG"])
                with tab1:
                    msgs = get_msgs(rid, limit=1000)
                    sc = get_config('scorecard')
                    
                    if st.button("RUN AUTO-ANALYSIS", use_container_width=True):
                        bd, crit, tips = auto_grade_chat(msgs, sc)
                        st.session_state['manual_grading'] = bd 
                        st.session_state['crit_fail'] = crit
                        st.session_state['tips'] = tips
                        st.rerun()

                    if 'manual_grading' in st.session_state and st.session_state['manual_grading']:
                        crit = st.session_state.get('crit_fail')
                        tips = st.session_state.get('tips', [])
                        
                        current_score = calculate_final_score(st.session_state['manual_grading'], crit, sc)
                        
                        if crit:
                            st.markdown(f"<div class='grade-container grade-fail'><div class='grade-score' style='color:#ff3b30'>0%</div><div style='text-align:center; color:#ff3b30'>{crit}</div></div>", unsafe_allow_html=True)
                        else:
                            cls = "grade-pass" if current_score >= 85 else "grade-fail"
                            color = "#00ffcc" if current_score >= 85 else "#ff3b30"
                            st.markdown(f"<div class='grade-container {cls}'><div class='grade-score' style='color:{color}'>{current_score}%</div></div>", unsafe_allow_html=True)
                        
                        # NEW: Manager Clear Chat
                        if st.button("🗑️ CLEAR CHAT HISTORY", use_container_width=True):
                             delete_room(rid)
                             scenario_data = get_room_details(rid)
                             create_room(st.session_state['user'], scenario_data) # Recreate same room
                             st.rerun()

                        st.write("---")
                        st.markdown("<h4>GRADING MATRIX</h4>", unsafe_allow_html=True)
                        
                        for item in sc:
                            name = item['name']
                            current_val = st.session_state['manual_grading'].get(name, "FAIL")
                            
                            new_val = st.radio(
                                f"{name} ({item['weight']}%)", 
                                ["PASS", "FAIL"], 
                                index=0 if current_val == "PASS" else 1,
                                horizontal=True,
                                key=f"radio_{name}"
                            )
                            
                            if new_val != current_val:
                                st.session_state['manual_grading'][name] = new_val
                                st.rerun() 

                        st.write("---")
                        
                        # --- PDF EXPORT LOGIC ---
                        sc_data = get_room_details(rid)
                        if HAS_FPDF:
                            pdf_bytes = generate_pdf_report(rid, msgs, current_score, st.session_state['manual_grading'], crit, sc_data)
                            st.download_button(
                                label="📄 EXPORT PDF REPORT",
                                data=pdf_bytes,
                                file_name=f"Lenovo_Chat_Report_{rid}.pdf",
                                mime="application/pdf",
                                use_container_width=True
                            )
                        else:
                             # Fallback to text
                            report_text = generate_export_text(rid, msgs, current_score, st.session_state['manual_grading'], crit, sc_data)
                            st.warning("Install 'fpdf' for PDF exports. Using TXT fallback.")
                            st.download_button(
                                label="📥 EXPORT TXT REPORT",
                                data=report_text,
                                file_name=f"Lenovo_Chat_Report_{rid}.txt",
                                mime="text/plain",
                                use_container_width=True
                            )
                        # -------------------------

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
