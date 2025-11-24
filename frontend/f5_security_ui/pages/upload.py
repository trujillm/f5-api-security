import streamlit as st
import sys
import os
from datetime import datetime
from typing import List, Dict, Any

# Add the ingestion service to the path
sys.path.append('/app/f5_security_ui')
sys.path.append('/app')

# We'll use the RAG-style approach directly with llama_stack_api

from modules.api import llama_stack_api
from constants import (
    DEFAULT_VECTOR_DB_NAME, 
    DEFAULT_EMBEDDING_MODEL, 
    DEFAULT_EMBEDDING_DIMENSION, 
    DEFAULT_CHUNK_SIZE_TOKENS
)


def document_upload_page():
    """Enhanced Document Upload Page with URL and File Upload support."""
    
    st.markdown("### 📤 Document Ingestion")
    
    
    
    # Create tabs for different ingestion methods
    tab1, tab2 = st.tabs(["📁 File Upload", "📊 Status"])
    
    with tab1:
        file_upload_section()
    
    with tab2:
        status_section()


def file_upload_section():
    """File upload section for document ingestion."""
    
    st.markdown("#### 📁 Upload Documents")
    st.markdown("Upload documents directly from your computer.")
    
    # File uploader
    uploaded_files = st.file_uploader(
        "Select Documents",
        accept_multiple_files=True,
        type=["pdf", "txt", "doc", "docx", "md", "json", "yaml"],
        help="Upload any documents you want to use for RAG - PDFs, text files, documentation, etc."
    )
    
    if uploaded_files:
        # Automatically add documents to vector database upon upload
        add_documents_to_vector_db(uploaded_files)




def status_section():
    """Status and management section."""
    
    st.markdown("#### 📊 Vector Database Status")
    
    # Vector database information
    try:
        # Try to list vector databases, but handle API differences gracefully
        try:
            vector_dbs = llama_stack_api.get_llamastack_client().vector_dbs.list() or []
            demo_db = None
            
            for db in vector_dbs:
                db_name = db.identifier if hasattr(db, 'identifier') else str(db)
                if db_name == DEFAULT_VECTOR_DB_NAME:
                    demo_db = db
                    break
            
            if demo_db:
                st.success("✅ Vector Database is available")
                
                # Database details
                with st.expander("🗂️ Database Details", expanded=True):
                    st.json({
                        "database_id": f5_security_db.identifier if hasattr(f5_security_db, 'identifier') else str(f5_security_db),
                        "embedding_model": DEFAULT_EMBEDDING_MODEL,
                        "embedding_dimension": DEFAULT_EMBEDDING_DIMENSION,
                        "chunk_size": DEFAULT_CHUNK_SIZE_TOKENS,
                        "status": "Active"
                    })
            else:
                st.warning("⚠️ Vector Database not found")
                st.info("The database will be created automatically when you upload your first document.")
            
            # All vector databases
            if vector_dbs:
                st.markdown("#### 📚 All Available Vector Databases")
                for db in vector_dbs:
                    db_name = db.identifier if hasattr(db, 'identifier') else str(db)
                    st.markdown(f"📄 {db_name}")
            else:
                st.info("No vector databases found.")
                
        except AttributeError as api_error:
            # Handle case where vector_dbs API is not available
            st.info("📋 Vector database status checking not available with current API version")
            st.info("The vector database will be created automatically when you upload documents.")
    
    except Exception as e:
        st.error(f"Error checking vector database status: {e}")
    
    # Management actions
    st.markdown("#### 🛠️ Management Actions")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🔄 Refresh Status", use_container_width=True):
            st.rerun()
    
    with col2:
        if st.button("🧪 Test Connection", use_container_width=True):
            test_llamastack_connection()


