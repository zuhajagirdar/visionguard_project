import os

try:
    import google.generativeai as genai
    # Configure Gemini API if available
    genai.configure(api_key=os.environ.get("GEMINI_API_KEY", "dummy_key"))
except Exception:
    genai = None

def generate_correction_draft(extracted, verification_issues):
    """Generate a correction message using Gemini if available.
    If the Gemini SDK is missing, return a clear placeholder message.
    """
    prompt = f"Given these extracted fields: {extracted} and these verification issues: {verification_issues}, write a polite correction request message to the submitter outlining exactly what needs to be fixed."
    if genai is None:
        return "Gemini AI functionality unavailable. Please correct the highlighted fields and re-upload the document."
    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(prompt)
        return response.text
    except Exception:
        return "Please correct the highlighted fields and re-upload the document."
