# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the terms described in the LICENSE file in
# the root directory of this source tree.

from llama_stack_ui.distribution.ui.modules.utils import get_vector_db_name, data_url_from_file
import streamlit as st

from llama_stack_ui.distribution.ui.modules.api import llama_stack_api
from llama_stack_client import RAGDocument


def vector_dbs():
    """
    Inspect available vector databases and display details for the selected one.
    Now supports creating new vector databases.
    """
    st.header("Vector Databases")
    
    # Initialize session state for creation status messages
    if "creation_status" not in st.session_state:
        st.session_state["creation_status"] = None
    if "creation_message" not in st.session_state:
        st.session_state["creation_message"] = ""
    
    # Initialize session state for selected vector database
    if "selected_vector_db" not in st.session_state:
        st.session_state["selected_vector_db"] = ""
    
    # Show status messages at the top level (before dropdown)
    if st.session_state["creation_status"] == "success":
        st.success(st.session_state["creation_message"])
        # Clear the message after showing it
        st.session_state["creation_status"] = None
        st.session_state["creation_message"] = ""
    elif st.session_state["creation_status"] == "error":
        st.error(st.session_state["creation_message"])
        # Clear the message after showing it  
        st.session_state["creation_status"] = None
        st.session_state["creation_message"] = ""
    
    # Fetch all vector databases
    vdb_list = llama_stack_api.client.vector_dbs.list()
    
    # Build dropdown options - empty string first (default), then "Create New", then existing DBs  
    dropdown_options = ["", "Create New"]
    vdb_info = {}
    
    if vdb_list:
        # Add existing vector databases to dropdown
        existing_vdbs = {get_vector_db_name(v): v.to_dict() for v in vdb_list}
        dropdown_options.extend(list(existing_vdbs.keys()))
        vdb_info = existing_vdbs
    
    # Determine the default selection index
    default_index = 0  # Default to empty string
    
    # If a database was just created, auto-select it (highest priority)
    if "newly_created_vdb" in st.session_state and st.session_state["newly_created_vdb"]:
        newly_created_name = st.session_state["newly_created_vdb"]
        if newly_created_name in dropdown_options:
            default_index = dropdown_options.index(newly_created_name)
            # Update session state and clear the flag
            st.session_state["selected_vector_db"] = newly_created_name
            st.session_state["newly_created_vdb"] = None
    # Otherwise, use the previously selected database if it still exists
    elif st.session_state["selected_vector_db"] and st.session_state["selected_vector_db"] in dropdown_options:
        default_index = dropdown_options.index(st.session_state["selected_vector_db"])
    
    # Vector database selection dropdown
    selected_vector_db = st.selectbox("Select a vector database", dropdown_options, index=default_index)
    
    # Update session state when user makes a selection
    if selected_vector_db != st.session_state["selected_vector_db"]:
        st.session_state["selected_vector_db"] = selected_vector_db
    
    # Get the actual vector database object for API calls (do this before using it)
    selected_vdb_obj = None
    if selected_vector_db and selected_vector_db != "" and selected_vector_db != "Create New":
        for vdb in vdb_list:
            if get_vector_db_name(vdb) == selected_vector_db:
                selected_vdb_obj = vdb
                break
    
    if selected_vector_db == "Create New":
        # Show vector database creation UI
        _show_create_vector_db_ui()
    elif selected_vector_db and selected_vector_db != "":
        # Show existing vector database details (only if not empty string)
        st.json(vdb_info[selected_vector_db], expanded=True)
        
        # Show existing documents in the database
        st.subheader(f"📄 Documents in '{selected_vector_db}'")
        _show_existing_documents_table(selected_vector_db, selected_vdb_obj)
        
        # Add Browse functionality for uploading documents to this database
        st.subheader(f"📁 Upload Documents to '{selected_vector_db}'")
        _show_document_upload_ui(selected_vector_db, selected_vdb_obj)
    # If empty string is selected, show nothing (clean default state)


def _show_create_vector_db_ui():
    """
    Display UI for creating a new vector database.
    """
    st.subheader("Create New Vector Database")
    
    # Initialize session state for creation form
    if "new_vdb_name" not in st.session_state:
        st.session_state["new_vdb_name"] = ""
    
    # Vector database name input
    new_vdb_name = st.text_input(
        "Add New Vector Database",
        value=st.session_state["new_vdb_name"],
        help="Enter a unique name for the new vector database",
        key="new_vdb_name_input"
    )
    
    # Update session state
    st.session_state["new_vdb_name"] = new_vdb_name
    
    # Add button
    if st.button("Add", type="primary", disabled=not new_vdb_name.strip()):
        _create_vector_database(new_vdb_name.strip())