def add_documents_to_vector_db(uploaded_files: List[Any]):
    """Automatically add documents to the F5 security vector database upon upload."""
    
    vector_db_name = DEFAULT_VECTOR_DB_NAME
    
    # Show initial upload success
    st.success(f"📄 Successfully uploaded {len(uploaded_files)} files")
    
    try:
        # Convert uploaded files into RAGDocument instances
        from llama_stack_client.types import Document as RAGDocument
        from modules.utils import data_url_from_file
        
        with st.spinner("🔄 Processing documents..."):
            documents = [
                RAGDocument(
                    document_id=uploaded_file.name,
                    content=data_url_from_file(uploaded_file),
                    metadata={"source": uploaded_file.name, "type": "uploaded_file"}
                )
                for uploaded_file in uploaded_files
            ]

        # Try to create the vector database (will skip if it already exists)
        try:
            with st.spinner("Setting up vector database..."):
                # Determine provider for vector IO
                providers = llama_stack_api.get_llamastack_client().providers.list()
                vector_io_provider = None
                for x in providers:
                    if x.api == "vector_io":
                        vector_io_provider = x.provider_id
                        break

                # Register new vector database
                llama_stack_api.get_llamastack_client().vector_dbs.register(
                    vector_db_id=vector_db_name,
                    embedding_dimension=DEFAULT_EMBEDDING_DIMENSION,
                    embedding_model=DEFAULT_EMBEDDING_MODEL,
                    provider_id=vector_io_provider,
                )
        except Exception as db_error:
            # Database likely already exists, which is fine
            error_msg = str(db_error) if db_error else ""
            if "already exists" not in error_msg.lower():
                # Re-raise if it's a different error (not "already exists")
                raise db_error

        # Insert documents into the vector database
        with st.spinner(f"🚀 Adding {len(uploaded_files)} documents to vector database..."):
            # Get the actual vector database ID (it might be a UUID, not the name)
            vector_dbs = llama_stack_api.get_llamastack_client().vector_dbs.list()
            actual_vector_db_id = None
            
            # Find the F5 security vector database
            for db in vector_dbs:
                if hasattr(db, 'vector_db_name') and db.vector_db_name == vector_db_name:
                    actual_vector_db_id = db.identifier
                    break
                elif hasattr(db, 'identifier') and vector_db_name in str(db.identifier):
                    actual_vector_db_id = db.identifier
                    break
            
            # If we couldn't find it, use the name as fallback
            if not actual_vector_db_id:
                actual_vector_db_id = vector_db_name
            
            llama_stack_api.get_llamastack_client().tool_runtime.rag_tool.insert(
                vector_db_id=actual_vector_db_id,
                documents=documents,
                chunk_size_in_tokens=DEFAULT_CHUNK_SIZE_TOKENS,
            )
        
        st.success(f"🎉 Documents successfully added to knowledge base!")
        st.info("💬 **Ready for Chat**: Your documents are now available for AI-powered security queries!")
        
    except Exception as e:
        st.error(f"❌ Error processing documents: {e}")
        st.exception(e)




def test_llamastack_connection():
    """Test connection to Llama Stack."""
    
    try:
        with st.spinner("🧪 Testing Llama Stack connection..."):
            # Test basic connection
            models = llama_stack_api.get_llamastack_client().models.list()
            st.success("✅ Llama Stack connection successful!")
            
            # Test vector DB provider
            providers = llama_stack_api.get_llamastack_client().providers.list()
            vector_provider = None
            for provider in providers:
                if provider.api == "vector_io":
                    vector_provider = provider.provider_id
                    break
            
            if vector_provider:
                st.success(f"✅ Vector IO provider available: {vector_provider}")
            else:
                st.warning("⚠️ No Vector IO provider found")
            
            # Display connection info
            with st.expander("🔍 Connection Details", expanded=False):
                st.json({
                    "llamastack_endpoint": llama_stack_api.get_current_endpoint(),
                    "models_available": len(models) if models else 0,
                    "vector_provider": vector_provider or "None",
                    "connection_status": "Active"
                })
    
    except Exception as e:
        st.error(f"❌ Llama Stack connection failed: {e}")


# Main page function
document_upload_page()
