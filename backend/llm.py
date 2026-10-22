import os

_genai = None
_genai_error = None

# Try the modern google-genai SDK first, fall back to deprecated google.generativeai
try:
    import google.genai as genai_new
    _api_key = os.environ.get("GEMINI_API_KEY")
    if _api_key:
        _genai = ("new", genai_new, _api_key)
    else:
        _genai_error = "GEMINI_API_KEY not set"
except ImportError:
    try:
        import google.generativeai as genai_old  # noqa: F401 – kept for compat
        _api_key = os.environ.get("GEMINI_API_KEY")
        if _api_key:
            genai_old.configure(api_key=_api_key)
            _genai = ("old", genai_old, _api_key)
        else:
            _genai_error = "GEMINI_API_KEY not set"
    except ImportError:
        _genai_error = "No Gemini SDK installed (install google-genai)"


def generate_correction_draft(extracted: dict, verification_issues: list) -> str:
    """Generate a correction message using Gemini if available.

    Returns a plain-text message suitable for showing to the submitter.
    If the Gemini SDK is missing or the API key is absent, returns a clear
    placeholder message that is NOT presented as an AI response.
    """
    if _genai is None:
        return (
            f"Gemini AI unavailable ({_genai_error}). "
            "Please correct the highlighted fields and re-upload the document."
        )

    sdk_type, sdk, api_key = _genai
    prompt = (
        "You are a document verification assistant. "
        f"The following fields were extracted from the expense document: {extracted}. "
        f"The following verification issues were found: {verification_issues}. "
        "Write a clear, polite correction request to the submitter explaining exactly "
        "what needs to be fixed or re-uploaded. Do NOT approve or reject the request."
    )

    try:
        if sdk_type == "new":
            client = sdk.Client(api_key=api_key)
            response = client.models.generate_content(
                model="gemini-2.0-flash",
                contents=prompt,
            )
            return response.text
        else:
            model = sdk.GenerativeModel("gemini-1.5-flash")
            response = model.generate_content(prompt)
            return response.text
    except Exception as exc:
        return (
            f"Gemini request failed ({exc}). "
            "Please correct the highlighted fields and re-upload the document."
        )
