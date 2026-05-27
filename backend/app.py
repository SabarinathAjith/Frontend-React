
import os
from flask import Flask, request, jsonify
from flask_cors import CORS
import torch
from sentence_transformers import SentenceTransformer, util
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
from pypdf import PdfReader

# Advanced parsing libraries
from unstructured.partition.pdf import partition_pdf
from unstructured.chunking.title import chunk_by_title

class AIDocumentIntelligenceSystem:
    def __init__(self):
        print("Initializing Advanced AI Document Intelligence System...")
        
        print("Loading Sentence-BERT embedding model...")
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        
        print("Loading Hugging Face Generative QA model (FLAN-T5)...")
        self.qa_tokenizer = AutoTokenizer.from_pretrained("google/flan-t5-base")
        self.qa_model = AutoModelForSeq2SeqLM.from_pretrained("google/flan-t5-base")
        
        print("Loading Hugging Face Summarization model (BART)...")
        self.sum_tokenizer = AutoTokenizer.from_pretrained("facebook/bart-large-cnn")
        self.sum_model = AutoModelForSeq2SeqLM.from_pretrained("facebook/bart-large-cnn")
        
        self.document_text = ""
        self.document_chunks = []
        self.chunk_embeddings = None
        self.chat_history = []

    def load_and_process_pdf(self, file_path):
        print(f"\nPerforming Document Analysis on: {file_path}")
        try:
            # ATTEMPT 1: Advanced Unstructured Layout Analysis
            elements = partition_pdf(filename=file_path, strategy="fast")
            chunks = chunk_by_title(elements, max_characters=1000, combine_text_under_n_chars=300)
            self.document_chunks = [str(chunk).strip() for chunk in chunks if str(chunk).strip()]
            self.document_text = " ".join(self.document_chunks)
            
            # ATTEMPT 2: Bulletproof Fallback if Unstructured returns blank
            if not self.document_text.strip():
                print("Unstructured failed to find text. Falling back to PyPDF...")
                reader = PdfReader(file_path)
                text = ""
                for page in reader.pages:
                    extracted = page.extract_text()
                    if extracted:
                        text += extracted + "\n"
                
                self.document_text = text.strip()
                # Split the raw text into 1000-character chunks for the AI
                self.document_chunks = [self.document_text[i:i+1000] for i in range(0, len(self.document_text), 1000)]

            # If both methods fail, the PDF is likely an image with no text layer
            if not self.document_text.strip():
                print("Both methods failed. PDF might be a scanned image.")
                return False

            print(f"Document segmented into {len(self.document_chunks)} context-aware chunks.")
            print("Generating vector embeddings...")
            
            # Force the tensor to load properly into the class memory
            self.chunk_embeddings = self.embedding_model.encode(self.document_chunks, convert_to_tensor=True)
            return True
            
        except Exception as e:
            print(f"Error during layout analysis: {e}")
            return False

    def semantic_search(self, query, top_k=3):
        if self.chunk_embeddings is None:
            return "No document loaded."

        query_embedding = self.embedding_model.encode(query, convert_to_tensor=True)
        hits = util.semantic_search(query_embedding, self.chunk_embeddings, top_k=top_k)[0]
        relevant_chunks = [self.document_chunks[hit['corpus_id']] for hit in hits]
        return " ".join(relevant_chunks)

    def answer_question(self, query):
        if self.chunk_embeddings is None:
            return "Please upload a document first."

        search_query = query
        if self.chat_history:
            last_interaction = self.chat_history[-1]
            search_query = f"{last_interaction['question']} {last_interaction['answer']} {query}"
            
        context = self.semantic_search(search_query, top_k=3)
        
        prompt = (
            f"Please answer the question comprehensively and in detail based ONLY on the provided context.\n\n"
            f"Context: {context}\n\n"
            f"Question: {query}\n\n"
            f"Detailed Answer:"
        )
        
        inputs = self.qa_tokenizer(prompt, return_tensors="pt", truncation=True, max_length=1024)
        outputs = self.qa_model.generate(
            inputs["input_ids"],
            max_new_tokens=250,
            min_length=30,
            do_sample=True,
            temperature=0.7
        )
        
        answer = self.qa_tokenizer.decode(outputs[0], skip_special_tokens=True)
        self.chat_history.append({"question": query, "answer": answer})
        
        return answer

    def generate_summary(self, max_length=200, min_length=50):
        if not self.document_text:
            return "No document available to summarize."

        text_to_summarize = " ".join(self.document_text.split()[:800]) 
        inputs = self.sum_tokenizer(text_to_summarize, return_tensors="pt", max_length=1024, truncation=True)
        summary_ids = self.sum_model.generate(
            inputs["input_ids"], 
            max_length=max_length, 
            min_length=min_length, 
            do_sample=False
        )
        return self.sum_tokenizer.decode(summary_ids[0], skip_special_tokens=True)

# --- FLASK APPLICATION SETUP ---
app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

# Initialize the AI System exactly once
ai_system = AIDocumentIntelligenceSystem()

# The persistent file name for Docker hard drive storage
PERSISTENT_PDF_PATH = "/tmp/persistent_document.pdf"

def check_and_restore_state():
    """If a cloud worker forgets the document, silently restore it from the hard drive."""
    if ai_system.chunk_embeddings is None and os.path.exists(PERSISTENT_PDF_PATH):
        print("Amnesia detected! Restoring AI state from persistent PDF...")
        ai_system.load_and_process_pdf(PERSISTENT_PDF_PATH)

# --- API ROUTES ---

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({"error": "No file uploaded"}), 400
        
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    # Save the file permanently so workers can find it later
    file.save(PERSISTENT_PDF_PATH)
    
    # Process the file into the AI's RAM
    success = ai_system.load_and_process_pdf(PERSISTENT_PDF_PATH)

    if success:
        return jsonify({
            "message": "File processed successfully!", 
            "text": ai_system.document_text[:1500] + "...\n[Content truncated for display]"
        })
    else:
        return jsonify({"error": "Failed to process file"}), 500

@app.route('/ask', methods=['POST'])
def ask_question():
    # Make sure the worker has the document in its RAM
    check_and_restore_state()
    
    if ai_system.chunk_embeddings is None:
        return jsonify({"answer": "No document context available. Please upload a PDF first."}), 400

    data = request.json
    user_question = data.get('question')

    if not user_question:
        return jsonify({"error": "No question provided"}), 400

    answer = ai_system.answer_question(user_question)
    return jsonify({"answer": answer})

@app.route('/summary', methods=['GET'])
def get_summary():
    # Make sure the worker has the document in its RAM
    check_and_restore_state()
    
    if ai_system.chunk_embeddings is None:
        return jsonify({"summary": "No document available to summarize."})

    summary = ai_system.generate_summary()
    return jsonify({"summary": summary})

if __name__ == '__main__':
    print("\n" + "="*50)
    print("🚀 Starting AI Document Intelligence API Server...")
    print("Server running on http://0.0.0.0:5000")
    print("="*50 + "\n")
    app.run(host='0.0.0.0', port=5000, debug=False)
