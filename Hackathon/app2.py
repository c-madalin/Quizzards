import os
import json
import time
import requests
from flask import Flask, request, jsonify
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_community.document_loaders import TextLoader, PyPDFLoader, PDFMinerLoader, PyMuPDFLoader, DirectoryLoader
from langchain_community.embeddings import OllamaEmbeddings

# Configuration for Ollama
DEFAULT_EMBEDDING_MODEL = "nomic-embed-text"

app = Flask(__name__)

# Configuration
UPLOAD_FOLDER = './uploads'
VECTORDB_PATH = './chroma_db'
OLLAMA_URL = 'http://localhost:11434/api/generate'
DEFAULT_MODEL = 'gemma:2b'
OLLAMA_BASE_URL = 'http://localhost:11434'

# Ensure upload directory exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Initialize Ollama embedding model
embedding_model = OllamaEmbeddings(
    model=DEFAULT_EMBEDDING_MODEL,
    base_url='http://localhost:11434'
)

# Global variable to store the vector DB
vectordb = None


def query_ollama(prompt, model=DEFAULT_MODEL):
    """Send a prompt to Ollama API and get the response."""
    data = {
        "model": model,
        "prompt": prompt,
        "stream": False
    }

    try:
        response = requests.post(OLLAMA_URL, json=data, timeout=60)
        return response.json()["response"]
    except Exception as e:
        app.logger.error(f"Error querying Ollama: {e}")
        return f"Error generating response: {str(e)}"


def load_document(file_path):
    """Load a single document with appropriate loader based on file extension."""
    if file_path.endswith('.txt'):
        try:
            # Try UTF-8 encoding first
            loader = TextLoader(file_path, encoding='utf-8')
            return loader.load()
        except UnicodeDecodeError:
            # If UTF-8 fails, try with Latin-1 encoding
            try:
                app.logger.info(f"Retrying {file_path} with latin-1 encoding")
                loader = TextLoader(file_path, encoding='latin-1')
                return loader.load()
            except Exception as e:
                app.logger.error(f"Error loading text file with latin-1 encoding {file_path}: {e}")
                # As a last resort, try to open and read the file manually
                try:
                    app.logger.info(f"Attempting manual file reading for {file_path}")
                    from langchain_core.documents import Document

                    # Try different encodings
                    for encoding in ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']:
                        try:
                            with open(file_path, 'r', encoding=encoding) as f:
                                text = f.read()
                                return [Document(page_content=text, metadata={"source": file_path})]
                        except UnicodeDecodeError:
                            continue
                        except Exception as e:
                            app.logger.error(f"Manual reading with {encoding} failed: {e}")

                    # If all encodings fail, return empty list
                    app.logger.error(f"All encoding attempts failed for {file_path}")
                    return []
                except Exception as e:
                    app.logger.error(f"Manual file reading failed: {e}")
                    return []
        except Exception as e:
            app.logger.error(f"Error loading text file {file_path}: {e}")
            return []

    elif file_path.endswith('.pdf'):
        # Try different PDF loaders
        pdf_loaders = [PyPDFLoader, PDFMinerLoader, PyMuPDFLoader]

        for loader_class in pdf_loaders:
            try:
                loader = loader_class(file_path)
                return loader.load()
            except Exception as e:
                app.logger.error(f"Error with {loader_class.__name__} for {file_path}: {e}")
                continue

        app.logger.error(f"Failed to load PDF with any loader: {file_path}")
        return []

    app.logger.warning(f"Unsupported file type: {file_path}")
    return []


def load_documents_with_error_handling(directory_path):
    """Load documents from a directory with better error handling for PDFs."""
    all_documents = []
    accepted_extensions = ['.txt', '.pdf']

    try:
        # First check if directory exists
        if not os.path.exists(directory_path):
            app.logger.error(f"Directory not found: {directory_path}")
            return all_documents

        # Use os.walk to recursively find all files with accepted extensions
        for root, _, files in os.walk(directory_path):
            # Process each file
            for file in files:
                file_ext = os.path.splitext(file)[1].lower()
                if file_ext in accepted_extensions:
                    file_path = os.path.join(root, file)

                    # Skip files that are too large (optional)
                    # file_size = os.path.getsize(file_path)
                    # if file_size > MAX_FILE_SIZE:  # e.g., 50MB
                    #     app.logger.warning(f"Skipping large file: {file_path} ({file_size/1024/1024:.2f} MB)")
                    #     continue

                    app.logger.info(f"Processing file: {file_path}")
                    try:
                        docs = load_document(file_path)
                        if docs:
                            all_documents.extend(docs)
                            app.logger.info(f"Successfully loaded {len(docs)} docs from {file_path}")
                        else:
                            app.logger.warning(f"No content extracted from {file_path}")
                    except Exception as e:
                        app.logger.error(f"Error processing {file_path}: {str(e)}")
    except Exception as e:
        app.logger.error(f"Error walking directory {directory_path}: {str(e)}")

    app.logger.info(f"Total documents loaded: {len(all_documents)}")
    return all_documents


def process_documents(directory_path):
    """Load documents from a directory and split them into chunks."""
    # Load text documents
    txt_loader = DirectoryLoader(directory_path, glob="**/*.txt", loader_cls=TextLoader)
    txt_documents = txt_loader.load()

    # Load PDF documents
    pdf_loader = DirectoryLoader(directory_path, glob="**/*.pdf", loader_cls=PyPDFLoader)
    pdf_documents = pdf_loader.load()

    # Combine all documents
    documents = txt_documents + pdf_documents

    # Split documents into chunks
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200
    )
    chunks = text_splitter.split_documents(documents)

    print(f"Loaded {len(documents)} documents ({len(txt_documents)} text, {len(pdf_documents)} PDF) "
          f"and split into {len(chunks)} chunks")
    return chunks


