from flask import Flask, render_template, request, jsonify, session, send_file
import os, json, requests
from openai import OpenAI
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Needed for session

# Configure upload folder
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'pdf', 'docx', 'doc'}

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Initialize OpenAI client
client = OpenAI(
    api_key='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')


# Helper function to check allowed file types
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/')
def homepage():
    # Get list of uploaded files
    uploaded_files = []
    if os.path.exists(app.config['UPLOAD_FOLDER']):
        uploaded_files = [f for f in os.listdir(app.config['UPLOAD_FOLDER'])]

    # Get chat input from session if available
    chat_input = session.get('chat_input', '')

    return render_template('index.html', uploaded_files=uploaded_files, chat_input=chat_input)


@app.route('/upload', methods=['POST'])
def upload_source():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'})

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'})

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)

        # Get the file type for icon display
        file_type = filename.rsplit('.', 1)[1].lower()

        return jsonify({
            'success': True,
            'filename': filename,
            'file_type': file_type
        })

    return jsonify({'error': 'File type not allowed'})


@app.route('/genereaza-intrebare', methods=['POST'])
def rag_query():
    """
    API endpoint to retrieve test questions

    Accepts a POST request with:
    - query: The prompt for generating a question

    Returns a JSON response with the generated question
    """
    # Parse request data
    data = request.get_json() or {}

    # Extract query (with default)
    query = data.get('query', "Generate a multiple choice question with 4 choices. Mark the correct answer.")

    # Make a request to the RAG API (app2.py) to generate the question
    url = "http://localhost:5001/api/rag/query"

    payload = json.dumps({
        "query": query
    })
    headers = {
        'Content-Type': 'application/json'
    }

    try:
        response = requests.request("POST", url, headers=headers, data=payload)
        ai_response = response.json().get("response", "")

        # Return the AI response
        return jsonify({
            "success": True,
            "data": ai_response
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        })

