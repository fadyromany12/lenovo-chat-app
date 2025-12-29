import streamlit as st
import sqlite3
import json
import datetime
import pandas as pd
import time

# --- CONFIGURATION & CONSTANTS ---
DB_FILE = "qa_database.db"

DEFAULT_KEYWORDS = {
    "greetings": ['hello', 'hi', 'welcome', 'good morning', 'good afternoon', 'my name is', 'assist you'],
    "empathy": ['sorry', 'apologize', 'understand', 'frustrating', 'regret', 'trouble', 'hear that'],
    "hold": ['hold', 'moment', 'check', 'bear with me', 'researching'],
    "discovery": ['?', 'what', 'how', 'need', 'looking for', 'usage', 'budget'],
    "closing": ['anything else', 'further', 'assist', 'help you with'],
    "prof_closing": ['thank', 'bye', 'wonderful day', 'take care', 'appreciate'],
    "cx_critical": ['shut up', 'idiot', 'stupid', 'dumb', 'waste of time'],
    "comp_critical": ['credit card', 'cvv', 'card number', 'expiry', 'password']
}

DEFAULT_SCORECARD = [
    {"id": "greet", "name": "Opening: Greet & Intro", "weight": 5.0, "type": "required", "keywords": "greetings"},
    {"id": "empathy", "name": "Comm: Empathy", "weight": 15.0, "type": "required", "keywords": "empathy"},
    {"id": "discovery", "name": "Sales: Discovery Questions", "weight": 10.0, "type": "required", "keywords": "discovery"},
    {"id": "hold", "name": "Comm: Hold Etiquette", "weight": 5.0, "type": "optional", "keywords": "hold"},
    {"id": "closing", "name": "Closing: Addressed Query", "weight": 5.0, "type": "required", "keywords": "closing"},
    {"id": "end_prof", "name": "Closing: Professional End", "weight": 5.0, "type": "required", "keywords": "prof_closing"}
]

# --- DATABASE FUNCTIONS ---
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    # Create Tables
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
    agent_msgs = messages[messages['role'] == 'Agent']
    full_text = " ".join(agent_msgs['text'].str.lower().tolist())
    
    score = 0
    max_score = 0
    breakdown = {}
    critical_fail = None

    # 1. Critical Checks
    for word in DEFAULT_KEYWORDS['cx_critical']:
        if word in full_text:
            critical_fail = f"CX Critical: Found '{word}'"
            break
    if not critical_fail:
        for word in DEFAULT_KEYWORDS['comp_critical']:
            if word in full_text:
                critical_fail = f"Compliance Critical: Found '{word}'"
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
            
            # Logic
            if kw_key == 'discovery':
                # Count questions
                q_count = full_text.count('?')
                if q_count >= 2: passed = True
            elif keywords:
                # Check simple existence
                if any(k in full_text for k in keywords):
                    passed = True
            else:
                # Default Pass if no keywords mapped (Manual check simulation)
                passed = True
            
            if passed:
                score += weight
                breakdown[criteria['name']] = "PASS"
            else:
                breakdown[criteria['name']] = "FAIL"
    
    final_score = 0 if critical_fail else int((score / max_score) * 100) if max_score > 0 else 0
    return final_score, breakdown, critical_fail

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
                for idx, m in msgs.iterrows():
                    is_me = m['sender'] == st.session_state['user']
                    with st.chat_message(m['role'], avatar="👤" if m['role']=='Agent' else "👔"):
                        st.markdown(f"**{m['sender']}**: {m['text']}")
            
            # Input
            if prompt := st.chat_input("Type a message..."):
                send_message(room_id, st.session_state['user'], st.session_state['role'], prompt)
                st.rerun()
                
            # Auto-Refresh Button (Streamlit limitation)
            if st.button("🔄 Refresh Chat"):
                st.rerun()

        # --- TOOLS COLUMN ---
        with col2:
            st.subheader("⚙️ Controls")
            
            if st.session_state['role'] == "Manager":
                tab1, tab2 = st.tabs(["📝 Grading", "🔧 Scorecard"])
                
                # Grading Tab
                with tab1:
                    if st.button("run_grading", label="Run Auto-Analysis"):
                        scorecard = get_config('scorecard')
                        score, breakdown, crit = perform_grading(msgs, scorecard)
                        
                        st.divider()
                        if crit:
                            st.error(f"CRITICAL FAIL: {crit}")
                            st.metric("Final Score", "0%")
                        else:
                            color = "normal" if score < 80 else "inverse"
                            st.metric("Final Score", f"{score}%", delta_color=color)
                        
                        st.write("### Breakdown")
                        for k, v in breakdown.items():
                            if v == "PASS":
                                st.success(f"{k}")
                            else:
                                st.error(f"{k}")

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
                    
                    if st.button("Save Scorecard Changes"):
                        update_config('scorecard', updated_sc)
                        st.success("Saved!")
            
            else:
                # Agent View
                st.info("You are in Agent Mode. Focus on the chat!")
                st.markdown("""
                **Tips:**
                - Use 'Greeting' words.
                - Ask at least 2 discovery questions (?).
                - Show empathy ('sorry', 'understand').
                """)

    else:
        st.info("👈 Select or Create a room from the sidebar to start.")
