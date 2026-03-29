import streamlit as st
import google.generativeai as genai
import os

# 1. Setup Gemini
genai.configure(api_key="YOUR_GEMINI_API_KEY")
model = genai.GenerativeModel('gemini-1.5-flash')

# 2. Streamlit UI Config
st.set_page_config(page_title="Gemini Chat", layout="centered")
st.title("💬 Gemini Assistant")

# 3. Initialize Chat History
if "messages" not in st.session_state:
    st.session_state.messages = []

# 4. Display Chat History
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# 5. Chat Input Logic
if prompt := st.chat_input("How can I help you?"):
    # Add user message to state
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Generate Gemini Response
    with st.chat_message("assistant"):
        response = model.generate_content("“You are a high school math tutor. Do not give direct answers unless the student has tried. Ask guiding questions, provide hints, and encourage step-by-step reasoning.” + 
prompt)
        st.markdown(response.text)
    
    # Add assistant response to state
    st.session_state.messages.append({"role": "assistant", "content": response.text})
