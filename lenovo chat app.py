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

# --- CUSTOM CSS STYLING (FORCED DARK MODE) ---
st.markdown("""
<style>
    /* Global Dark Theme */
    .stApp {
        background-color: #121212;
        color: #E0E0E0;
    }
    
    /* Sidebar Styling */
    section[data-testid="stSidebar"] {
        background-color: #000000;
        border-right: 1px solid #333;
    }
    section[data-testid="stSidebar"] h1, section[data-testid="stSidebar"] h2, section[data-testid="stSidebar"] h3 {
        color: #E2231A !important;
    }
    section[data-testid="stSidebar"] p, section[data-testid="stSidebar"] span {
        color: #bbbbbb;
    }
    
    /* Input Fields */
    .stTextInput > div > div > input {
        background-color: #2D2D2D;
        color: white;
        border: 1px solid #444;
    }
    .stSelectbox > div > div > div {
        background-color: #2D2D2D;
        color: white;
    }
    
    /* Primary Buttons (Lenovo Red) */
    .stButton > button {
        background-color: #E2231A;
        color: white;
        border: none;
        border-radius: 4px;
        font-weight: 600;
        transition: background 0.2s;
    }
    .stButton > button:hover {
        background-color: #ff3b30;
        box-shadow: 0 0 10px rgba(226, 35, 26, 0.4);
    }
    
    /* Chat Interface */
    .stChatMessage {
        background-color: #1E1E1E;
        border: 1px solid #333;
        border-radius: 8px;
    }
    .stChatMessage [data-testid="stChatMessageContent"] {
        color: #E0E0E0;
    }
    div[data-testid="stChatMessageAvatar"] {
        background-color: #E2231A;
    }

    /* Metrics */
    div[data-testid="stMetricValue"] {
        color: #ffffff !important;
    }
    
    /* Tabs */
    .stTabs [data-baseweb="tab-list"] button {
        background-color: #1E1E1E;
        color: #888;
        border-radius: 4px;
        margin-right: 5px;
    }
    .stTabs [aria-selected="true"] {
        background-color: #E2231A !important;
        color: white !important;
    }

    /* Custom Alert Boxes */
    .success-box { padding: 12px; background-color: #0f3d24; color: #81c784; border-left: 4px solid #2e7d32; margin-bottom: 8px; border-radius: 4px; }
    .fail-box { padding: 12px; background-color: #3d0f0f; color: #e57373; border-left: 4px solid #c62828; margin-bottom: 8px; border-radius: 4px; }
    .tip-box { padding: 12px; background-color: #3e2723; color: #ffcc80; border-left: 4px solid #f57c00; margin-bottom: 8px; border-radius: 4px; }

</style>
""", unsafe_allow_html=True)

# --- CONFIGURATION & CONSTANTS ---
DB_FILE = "qa_database.db"

