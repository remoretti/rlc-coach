import os
from langchain_community.document_loaders import DirectoryLoader, TextLoader, PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_aws import BedrockEmbeddings
from langchain_community.vectorstores import Chroma
import chromadb
from src.config.model_constants import EMBEDDING_MODEL
from langchain_community.document_loaders import DirectoryLoader, TextLoader, Docx2txtLoader
from src.ai_coach.cohere_embeddings import CohereBedrockEmbeddings
from typing import List
from langchain_core.documents import Document

def load_and_split_documents(docs_directory):
    """Load documents from a directory and split them into chunks."""
    # Create loaders for different file types
    txt_loader = DirectoryLoader(
        docs_directory,
        glob="*.txt",
        loader_cls=TextLoader
    )
    docx_loader = DirectoryLoader(
        docs_directory,
        glob="*.docx",
        loader_cls=Docx2txtLoader
    )
    # Add PDF loader
    pdf_loader = DirectoryLoader(
        docs_directory,
        glob="*.pdf",
        loader_cls=PyPDFLoader
    )
    # Load all documents
    txt_documents = txt_loader.load()
    docx_documents = docx_loader.load()
    pdf_documents = pdf_loader.load()  # Load PDF documents
    documents = txt_documents + docx_documents + pdf_documents  # Add PDFs to the document list
    print(f"Loaded {len(documents)} files: {len(txt_documents)} .txt, {len(docx_documents)} .docx, and {len(pdf_documents)} .pdf")
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=400,        # Reduced to stay under 2048 char limit
        chunk_overlap=40,      # Proportionally reduced
        separators=["\n\n", "\n", ".", " ", ""]
    )
    chunks = text_splitter.split_documents(documents)
    return chunks

def initialize_vector_db(chunks, persist_directory="./chroma_db"):
    """Initialize the vector database with document chunks."""
    # Initialize Bedrock embeddings with Cohere
    embeddings = CohereBedrockEmbeddings(
        model_id=EMBEDDING_MODEL,  # "cohere.embed-multilingual-v3"
        region_name=os.getenv("AWS_REGION", "us-east-1")
        #model_kwargs={"input_type": "search_document"}  # ADD THIS LINE
    )
    # Create and persist the vector store
    vectordb = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory=persist_directory
    )
    return vectordb

###### DEBUG ######

    
################

def get_retriever(persist_directory="./chroma_db"):
    """Get a retriever from an existing vector database."""
    # Initialize Bedrock embeddings with Cohere
    embeddings = CohereBedrockEmbeddings(
        model_id=EMBEDDING_MODEL,  # "cohere.embed-multilingual-v3"
        region_name=os.getenv("AWS_REGION", "us-east-1")
        #model_kwargs={"input_type": "search_document"}  # ADD THIS LINE
    )
    # Load the existing vector store
    try:
        vectordb = Chroma(
            persist_directory=persist_directory,
            embedding_function=embeddings
        )
        return vectordb.as_retriever(search_kwargs={"k": 4})
    except Exception as e:
        print(f"Error loading vector database: {e}")
        return None

def add_to_vector_db(chunks, persist_directory="./chroma_db"):
    """Add document chunks to an existing vector database."""
    try:
        # Initialize Bedrock embeddings with Cohere
        embeddings = CohereBedrockEmbeddings(
            model_id=EMBEDDING_MODEL,  # "cohere.embed-multilingual-v3"
            region_name=os.getenv("AWS_REGION", "us-east-1")
            #model_kwargs={"input_type": "search_document"}  # ADD THIS LINE
        )
        # Load the existing vector store
        try:
            vectordb = Chroma(
                persist_directory=persist_directory,
                embedding_function=embeddings
            )
            # Add the new chunks to the vector database
            vectordb.add_documents(chunks)
            # Persist the changes
            vectordb.persist()
            print(f"Successfully added {len(chunks)} chunks to the database")
            return True
        except Exception as e:
            print(f"Error accessing vector database: {e}")
            return False
    except Exception as e:
        print(f"Error adding documents to vector database: {e}")
        return False