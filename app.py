import streamlit as st
import google.generativeai as genai
import os

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel('gemini-1.5-flash')

st.set_page_config(page_title="Gemini Chat", layout="centered")
st.title("💬 Gemini Assistant")

with st.chat_message("assistant"):
    st.markdown("HI")

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("How can I help you?"):
    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        response = model.generate_content(
            "You are a high school math tutor. "
            "Do not give direct answers unless the student has tried. "
            "Ask guiding questions and give hints.\n\n"
            + prompt
        )
        st.markdown(response.text + "HI")

    st.session_state.messages.append({"role": "assistant", "content": response.text})
