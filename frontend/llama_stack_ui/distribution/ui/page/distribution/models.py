# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the terms described in the LICENSE file in
# the root directory of this source tree.

import streamlit as st

from llama_stack_ui.distribution.ui.modules.api import llama_stack_api


def fetch_models_from_xc_url():
    """Fetch models from the XC URL and update session state"""
    xc_url = st.session_state.get("xc_url", "http://llamastack:8321")
    
    # Set loading state
    st.session_state["models_loading"] = True
    st.session_state["models_error"] = None
    st.session_state["models_list"] = []
    
    # Fetch models from XC URL
    success, models_list, error_message = llama_stack_api.fetch_models_from_url(xc_url)
    
    # Update session state based on results
    st.session_state["models_loading"] = False
    
    if success and models_list:
        st.session_state["models_list"] = models_list
        st.session_state["models_error"] = None
        st.session_state["connection_status"] = "success"
    else:
        st.session_state["models_list"] = []
        st.session_state["models_error"] = error_message or "Failed to fetch models"
        st.session_state["connection_status"] = "error"


def models():
    """
    Inspect available models and display details for a selected one.
    Now supports dynamic XC URL configuration.
    """
    st.header("Models")
    
    # Initialize session state
    if "xc_url" not in st.session_state:
        st.session_state["xc_url"] = "http://llamastack:8321"
    if "models_list" not in st.session_state:
        st.session_state["models_list"] = []
    if "models_loading" not in st.session_state:
        st.session_state["models_loading"] = False
    if "models_error" not in st.session_state:
        st.session_state["models_error"] = None
    if "connection_status" not in st.session_state:
        st.session_state["connection_status"] = None
    if "models_fetched" not in st.session_state:
        st.session_state["models_fetched"] = False
    if "previous_xc_url" not in st.session_state:
        st.session_state["previous_xc_url"] = st.session_state["xc_url"]

    # XC URL input field
    st.subheader("LlamaStack Configuration")
    
    xc_url = st.text_input(
        "XC URL",
        value=st.session_state["xc_url"],
        help="Enter the LlamaStack endpoint URL to fetch models from",
        key="xc_url_input",
        on_change=lambda: st.session_state.update({"models_fetched": False})
    )
    
    # Check if URL actually changed (not just initial load)
    url_changed = xc_url != st.session_state["previous_xc_url"]
    
    # Update session state if URL changed
    if xc_url != st.session_state["xc_url"]:
        st.session_state["xc_url"] = xc_url
        st.session_state["models_fetched"] = False
    
    # Auto-fetch models when URL changes or on first load
    if not st.session_state["models_fetched"] and xc_url and not st.session_state["models_loading"]:
        with st.spinner("🔄 Fetching models from XC URL..."):
            fetch_models_from_xc_url()
        st.session_state["models_fetched"] = True
        st.session_state["previous_xc_url"] = xc_url
        # Only show the connection status message if URL was explicitly changed
        if url_changed:
            st.session_state["show_connection_status"] = True
        st.rerun()
    
    # Display connection status only once after a fetch operation
    if st.session_state.get("show_connection_status", False):
        if st.session_state["connection_status"] == "success":
            st.success("✅ Connected to LlamaStack endpoint")
        elif st.session_state["connection_status"] == "error" and st.session_state["models_error"]:
            st.error(f"❌ {st.session_state['models_error']}")
        # Clear the flag so message doesn't show on subsequent visits
        st.session_state["show_connection_status"] = False
    
    # Show loading state
    if st.session_state["models_loading"]:
        st.info("🔄 Fetching models from XC URL...")
        return
    
    # Display models section
    st.subheader("Available Models")
    
    models_list = st.session_state["models_list"]
    
    if not models_list and st.session_state["models_error"]:
        st.info("No models available. Please check your XC URL configuration.")
        return
    elif not models_list:
        # Fallback to default endpoint for backward compatibility
        try:
            models_list = llama_stack_api.client.models.list()
            if models_list:
                st.info("Using default endpoint. Configure XC URL above to use a different LlamaStack instance.")
        except Exception:
            st.info("No models available. Please configure a valid XC URL.")
            return
    
    if not models_list:
        st.info("No models available.")
        return

    # Filter models to only include LLM models (exclude embedding models, etc.)
    llm_models = [model for model in models_list if hasattr(model, 'api_model_type') and model.api_model_type == "llm"]
    
    if not llm_models:
        st.info("No LLM models available from this endpoint.")
        return

    # Display models in a table with single column
    import pandas as pd
    
    # Create DataFrame with model identifiers
    models_data = [{"Model Identifier": model.identifier} for model in llm_models]
    df = pd.DataFrame(models_data)
    
    # Add row numbering starting from 1
    df.index = df.index + 1
    
    # Display the table
    st.dataframe(df, use_container_width=True, hide_index=False)
