import streamlit as st
import sys
import os
from datetime import datetime
from typing import List, Dict, Any

# Page config is now handled by app.py

# CSS is now handled centrally by app.py

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
    """Unified Document Upload and Status Page."""
    
    st.markdown("### 📤 Document Ingestion")
    
    # File upload section
    file_upload_section()
    
    # Add separator
    st.markdown("---")
    
    # Status and document list section
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
    """Status and document management section."""
    
    # Vector database information
    try:
        # Try to list vector databases, but handle API differences gracefully
        try:
            vector_dbs = llama_stack_api.get_llamastack_client().vector_dbs.list() or []
            
            # All vector databases
            st.markdown("#### 📚 Vector Databases")
            if vector_dbs:
                for db in vector_dbs:
                    # Try to get a user-friendly name, fallback to identifier
                    if hasattr(db, 'name') and db.name:
                        display_name = db.name
                    elif hasattr(db, 'identifier'):
                        # If identifier looks like a UUID, try to find a more friendly name
                        identifier = db.identifier
                        if identifier.startswith('vs_') and len(identifier) > 20:
                            # This looks like a UUID-style identifier, try to get a better name
                            display_name = DEFAULT_VECTOR_DB_NAME  # Use the expected name
                        else:
                            display_name = identifier
                    else:
                        display_name = str(db)
                    
                    # Show both the display name and identifier for clarity
                    if hasattr(db, 'identifier') and display_name != db.identifier:
                        st.markdown(f"📄 **{display_name}** (`{db.identifier}`)")
                    else:
                        st.markdown(f"📄 {display_name}")
                
                # Show database details for the first/primary database
                primary_db = None
                for db in vector_dbs:
                    db_name = db.identifier if hasattr(db, 'identifier') else str(db)
                    if db_name == DEFAULT_VECTOR_DB_NAME:
                        primary_db = db
                        break
                
                # If no default found, use the first one
                if not primary_db and vector_dbs:
                    primary_db = vector_dbs[0]
                
                if primary_db:
                    # Database details
                    with st.expander("🗂️ Database Details", expanded=False):
                        st.json({
                            "database_id": primary_db.identifier if hasattr(primary_db, 'identifier') else str(primary_db),
                            "embedding_model": DEFAULT_EMBEDDING_MODEL,
                            "embedding_dimension": DEFAULT_EMBEDDING_DIMENSION,
                            "chunk_size": DEFAULT_CHUNK_SIZE_TOKENS,
                            "status": "Active"
                        })
            else:
                st.info("📋 No vector databases found. The database will be created automatically when you upload your first document.")
                
        except AttributeError as api_error:
            # Handle case where vector_dbs API is not available
            st.markdown("#### 📚 Vector Databases")
            st.info("📋 Vector database status checking not available with current API version. The vector database will be created automatically when you upload documents.")
    
    except Exception as e:
        st.markdown("#### 📚 Vector Databases")
        st.error(f"Error checking vector database status: {e}")
    
    # Display uploaded documents
    display_uploaded_documents()


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