def setup_vectordb(chunks):
    """Create vector database from document chunks."""
    # Create a Chroma vector store
    vectordb = Chroma.from_documents(
        documents=chunks,
        embedding=embedding_model,
        persist_directory=VECTORDB_PATH
    )
    return vectordb


def rag_query(query, vectordb, model=DEFAULT_MODEL, num_results=3):
    """
    Perform RAG query:
    1. Retrieve relevant chunks from vector database
    2. Generate response using Ollama LLM
    """
    # Retrieve relevant documents
    docs = vectordb.similarity_search(query, k=num_results)

    if not docs:
        return {
            "query": query,
            "response": "I couldn't find any relevant information to answer your question.",
            "source_docs": []
        }

    # Create context from retrieved documents
    context = "\n\n".join([doc.page_content for doc in docs])

    # Create the prompt with context
    prompt = f"""You are a helpful assistant. Answer the question based on the context provided. 
    If you cannot answer based on the context, say "I don't have enough information to answer that."

    Context:
    {context}

    Question: {query}

    Answer:"""

    # Generate response
    response = query_ollama(prompt, model)

    return {
        "query": query,
        "response": response,
        "source_docs": [
            {
                "content": doc.page_content,
                "source": doc.metadata.get("source", "unknown"),
                "metadata": doc.metadata
            } for doc in docs
        ]
    }


@app.route('/api/vectordb/create/directory', methods=['POST'])
def create_vectordb_from_directory():
    """
    Create or update the vector database from a specified directory.

    Expects JSON with:
    {
        "directory": "/path/to/documents",
        "embedding_model": "nomic-embed-text"  // Optional
    }
    """
    global vectordb

    data = request.json
    if not data or 'directory' not in data:
        return jsonify({"error": "Directory path not provided"}), 400

    directory_path = data['directory']
    if not os.path.exists(directory_path) or not os.path.isdir(directory_path):
        return jsonify({"error": f"Directory not found: {directory_path}"}), 404

    # Get embedding model name, use default if not provided
    embedding_model_name = data.get('embedding_model', DEFAULT_EMBEDDING_MODEL)
    custom_embedding_model = OllamaEmbeddings(
        model=embedding_model_name,
        base_url=OLLAMA_BASE_URL
    )

    # Load and process documents
    start_time = time.time()
    try:
        # Use either the process_documents or load_documents_with_error_handling function
        # depending on preference
        documents = load_documents_with_error_handling(directory_path)

        if not documents:
            return jsonify({"error": "No documents could be loaded from the directory"}), 400

        # Split documents into chunks
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=600,
            chunk_overlap=300
        )
        chunks = text_splitter.split_documents(documents)

        # Create vector database with specified embedding model
        vectordb = Chroma.from_documents(
            documents=chunks,
            embedding=custom_embedding_model,
            persist_directory=VECTORDB_PATH
        )

        processing_time = time.time() - start_time

        return jsonify({
            "status": "success",
            "message": f"Vector database created successfully with {len(chunks)} chunks from {len(documents)} documents",
            "embedding_model": embedding_model_name,
            "processing_time_seconds": processing_time
        })

    except Exception as e:
        app.logger.error(f"Error creating vector database from directory: {e}")
        return jsonify({"error": f"Failed to create vector database: {str(e)}"}), 500


@app.route('/api/rag/query', methods=['POST'])
def query_rag_endpoint():
    """
    Query the RAG system with a question.

    Expects JSON with:
    {
        "query": "Your question here",
        "model": "llama3",          # Optional, defaults to llama3
        "num_results": 3,           # Optional, number of documents to retrieve
        "embedding_model": "nomic-embed-text"  # Optional, embedding model to use
    }
    """
    global vectordb

    # Get request data
    data = request.json
    if not data or 'query' not in data:
        return jsonify({"error": "Query not provided"}), 400

    query = data['query']
    model = data.get('model', DEFAULT_MODEL)
    num_results = data.get('num_results', 3)
    embedding_model_name = data.get('embedding_model', DEFAULT_EMBEDDING_MODEL)

    # Create embedding model with specified model name
    custom_embedding_model = OllamaEmbeddings(
        model=embedding_model_name,
        base_url=OLLAMA_BASE_URL
    )

    # Check if vectordb exists
    if vectordb is None:
        try:
            vectordb = Chroma(
                persist_directory=VECTORDB_PATH,
                embedding_function=custom_embedding_model
            )
        except Exception as e:
            app.logger.error(f"Error loading vector database: {e}")
            return jsonify({
                "error": "Vector database not found or could not be loaded. Please create it first."
            }), 404

    try:
        # Retrieve relevant documents
        docs = vectordb.similarity_search(query, k=num_results)

        if not docs:
            return jsonify({
                "query": query,
                "response": "I couldn't find any relevant information to answer your question.",
                "source_docs": []
            })

        # Create context from retrieved documents
        context = "\n\n".join([doc.page_content for doc in docs])

        # Create the prompt with context
        prompt = f"""You are a helpful assistant. Answer the question based on the context provided. 
        If you cannot answer based on the context, say "I don't have enough information to answer that."

        Context:
        {context}

        Question: {query}

        Answer:"""

        # Generate response
        response = query_ollama(prompt, model)

        return jsonify({
            "query": query,
            "response": response,
            "embedding_model": embedding_model_name,
            "llm_model": model,
            "source_docs": [
                {
                    "content": doc.page_content,
                    "source": doc.metadata.get("source", "unknown"),
                    "metadata": doc.metadata
                } for doc in docs
            ]
        })

    except Exception as e:
        app.logger.error(f"Error during RAG query: {e}")
        return jsonify({"error": f"Error processing query: {str(e)}"}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)