from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
from ibm_watson import DiscoveryV2
from ibm_cloud_sdk_core.authenticators import IAMAuthenticator
import time
from dotenv import load_dotenv
import os
from langchain_ibm import WatsonxLLM

load_dotenv()

app = Flask(__name__)

# Specify the allowed origins (frontend URL)
CORS(app, resources={r"/api/*": {"origins": "*"}})

#CORS(app)

WATSON_DISCOVERY_API_KEY = os.getenv('WATSON_DISCOVERY_API_KEY')
WATSON_DISCOVERY_URL = os.getenv('WATSON_DISCOVERY_URL')
PROJECT_ID = os.getenv('PROJECT_ID')
COLLECTION_ID = os.getenv('COLLECTION_ID')
VERSION = os.getenv('VERSION')
WATSONX_LLM_URL = os.getenv('WATSONX_LLM_URL')
WATSONX_PROJECT_ID = os.getenv('WATSONX_PROJECT_ID')
WATSONX_API_KEY = os.getenv('WATSONX_API_KEY')
WATSONX_MODEL_ID = os.getenv('WATSONX_MODEL_ID')

# Initializing Watson Discovery
def get_discovery_client():
    """Initialize and return Watson Discovery client"""
    try:
        authenticator = IAMAuthenticator(WATSON_DISCOVERY_API_KEY)
        discovery = DiscoveryV2(
            version=VERSION,
            authenticator=authenticator
        )
        discovery.set_service_url(WATSON_DISCOVERY_URL)
        return discovery
    except Exception as e:
        print(f"Error initializing Watson Discovery: {str(e)}")
        return None
    
@app.route('/api/documents', methods=['GET'])
def get_documents():
    """Fetch list of documents from Watson Discovery"""
    try:
        discovery = get_discovery_client()
        
        if not discovery:
            return jsonify({
                'error': 'Watson Discovery not configured',
                'documents': []
            }), 500
                
        # Query Watson Discovery to list documents
        response = discovery.list_documents(project_id=PROJECT_ID, collection_id=COLLECTION_ID).get_result()
        #response = requests.get(WATSON_URL, params=params, auth=auth)
        documents = []
        for doc in response.get('documents', []):
            documents.append({
                'document_id': doc.get('document_id'),
                'created': doc.get('created'),
                'metadata': {
                    'file_type': doc.get('file_type'),
                    'size': doc.get('file_size')
                }
            })
        
        return jsonify({
            'documents': documents,
            'count': len(documents),
            'timestamp': time.time()
        })
        
    except Exception as e:
        print(f"Error fetching documents: {str(e)}")
        return jsonify({'error': str(e), 'documents': []}), 500
    '''documents = []
    documents.append({
                'document_id': '1',
                'title': 'Sample Doc',
                'name': 'Sample Doc.pdf',
                'created': '14.10.2025',
                'metadata': {
                    'file_type': 'pdf',
                    'size': '2.0 KB'
                }
            })
    return jsonify({
            'documents': documents,
            'count': len(documents),
            'timestamp': time.time()
        })'''
    
@app.route('/api/chat', methods=['POST'])
def chat():
    try:
        # Get the JSON data from the request
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        user_message = data.get('message', '')
        document_name = data.get('document_name', 'Unknown Document')
        
        if not user_message.strip():
            return jsonify({'error': 'Empty message'}), 400
        
        print(f"Received message: {user_message}")
        print(f"Document: {document_name}")
        
        # Query Watson Discovery for answer
        bot_response = query_watson_discovery(user_message, document_name)
        
        return jsonify({
            'response': bot_response,
            'document': document_name,
            'timestamp': time.time()
        })
        
    except Exception as e:
        print(f"Error in chat endpoint: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

def query_watson_discovery(question, document_name):
    """
    Sending the query from the user to Watson Discovery
    """
    try:
        discovery = get_discovery_client()
        
        if not discovery:
            return "Watson Discovery is not configured. Please check your credentials."
        
        # Query Watson Discovery
        response = discovery.query(
            project_id=PROJECT_ID,
            natural_language_query=question,
            count=3 
        ).get_result()
        
        results = response.get('results', [])
        
        if not results:
            return "I couldn't find any relevant information in the documents for your question."
        
        # Build response from top result, since there is a need to know on the flow of data from Watson Discovery to the LLM
        top_result = results[0]
        answer_text = top_result['text'][:500]

        ret_data = str(answer_text)

        prompt = f"Based on the following information: '{ret_data}', {question}"

        watsonx_llm = WatsonxLLM(
             model_id=WATSONX_MODEL_ID,
             url=WATSONX_LLM_URL,
             project_id=WATSONX_PROJECT_ID,
             params={"decoding_method": "greedy", "max_new_tokens": 1000},
             apikey = WATSONX_API_KEY
         )
        try:
            llm_response = watsonx_llm.generate(prompts=[prompt])
            return f"Based on the document, here's what I found: {llm_response.generations[0][0].text}"
        except Exception as e:
            return jsonify({"error": str(e)}), 500
        
        """ if answer_text:
            return f"Based on the document, here's what I found: {answer_text}"
        else:
            return "I found relevant information but couldn't extract a clear answer. Please try rephrasing your question." """
            
    except Exception as e:
        print(f"Error querying Watson Discovery: {str(e)}")
        # Fallback to sample response if Watson fails
        return process_input(question, document_name)

def process_input(query, doc_name):
    question_lower = query.lower()
    if 'summary' in question_lower or 'summarize' in question_lower:
        return f"Here's a summary of {doc_name}: The document covers key concepts including methodology, findings, and conclusions. The main themes revolve around..."
    
    elif 'key finding' in question_lower or 'main point' in question_lower:
        return f"The key findings from {doc_name} include: 1) Primary discovery regarding the research question, 2) Supporting evidence from data analysis, 3) Implications for future work..."
    
    elif 'conclusion' in question_lower:
        return f"The conclusions drawn in {doc_name} suggest that the research objectives were met and the hypothesis was supported by the evidence presented..."
    else:
        return "There are currently no answers for this request. We are deeply sorry for this."

if __name__ == '__main__':
    #port = int(os.getenv('PORT', 8080))
    #app.run(debug=True, host='0.0.0.0', port=port)
    #app.run(debug=True)
    app.run(
        debug=True,
        host='0.0.0.0',
        port=5000,
        threaded=True
    )