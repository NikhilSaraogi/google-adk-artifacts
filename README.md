# Artifact Agent 🚀

A dedicated specialist agent for high-performance file management, automatic document conversion, and persistent artifact storage built on the **Google ADK (Agent Development Kit)**.

## Overview

The Artifact Agent solves the problem of "LLM context bloat" by intercepting large binary or complex files before they reach the model. It stores them in a persistent session-scoped artifact service and provides the agent with a clean, text-based navigation hint instead of raw bytes.

### Key Features
- **Universal Stripping**: Automatically intercepts Office docs, PDFs, images, and videos.
- **Deep Extraction**: Native high-precision data retrieval using Gemini vision for technical formulas, symbols, and parameters.
- **Auto-Conversion**: Transforms Excel (.xlsx), Word (.docx), and PowerPoint (.pptx) into text/CSV for easy LLM analysis.
- **Vision Support**: Exempts tool outputs from stripping, allowing the model to accurately summarize images and documents.

---

## Project Structure

```text
artifact_agent/
├── .env                # API Keys (GOOGLE_API_KEY)
├── agent.py            # LlmAgent definition (root_agent entry point)
├── artifacts.py        # Core tool logic (upload, load, conversion, extraction)
├── instruction.py      # System prompts & 3-Step Mandatory Workflow
├── utils.py            # Model definition & Universal Stripping callback
```

---

## How it Works

### 1. The Interception Flow (`Universal Stripping`)
When a user uploads a file, the `strip_unsupported_mimes` callback runs **before** the model is called. 
- It replaces binary parts with a navigation hint to keep the core prompt clean.
- **Crucial**: Tool role contents (like image data returned by `load_artifacts`) are **exempted**, ensuring the model can actually "see" and summarize the content.

### 2. The Mandatory Workflow (4-Steps)
The agent operates on a strict, 4-step High-Precision protocol for every attachment:
1. **SAVE** (`handle_file_upload`): Intercepts and persists the file.
2. **LOAD** (`load_artifacts`): Retrieves the content (vision or text).
3. **EXTRACT** (`extract_data_from_artifact`): Performs a native deep-scan to retrieve high-fidelity summaries and data.
4. **REPORT**: Presents the synthesized, technical findings to the user.
- **Note**: This protocol prioritizes analytical precision over token efficiency.

### 3. Deep Extraction Protocol
For technical requests requiring absolute precision (e.g., extracting a symbolic formula from an image), the agent uses `extract_data_from_artifact`. This performs a native Gemini scan with a zero-hallucination mandate.

---

## Setup & Installation

### 1. Prerequisites
- Python 3.10+
- [Google ADK](https://github.com/google/adk) installed.

### 2. Install Dependencies
```bash
pip install google-adk pandas openpyxl python-docx python-pptx reportlab google-genai
```

### 3. Environment Configuration
Create a `.env` file in the `artifact_agent/` directory:
```env
GOOGLE_API_KEY=your_gemini_api_key_here
```

---

## Usage Examples

**User**: "Extract the calculation formula from this attached image."

**Artifact Agent Workflow**:
1. `handle_file_upload("formula.jpg")` ⮕ Saves artifact.
2. `extract_data_from_artifact("formula.jpg", "extract the symbolic formula")` ⮕ Native vision extraction.
3. **Response**: Returns the precise formula in a structured Markdown table.

---

## Contributing
When adding new file formats, update the `_convert_office_content` function in `artifacts.py`. Core stripping logic is maintained in `utils.py`.

---
*Built with ❤️ using Google ADK.*