def format_test_questions(ai_response):
    """
    Parse AI-generated test questions and format them into a structured JSON format.

    Args:
        ai_response (str): The raw text response from the AI containing questions

    Returns:
        list: A list of dictionaries, each representing a question with:
            - id: unique identifier for the question
            - text: the question text
            - options: list of possible answers
            - correct_answer: the correct answer(s)
    """
    formatted_questions = []

    # Split the response into individual questions
    # This assumes questions start with numbers followed by a period or parenthesis
    import re

    # Clean up the response text
    cleaned_text = ai_response.strip()

    # Split by question pattern (1., 2., etc.)
    questions_raw = re.split(r'\n\s*\d+[\.\)]\s*', '\n' + cleaned_text)

    # Remove any empty first element if the split created one
    if questions_raw and not questions_raw[0].strip():
        questions_raw.pop(0)

    for i, question_text in enumerate(questions_raw):
        if not question_text.strip():
            continue

        question_id = i + 1
        question_data = {
            "id": question_id,
            "text": "",
            "options": [],
            "correct_answer": []
        }

        # Split into lines for processing
        lines = question_text.strip().split('\n')

        # Extract question text (everything up to the first option)
        question_text_lines = []
        option_start_idx = None

        for j, line in enumerate(lines):
            # Look for option patterns: A), a., 1), etc.
            if re.match(r'^\s*[A-Da-d1-4][\.\)]\s+', line) or re.match(r'^\s*True|False\s*[\.\:]', line, re.IGNORECASE):
                option_start_idx = j
                break
            else:
                question_text_lines.append(line)

        # Set the question text
        question_data["text"] = " ".join([l.strip() for l in question_text_lines]).strip()

        # If no options were found, continue to next question
        if option_start_idx is None:
            continue

        # Extract options
        options = []
        option_texts = {}
        current_option = None

        for line in lines[option_start_idx:]:
            # Check if this is a new option
            option_match = re.match(r'^\s*([A-Da-d1-4])[\.\)]\s+(.*)', line)
            tf_match = re.match(r'^\s*(True|False)\s*[\.\:]?(.*)', line, re.IGNORECASE)

            if option_match:
                current_option = option_match.group(1).upper()
                option_text = option_match.group(2).strip()
                options.append(current_option)
                option_texts[current_option] = option_text
            elif tf_match:
                current_option = tf_match.group(1).capitalize()
                option_text = current_option
                options.append(current_option)
                option_texts[current_option] = current_option
            elif current_option and line.strip():
                # Continuation of previous option
                option_texts[current_option] += " " + line.strip()

        # Set the options in the required format
        question_data["options"] = [{"id": opt, "text": option_texts[opt]} for opt in options]

        # Try to determine correct answer(s)
        for line in lines:
            # Look for patterns indicating correct answers
            correct_answer_match = re.search(r'correct\s+answer\s*[:\-]?\s*([A-Da-d1-4,\s]+)', line, re.IGNORECASE)
            answer_key_match = re.search(r'answer\s*[:\-]?\s*([A-Da-d1-4,\s]+)', line, re.IGNORECASE)

            if correct_answer_match:
                # Extract letter answers (A, B, C, D)
                answers = re.findall(r'[A-Da-d1-4]', correct_answer_match.group(1))
                question_data["correct_answer"] = [answer.upper() for answer in answers]
                break
            elif answer_key_match and not question_data["correct_answer"]:
                # Alternative pattern
                answers = re.findall(r'[A-Da-d1-4]', answer_key_match.group(1))
                question_data["correct_answer"] = [answer.upper() for answer in answers]

        # If no explicit correct answer was found in text markers, look for other indicators
        if not question_data["correct_answer"]:
            for opt_id, opt_text in option_texts.items():
                # Check for asterisks, "correct", or other markers
                if '*' in opt_text or re.search(r'\(correct\)', opt_text, re.IGNORECASE):
                    # Remove the marker from the option text
                    clean_text = re.sub(r'\s*\*\s*|\s*\(correct\)\s*', '', opt_text, flags=re.IGNORECASE)
                    option_texts[opt_id] = clean_text
                    # Update the option text in the options list
                    for i, opt in enumerate(question_data["options"]):
                        if opt["id"] == opt_id:
                            question_data["options"][i]["text"] = clean_text
                    # Add to correct answers
                    question_data["correct_answer"].append(opt_id)

        # For True/False questions
        if len(options) == 2 and "True" in options and "False" in options:
            # Check for specific indications in the question text
            if "correct answer: true" in question_data["text"].lower():
                question_data["correct_answer"] = ["True"]
            elif "correct answer: false" in question_data["text"].lower():
                question_data["correct_answer"] = ["False"]

            # Remove any correct answer indicators from the question text
            question_data["text"] = re.sub(r'\s*\(correct answer:?\s*(?:true|false)\)\s*', '',
                                           question_data["text"], flags=re.IGNORECASE)

        formatted_questions.append(question_data)

    return formatted_questions


