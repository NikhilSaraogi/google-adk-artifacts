"""
Artifact Tools — ADK-layer utilities.

Contains the `strip_unsupported_mimes` before-model callback, shared between
the root `pulse_manager` agent and the `artifact_agent` so that binary blobs
are intercepted and cached before they reach any LLM.
"""

import time
import mimetypes
import base64
from typing import Optional

from google.adk.agents.callback_context import CallbackContext
from google.adk.models import LlmRequest, LlmResponse
from google.adk.models.google_llm import Gemini
from google.genai import types


# ──────────────────────────────────────────────────────────────
# MODEL DEFINITION
# ──────────────────────────────────────────────────────────────

model = Gemini(
    model="gemini-2.0-flash",
    retry_options=types.HttpRetryOptions(
        attempts=3,
        initial_delay=2,
        max_delay=10,
        exp_base=2,
    )
)


# ──────────────────────────────────────────────────────────────
# BEFORE-MODEL CALLBACK
# ──────────────────────────────────────────────────────────────

def strip_unsupported_mimes(
    callback_context: CallbackContext,
    llm_request: LlmRequest,
) -> Optional[LlmResponse]:
    """
    Before-model callback that intercepts binary file parts (Office docs,
    PDFs, images, videos, etc.) in the LLM request, caches their raw data
    in session state under ``pending_office_uploads``, and replaces the
    binary parts with a text hint so the LLM is not confused by raw bytes.

    When a new file is detected in the **current turn** of the
    ``pulse_manager`` agent the callback additionally:
    * Removes all tools except ``handle_file_upload`` from the request so
      the model is forced to process the attachment first.
    * Injects a high-priority system instruction reminding the model to call
      ``handle_file_upload`` for every detected file.

    Returns ``None`` in all cases so the LLM always generates its own
    thoughts/response after the cleanup.
    """
    print("\n" + "=" * 50)
    print("🚀 [ArtifactUtils] EXECUTING strip_unsupported_mimes")
    print("=" * 50)

    try:
        pending_uploads = callback_context.state.get("pending_office_uploads", [])
        if not isinstance(pending_uploads, list):
            pending_uploads = []

        modified_any = False
        found_in_last_turn: list[dict] = []

        # Scan ALL contents in the LLM Request (current turn + history)
        for c_idx, content in enumerate(llm_request.contents):
            if not content.parts:
                continue

            # NEW: Exempt tool responses from stripping to allow vision/text to pass
            # This ensures the model can 'see' what a tool like load_artifacts returns.
            if content.role == "tool":
                print(f"🛡️ [ArtifactUtils] Content[{c_idx}]: Role is 'tool'. Skipping stripping.")
                continue

            new_parts = []
            modified_content = False

            for p_idx, part in enumerate(content.parts):
                # Identify binary blob (inline_data or file_data)
                blob = getattr(part, "inline_data", None) or getattr(part, "file_data", None)
                mime = getattr(blob, "mime_type", None) if blob else None

                # Plain-text parts pass through unchanged
                if hasattr(part, "text") and part.text:
                    new_parts.append(part)
                    continue

                # NEW: Allow text-based blobs to pass through as text parts
                if blob and mime and (mime.startswith("text/") or mime == "application/json"):
                    try:
                        text_data = ""
                        if getattr(part, "inline_data", None) and part.inline_data.data:
                            text_data = part.inline_data.data.decode("utf-8")
                        elif getattr(part, "file_data", None) and part.file_data.file_uri:
                            # We'll rely on the model calling load_artifacts for file_uri-based text
                            # but if it's already inline, let's keep it as text.
                            pass
                        
                        if text_data:
                            print(f"📄 [ArtifactUtils] Content[{c_idx}] Part[{p_idx}]: Converting {mime} to text part.")
                            new_parts.append(types.Part(text=text_data))
                            modified_content = True
                            modified_any = True
                            continue
                    except Exception as e:
                        print(f"⚠️ [ArtifactUtils] Failed to decode text blob: {e}")

                # UNIVERSAL STRIPPING — anything with binary data that is not text
                if blob and mime:
                    ext = mimetypes.guess_extension(mime) or ".bin"
                    print(
                        f"⚠️ [ArtifactUtils] Content[{c_idx}] Part[{p_idx}]: "
                        f"Stripping {mime} ({ext})"
                    )

                    b64_data: Optional[str] = None
                    file_uri: Optional[str] = None

                    # 1 — Extract raw bytes from inline_data (preferred)
                    if getattr(part, "inline_data", None) and part.inline_data.data:
                        b64_data = base64.b64encode(part.inline_data.data).decode("utf-8")
                    # 2 — Extract URI from file_data
                    elif getattr(part, "file_data", None) and part.file_data.file_uri:
                        file_uri = part.file_data.file_uri
                        print(f"🔗 [ArtifactUtils] Detected file_uri: {file_uri}")

                    # Cache the upload info (dedup by data + URI)
                    if b64_data or file_uri:
                        already_cached = any(
                            u.get("data") == b64_data and u.get("file_uri") == file_uri
                            for u in pending_uploads
                        )
                        if not already_cached:
                            pending_uploads.append(
                                {
                                    "name": getattr(blob, "display_name", None)
                                    or f"upload{ext}",
                                    "mime_type": mime,
                                    "data": b64_data,
                                    "file_uri": file_uri,
                                    "timestamp": time.time(),
                                    "label": f"Stripped in Model Callback content[{c_idx}]",
                                }
                            )
                            print(
                                f"✅ [ArtifactUtils] Cached binary info for {ext} "
                                f"(Data: {bool(b64_data)}, URI: {bool(file_uri)})"
                            )
                    else:
                        print(
                            f"❓ [ArtifactUtils] Warning: No data or URI found "
                            f"for stripped part {ext}"
                        )

                    # Track files detected in the current (last) turn
                    if c_idx == len(llm_request.contents) - 1:
                        file_name = (
                            getattr(blob, "display_name", None)
                            or f"uploaded_file{ext}"
                        )
                        found_in_last_turn.append(
                            {"name": file_name, "content": b64_data or ""}
                        )

                    # Replace the binary part with a navigation hint for the agent
                    new_parts.append(
                        types.Part(
                            text=(
                                f"[Native File Upload: Detected {ext} file. "
                                "MUST call handle_file_upload to process it.]"
                            )
                        )
                    )
                    modified_content = True
                    modified_any = True
                else:
                    new_parts.append(part)

            if modified_content:
                llm_request.contents[c_idx].parts = new_parts

        if modified_any:
            callback_context.state["pending_office_uploads"] = pending_uploads
            cleaned_count = sum(
                1
                for c in llm_request.contents
                if any("[Native File Upload:" in p.text for p in c.parts if p.text)
            )
            print(
                f"✨ [ArtifactUtils] Successfully cleaned {cleaned_count} content(s)."
            )

            # ── TOOL BOTTLENECK ─────────────────────────────────────────────
            # If new files arrived in the current turn and we are inside an
            # LlmAgent that carries `handle_file_upload`, restrict available
            # tools to that single function so the model cannot stray.
            agent_name = callback_context.agent_name
            bottleneck_agents = {"pulse_manager", "artifact_agent"}

            if agent_name in bottleneck_agents and found_in_last_turn:
                print(
                    f"⚡ [ArtifactUtils] BOTTLENECKING tools in '{agent_name}' "
                    "to force handle_file_upload"
                )
                hfu_tool = llm_request.tools_dict.get("handle_file_upload")
                if hfu_tool:
                    llm_request.tools_dict = {"handle_file_upload": hfu_tool}
                    hfu_declaration = hfu_tool._get_declaration()
                    if hfu_declaration:
                        llm_request.config.tools = [
                            types.Tool(function_declarations=[hfu_declaration])
                        ]

                # Inject a high-priority system instruction
                num_files = len(found_in_last_turn)
                file_list = ", ".join([f"'{f['name']}'" for f in found_in_last_turn])
                priority_instr = (
                    f"CRITICAL: {num_files} attachment(s) ({file_list}) detected. "
                    "You MUST use the 'handle_file_upload' tool for EVERY file to "
                    "process them IMMEDIATELY. Do NOT attempt to use other tools or "
                    "answer the user until EVERY file is saved as an artifact. "
                    "All other tools are temporarily restricted to enforce this workflow."
                )
                llm_request.append_instructions([priority_instr])
                print(
                    "📝 [ArtifactUtils] Injected priority file-handling instruction."
                )
        else:
            print("🟢 [ArtifactUtils] No unsupported binary parts found in request.")

    except Exception as e:
        print(f"❌ [ArtifactUtils] Error during stripping: {e}")
        import traceback
        traceback.print_exc()

    # Always return None — let the model generate its own response
    return None
