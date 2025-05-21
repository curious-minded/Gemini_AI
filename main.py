from dotenv import load_dotenv
import streamlit as st
import os
import google.generativeai as genai
from google.api_core.exceptions import InternalServerError, DeadlineExceeded
from PIL import Image
import requests
import time
import io

load_dotenv()

api_key = os.getenv("GOOGLE_API_KEY")
assembly_api_key = os.getenv("ASSEMBLYAI_API_KEY")

genai.configure(api_key=api_key)
text_model = genai.GenerativeModel("gemini-pro")
image_model = genai.GenerativeModel("gemini-1.5-flash")

if 'chat_history' not in st.session_state:
    st.session_state['chat_history'] = []
if 'input_text' not in st.session_state:
    st.session_state['input_text'] = ""

def get_text_response(question):
    max_retries = 3
    retries = 0
    while retries < max_retries:
        try:
            response = text_model.generate_content(question)
            if hasattr(response, 'text') and response.text:
                return response.text
            else:
                raise ValueError("No valid response returned.")
        except InternalServerError:
            st.warning("Internal server error occurred. Retrying...")
            retries += 1
            time.sleep(2)
        except DeadlineExceeded:
            st.warning("Request timed out. Retrying...")
            retries += 1
            time.sleep(2)
        except ValueError:
            st.warning("Unable to process the request. It may have been blocked or flagged.\nPlease try a different query.")
            return "Sorry, I'm unable to answer that right now."
        except Exception as e:
            st.error(f"An unexpected error occurred: {e}")
            return "Sorry, something went wrong."
    st.error("Failed to get a response after multiple attempts. Please try again later.")
    return "Sorry, I'm unable to provide an answer at the moment."

def get_image_response(image):
    response = image_model.generate_content(image)
    return response.text if hasattr(response, 'text') else str(response)

def submit_text():
    user_input = st.session_state['input_text']
    if user_input:
        # Append user message
        st.session_state['chat_history'].append(("You", user_input))
        # Get bot response
        response = get_text_response(user_input)
        st.session_state['chat_history'].append(("Bot", response))
        st.session_state['input_text'] = ""

def download_chat_history():
    return "\n".join(f"{role}: {text}" for role, text in st.session_state['chat_history'])

def generate_download_link(text, filename):
    st.sidebar.download_button(
        label="Download Chat History",
        data=text,
        file_name=filename,
        mime="text/plain"
    )

st.sidebar.subheader(f"Welcome to your dashboard {st.session_state.get('handle', 'User')}!")
option = st.sidebar.selectbox(
    "How can I assist you?",
    ['Chat', 'Image Analysis', 'Speech-to-text', 'About'],
    help='Choose a functionality. Click outside to close.'
)

st.markdown("""
<style>
[data-testid="stSidebar"] {
        background-color: rgba(0, 0, 0, 0.7);
        color: white;
}
</style>
""", unsafe_allow_html=True)

if option == 'Chat':
    example_text = st.sidebar.selectbox(
        "You can start by asking me...",
        [
            'Tell me a joke', 'Tell me a fun fact', 'Invent a new superhero',
            'Name a dish and tell me its recipe', 'Recommend a holiday destination',
            'Recommend good movies', 'Recommend a new hobby', 'Write a poem',
            'Write a letter', 'Recommend books', 'Format for Resume',
            'Thought for the day', 'Explain the theory of relativity'
        ]
    )
    if st.sidebar.button("Use Example"):
        st.session_state['input_text'] = example_text
        submit_text()

    st.text_input("Input for Chatbot:", key="input_text", on_change=submit_text)

    # Display conversation
    for role, message in st.session_state['chat_history']:
        if role == "You":
            st.markdown(f"**You:** {message}")
        else:
            st.markdown(f"**Bot:** {message}")

elif option == 'Image Analysis':
    uploaded_file = st.file_uploader("Choose an image...", type=['jpg', 'jpeg', 'png'])
    if uploaded_file:
        img = Image.open(uploaded_file)
        st.image(img, caption='Uploaded Image', use_column_width=True)
        if st.button("Tell me about this image"):
            response = get_image_response(img)
            st.subheader("The response is:")
            st.write(response)
            st.session_state['chat_history'].append(("You", uploaded_file.name))
            st.session_state['chat_history'].append(("Bot", response))

elif option == 'Speech-to-text':
    def transcribe_audio(audio_file):
        headers = {'authorization': assembly_api_key, 'content-type': 'application/json'}
        upload_resp = requests.post(
            'https://api.assemblyai.com/v2/upload', headers=headers, files={'file': audio_file}
        )
        audio_url = upload_resp.json().get('upload_url')
        if not audio_url:
            return "Failed to upload file."
        json_data = {'audio_url': audio_url}
        transcript_resp = requests.post(
            'https://api.assemblyai.com/v2/transcript', headers=headers, json=json_data
        )
        transcript_id = transcript_resp.json().get('id')
        if not transcript_id:
            return "Failed to request transcription."
        while True:
            status_resp = requests.get(
                f'https://api.assemblyai.com/v2/transcript/{transcript_id}', headers=headers
            )
            status = status_resp.json().get('status')
            if status == 'completed':
                return status_resp.json().get('text')
            if status == 'failed':
                return 'Transcription failed.'
            time.sleep(5)

    uploaded_audio = st.file_uploader("Choose an audio file...", type=["wav", "mp3"])
    if uploaded_audio and st.button("Generate response"):
        st.write("Processing your audio...")
        transcription = transcribe_audio(uploaded_audio)
        st.subheader("Your query:")
        st.write(transcription)
        st.session_state['input_text'] = transcription
        submit_text()
        for role, message in st.session_state['chat_history']:
            if role == "Bot":
                st.subheader("The response is:")
                st.write(message)

elif option == 'About':
    st.header("About")
    st.write(
        """
        - AI chatbot clone of Google Gemini.
        - Uses Google Gemini and AssemblyAI for speech-to-text.
        - Built with Streamlit and Firebase.
        """
    )

# Sidebar chat history and download
with st.sidebar.expander("Chat History"):
    if not st.session_state['chat_history']:
        st.write("None")
    else:
        for role, text in st.session_state['chat_history']:
            st.write(f"{role}: {text}")

if st.session_state['chat_history']:
    chat_str = download_chat_history()
    generate_download_link(chat_str, "chat_history.txt")

st.write("---\n*© 2024 Gemini Assistant. All rights reserved.*")
