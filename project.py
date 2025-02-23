import os
import json
import requests
from PyPDF2 import PdfReader
from dotenv import load_dotenv
import re

# Load API key
load_dotenv()
API_KEY = os.getenv("TOGETHER_API_KEY")

if not API_KEY:
    print("❌ Error: API Key not found! Please check your .env file or environment variables.")
    exit()

# ✅ Correct Together AI API URL
API_URL = "https://api.together.xyz/v1/chat/completions"
HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

# ✅ Function to call Together AI API
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

    try:
        response = requests.post(API_URL, headers=HEADERS, json=payload)
        response.raise_for_status()
        data = response.json()

        if "choices" in data and data["choices"]:
            return data["choices"][0]["message"]["content"]
        else:
            return "⚠️ API responded, but format is unexpected."
    except requests.exceptions.RequestException as e:
        return f"❌ API Request Error: {e}"

# ✅ Function to extract text from PDF
def extract_text_from_pdf(pdf_path):
    try:
        reader = PdfReader(pdf_path)
        text = "".join([page.extract_text() for page in reader.pages if page.extract_text()])
        return text
    except Exception as e:
        return f"❌ Error extracting text: {e}"

# ✅ Remove answers and explanations from quiz (for student version)
def remove_answers(quiz_text):
    quiz_text = re.sub(r'Correct answer: .*', '', quiz_text)  # Remove MCQ answers
    quiz_text = re.sub(r'Answer:.*', '', quiz_text)  # Remove Fill in the Blanks answers
    quiz_text = re.sub(r'True or False: .*', 'True or False: __________', quiz_text)  # Mask True/False answers
    quiz_text = re.sub(r'Explanation: .*', '', quiz_text)  # Remove True/False explanations
    return quiz_text.strip()

# ✅ Adaptive Difficulty for Student Mode
def adjust_difficulty(correct, total, current_difficulty):
    accuracy = (correct / total) * 100
    if accuracy <= 25:
        return "easy"
    elif accuracy <= 50:
        return current_difficulty
    elif accuracy <= 75:
        return "hard" if current_difficulty == "medium" else current_difficulty
    else:
        return "hardest"

# ✅ Generate structured quiz questions
def generate_quiz(text, difficulty, question_counts):
    if not text:
        return "⚠️ Error: Could not extract text from PDF."
    
    quiz_with_answers = []
    
    for q_type, num in question_counts.items():
        if num > 0:
            format_example = f"Each {q_type} question should follow a structured format and clearly mention the correct answer."
            prompt = f"Generate {num} {q_type} questions with {difficulty} difficulty from the following text:\n{text[:1000]}...\nEnsure the format follows: {format_example}"
            questions_with_answers = ask_together_api(prompt)
            quiz_with_answers.append(questions_with_answers)
    
    full_quiz_with_answers = "\n\n".join(quiz_with_answers)
    quiz_questions_only = remove_answers(full_quiz_with_answers)
    
    return quiz_questions_only, full_quiz_with_answers

# ✅ Save the quiz to two separate files
def save_quiz(quiz_questions, quiz_with_answers):
    try:
        with open("quiz_questions.txt", "w", encoding="utf-8") as file:
            file.write("Generated Quiz (Without Answers)\n")
            file.write("=" * 50 + "\n\n")
            file.write(quiz_questions)
        print("✅ Quiz (questions only) saved as quiz_questions.txt")
        
        with open("quiz_with_answers.txt", "w", encoding="utf-8") as file:
            file.write("Generated Quiz (With Answers)\n")
            file.write("=" * 50 + "\n\n")
            file.write(quiz_with_answers)
        print("✅ Quiz (with answers) saved as quiz_with_answers.txt")
        
    except Exception as e:
        print(f"❌ Error saving quiz: {e}")

# ✅ Main function (Handles Teacher & Student Mode)
def main():
    user_type = input("Are you a Teacher or Student? (Enter 'teacher' or 'student'): ").strip().lower()

    pdf_paths = []
    while True:
        pdf_path = input("Enter the full path of your PDF file (or type 'done' to finish): ").strip()
        if pdf_path.lower() == "done":
            break
        pdf_paths.append(pdf_path)
    
    text = "\n".join([extract_text_from_pdf(pdf) for pdf in pdf_paths])

    if user_type == "teacher":
        difficulty = input("Select quiz difficulty (easy, medium, hard): ").strip().lower()
        num_mcq = int(input("How many MCQs? ").strip())
        num_fill = int(input("How many Fill in the Blanks? ").strip())
        num_tf = int(input("How many True/False? ").strip())
        question_counts = {"MCQs": num_mcq, "Fill in the Blanks": num_fill, "True/False": num_tf}

        quiz_questions, quiz_with_answers = generate_quiz(text, difficulty, question_counts)
        print("\n🎯 Generated Quiz:\n", quiz_with_answers)

        save_option = input("Do you want to save this quiz? (yes/no): ").strip().lower()
        if save_option == "yes":
            save_quiz(quiz_questions, quiz_with_answers)
    
    elif user_type == "student":
        difficulty = input("Select initial quiz difficulty (easy, medium, hard): ").strip().lower()
        correct_answers = 0
        total_questions = 0

        while True:
            question_with_answers = generate_quiz(text, difficulty, {"MCQs": 1})[1]
            question_only = remove_answers(question_with_answers)
            
            print("\n🎯 Question:", question_only)
            answer = input("Your Answer: ").strip()
            print("✅ Correct Answer:", question_with_answers.split("Correct answer:")[-1].strip())
            
            correct = input("Was your answer correct? (yes/no): ").strip().lower() == "yes"
            if correct:
                correct_answers += 1
            total_questions += 1
            difficulty = adjust_difficulty(correct_answers, total_questions, difficulty)

            stop = input("Do you want to stop the quiz? (yes/no): ").strip().lower()
            if stop == "yes":
                break
        
        print(f"\n📊 Final Score: {correct_answers}/{total_questions}")

if __name__ == "__main__":
    main()
