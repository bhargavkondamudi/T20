import streamlit as st
import bcrypt
from datetime import datetime
import pymssql
import teradatasql
# Initialize session state variables safely
st.session_state.setdefault("logged_in", False)
st.session_state.setdefault("username", None)
st.session_state.setdefault("show_signup", False)  # Track whether to show signup page

# Use Streamlit's secret management system
DB_SERVER = st.secrets["DB_SERVER"]
#DB_PORT = st.secrets["DB_PORT"]
DB_DATABASE = st.secrets["DB_DATABASE"]
DB_USERNAME = st.secrets["DB_USERNAME"]
DB_PASSWORD = st.secrets["DB_PASSWORD"]
#tds_version = st.secrets["tds_version"]
user_table = st.secrets["user_table"]
Feedback_table = st.secrets["Feedback_table"]
user_session = st.secrets["user_logs"]

# Database connection with specific parameters
def get_db_connection():
    #host = f"{DB_SERVER},{DB_PORT}"
    return pymssql.connect(
        host=DB_SERVER,  # Server IP or hostname
        #port=DB_PORT,            # Port number
        user=DB_USERNAME,     # Your username
        password=DB_PASSWORD, # Your password
        database=DB_DATABASE, # Database name
        #tds_version=tds_version    # TDS protocol version
    )

def create_tables():
    with get_db_connection() as conn:
        cursor = conn.cursor()

        # Create User table
        cursor.execute(f"""
        IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='{user_table}' AND xtype='U')
        CREATE TABLE {user_table} (
            id INT IDENTITY(1,1) PRIMARY KEY,
            username NVARCHAR(255) UNIQUE NOT NULL,
            password_hash NVARCHAR(255) NOT NULL
        )
        """)

        # Create Feedback table
        cursor.execute(f"""
        IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='{Feedback_table}' AND xtype='U')
        CREATE TABLE {Feedback_table} (
            id INT IDENTITY(1,1) PRIMARY KEY,
            username NVARCHAR(255) NOT NULL,
            feedback_date NVARCHAR(255) NOT NULL,
            feedback_text NVARCHAR(MAX) NOT NULL
        )
        """)

        # Create UserSession table
        cursor.execute(f"""
        IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='{user_session}' AND xtype='U')
        CREATE TABLE {user_session} (
            id INT IDENTITY(1,1) PRIMARY KEY,
            username NVARCHAR(255) NOT NULL,
            login_time NVARCHAR(255) NOT NULL,
            logout_time NVARCHAR(255)
        )
        """)

        conn.commit()

create_tables()

# Helper functions for password handling
def hash_password(password):
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def check_password(password, hashed):
    return bcrypt.checkpw(password.encode(), hashed.encode())

# Password validation
def is_valid_password(password):
    if len(password) < 8:
        return False, "Password must be at least 8 characters long."
    if not any(char.isupper() for char in password):
        return False, "Password must contain at least one uppercase letter."
    if not any(char in '!@#$%^&*()-_=+[]{};:,.<>?/' for char in password):
        return False, "Password must contain at least one special character."
    return True, ""

# Login logic
def login():
    if not st.session_state["logged_in"]:
        st.title("Login")
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")

        col1, col2 = st.columns([1, 1])
        with col1:
            if st.button("Login"):
                with get_db_connection() as conn:
                    cursor = conn.cursor(as_dict=True)
                    cursor.execute(f"SELECT * FROM {user_table} WHERE username=%s", (username,))
                    user = cursor.fetchone()

                    if user and check_password(password, user['password_hash']):
                        st.session_state["logged_in"] = True
                        st.session_state["username"] = username
                        st.session_state["show_signup"] = False

                        # Record login time
                        login_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        cursor.execute(f"""
                            INSERT INTO {user_session} (username, login_time) VALUES (%s, %s)
                        """, (username, login_time))
                        conn.commit()
                        st.stop()
                    else:
                        st.error("Invalid credentials")

        with col2:
            if st.button("Create Account"):
                st.session_state["show_signup"] = True
                st.stop()

# Signup logic
def signup():
    st.title("Create Account")
    username = st.text_input("Choose a Username")
    password = st.text_input("Choose a Password", type="password")

    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("Sign Up"):
            valid, message = is_valid_password(password)
            if not valid:
                st.error(message)
                return

            if username and password:
                with get_db_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute(f"SELECT * FROM {user_table} WHERE username=%s", (username,))
                    existing_user = cursor.fetchone()

                    if existing_user:
                        st.error("Username already exists! Please log in.")
                    else:
                        cursor.execute(f"""
                            INSERT INTO {user_table} (username, password_hash) VALUES (%s, %s)
                        """, (username, hash_password(password)))
                        conn.commit()
                        st.session_state["show_signup"] = False
                        st.success("Account created successfully! Please log in.")

    with col2:
        if st.button("Back to Login"):
            st.session_state["show_signup"] = False
            st.stop()

# Feedback functionality with 500-character limit
def feedback_section():
    st.markdown("### Feedback")
    username = st.text_input("Your Username", value=st.session_state.get("username", ""), disabled=True)

    # Text area for feedback
    feedback = st.text_area("We value your feedback. Please share your thoughts below:", max_chars=500)

    if st.button("Submit Feedback"):
        if feedback.strip():
            feedback_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            try:
                with get_db_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute(f"""
                        INSERT INTO {Feedback_table} (username, feedback_date, feedback_text)
                        VALUES (%s, %s, %s)
                    """, (username, feedback_date, feedback))
                    conn.commit()
                    st.success("Thank you for your feedback!")
            except Exception as e:
                st.error(f"An error occurred while saving your feedback: {e}")
        else:
            st.error("Feedback cannot be empty. Please enter your details.")

# Main app logic
if st.session_state.get("logged_in"):
    st.title("Power BI Report Viewer")
    st.markdown(""" T20 Men World Cup Best 11 """)
    
    power_bi_url = "https://app.powerbi.com/view?r=eyJrIjoiMGUwOGUyY2YtMGFmMi00M2FlLWFkMTUtZTM2OTk2YmEwZTEyIiwidCI6ImFkNmQ2NjI0LTgyYTAtNDgyYS1hOWY1LTg5NmJiNzg3ZWUzOCJ9"
    st.markdown(
        f"""
        <iframe 
            src="{power_bi_url}" 
            width="100%" 
            height="350" 
            frameborder="0" 
            allowFullScreen="true">
        </iframe>
        """,
        unsafe_allow_html=True
    )

    feedback_section()

    if st.button("Logout"):
        with get_db_connection() as conn:
            cursor = conn.cursor()
            logout_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute(f"""
                UPDATE {user_session}
                SET logout_time = %s
                WHERE username = %s AND logout_time IS NULL
            """, (logout_time, st.session_state["username"]))
            conn.commit()

        st.session_state["logged_in"] = False
        st.info("You have been logged out.")
        st.stop()
else:
    if st.session_state.get("show_signup"):
        signup()
    else:
        login()
