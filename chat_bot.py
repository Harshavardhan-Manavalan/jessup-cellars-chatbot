from flask import Flask, request, jsonify, render_template
from transformers import pipeline, AutoTokenizer, AutoModelForQuestionAnswering
from fuzzywuzzy import fuzz
import json
import os
import re

app = Flask(__name__)

# Load the corpus
corpus_path = os.path.join(os.path.dirname(__file__), 'Sample Question Answers.json')
with open(corpus_path, 'r', encoding='utf-8') as file:
    corpus = json.load(file)

# Initialize QA pipeline
tokenizer = AutoTokenizer.from_pretrained('distilbert-base-uncased-distilled-squad')
model = AutoModelForQuestionAnswering.from_pretrained('distilbert-base-uncased-distilled-squad')
qa_pipeline = pipeline('question-answering', model=model, tokenizer=tokenizer)

# Store conversation history
conversation_history = []

# Helper function to find the best answer from the corpus using fuzzy matching
def find_best_answer(question, language='en'):
    best_answer = ""
    best_score = float('-inf')
    for entry in corpus:
        context = entry.get(f'answer_{language}', entry['answer'])
        question_score = fuzz.partial_ratio(question.lower(), entry['question'].lower())
        if question_score > best_score:
            best_answer = context
            best_score = question_score
    return best_answer

# Helper function to handle follow-up questions
def handle_follow_up_question(question, language='en'):
    if not conversation_history:
        return "I'm sorry, I don't have any previous context to refer to."

    last_user_question = conversation_history[-1]['user']

    # Use regular expressions to identify references to previous questions
    match = re.search(r'(?:tell me|what about|more about)\s+(.*)', question.lower())
    if match:
        keyword = match.group(1).strip()
        for entry in reversed(conversation_history):
            if keyword in entry['user'].lower():
                return find_best_answer(keyword, language)

    # If no direct match, default to the last user question
    return find_best_answer(last_user_question, language)

@app.route('/')
def home():
    return render_template('index.html', bot_name="Jessup Cellars Chat bot")

@app.route('/chat', methods=['POST'])
def chat():
    try:
        data = request.json
        if not data or 'message' not in data:
            return jsonify({'answer': 'Error: Invalid request format. Missing "message" in JSON.'})

        user_input = data['message']
        language = data.get('language', 'en')
        print(f"User input: {user_input}, Language: {language}")

        # Manage conversation history
        conversation_history.append({'user': user_input, 'language': language})

        # Handle follow-up questions based on context
        if any(word in user_input.lower() for word in ['tell me', 'what about', 'more about']):
            answer = handle_follow_up_question(user_input, language)
        else:
            answer = find_best_answer(user_input, language)

        if not answer:
            answer = 'Please contact the business directly for more information.'

        conversation_history.append({'bot': answer, 'language': language})

        return jsonify({'answer': answer})

    except KeyError as ke:
        return jsonify({'answer': f'KeyError: {str(ke)}. Please check your request format.'})

    except Exception as e:
        return jsonify({'answer': f'Error: {str(e)}'})

if __name__ == "__main__":
    app.run(debug=True)
