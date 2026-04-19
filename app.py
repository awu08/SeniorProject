import streamlit as st
import google.generativeai as genai
import os

genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
model = genai.GenerativeModel('gemini-2.5-flash')

st.set_page_config(page_title="Gemini Chat", layout="centered")
st.title("Guided Helper")

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
        try:
            response = model.generate_content(
                "You are a high school math tutor. Do not give direct answers unless the student has tried. Ask guiding questions and give hints.\n\n" + prompt
            )
            reply = response.text if response.text else "No response."
            st.markdown(reply)
        except Exception as e:
            st.error(f"Error: {e}")
            reply = "Error occurred."

    st.session_state.messages.append({"role": "assistant", "content": response.text})
