from flask import Flask, request, jsonify
from flask_cors import CORS
import os

app = Flask(__name__)

# Specify the allowed origins (frontend URL)
CORS(app, resources={r"/api/*": {"origins": "*"}})

#CORS(app)

@app.route('/api/process', methods=['POST'])
def process_input():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        user_input = data.get('message', '')
        if not user_input.strip():
            return jsonify({'error': 'Empty message'}), 400
        print(f"Received the message: {user_input}")
        response = f"Hello! Unfortunately, the app is not yet smart enough to handle your requirements: {user_input}. Sorry and Thank You for Your Patience."
        return jsonify({'response': response})
    except Exception as e:
        print(f"Exception occured in endpoint: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    port = int(os.getenv('PORT', 8080))
    app.run(debug=True, host='0.0.0.0', port=port)
    #app.run(debug=True)