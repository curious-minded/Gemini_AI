from dotenv import load_dotenv
import streamlit as st
import os
import google.generativeai as genai
from google.api_core.exceptions import InternalServerError, DeadlineExceeded
from PIL import Image
import requests
import time
import io

# Load environment variables
load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")
assembly_api_key = os.getenv("ASSEMBLYAI_API_KEY")

genai.configure(api_key=api_key)

# Initialize or retrieve session state variables
st.session_state.setdefault('chat_history', [])
st.session_state.setdefault('input_text', "")

# Function to get chatbot response
def get_text_response(question):
    for _ in range(3):
        try:
            response = text_model.generate_content(question)
            if getattr(response, 'text', None):
                return response.text
            raise ValueError("No valid response returned.")
        except (InternalServerError, DeadlineExceeded):
            st.warning("Server issue, retrying...")
            time.sleep(2)
        except ValueError:
            st.warning("Unable to process request. Try a different query.")
            return "Sorry, I can't answer that right now."
        except Exception as e:
            return f"Error: {e}"
    return "Failed after multiple attempts."

# Function to get image analysis
def get_image_response(image):
    response = image_model.generate_content(image)
    return getattr(response, 'text', str(response))

# Submit user text to chat history and generate bot reply
def submit_text():
    user_input = st.session_state['input_text']
    if not user_input:
        return
    # Append user message
    st.session_state['chat_history'].append(("You", user_input))
    # Get and append bot response
    bot_reply = get_text_response(user_input)
    st.session_state['chat_history'].append(("Bot", bot_reply))
    # Clear input field
    st.session_state['input_text'] = ""
    return bot_reply

# Prepare download of chat history
def download_chat_history():
    return "\n".join(f"{r}: {m}" for r, m in st.session_state['chat_history'])

def generate_download_link(text, filename):
    st.sidebar.download_button(
        label="Download Chat History",
        data=text,
        file_name=filename,
        mime="text/plain"
    )

# Sidebar: choose function
st.sidebar.subheader(f"Welcome, {st.session_state.get('handle','User')}!")
option = st.sidebar.selectbox(
    "Functionality:", ['Chat','Image Analysis','Speech-to-text','About']
)

st.markdown("""
<style>
[data-testid="stSidebar"] { background-color: rgba(0,0,0,0.7); color: white; }
</style>
""", unsafe_allow_html=True)

# Chat section with latest Q then A first
def render_chat():
    example = st.sidebar.selectbox("Example prompts:", [
        'Tell me a joke','Explain relativity','Suggest a hobby', 'Write a poem', 'give me a resume template'
    ])
    if st.sidebar.button("Use example"):
        st.session_state['input_text'] = example
        submit_text()

    st.text_input("Your question:", key='input_text', on_change=submit_text)
    history = st.session_state['chat_history']
    # Display pairs in reverse order: latest question then its response
    for i in range(len(history)-2, -1, -2):
        user, question = history[i]
        bot_label, answer = history[i+1]
        st.markdown(f"**{user}:** {question}")
        st.markdown(f"**{bot_label}:** {answer}")

# Set models (replace with your valid model names)
text_model = genai.GenerativeModel("models/gemini-1.5-flash")
image_model = genai.GenerativeModel("models/gemini-1.5-flash")

# Render based on selected option
if option == 'Chat':
    render_chat()
elif option == 'Image Analysis':
    file = st.file_uploader("Upload image:", type=['jpg','jpeg','png'])
    if file:
        img = Image.open(file)
        st.image(img, use_column_width=True)
        if st.button("Analyze image"):
            resp = get_image_response(img)
            st.subheader("Analysis result:")
            st.write(resp)
            st.session_state['chat_history'] += [("You", file.name), ("Bot", resp)]
elif option == 'Speech-to-text':
    audio = st.file_uploader("Upload audio:", type=['wav','mp3'])
    if audio and st.button("Transcribe & Chat"):
        st.write("Processing audio...")
        # Transcribe audio
        def transcribe(aud_file):
            headers = {'authorization': assembly_api_key, 'content-type': 'application/json'}
            up = requests.post('https://api.assemblyai.com/v2/upload', headers=headers, files={'file': aud_file})
            url = up.json().get('upload_url')
            if not url:
                return "Upload failed."
            tr = requests.post('https://api.assemblyai.com/v2/transcript', headers=headers, json={'audio_url': url})
            tid = tr.json().get('id')
            if not tid:
                return "Transcription failed."
            while True:
                stt = requests.get(f'https://api.assemblyai.com/v2/transcript/{tid}', headers=headers)
                status = stt.json().get('status')
                if status == 'completed':
                    return stt.json().get('text')
                if status == 'failed':
                    return 'Transcription failed.'
                time.sleep(5)
        text = transcribe(audio)
        st.subheader("Your query:")
        st.write(text)
        # Submit to chat and display bot response
        st.session_state['input_text'] = text
        bot_response = submit_text()
        st.subheader("Bot response:")
        st.write(bot_response)
elif option == 'About':
    st.header("About")
    st.write(
        "- AI chatbot using Google Gemini API.\n"
        "- Speech-to-text via AssemblyAI.\n"
        "- Built with Streamlit."
    )

# Sidebar chat history and download
with st.sidebar.expander("Chat History"):
    if not st.session_state['chat_history']:
        st.write("No history.")
    for r, m in st.session_state['chat_history']:
        st.write(f"{r}: {m}")

if st.session_state['chat_history']:
    generate_download_link(download_chat_history(), "chat_history.txt")

st.write("---\n*© 2024 Gemini Assistant.*")
