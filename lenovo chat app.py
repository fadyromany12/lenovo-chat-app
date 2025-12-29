import streamlit as st
import sqlite3
import json
import datetime
import pandas as pd
import time

# --- CONFIGURATION & CONSTANTS ---
DB_FILE = "qa_database.db"

# 1. FULL KEYWORD DICTIONARY (Exact match to original)
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
    {"id": "confirm", "name": "Opening: Confirm Name/Reason", "weight": 3.0, "keywords": ""}, # Manual/Context
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

# 3. COACHING TIPS (Suggestions)
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

# --- AUTO GRADING ENGINE (PYTHON) ---
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
            
            # Get keyword list name from criteria
            kw_key = criteria.get('keywords', '')
            keywords = DEFAULT_KEYWORDS.get(kw_key, [])
            c_id = criteria.get('id', '')

            # Logic Handlers
            if c_id == 'discovery':
                # Count questions (?) or discovery words
                q_count = full_text.count('?')
                disc_count = sum(1 for k in keywords if k in full_text)
                if q_count >= 2 or disc_count >= 2: passed = True
            elif c_id == 'hold':
                # Pass if hold wasn't used, or if used correctly. 
                # For simulation, we look for hold words. If found -> PASS. If not -> N/A (Full Points)
                # To simplify: Check if they used hold words OR if it's N/A
                passed = True 
            elif keywords:
                # Check simple existence
                if any(k in full_text for k in keywords):
                    passed = True
            else:
                # Default Pass for subjective items (Listening, Tone, etc)
                # In a real app, Manager would manually toggle these. 
                # Here we default to Pass for the simulation flow.
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
st.set_page_config(page_title="Lenovo QA Sim", page_icon="💬", layout="wide")

# Initialize Session State
if 'user' not in st.session_state:
    st.session_state['user'] = None
if 'role' not in st.session_state:
    st.session_state['role'] = None

# 1. LOGIN SCREEN
if not st.session_state['user']:
    st.title("Lenovo QA Simulation (Python)")
    with st.form("login"):
        name = st.text_input("Enter your Name")
        role = st.selectbox("Select Role", ["Manager", "Agent"])
        submitted = st.form_submit_button("Enter Lobby")
        if submitted and name:
            st.session_state['user'] = name
            st.session_state['role'] = role
            init_db() # Ensure DB exists
            st.rerun()

else:
    # 2. MAIN APP
    with st.sidebar:
        st.header(f"👤 {st.session_state['user']}")
        st.caption(f"Role: {st.session_state['role']}")
        if st.button("Logout"):
            st.session_state['user'] = None
            st.rerun()
        
        st.divider()
        st.subheader("Rooms")
        
        # Room Controls
        if st.session_state['role'] == "Manager":
            if st.button("➕ Create New Room"):
                rid = create_room(st.session_state['user'])
                st.session_state['active_room'] = rid
                st.rerun()

        # Room List
        rooms = get_rooms()
        for idx, row in rooms.iterrows():
            label = f"#{row['id']} {row['host']} vs {row['agent']}"
            if st.button(label, key=f"room_{row['id']}"):
                st.session_state['active_room'] = row['id']
                if st.session_state['role'] == 'Agent' and row['agent'] == 'Waiting...':
                    join_room(row['id'], st.session_state['user'])
                st.rerun()

    # 3. WORKSPACE
    if 'active_room' in st.session_state:
        room_id = st.session_state['active_room']
        
        # Layout: Chat | Tools
        col1, col2 = st.columns([2, 1])
        
        # --- CHAT COLUMN ---
        with col1:
            st.subheader(f"💬 Chat Room #{room_id}")
            
            # Display Messages
            msgs = get_messages(room_id)
            chat_container = st.container(height=500)
            with chat_container:
                if msgs.empty:
                    st.info("No messages yet. Start typing below!")
                else:
                    for idx, m in msgs.iterrows():
                        is_me = m['sender'] == st.session_state['user']
                        # Differentiate bubbles
                        with st.chat_message(m['role'], avatar="👤" if m['role']=='Agent' else "👔"):
                            st.write(f"**{m['sender']}**: {m['text']}")
            
            # Input
            if prompt := st.chat_input("Type a message..."):
                send_message(room_id, st.session_state['user'], st.session_state['role'], prompt)
                st.rerun()
                
            # Refresh button for manual update
            st.button("🔄 Refresh Chat", key="refresh_chat")

        # --- TOOLS COLUMN ---
        with col2:
            st.subheader("⚙️ Controls")
            
            if st.session_state['role'] == "Manager":
                tab1, tab2 = st.tabs(["📝 Grading", "🔧 Scorecard"])
                
                # Grading Tab
                with tab1:
                    st.write("Click below to analyze the chat for QA scores.")
                    
                    # FIXED BUTTON ERROR HERE:
                    if st.button("Run Auto-Analysis", key="run_grading"):
                        scorecard = get_config('scorecard')
                        score, breakdown, crit, suggestions = perform_grading(msgs, scorecard)
                        
                        st.divider()
                        if crit:
                            st.error(f"CRITICAL FAIL: {crit}")
                            st.metric("Final Score", "0%")
                        else:
                            color = "normal" if score < 80 else "inverse"
                            st.metric("Final Score", f"{score}%", delta_color=color)
                        
                        # Coaching Tips
                        if suggestions:
                            st.warning("💡 Coaching Suggestions:")
                            for tip in suggestions:
                                st.write(f"- {tip}")
                        else:
                            if not crit: st.success("🎉 Perfect Chat! No suggestions.")

                        st.write("### Breakdown")
                        for k, v in breakdown.items():
                            if v == "PASS":
                                st.success(f"✅ {k}")
                            else:
                                st.error(f"❌ {k}")

                # Scorecard Editor Tab
                with tab2:
                    current_sc = get_config('scorecard')
                    st.info("Edit Weights & Criteria")
                    
                    updated_sc = []
                    for item in current_sc:
                        with st.expander(item['name'], expanded=False):
                            new_w = st.number_input("Weight", value=float(item['weight']), key=f"w_{item['id']}")
                            new_n = st.text_input("Name", value=item['name'], key=f"n_{item['id']}")
                            item['weight'] = new_w
                            item['name'] = new_n
                            updated_sc.append(item)
                    
                    if st.button("Save Scorecard Changes", key="save_scorecard"):
                        update_config('scorecard', updated_sc)
                        st.success("Saved!")
            
            else:
                # Agent View
                st.info("You are in Agent Mode. Focus on the chat!")
                st.markdown("""
                **Quick Guide:**
                - **Greeting:** Start professionally.
                - **Discovery:** Ask 'What usage?' or 'What budget?'.
                - **Empathy:** Say 'sorry' or 'understand' if needed.
                - **Warranty:** Mention warranty support.
                - **Closing:** 'Is there anything else?'
                """)

    else:
        st.info("👈 Select or Create a room from the sidebar to start.")