def get_uploaded_documents():
    """Retrieve list of uploaded documents from vector databases."""
    try:
        # Get all vector databases
        vector_dbs = llama_stack_api.get_llamastack_client().vector_dbs.list() or []
        
        documents = []
        for vector_db in vector_dbs:
            try:
                # Try multiple approaches to find documents
                search_queries = [
                    "document source file",
                    "metadata filename",
                    "uploaded file",
                    "pdf txt doc",
                    "content source"
                ]
                
                found_sources = set()
                
                for query in search_queries:
                    try:
                        search_response = llama_stack_api.get_llamastack_client().tool_runtime.rag_tool.query(
                            content=query, 
                            vector_db_ids=[vector_db.identifier]
                        )
                        
                        # Extract document information from search results
                        if hasattr(search_response, 'content') and search_response.content:
                            # Parse the content to extract document sources
                            content_items = search_response.content if isinstance(search_response.content, list) else [search_response.content]
                            
                            for item in content_items:
                                if hasattr(item, 'text'):
                                    text = item.text
                                    # Look for various patterns that indicate source files
                                    patterns = [
                                        r'source[:\s]+([^\n\r,]+\.(?:pdf|txt|doc|docx|md|json|yaml))',
                                        r'Source[:\s]+([^\n\r,]+\.(?:pdf|txt|doc|docx|md|json|yaml))',
                                        r'Metadata:.*?source[\'"]?\s*:\s*[\'"]?([^\'",\n\r]+\.(?:pdf|txt|doc|docx|md|json|yaml))',
                                        r'filename[:\s]+([^\n\r,]+\.(?:pdf|txt|doc|docx|md|json|yaml))',
                                        r'file[:\s]+([^\n\r,]+\.(?:pdf|txt|doc|docx|md|json|yaml))'
                                    ]
                                    
                                    import re
                                    for pattern in patterns:
                                        matches = re.findall(pattern, text, re.IGNORECASE)
                                        for match in matches:
                                            clean_source = match.strip().strip('\'"')
                                            if clean_source and clean_source not in found_sources:
                                                found_sources.add(clean_source)
                                                documents.append({
                                                    'name': clean_source,
                                                    'vector_db': vector_db.identifier,
                                                    'type': 'document',
                                                    'status': 'indexed'
                                                })
                    except Exception:
                        continue
                        
            except Exception as e:
                # If we can't query this vector DB, skip it
                continue
        
        # If no documents found through search but vector DB exists and has content, 
        # add a generic entry to show that documents exist
        if not documents and vector_dbs:
            for vector_db in vector_dbs:
                try:
                    # Test if the vector DB has any content at all
                    test_response = llama_stack_api.get_llamastack_client().tool_runtime.rag_tool.query(
                        content="test", 
                        vector_db_ids=[vector_db.identifier]
                    )
                    
                    if (hasattr(test_response, 'content') and test_response.content and 
                        any(hasattr(item, 'text') and item.text.strip() for item in 
                            (test_response.content if isinstance(test_response.content, list) else [test_response.content]))):
                        # Vector DB has content, add a generic document entry
                        documents.append({
                            'name': 'Uploaded Document (filename not detected)',
                            'vector_db': vector_db.identifier,
                            'type': 'document',
                            'status': 'indexed'
                        })
                except Exception:
                    continue
        
        return documents
        
    except Exception as e:
        st.error(f"Error retrieving document list: {str(e)}")
        return []

def display_uploaded_documents():
    """Display aesthetically pleasing list of uploaded documents."""
    
    st.markdown("---")
    st.markdown("### 📚 Uploaded Documents")
    
    documents = get_uploaded_documents()
    
    if not documents:
        st.info("📝 No documents uploaded yet. Upload some documents above to see them listed here.")
        return
    
    st.markdown(f"**Total Documents**: {len(documents)}")
    
    # Create a nice display for each document
    for i, doc in enumerate(documents):
        with st.container():
            col1, col2, col3 = st.columns([3, 1, 1])
            
            with col1:
                # Document name with icon
                if doc['name'].endswith('.pdf'):
                    icon = "📄"
                elif doc['name'].endswith(('.txt', '.md')):
                    icon = "📝"
                elif doc['name'].endswith(('.doc', '.docx')):
                    icon = "📃"
                else:
                    icon = "📋"
                
                st.markdown(f"{icon} **{doc['name']}**")
            
            with col2:
                # Show friendly name for vector DB
                db_display = doc['vector_db']
                if db_display.startswith('vs_') and len(db_display) > 20:
                    db_display = DEFAULT_VECTOR_DB_NAME
                st.markdown(f"🗄️ `{db_display}`")
            
            with col3:
                if doc['status'] == 'indexed':
                    st.markdown("✅ **Indexed**")
                else:
                    st.markdown("⏳ **Processing**")
        
        # Add a subtle separator between documents
        if i < len(documents) - 1:
            st.markdown("<hr style='margin: 0.5rem 0; border: none; border-top: 1px solid #e0e0e0;'>", unsafe_allow_html=True)

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
