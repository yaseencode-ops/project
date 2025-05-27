from flask import Blueprint, render_template, request, jsonify
from app.models.code_analyzer import CodeReviewModel

main = Blueprint('main', __name__)
code_reviewer = CodeReviewModel()

@main.route('/')
def index():
    return render_template('index.html')

@main.route('/analyze', methods=['POST'])
def analyze_code():
    try:
        code = request.json.get('code', '')
        if not code:
            return jsonify({'error': 'No code provided'}), 400
            
        issues = code_reviewer.analyze_code(code)
        return jsonify({'issues': issues})
    except Exception as e:
        return jsonify({'error': str(e)}), 500 