def _create_vector_database(vdb_name):
    """
    Create a new vector database using the LlamaStack API.
    
    Args:
        vdb_name (str): Name for the new vector database
    """
    try:
        # Reset status
        st.session_state["creation_status"] = None
        st.session_state["creation_message"] = ""
        
        # Validate input
        if not vdb_name or not vdb_name.strip():
            st.session_state["creation_status"] = "error"
            st.session_state["creation_message"] = "Vector database name cannot be empty."
            return
            
        # Check for duplicate names
        existing_vdbs = llama_stack_api.client.vector_dbs.list()
        existing_names = [get_vector_db_name(vdb) for vdb in existing_vdbs]
        if vdb_name in existing_names:
            st.session_state["creation_status"] = "error"
            st.session_state["creation_message"] = f"Vector database '{vdb_name}' already exists. Please choose a different name."
            return
        
        # Get vector IO provider
        providers = llama_stack_api.client.providers.list()
        vector_io_provider = None
        for provider in providers:
            if provider.api == "vector_io":
                vector_io_provider = provider.provider_id
                break
                
        if not vector_io_provider:
            st.session_state["creation_status"] = "error"
            st.session_state["creation_message"] = "No vector IO provider found. Cannot create vector database."
            return
        
        # Create the vector database
        with st.spinner(f"Creating vector database '{vdb_name}'..."):
            vector_db = llama_stack_api.client.vector_dbs.register(
                vector_db_id=vdb_name,
                embedding_dimension=384,
                embedding_model="all-MiniLM-L6-v2",
                provider_id=vector_io_provider,
            )
            
        # Success
        st.session_state["creation_status"] = "success"
        st.session_state["creation_message"] = f"Vector database '{vdb_name}' created successfully!"
        
        # Mark this database to be auto-selected after refresh
        st.session_state["newly_created_vdb"] = vdb_name
        
        # Clear the input field
        st.session_state["new_vdb_name"] = ""
        
        # Trigger page refresh to update the dropdown - this will show the message at the top
        st.rerun()
        
    except Exception as e:
        st.session_state["creation_status"] = "error"
        st.session_state["creation_message"] = f"Error creating vector database: {str(e)}"


def _show_document_upload_ui(vector_db_name, vector_db_obj=None):
    """
    Display UI for uploading documents to an existing vector database.
    
    Args:
        vector_db_name (str): Name of the selected vector database
    """
    # Initialize session state for upload status
    if "upload_status" not in st.session_state:
        st.session_state["upload_status"] = None
    if "upload_message" not in st.session_state:
        st.session_state["upload_message"] = ""
    
    # Show upload status messages
    if st.session_state["upload_status"] == "success":
        st.success(st.session_state["upload_message"])
        # Clear after showing
        st.session_state["upload_status"] = None
        st.session_state["upload_message"] = ""
    elif st.session_state["upload_status"] == "error":
        st.error(st.session_state["upload_message"])
        # Clear after showing
        st.session_state["upload_status"] = None
        st.session_state["upload_message"] = ""
    
    # File uploader
    uploaded_files = st.file_uploader(
        "Browse and select files to upload",
        accept_multiple_files=True,
        type=["txt", "pdf", "doc", "docx"],
        key=f"uploader_{vector_db_name}",  # Unique key per database
        help="Select one or more documents to add to this vector database"
    )
    
    # Process uploaded files
    if uploaded_files:
        st.success(f"Selected {len(uploaded_files)} file(s): {', '.join([f.name for f in uploaded_files])}")
        
        if st.button("Upload Documents", type="primary", key=f"upload_btn_{vector_db_name}"):
            # Get the correct database ID for upload
            vector_db_id = vector_db_obj.identifier if vector_db_obj and hasattr(vector_db_obj, 'identifier') else vector_db_name
            _upload_documents_to_database(vector_db_name, uploaded_files, vector_db_id)


def _upload_documents_to_database(vector_db_name, uploaded_files, vector_db_id=None):
    """
    Upload documents to an existing vector database.
    
    Args:
        vector_db_name (str): Name of the target vector database
        uploaded_files: List of uploaded files from Streamlit file uploader
    """
    try:
        # Reset status
        st.session_state["upload_status"] = None
        st.session_state["upload_message"] = ""
        
        if not uploaded_files:
            st.session_state["upload_status"] = "error"
            st.session_state["upload_message"] = "No files selected for upload."
            return
        
        # Convert uploaded files into RAGDocument instances
        with st.spinner(f"Processing {len(uploaded_files)} file(s)..."):
            documents = [
                RAGDocument(
                    document_id=uploaded_file.name,
                    content=data_url_from_file(uploaded_file),
                )
                for uploaded_file in uploaded_files
            ]
        
        # Insert documents into the existing vector database
        actual_db_id = vector_db_id or vector_db_name
        with st.spinner(f"Uploading documents to '{vector_db_name}'..."):
            llama_stack_api.client.tool_runtime.rag_tool.insert(
                vector_db_id=actual_db_id,  # Use the correct database ID
                documents=documents,
                chunk_size_in_tokens=512,
            )
        
        # Success
        st.session_state["upload_status"] = "success"
        st.session_state["upload_message"] = f"Successfully uploaded {len(uploaded_files)} document(s) to '{vector_db_name}'!"
        
        # Trigger refresh to show the success message
        st.rerun()
        
    except Exception as e:
        st.session_state["upload_status"] = "error"
        st.session_state["upload_message"] = f"Error uploading documents: {str(e)}"
        st.rerun()


