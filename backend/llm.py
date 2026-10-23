import os
import re

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


def explain_request_findings(
    req_data: dict,
    documents_data: list,
    extractions_data: list,
    verifications_data: list,
    user_question: str
) -> str:
    """Provide grounded analysis of request data, OCR extractions, and verification checks.
    Uses Gemini when configured; otherwise provides an accurate deterministic offline analysis.
    """
    # If Gemini is available, build structured prompt
    if _genai is not None:
        sdk_type, sdk, api_key = _genai
        context_str = f"""
Request Context:
- Request ID: #{req_data.get('id')} ({req_data.get('type')})
- Current Status: {req_data.get('status')}
- Claim Form Values: Merchant='{req_data.get('merchant_name') or 'Not provided'}', Date='{req_data.get('expense_date') or 'Not provided'}', Amount=${req_data.get('expense_amount') if req_data.get('expense_amount') is not None else 'Not provided'}
- Category: {req_data.get('category') or 'General'}, Description: {req_data.get('description') or 'None'}
- Reviewer Reason / Note: {req_data.get('reviewer_reason') or 'None'}
- Attached Documents: {documents_data}
- Extracted Document Fields: {extractions_data}
- Verification Checks: {verifications_data}
"""
        system_instruction = (
            "You are Veriflow's AI document verification assistant. "
            "Analyze the reimbursement request strictly using ONLY the provided evidence above. "
            "Directly answer the user's question. Point out any specific discrepancies between claim form "
            "values and extracted receipt values. Identify any missing or unreadable fields. "
            "Recommend clear, actionable next steps for the user based on the request's current status. "
            "Never invent facts, pass/fail results, or values not in the evidence. "
            "Never approve or reject the request."
        )
        prompt = f"{system_instruction}\n\n{context_str}\n\nUser Question: {user_question}"

        try:
            if sdk_type == "new":
                client = sdk.Client(api_key=api_key)
                response = client.models.generate_content(
                    model="gemini-2.0-flash",
                    contents=prompt,
                )
                return response.text.strip()
            else:
                model = sdk.GenerativeModel("gemini-1.5-flash")
                response = model.generate_content(prompt)
                return response.text.strip()
        except Exception as exc:
            # Fall back to deterministic offline analysis on model error
            pass

    # Deterministic Offline Analysis
    sections = []
    req_id = req_data.get("id")
    status = req_data.get("status")
    req_type = req_data.get("type", "Expense")

    sections.append(f"Analysis for Request #{req_id} ({req_type} Expense) — Current Status: '{status}'")

    # 1. Document & Version Information
    if not documents_data:
        sections.append("Document Status: No supporting document has been uploaded yet. A valid receipt (PDF or image) is required.")
    else:
        doc = documents_data[0]
        ver_count = len(doc.get("versions", []))
        latest_ver = doc.get("versions", [{}])[0] if doc.get("versions") else {}
        p_state = latest_ver.get("processing_state", "Unknown")
        sections.append(f"Document: '{doc.get('original_filename')}' (Version {ver_count}, Processing State: {p_state})")

    # 2. Extracted vs Claimed Fields
    if extractions_data:
        ext_dict = {}
        for e in extractions_data:
            val = e.get("corrected_value") if e.get("corrected_value") is not None else e.get("original_value")
            ext_dict[e.get("field_name")] = val

        ext_m = ext_dict.get("merchant", "Unknown")
        ext_d = ext_dict.get("date", "Unknown")
        ext_a = ext_dict.get("amount", "0.0")

        sections.append(f"Extracted Document Data:\n• Merchant: {ext_m}\n• Date: {ext_d}\n• Amount: ${ext_a}")

        # Discrepancy analysis
        discrepancies = []
        claim_amt = req_data.get("expense_amount")
        if claim_amt is not None and ext_a not in ("0.0", "Unknown"):
            try:
                diff = abs(float(claim_amt) - float(ext_a))
                if diff >= 0.01:
                    discrepancies.append(f"Amount mismatch: Form specifies ${float(claim_amt):.2f}, but document shows ${float(ext_a):.2f} (difference of ${diff:.2f}).")
            except ValueError:
                pass
        elif claim_amt is None:
            discrepancies.append("Amount: Not provided in claim form.")

        claim_date = req_data.get("expense_date")
        if claim_date and ext_d != "Unknown":
            if str(claim_date) != str(ext_d):
                discrepancies.append(f"Date mismatch: Form specifies {claim_date}, but document shows {ext_d}.")
        elif not claim_date:
            discrepancies.append("Date: Not provided in claim form.")

        claim_merch = req_data.get("merchant_name")
        if claim_merch and ext_m != "Unknown":
            norm_c = re.sub(r'[^\w]', '', claim_merch.lower())
            norm_e = re.sub(r'[^\w]', '', ext_m.lower())
            if norm_c != norm_e and norm_c not in norm_e and norm_e not in norm_c:
                import difflib
                ratio = difflib.SequenceMatcher(None, norm_c, norm_e).ratio()
                if ratio >= 0.65:
                    discrepancies.append(f"Possible spelling mistake or typo: Form specifies '{claim_merch}', but document shows '{ext_m}' (similarity: {ratio:.0%}).")
                else:
                    discrepancies.append(f"Merchant mismatch: Form specifies '{claim_merch}', but document shows '{ext_m}'.")
        elif not claim_merch:
            discrepancies.append("Merchant: Not provided in claim form.")

        if discrepancies:
            sections.append("Identified Discrepancies:\n• " + "\n• ".join(discrepancies))
        else:
            sections.append("Claim Alignment: Claim form fields match the extracted document values.")
    else:
        sections.append("Extracted Document Data: No text has been extracted yet.")

    # 3. Verification Findings
    if verifications_data:
        v_lines = ["Verification Findings:"]
        for v in verifications_data:
            res = v.get("result", "UNKNOWN")
            rule = v.get("rule_name", "Check")
            ev = v.get("evidence", "")
            v_lines.append(f"• [{res}] {rule}: {ev}")
        sections.append("\n".join(v_lines))

    # 4. Recommended Next Steps
    steps = []
    if status == "Draft":
        missing = []
        if req_data.get("expense_amount") is None: missing.append("Amount")
        if not req_data.get("merchant_name"): missing.append("Merchant")
        if not req_data.get("expense_date"): missing.append("Date")
        if missing:
            steps.append(f"Complete the missing claim fields: {', '.join(missing)}.")
        if not documents_data:
            steps.append("Upload a legible PDF, JPG, or PNG receipt.")
        if not missing and documents_data:
            steps.append("Review extracted document details and click 'Submit for Review'.")
    elif status == "More Information Required":
        reason = req_data.get("reviewer_reason")
        if reason:
            steps.append(f"Address the reviewer's request: '{reason}'.")
        steps.append("Upload a replacement document or adjust claim fields, then click 'Resubmit Request'.")
    elif status == "Under Review":
        steps.append("A reviewer will inspect the claim, correct any OCR discrepancies if necessary, and approve or reject the request.")
    elif status == "Processing Failed":
        steps.append("Document text could not be extracted. Upload a clearer copy or retry processing.")

    if steps:
        sections.append("Recommended Next Steps:\n1. " + "\n2. ".join(steps))

    sections.append("[Offline Analysis: GEMINI_API_KEY is not configured; deterministic verification engine used]")
    return "\n\n".join(sections)
