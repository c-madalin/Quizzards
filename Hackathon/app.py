from flask import Flask, render_template, request, jsonify, session
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Needed for session

# Configure upload folder
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'pdf', 'docx', 'doc'}

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/')
def homepage():
    # Get list of uploaded files
    uploaded_files = []
    if os.path.exists(app.config['UPLOAD_FOLDER']):
        # Get files from the upload folder
        uploaded_files = [f for f in os.listdir(app.config['UPLOAD_FOLDER'])]

    return render_template('index.html', uploaded_files=uploaded_files)


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


if __name__ == '__main__':
    app.run(debug=True)