def process_ai_response(ai_response):
    """
    Process the AI response and return formatted test questions

    Args:
        ai_response (str): Raw AI-generated text

    Returns:
        dict: A dictionary with the formatted test questions
    """
    try:
        formatted_questions = format_test_questions(ai_response)
        return {
            "success": True,
            "questions": formatted_questions
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

@app.route('/genereaza-test', methods=['POST'])
def genereaza_test():
    """
    Route to handle test generation requests.
    Expects a JSON payload with:
    - questionType: Type of questions (TrueFalse, SingleChoice, MultipleChoice)
    - topic: The topic for the test
    - numQuestions: Number of questions to generate

    Returns:
    - A JSON response with formatted questions and a filename for downloading
    """
    # Get JSON data from request
    data = request.get_json()

    # Extract and validate required fields
    question_type = data.get('questionType')
    topic = data.get('topic')
    num_questions = data.get('numQuestions')

    print(f"Generating test: {question_type} with {num_questions} questions on '{topic}'")

    url = "http://localhost:5001/api/rag/query"

    payload = json.dumps({
        "query": f"Generate a test with {num_questions} {question_type} questions based on the following topic {topic}. Mark the correct answer."
    })
    headers = {
        'Content-Type': 'application/json'
    }

    response = requests.request("POST", url, headers=headers, data=payload)
    ai_response = response.json()["response"]

    print(ai_response)

    # Format the questions into the required structure
    formatted_result = process_ai_response(ai_response)

    # Include both raw text and formatted questions in response
    response_data = {
        "raw_text": ai_response,
        "formatted_questions": formatted_result["questions"] if formatted_result["success"] else []
    }

    # Save response to a text file for backward compatibility
    filename = "Test.txt"
    with open(filename, 'w', encoding='utf-8') as file:
        file.write(f"Test: {question_type} on {topic}\n")
        file.write(f"Number of questions: {num_questions}\n")
        file.write("\n" + "-" * 40 + "\n\n")
        file.write(ai_response)

    # Add the filename to the response
    response_data["filename"] = filename

    return jsonify(response_data)



@app.route('/delete', methods=['POST'])
def delete_file():
    data = request.get_json()
    if not data or 'filename' not in data:
        return jsonify({'error': 'No filename provided'}), 400

    filename = data['filename']
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)

    # Check if file exists and delete it
    if os.path.exists(file_path):
        try:
            os.remove(file_path)
            return jsonify({'success': True, 'message': f'File {filename} deleted successfully'})
        except Exception as e:
            return jsonify({'error': f'Error deleting file: {str(e)}'}), 500
    else:
        return jsonify({'error': 'File not found'}), 404

@app.route('/download')
def downloadFile ():
    #For windows you need to use drive name [ex: F:/Example.pdf]
    path = "C:\\Users\\popai\\OneDrive\\Desktop\\Hachathon\\Hackathon\\Test.txt"
    return send_file(path, as_attachment=True)
@app.route('/submit_chat', methods=['POST'])
def submit_chat():
    data = request.get_json()
    if not data or 'message' not in data:
        return jsonify({'error': 'No message provided'}), 400

    # Store the chat input in session
    chat_input = data['message']
    session['chat_input'] = chat_input

    # try:
    #     # Send the chat input to the OpenAI API using the new client
    #     response = client.chat.completions.create(
    #         model="gpt-4",  # Use the desired model
    #         messages=[
    #             {"role": "system", "content": "You are a helpful assistant."},
    #             {"role": "user", "content": chat_input}
    #         ]
    #     )
    #
    #     # Extract the AI's response
    #     ai_response = response.choices[0].message.content
    #
    #     return jsonify({
    #         'success': True,
    #         'received_message': chat_input,
    #         'ai_response': ai_response
    #     })
    # except Exception as e:
    #     return jsonify({'error': f'Error communicating with AI: {str(e)}'}), 500


    url = "http://localhost:5001/api/rag/query"

    payload = json.dumps({
        "query": chat_input
    })
    headers = {
        'Content-Type': 'application/json'
    }

    response = requests.request("POST", url, headers=headers, data=payload)
    ai_response = response.json()["response"]

    return jsonify({
                            'success': True,
                            'received_message': chat_input,
                            'ai_response': ai_response
                     })



# @app.route('/generate_test', methods=['POST'])
# def generate_test():
#     data = request.get_json()
#     if not data or 'message' not in data:
#         return jsonify({'error': 'No message provided'}), 400
#
#     # Store the chat input in session
#     chat_input = data['message']
#     session['chat_input'] = chat_input
#
#     try:
#         # Send the chat input to the OpenAI API
#         response = client.chat.completions.create(
#             model="gpt-4",  # Use the desired model
#             messages=[
#                 {"role": "system",
#                  "content": "Tu esti un asistent AI care raspunde la intrebari pe baza continutuli fsierelor incarcate."},
#                 {"role": "user", "content": chat_input}
#             ]
#         )
#
#         # Extract the AI's response
#         ai_response = response.choices[0].message.content
#
#         return jsonify({
#             'success': True,
#             'received_message': chat_input,
#             'ai_response': ai_response
#         })
#     except Exception as e:
#         return jsonify({'error': f'Error communicating with AI: {str(e)}'}), 500
#

if __name__ == '__main__':
    app.run(debug=True)