# 1. FULL KEYWORD DICTIONARY
DEFAULT_KEYWORDS = {
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
    "closing": [
        'anything else', 'further', 'assist you', 'other questions', 'help you with',
        'additional questions', 'support you', 'else i can do', 'proceed with', 
        'ready to', 'secure this'
    ],
    "prof_closing": [
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
    "cx_critical": [
        'shut up', 'idiot', 'stupid', 'dumb', 'hate you', 'don\'t care', 'whatever', 
        'ridiculous', 'liar', 'waste of time', 'bullshit', 'damn'
    ],
    "comp_critical": [
        'credit card', 'cvv', 'card number', 'expiry', 'social security', 'ssn', 
        'password', 'login credentials', 'pwd'
    ],
    "biz_critical": [
        'stacking', 'unauthorized discount', 'fake price'
    ]
}

# 2. FULL SCORECARD DEFINITION
DEFAULT_SCORECARD = [
    # Opening
    {"id": "greet", "name": "Opening: Greet & Intro", "weight": 2.0, "keywords": "greetings"},
    {"id": "confirm", "name": "Opening: Confirm Name/Reason", "weight": 3.0, "keywords": ""}, 
    # Communication
    {"id": "listening", "name": "Comm: Active Listening", "weight": 5.0, "keywords": ""},
    {"id": "clear", "name": "Comm: Clear Language", "weight": 5.0, "keywords": ""},
    {"id": "empathy", "name": "Comm: Empathy", "weight": 5.0, "keywords": "empathy"},
    {"id": "tone", "name": "Comm: Tone", "weight": 2.0, "keywords": ""},
    {"id": "hold", "name": "Comm: Hold Etiquette", "weight": 3.0, "keywords": "hold"},
    # Sales
    {"id": "discovery", "name": "Sales: Discovery Questions", "weight": 7.5, "keywords": "discovery"},
    {"id": "product", "name": "Sales: Product Knowledge", "weight": 7.5, "keywords": ""},
    {"id": "solution", "name": "Sales: Right Solution", "weight": 7.5, "keywords": ""},
    {"id": "objection", "name": "Sales: Objection Handling", "weight": 7.5, "keywords": ""},
    {"id": "warranty", "name": "Sales: Warranty/Accessories", "weight": 15.0, "keywords": "warranty"},
    # Process
    {"id": "next_steps", "name": "Process: Next Steps", "weight": 5.0, "keywords": ""},
    {"id": "compliance", "name": "Process: Compliance", "weight": 10.0, "keywords": ""},
    # Closing
    {"id": "addressed", "name": "Closing: Query Addressed", "weight": 2.0, "keywords": "closing"},
    {"id": "end_prof", "name": "Closing: Professional End", "weight": 2.0, "keywords": "prof_closing"},
    {"id": "csat", "name": "Closing: CSAT Statement", "weight": 5.0, "keywords": "csat"}
]

# 3. COACHING TIPS
COACHING_TIPS = {
    "greet": "Start with a standard greeting: 'Thank you for contacting Lenovo, my name is...'",
    "empathy": "Use empathy statements like 'I understand how frustrating this is' or 'I apologize for the delay'.",
    "discovery": "Ask at least 2 probing questions (Who, What, Where, When, Why) to uncover customer needs.",
    "hold": "Ask for permission before placing the customer on hold: 'May I place you on a brief hold?'",
    "warranty": "Don't forget to mention Warranty upgrades or Accessories (ADP, Premium Support).",
    "closing": "Ensure you explicitly ask if the customer needs further assistance.",
    "end_prof": "Close professionally: 'Thank you for choosing Lenovo, have a great day.'",
    "csat": "Remember to ask for the survey/feedback at the very end.",
    "cx_critical": "Avoid negative words. Remain professional even if the customer is difficult.",
    "comp_critical": "NEVER ask for Credit Card details or Passwords in chat."
}

# --- DATABASE FUNCTIONS ---
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS rooms 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, host TEXT, agent TEXT, status TEXT, created_at TIMESTAMP)''')
    c.execute('''CREATE TABLE IF NOT EXISTS messages 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, room_id INTEGER, sender TEXT, role TEXT, text TEXT, timestamp TIMESTAMP)''')
    c.execute('''CREATE TABLE IF NOT EXISTS config 
                 (key TEXT PRIMARY KEY, value TEXT)''')
    
    # Init Config if empty
    c.execute("SELECT * FROM config WHERE key='scorecard'")
    if not c.fetchone():
        c.execute("INSERT INTO config (key, value) VALUES (?, ?)", ('scorecard', json.dumps(DEFAULT_SCORECARD)))
    
    conn.commit()
    conn.close()

def get_rooms():
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query("SELECT * FROM rooms ORDER BY created_at DESC", conn)
    conn.close()
    return df

def create_room(host_name):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT INTO rooms (host, agent, status, created_at) VALUES (?, ?, ?, ?)", 
              (host_name, 'Waiting...', 'Active', datetime.datetime.now()))
    room_id = c.lastrowid
    conn.commit()
    conn.close()
    return room_id

def join_room(room_id, agent_name):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("UPDATE rooms SET agent = ? WHERE id = ?", (agent_name, room_id))
    conn.commit()
    conn.close()

def send_message(room_id, sender, role, text):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT INTO messages (room_id, sender, role, text, timestamp) VALUES (?, ?, ?, ?, ?)",
              (room_id, sender, role, text, datetime.datetime.now()))
    conn.commit()
    conn.close()

def get_messages(room_id):
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query("SELECT * FROM messages WHERE room_id = ? ORDER BY timestamp ASC", conn, params=(room_id,))
    conn.close()
    return df

def get_config(key):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT value FROM config WHERE key=?", (key,))
    row = c.fetchone()
    conn.close()
    return json.loads(row[0]) if row else []

def update_config(key, value):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("REPLACE INTO config (key, value) VALUES (?, ?)", (key, json.dumps(value)))
    conn.commit()
    conn.close()

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "127.0.0.1"

# --- AUTO GRADING ENGINE ---
def perform_grading(messages, scorecard):
    if messages.empty:
        return 0, {}, None, []

    agent_msgs = messages[messages['role'] == 'Agent']
    full_text = " ".join(agent_msgs['text'].str.lower().tolist())
    
    score = 0
    max_score = 0
    breakdown = {}
    critical_fail = None
    suggestions = []

    # 1. Critical Checks
    for word in DEFAULT_KEYWORDS['cx_critical']:
        if word in full_text:
            critical_fail = f"CX Critical: Found '{word}'"
            suggestions.append(COACHING_TIPS['cx_critical'])
            break
    if not critical_fail:
        for word in DEFAULT_KEYWORDS['comp_critical']:
            if word in full_text:
                critical_fail = f"Compliance Critical: Found '{word}'"
                suggestions.append(COACHING_TIPS['comp_critical'])
                break
        for word in DEFAULT_KEYWORDS['biz_critical']:
            if word in full_text:
                critical_fail = f"Business Critical: Found '{word}'"
                break
    
    # 2. Scorecard Checks
    if not critical_fail:
        for criteria in scorecard:
            weight = float(criteria['weight'])
            max_score += weight
            passed = False
            
            kw_key = criteria.get('keywords', '')
            keywords = DEFAULT_KEYWORDS.get(kw_key, [])
            c_id = criteria.get('id', '')

            if c_id == 'discovery':
                q_count = full_text.count('?')
                disc_count = sum(1 for k in keywords if k in full_text)
                if q_count >= 2 or disc_count >= 2: passed = True
            elif c_id == 'hold':
                passed = True 
            elif keywords:
                if any(k in full_text for k in keywords):
                    passed = True
            else:
                passed = True
            
            if passed:
                score += weight
                breakdown[criteria['name']] = "PASS"
            else:
                breakdown[criteria['name']] = "FAIL"
                if c_id in COACHING_TIPS:
                    suggestions.append(f"**{criteria['name']}**: {COACHING_TIPS[c_id]}")
    
    final_score = 0 if critical_fail else int((score / max_score) * 100) if max_score > 0 else 0
    return final_score, breakdown, critical_fail, suggestions

# --- MAIN APP UI ---

# Initialize Session State
if 'user' not in st.session_state:
    st.session_state['user'] = None
if 'role' not in st.session_state:
    st.session_state['role'] = None

# Sidebar Content (Persistent)
with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/b/b8/Lenovo_logo_2015.svg/2560px-Lenovo_logo_2015.svg.png", width=150)
    st.write("---")
    
    # Display Server IP for Network Access
    local_ip = get_local_ip()
    st.info(f"📡 **Network Access Link:**\n\n`http://{local_ip}:8501`")
    st.caption("Share this link with other PCs on the same Wi-Fi.")

    if st.session_state['user']:
        st.subheader(f"👤 {st.session_state['user']}")
        st.caption(f"Role: {st.session_state['role']}")
        if st.button("Logout", key="logout_btn", use_container_width=True):
            st.session_state['user'] = None
            st.rerun()
        
        st.write("---")
        st.subheader("Simulations")
        
        if st.session_state['role'] == "Manager":
            if st.button("➕ Start New Sim", key="create_sim_btn", use_container_width=True):
                rid = create_room(st.session_state['user'])
                st.session_state['active_room'] = rid
                st.rerun()

        # REFRESH BUTTON FOR ROOMS
        if st.button("🔄 Refresh Room List", key="refresh_rooms_btn", use_container_width=True):
            st.rerun()

        # Room List
        rooms = get_rooms()
        if rooms.empty:
            st.caption("No active rooms.")
        else:
            for idx, row in rooms.iterrows():
                # Dynamic Icon
                status_icon = "🟢" if row['status'] == 'Active' else "🏁"
                btn_label = f"{status_icon} #{row['id']} {row['host']}"
                if row['agent'] != 'Waiting...':
                     btn_label += f" vs {row['agent']}"
                
                if st.button(btn_label, key=f"room_btn_{row['id']}", use_container_width=True):
                    st.session_state['active_room'] = row['id']
                    if st.session_state['role'] == 'Agent' and row['agent'] == 'Waiting...':
                        join_room(row['id'], st.session_state['user'])
                    st.rerun()

# 1. LOGIN SCREEN
if not st.session_state['user']:
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        st.write("")
        st.write("")
        st.markdown("<h1 style='text-align: center; color: #E2231A;'>QA Manager Pro</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: #888;'>Quality Assurance Simulation Environment</p>", unsafe_allow_html=True)
        
        with st.form("login"):
            name = st.text_input("Enter your Name", placeholder="e.g. John Doe")
            role = st.selectbox("Select Role", ["Manager", "Agent"])
            st.write("")
            submitted = st.form_submit_button("Enter Workspace", use_container_width=True)
            if submitted and name:
                st.session_state['user'] = name
                st.session_state['role'] = role
                init_db()
                st.rerun()

else:
    # 2. WORKSPACE
    if 'active_room' in st.session_state:
        room_id = st.session_state['active_room']
        
        # Header
        col_head_1, col_head_2 = st.columns([3, 1])
        with col_head_1:
            st.title(f"Simulation Room #{room_id}")
        with col_head_2:
            if st.button("🔄 Refresh Chat", key="refresh_chat_btn", use_container_width=True):
                st.rerun()

        col1, col2 = st.columns([2, 1])
        
        # --- CHAT COLUMN ---
        with col1:
            st.markdown("### 💬 Live Conversation")
            
            # Message Container
            msgs = get_messages(room_id)
            chat_container = st.container(height=600)
            
            with chat_container:
                if msgs.empty:
                    st.markdown("<div style='text-align: center; color: #666; padding: 50px;'>No messages yet.<br>Start the roleplay!</div>", unsafe_allow_html=True)
                else:
                    for idx, m in msgs.iterrows():
                        role_type = m['role']
                        avatar = "👤" if role_type == 'Agent' else "👔"
                        with st.chat_message(role_type, avatar=avatar):
                            st.write(m['text'])
            
            # Input Area
            if prompt := st.chat_input("Type your message here..."):
                send_message(room_id, st.session_state['user'], st.session_state['role'], prompt)
                st.rerun()

        # --- TOOLS COLUMN ---
        with col2:
            st.markdown("### ⚙️ QA Tools")
            
            if st.session_state['role'] == "Manager":
                tab1, tab2 = st.tabs(["📊 Grading", "🔧 Settings"])
                
                # Grading Tab
                with tab1:
                    st.write("Real-time Analysis")
                    
                    if st.button("Run Auto-Analysis", key="run_grading_btn", use_container_width=True):
                        with st.spinner("Analyzing sentiment and compliance..."):
                            time.sleep(0.5) # UI feel
                            scorecard = get_config('scorecard')
                            score, breakdown, crit, suggestions = perform_grading(msgs, scorecard)
                        
                        st.markdown("---")
                        if crit:
                            st.error(f"⚠️ {crit}")
                            st.markdown(f"<div style='text-align: center; font-size: 40px; font-weight: bold; color: #e57373;'>0%</div>", unsafe_allow_html=True)
                        else:
                            color = "#81c784" if score >= 80 else "#ffcc80"
                            st.markdown(f"<div style='text-align: center; font-size: 50px; font-weight: bold; color: {color};'>{score}%</div>", unsafe_allow_html=True)
                        
                        # Coaching Tips
                        if suggestions:
                            st.warning("💡 Coaching Required:")
                            for tip in suggestions:
                                st.markdown(f"<div class='tip-box'>- {tip}</div>", unsafe_allow_html=True)
                        elif not crit:
                             st.success("🎉 Excellent Handling!")

                        st.write("### Breakdown")
                        for k, v in breakdown.items():
                            if v == "PASS":
                                st.markdown(f"<div class='success-box'>✅ {k}</div>", unsafe_allow_html=True)
                            else:
                                st.markdown(f"<div class='fail-box'>❌ {k}</div>", unsafe_allow_html=True)

                # Scorecard Editor Tab
                with tab2:
                    current_sc = get_config('scorecard')
                    st.info("Customize Scorecard Weights")
                    
                    updated_sc = []
                    for item in current_sc:
                        with st.expander(item['name'], expanded=False):
                            new_w = st.number_input("Weight", value=float(item['weight']), key=f"w_{item['id']}")
                            new_n = st.text_input("Name", value=item['name'], key=f"n_{item['id']}")
                            item['weight'] = new_w
                            item['name'] = new_n
                            updated_sc.append(item)
                    
                    if st.button("Save Changes", key="save_scorecard_btn", use_container_width=True):
                        update_config('scorecard', updated_sc)
                        st.success("Configuration Saved!")
            
            else:
                # Agent View
                st.info("Agent Dashboard")
                st.markdown("""
                **Active Guidelines:**
                - **Greeting:** Standard Intro.
                - **Discovery:** 2+ Probing Questions.
                - **Empathy:** Acknowledge frustration.
                - **Warranty:** Pitch support options.
                - **Closing:** Professional wrap-up.
                """)

    else:
        st.markdown("""
        <div style='text-align: center; margin-top: 50px; color: #666;'>
            <h2>Ready to start?</h2>
            <p>Select a room from the sidebar or create a new one.</p>
        </div>
        """, unsafe_allow_html=True)