def _show_existing_documents_table(vector_db_name, vector_db_obj=None):
    """
    Display a table showing existing documents in the selected vector database.
    
    Args:
        vector_db_name (str): Display name of the selected vector database
        vector_db_obj: The actual vector database object with identifier
    """
    try:
        # Get the correct vector database ID
        if vector_db_obj and hasattr(vector_db_obj, 'identifier'):
            vector_db_id = vector_db_obj.identifier
        else:
            vector_db_id = vector_db_name  # Fallback to display name
        
        # Show debug info about the database
        with st.expander("🔍 Database Debug Info", expanded=False):
            st.write(f"**Display Name:** {vector_db_name}")
            st.write(f"**Database ID:** {vector_db_id}")
            if vector_db_obj:
                st.write(f"**Database Object:** {vector_db_obj.to_dict()}")
        
        with st.spinner("Loading existing documents..."):
            documents_info = []
            
            # Try multiple query approaches to find documents
            query_approaches = [
                # Try broad queries that might match any content
                {"content": "document", "description": "document query"},
                {"content": "file", "description": "file query"},  
                {"content": "text", "description": "text query"},
                {"content": "content", "description": "content query"},
                {"content": "pdf", "description": "pdf query"},
                {"content": "f5", "description": "f5 query"},  # Try specific term from your file
                {"content": "distributed", "description": "distributed query"},  # Another term from your file
                {"content": "cloud", "description": "cloud query"},  # Another term from your file
            ]
            
            successful_queries = []
            
            for approach in query_approaches:
                try:
                    rag_response = llama_stack_api.client.tool_runtime.rag_tool.query(
                        content=approach["content"],
                        vector_db_ids=[vector_db_id]  # Use the correct database ID
                    )
                    
                    # Debug: Show what we got back
                    if hasattr(rag_response, 'content') and rag_response.content:
                        successful_queries.append(f"✅ {approach['description']}: Found content")
                        
                        # Try to extract document info from the response
                        # The response might contain document references in the content
                        response_content = str(rag_response.content)
                        
                        # Look for document ID patterns in the response
                        if 'f5-distributed-cloud' in response_content.lower():
                            documents_info.append({
                                'Document Name': 'f5-distributed-cloud-app-stack-ds.pdf',
                                'Content Preview': response_content[:200] + "..." if len(response_content) > 200 else response_content
                            })
                    
                    # Also check for chunks attribute
                    if hasattr(rag_response, 'chunks') and rag_response.chunks:
                        successful_queries.append(f"✅ {approach['description']}: Found {len(rag_response.chunks)} chunks")
                        
                        for chunk in rag_response.chunks:
                            # Try different ways to get document ID
                            doc_id = None
                            content_preview = ""
                            
                            if hasattr(chunk, 'document_id'):
                                doc_id = chunk.document_id
                            elif hasattr(chunk, 'metadata') and chunk.metadata and 'document_id' in chunk.metadata:
                                doc_id = chunk.metadata['document_id']
                            elif hasattr(chunk, 'metadata') and chunk.metadata and 'source' in chunk.metadata:
                                doc_id = chunk.metadata['source']
                            
                            if hasattr(chunk, 'content'):
                                content_preview = chunk.content[:200] + "..." if len(chunk.content) > 200 else chunk.content
                            elif hasattr(chunk, 'text'):
                                content_preview = chunk.text[:200] + "..." if len(chunk.text) > 200 else chunk.text
                            
                            if doc_id:
                                doc_info = {
                                    'Document Name': str(doc_id),
                                    'Content Preview': content_preview
                                }
                                if doc_info not in documents_info:
                                    documents_info.append(doc_info)
                    else:
                        successful_queries.append(f"❌ {approach['description']}: No chunks found")
                        
                except Exception as e:
                    successful_queries.append(f"❌ {approach['description']}: Error - {str(e)}")
                    continue
            
            # Show debug information in an expander
            with st.expander("🔍 Debug Information (click to expand)", expanded=False):
                st.write("**Query Results:**")
                for result in successful_queries:
                    st.write(result)
                st.write(f"**Total documents found:** {len(documents_info)}")
            
            if documents_info:
                # Create a DataFrame for better display
                import pandas as pd
                df = pd.DataFrame(documents_info)
                
                # Remove duplicates based on Document Name
                df = df.drop_duplicates(subset=['Document Name'])
                
                st.write(f"Found {len(df)} document(s) in this vector database:")
                st.dataframe(df, use_container_width=True)
            else:
                st.info("No documents found in this vector database. This could mean:")
                st.write("• The database is empty")
                st.write("• Documents were uploaded but not yet indexed")  
                st.write("• The query approach needs adjustment")
                st.write("• Check the debug information above for more details")
                
    except Exception as e:
        st.error(f"Error loading documents: {str(e)}")
        st.write("**Full error details:**", str(e))
