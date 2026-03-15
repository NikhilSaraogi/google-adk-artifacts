"""
Artifact Agent — LlmAgent definition.

This module defines `artifact_agent`, a dedicated specialist LlmAgent that
wraps the four artifact management functions and handles all file upload,
storage, and retrieval tasks on behalf of the root `pulse_manager` agent.
"""

import sys
import os

# ── Import shared model from the root utilis.py ──────────────────────────────
# Relative import path: pulse_manager.sub_agents.artifact_tools → pulse_manager.utilis
from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool

# Import model from root utilities
from .utils import model

from .artifacts import (
    handle_file_upload,
    load_artifacts,
    list_artifact_keys,
    save_artifact_content,
    extract_data_from_artifact,
)

# Import instructions
from .instruction import artifact_agent_inst

# Import the before-model callback (binary stripping)
from .utils import strip_unsupported_mimes

# ── Wrap functions as FunctionTools ──────────────────────────────────────────
handle_file_upload_tool   = FunctionTool(func=handle_file_upload)
load_artifacts_tool       = FunctionTool(func=load_artifacts)
list_artifact_keys_tool   = FunctionTool(func=list_artifact_keys)
save_artifact_content_tool = FunctionTool(func=save_artifact_content)
extract_data_tool          = FunctionTool(func=extract_data_from_artifact)

# ── Define the LlmAgent ──────────────────────────────────────────────────────
artifact_agent = LlmAgent(
    name="artifact_agent",
    model=model,
    description=(
        "Specialist agent for file upload processing, artifact storage, and "
        "content retrieval. Handles any binary or text file uploaded by the "
        "user, auto-converts Office documents, and saves/loads session artifacts."
    ),
    instruction=artifact_agent_inst,
    tools=[
        handle_file_upload_tool,
        load_artifacts_tool,
        list_artifact_keys_tool,
        save_artifact_content_tool,
        extract_data_tool,
    ],
    before_model_callback=strip_unsupported_mimes,
)

# ── ADK CLI Entry Point ──────────────────────────────────────────────────────
# The ADK CLI expects 'root_agent' to be exposed.
root_agent = artifact_agent
