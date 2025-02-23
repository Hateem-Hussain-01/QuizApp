import os
import json
import requests
import streamlit as st
from PyPDF2 import PdfReader
import re
from dotenv import load_dotenv

# Load API key
load_dotenv()
API_KEY = os.getenv("TOGETHER_API_KEY")
API_URL = "https://api.together.xyz/v1/chat/completions"
HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

def ask_together_api(prompt, model="meta-llama/Llama-2-7b-chat-hf"):
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "You are an AI that generates well-structured quiz questions."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7,
        "max_tokens": 500
    }
    response = requests.post(API_URL, headers=HEADERS, json=payload)
    data = response.json()
    return data.get("choices", [{}])[0].get("message", {}).get("content", "API Error")

def extract_text_from_pdf(uploaded_file):
    reader = PdfReader(uploaded_file)
    text = "".join([page.extract_text() for page in reader.pages if page.extract_text()])
    return text

def remove_answers(quiz_text):
    quiz_text = re.sub(r'Correct answer: .*', '', quiz_text)
    quiz_text = re.sub(r'Answer:.*', '', quiz_text)
    quiz_text = re.sub(r'True or False: .*', 'True or False: __________', quiz_text)
    return quiz_text.strip()

def generate_quiz(text, difficulty, question_counts):
    quiz_with_answers = []
    for q_type, num in question_counts.items():
        if num > 0:
            prompt = f"Generate {num} {q_type} questions with {difficulty} difficulty from the text: {text[:1000]}..."
            questions_with_answers = ask_together_api(prompt)
            quiz_with_answers.append(questions_with_answers)
    return "\n\n".join(quiz_with_answers), remove_answers("\n\n".join(quiz_with_answers))

st.title("AI-Powered Quiz Generator")
user_type = st.radio("Are you a Teacher or Student?", ("Teacher", "Student"))

uploaded_file = st.file_uploader("Upload PDF Notes", type=["pdf"])

difficulty = st.selectbox("Select Difficulty Level", ["easy", "medium", "hard"])

if user_type == "Teacher":
    num_mcq = st.number_input("Number of MCQs", min_value=0, step=1)
    num_fill = st.number_input("Number of Fill in the Blanks", min_value=0, step=1)
    num_tf = st.number_input("Number of True/False", min_value=0, step=1)
    
    if st.button("Generate Quiz"):
        if uploaded_file:
            text = extract_text_from_pdf(uploaded_file)
            question_counts = {"MCQs": num_mcq, "Fill in the Blanks": num_fill, "True/False": num_tf}
            quiz_with_answers, quiz_questions = generate_quiz(text, difficulty, question_counts)
            st.text_area("Generated Quiz (Without Answers)", quiz_questions, height=300)
            st.text_area("Generated Quiz (With Answers)", quiz_with_answers, height=300)
            
            quiz_questions_bytes = quiz_questions.encode('utf-8')
            quiz_with_answers_bytes = quiz_with_answers.encode('utf-8')
            
            st.download_button("Download Quiz (Without Answers)", quiz_questions_bytes, "quiz_questions.txt", "text/plain")
            st.download_button("Download Quiz (With Answers)", quiz_with_answers_bytes, "quiz_with_answers.txt", "text/plain")
        else:
            st.error("Please upload a PDF file.")

elif user_type == "Student":
    if uploaded_file:
        text = extract_text_from_pdf(uploaded_file)
        if "quiz_state" not in st.session_state:
            st.session_state.quiz_state = {"questions": [], "current_index": 0}
        
        if st.button("Start Quiz") or st.session_state.quiz_state["questions"]:
            if not st.session_state.quiz_state["questions"]:
                for _ in range(5):  # Generate 5 questions
                    quiz_with_answers, question_only = generate_quiz(text, difficulty, {"MCQs": 1})
                    st.session_state.quiz_state["questions"].append((question_only, quiz_with_answers))
            
            current_index = st.session_state.quiz_state["current_index"]
            if current_index < len(st.session_state.quiz_state["questions"]):
                question_only, quiz_with_answers = st.session_state.quiz_state["questions"][current_index]
                st.write("**Question:**", question_only)
                user_answer = st.text_input("Your Answer", key=f"answer_{current_index}")
                if st.button("Submit Answer"):
                    st.write("**Correct Answer:**", quiz_with_answers.split("Correct answer:")[-1].strip())
                    st.session_state.quiz_state["current_index"] += 1
            else:
                st.write("Quiz Completed!")
    else:
        st.error("Please upload a PDF file.")

#ended
