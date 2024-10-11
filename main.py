from dotenv import load_dotenv
import streamlit as st
import os
import google.generativeai as genai
from PIL import Image
import requests
import time
import io
#from auth1 import login_page
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
    try:
        response = text_model.generate_content(question)
        if response.text:
                return response.text
        else:
            raise ValueError("No valid response returned.")
        
    except ValueError as e:
        st.warning("Unable to process the request. It may have been blocked or flagged. Please try a different query.")
        return "Sorry, I'm unable to answer that right now."

def get_image_response(image):
    response = image_model.generate_content(image)
    return response.text

def submit_text():
        user_input = st.session_state['input_text']
        if user_input:
            response = get_text_response(user_input)
            st.session_state['chat_history'].append(("You", user_input))
            st.session_state['chat_history'].append(("Bot", response))
            st.session_state['input_text'] = ""

def download_chat_history():
    chat_history_str = ""
    for role, text in st.session_state['chat_history']:
        chat_history_str += f"{role}: {text}\n"

    return chat_history_str

def generate_download_link(text, filename):
    buffer = io.StringIO(text)
    st.sidebar.download_button(
        label="Download Chat History",
        data=buffer.getvalue(),
        file_name=filename,
        mime="text/plain"
    )
st.sidebar.subheader(f"Welcome to your dashboard {st.session_state.get('handle', 'User')}!")
option = st.sidebar.selectbox("How can I assist you?", ['Chat', 'Image Analysis', 'Speech-to-text', 'About'], help = 'Choose a functionality. If you are done click outside the menu to close it.')
st.markdown("""
<style>
[data-testid="stSidebar"] {
        background-color: rgba(0, 0, 0, 0.7);  /* Sidebar with semi-transparent black */
        color: white;
    }
</style>
""", unsafe_allow_html=True)

if option == 'Chat':
    example_text = st.sidebar.selectbox("You can start by asking me...", ['Tell me a joke', 'Tell me a fun fact', 'Invent a new superhero and describe their powers.',
                                                                       'Name a dish and tell me its recipe', 'Recommend me a holiday destination', 'Recommend me some good movies', 'Recommend me a new hobby',
                                                                       'Write a poem', 'Write a letter', 'Recommend me some books for reading', 'Give a format for Resume', "Tell me the thought for the day", 
                                                                         'Explain the theory of relativity'])
    if st.sidebar.button("Use Example"):
        st.session_state['input_text'] = example_text
        submit_text()
    user_input = st.text_input("Input for Chatbot:", key="input_text", on_change=submit_text)
    if len(st.session_state['chat_history']) > 0:
            last_message = st.session_state['chat_history'][-1]
            if last_message[0] == "Bot":
                st.subheader("The response is:")
                st.write(last_message[1])

elif option == 'Image Analysis':
    uploaded_file = st.file_uploader("Choose an image...", type=['jpg', 'jpeg', 'png'], help = 'Once the image is uploaded you can ask the interpretation of AI.')
    image = None
    if uploaded_file is not None:
        image = Image.open(uploaded_file)
        st.image(image, caption='Uploaded Image.', use_column_width=True)
        if st.button("Tell me about this image"):
            if image is not None:
                response = get_image_response(image)
                st.subheader("The response is:")
                st.write(response)
                st.session_state['chat_history'].append(("You", uploaded_file))
                st.session_state['chat_history'].append(("Bot", response))
            else:
                st.warning("Please upload an image first.")
    
elif option == 'Speech-to-text':
    def transcribe_audio(audio_file):
        headers = {
            'authorization': assembly_api_key,
            'content-type': 'application/json'
        }

        files = {'file': audio_file}
        upload_response = requests.post('https://api.assemblyai.com/v2/upload', headers=headers, files=files)
        audio_url = upload_response.json().get('upload_url')
    
        if not audio_url:
            return "Failed to upload the file."
    
        json_data = {'audio_url': audio_url}
        transcript_response = requests.post('https://api.assemblyai.com/v2/transcript', headers=headers, json=json_data)
        transcript_id = transcript_response.json().get('id')

        if not transcript_id:
            return "Failed to request transcription."
    
        while True:
            status_response = requests.get(f'https://api.assemblyai.com/v2/transcript/{transcript_id}', headers=headers)
            status = status_response.json().get('status')
            if status == 'completed':
                return status_response.json().get('text')
            elif status == 'failed':
                return 'Transcription failed'
            time.sleep(5)

    uploaded_file = st.file_uploader("Choose an audio file...", type=["wav", "mp3"], help='Once the audio is uploaded you can ask the interpretation of AI.')
    
    if uploaded_file is not None and st.button("Generate response"):
        st.write("You have a lovely accent. Trying our best to process it correctly...")
        transcription = transcribe_audio(uploaded_file)
        st.subheader("Your query:")
        st.write(transcription)
        st.session_state["input_text"] = transcription
        submit_text() 
    
        if len(st.session_state['chat_history']) > 0:
                last_message = st.session_state['chat_history'][-1]
                if last_message[0] == "Bot":
                    st.subheader("The response is:")
                    st.write(last_message[1])

elif option == 'About':
    st.header("About")
    st.write(""" 
    ### About this Web Service
    - It is an AI chatbot clone of Google Gemini.
    - This web service utilizes API keys from [Google Gemini](https://gemini.google.com/app) to incorporate chat based and image to text models.
    - This web service makes use of the [Assembly AI](https://www.assemblyai.com/) model for speech to text functionality.
    - The web service is built using [Streamlit](https://streamlit.io/), with backend services powered by [Firebase](https://firebase.google.com/)""")
    
with st.sidebar.expander("Chat History"):
        if len(st.session_state['chat_history']) == 0:
            st.write("None")
        else:
            for role, text in st.session_state['chat_history']:
                st.write(f"{role}: {text}")
            
if len(st.session_state['chat_history']) > 0:
    chat_history_str = download_chat_history()
    generate_download_link(chat_history_str, "chat_history.txt")

st.write("""
    ---
    *© 2024 Gemini Assistant. All rights reserved.*
    """)
