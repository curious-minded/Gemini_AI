import streamlit as st
from datetime import datetime
import firebase_admin
from firebase_admin import credentials, auth, db
import importlib.util
import requests
import os
from dotenv import load_dotenv
from firebase_admin.exceptions import FirebaseError
st.set_page_config(page_title="GEMINI Chatbot", page_icon="👾")
load_dotenv()

FIREBASE_API_KEY2 = os.getenv("apiKey2")
FIREBASE_AUTH_URL2 = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={FIREBASE_API_KEY2}"
DATABASE_URL2 = os.getenv("database_url2")
#GOOGLE_CLIENT_ID = os.getenv("google_client_id")

def authenticate_user(email, password):
    payload = {
        "email": email,
        "password": password,
        "returnSecureToken": True
    }
    response = requests.post(FIREBASE_AUTH_URL2, json=payload)
    auth_response = response.json()
    
    if "error" in auth_response:
        return {"error": auth_response["error"]}
    
    id_token = auth_response.get("idToken")
    local_id = auth_response.get("localId")  
    
    user_ref = db.reference(f'users/{local_id}')
    user_profile = user_ref.get()
    
    if user_profile:
        return {
            "handle": user_profile.get("handle"),
            "email": user_profile.get("email")
        }
    else:
        return {"error": "User profile not found"}

# def google_sign_in():
#     token = st.query_params.get("token")
#     if not token:
#         raise ValueError('No token provided.')
    
#     request = google.auth.transport.requests.Request()
#     id_info = id_token.verify_oauth2_token(token[0], request, GOOGLE_CLIENT_ID)
    
#     if id_info['iss'] not in ['accounts.google.com', 'https://accounts.google.com']:
#         raise ValueError('Wrong issuer.')

#     local_id = id_info['sub']
#     user_ref = db.reference(f'users/{local_id}')
#     user_profile = user_ref.get()
    
#     if user_profile:
#         return {
#             "handle": user_profile.get("handle", 'User'),
#             "email": user_profile.get("email")
#         }
#     else:
#         user_ref.set({
#             'handle': id_info.get('name', 'User'),
#             'email': id_info.get('email'),
#             'created_at': datetime.now().isoformat()
#         })
#         return {
#             "handle": id_info.get('name', 'User'),
#             "email": id_info.get('email')
#         }

cred = credentials.Certificate("json_key1.json")
if not firebase_admin._apps:
    firebase_admin.initialize_app(cred, {
        'databaseURL': DATABASE_URL2
    })

st.markdown("""
    <style>
    .title {
        font-size: 50px;
        color: #ff6347; 
        text-align: center;
        font-family: 'Courier New', Courier, monospace;
    }

    .stButton>button {
            background-color: #4CAF50;
            color: white;
            padding: 10px 20px;
            text-align: center;
            text-decoration: none;
            display: inline-block;
            font-size: 16px;
            margin: 4px 2px;
            cursor: pointer;
            border-radius: 12px;
        }

    .stButton>button:hover {
        background-color: #32CD32; /* Light green on hover */
    }
    </style>
""", unsafe_allow_html=True)
st.markdown("<h1 class='title'>WELCOME TO GEMINI 👾</h1>", unsafe_allow_html=True)

def login_page():
    with st.expander("Help", expanded=False):
        st.write("""
        **Instructions:**
        - If you do not have an account please SignUp. Please use a valid email.
        - If you are new to this site please ensure the password is at least 6 characters long while creating an account.
        - One should use digits or special symbols as well to make the password strong.
        - You can always change the theme/mode according to your preference from top right.
        """)
    
    choice = st.selectbox('Login/SignUp', ['Login', 'SignUp'])
    if choice == 'SignUp':
        email = st.text_input('Please enter your email address')
        password = st.text_input('Please enter your password', type='password')
        confirm_pass = st.text_input('Please confirm your password', type='password')
        handle = st.text_input('Please input your Username', value='Default')
        if st.button('Create Account'):
            if password != confirm_pass:
                st.error('Passwords do not match. Please try again')
            else:
                all_users_ref = db.reference('users')
                all_users = all_users_ref.get()
                if all_users:
                    existing_handles = [user_data['handle'] for user_data in all_users.values() if 'handle' in user_data]
                    if handle in existing_handles:
                        st.error(f"The handle '{handle}' is already taken. Please choose another one.")
                        return
                try:
                    user = auth.create_user(
                        email=email,
                        password=password
                    )
                    st.success('Account created successfully')
                    user_ref = db.reference('users').child(user.uid)
                    user_ref.set({
                        'handle': handle,
                        'email': email,
                        'created_at': datetime.now().isoformat()
                    })
                    st.session_state['handle'] = handle
                    st.session_state['logged_in'] = True
                    st.rerun()
                except FirebaseError as e:
                    st.error(f'Error creating account: {e}')
                    
    elif choice == 'Login':
        email = st.text_input('Please enter your email address')
        password = st.text_input('Please enter your password', type='password')
        if st.button('Login'):
            response = authenticate_user(email, password)
            if "error" in response:
                error_message = response["error"].get("message", "Login failed")
                st.error(f"Error logging in: {error_message}")
            else:
                st.success('Logged in successfully')
                st.session_state['logged_in'] = True
                st.session_state['handle'] = response.get('handle', 'User')
                st.rerun()

    st.write("""
        ---
        *© 2024 Gemini Assistant. All rights reserved.*
        """)

def main_website():
    main_website_path = 'main.py'
    spec = importlib.util.spec_from_file_location("main_website", main_website_path)
    main_website_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(main_website_module)
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

if st.session_state['logged_in']:
    main_website()
    if st.sidebar.button('Logout', key='logout', help='Click to logout'):
        st.markdown("""
            <style>
            .stButton[data-baseweb="button"] {
                background-color: #FF6347;
                color: white;
                border-radius: 12px;
            }
            .stButton[data-baseweb="button"]:hover {
                background-color: #FF4500;
            }
            </style>
        """, unsafe_allow_html=True)
        st.session_state['logged_in'] = False
        st.session_state.pop('handle', None)
        st.rerun()
else:
    login_page()
