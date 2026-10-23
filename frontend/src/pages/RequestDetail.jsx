import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { api } from '../api';
import { useAuth } from '../AuthContext';
import StatusBadge from '../components/StatusBadge';
import { 
  AlertCircle, AlertTriangle, CheckCircle, XCircle, FileText, Cpu, 
  FileClock, History, RefreshCw, Clock, Sparkles, ShieldCheck 
} from 'lucide-react';

export default function RequestDetail() {
  const { id } = useParams();
  const { user } = useAuth();
  const navigate = useNavigate();
  
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [processing, setProcessing] = useState(false);
  const [retrying, setRetrying] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState('');
  
  const [editForm, setEditForm] = useState({ merchant_name: '', expense_date: '', expense_amount: '' });
  const [file, setFile] = useState(null);
  const [uploadError, setUploadError] = useState('');
  const [reviewAction, setReviewAction] = useState('approve');
  const [reviewReason, setReviewReason] = useState('');
  const [reviewError, setReviewError] = useState('');
  const [submittingReview, setSubmittingReview] = useState(false);
  const [reviewNotice, setReviewNotice] = useState('');
  
  const [correctingFieldId, setCorrectingFieldId] = useState(null);
  const [correctingValue, setCorrectingValue] = useState('');
  const [previewUrl, setPreviewUrl] = useState(null);
  const [previewType, setPreviewType] = useState(null);
  const [selectedDocId, setSelectedDocId] = useState(null);
  const [copyNotice, setCopyNotice] = useState('');
  const [formError, setFormError] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isSavingDraft, setIsSavingDraft] = useState(false);

  // GenAI State
  const [aiQuestion, setAiQuestion] = useState('Explain this request');
  const [aiAnswer, setAiAnswer] = useState('');
  const [aiLoading, setAiLoading] = useState(false);

  const fetchDocumentPreview = async (docId, docsList) => {
    const doc = docsList.find(d => d.id === docId) || docsList[0];
    if (doc && doc.versions && doc.versions.length > 0) {
      setSelectedDocId(doc.id);
      const latestVersion = doc.versions[0];
      try {
        const res = await api.getDocumentContent(latestVersion.id);
        setPreviewUrl(URL.createObjectURL(res.blob));
        setPreviewType(res.type);
      } catch (e) {
        console.error('Failed to load document preview', e);
      }
    }
  };

  const loadData = async () => {
    try {
      setLoading(true);
      const details = await api.getRequestDetails(id);
      setData(details);

      if (details.documents && details.documents.length > 0) {
        const targetDocId = selectedDocId || details.documents[0].id;
        await fetchDocumentPreview(targetDocId, details.documents);
      }

      setEditForm({
        merchant_name: details.request.merchant_name || '',
        expense_date: details.request.expense_date || '',
        expense_amount: details.request.expense_amount != null ? String(details.request.expense_amount) : ''
      });
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [id]);

  const normalizeDateInput = (val) => {
    if (!val) return null;
    const str = String(val).trim();
    if (!str) return null;
    if (/^\d{4}-\d{2}-\d{2}$/.test(str)) return str;
    const parts = str.split('/');
    if (parts.length === 3) {
      if (parts[2].length === 4) {
        return `${parts[2]}-${parts[0].padStart(2, '0')}-${parts[1].padStart(2, '0')}`;
      } else if (parts[0].length === 4) {
        return `${parts[0]}-${parts[1].padStart(2, '0')}-${parts[2].padStart(2, '0')}`;
      }
    }
    return str;
  };

  const handleUpdate = async (e) => {
    if (e && e.preventDefault) e.preventDefault();
    setFormError('');
    setIsSavingDraft(true);
    try {
      let parsedAmount = null;
      if (editForm.expense_amount !== '' && editForm.expense_amount != null) {
        parsedAmount = parseFloat(editForm.expense_amount);
        if (isNaN(parsedAmount) || parsedAmount <= 0) {
          throw new Error('Claim amount must be a positive number.');
        }
      }

      const payload = {
        merchant_name: editForm.merchant_name ? editForm.merchant_name.trim() : null,
        expense_date: normalizeDateInput(editForm.expense_date),
        expense_amount: parsedAmount
      };

      await api.updateRequest(id, payload);
      setCopyNotice('Saved draft details successfully. Verification checks updated.');
      setTimeout(() => setCopyNotice(''), 5000);
      await loadData();
    } catch (err) {
      setFormError(err.message || 'Failed to save draft details.');
    } finally {
      setIsSavingDraft(false);
    }
  };

  const handleUpload = async (e) => {
    e.preventDefault();
    if (!file) return;
    try {
      setUploading(true);
      await api.uploadDocument(id, file);
      setFile(null);
      await loadData();
    } catch (err) {
      alert(err.message);
    } finally {
      setUploading(false);
    }
  };

  const handleSubmit = async () => {
    setFormError('');
    setIsSubmitting(true);
    try {
      const merchant = editForm.merchant_name ? editForm.merchant_name.trim() : '';
      const normDate = normalizeDateInput(editForm.expense_date);
      const amountStr = editForm.expense_amount != null ? String(editForm.expense_amount).trim() : '';
      const amount = parseFloat(amountStr);

      const missing = [];
      if (!merchant) missing.push('Merchant Name');
      if (!normDate) missing.push('Expense Date');
      if (!amountStr || isNaN(amount) || amount <= 0) missing.push('Positive Expense Amount');

      if (missing.length > 0) {
        throw new Error(`Cannot submit: Please provide ${missing.join(', ')}.`);
      }

      const payload = {
        merchant_name: merchant,
        expense_date: normDate,
        expense_amount: amount
      };

      // 1. Save draft details first to guarantee database persistence
      await api.updateRequest(id, payload);

      // 2. Submit the request with payload
      if (data?.request?.status === 'More Information Required') {
        await api.resubmitRequest(id, payload);
      } else {
        await api.submitRequest(id, payload);
      }

      setCopyNotice('Request submitted successfully for review.');
      setTimeout(() => setCopyNotice(''), 5000);
      await loadData();
    } catch (err) {
      setFormError(err.message || 'Submission failed.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleProcess = async () => {
    try {
      setProcessing(true);
      await api.processRequest(id);
    } catch (err) {
      alert(err.message);
    } finally {
      await loadData();
      setProcessing(false);
    }
  };

  const handleReview = async () => {
    setReviewError('');
    const cleanReason = reviewReason ? reviewReason.trim() : '';
    if ((reviewAction === 'reject' || reviewAction === 'request_correction') && !cleanReason) {
      setReviewError(
        reviewAction === 'reject'
          ? 'Please specify a reason for rejecting this claim.'
          : 'Please specify what additional information or documents are needed.'
      );
      return;
    }

    try {
      setSubmittingReview(true);
      await api.reviewRequest(id, { action: reviewAction, reason: cleanReason });
      setReviewNotice(
        reviewAction === 'approve'
          ? 'Claim approved successfully.'
          : reviewAction === 'reject'
          ? 'Claim rejected.'
          : 'Requested more information from submitter.'
      );
      setReviewReason('');
      setTimeout(() => setReviewNotice(''), 6000);
      await loadData();
    } catch (err) {
      setReviewError(err.message || 'Failed to submit decision.');
    } finally {
      setSubmittingReview(false);
    }
  };

  const handleRetryOcr = async () => {
    try {
      setRetrying(true);
      await api.retryOcr(id);
      await loadData();
    } catch (err) {
      alert("Retry OCR failed: " + err.message);
    } finally {
      setRetrying(false);
    }
  };

  const handleCopyDocToForm = (docRecord) => {
    if (!docRecord) return;
    const fields = docRecord.fields || [];
    const fieldMap = {};
    fields.forEach(f => {
      fieldMap[f.field_name] = f.corrected_value || f.original_value;
    });

    setEditForm(prev => ({
      merchant_name: (fieldMap.merchant && fieldMap.merchant !== 'Unknown') ? fieldMap.merchant : prev.merchant_name,
      expense_date: (fieldMap.date && fieldMap.date !== 'Unknown') ? fieldMap.date : prev.expense_date,
      expense_amount: (fieldMap.amount && fieldMap.amount !== '0.0') ? fieldMap.amount : prev.expense_amount,
    }));

    setCopyNotice(`Copied data from "${docRecord.document_filename}" into claim form. Click "Save Draft Details" to save and verify.`);
    setTimeout(() => setCopyNotice(''), 7000);
  };

  const handleFillFromExtraction = () => {
    if (data?.document_extractions && data.document_extractions.length > 0) {
      const targetDoc = data.document_extractions.find(d => d.document_id === selectedDocId) || data.document_extractions[0];
      handleCopyDocToForm(targetDoc);
      return;
    }
    if (!data?.extractions) return;
    const extMap = {};
    data.extractions.forEach(ex => {
      extMap[ex.field_name] = ex.corrected_value || ex.original_value;
    });
    setEditForm(prev => ({
      merchant_name: extMap.merchant && extMap.merchant !== 'Unknown' ? extMap.merchant : prev.merchant_name,
      expense_date: extMap.date && extMap.date !== 'Unknown' ? extMap.date : prev.expense_date,
      expense_amount: extMap.amount && extMap.amount !== '0.0' ? extMap.amount : prev.expense_amount,
    }));
    setCopyNotice('Copied extracted values into form. Click "Save Draft Details" to save and verify.');
    setTimeout(() => setCopyNotice(''), 7000);
  };

  const handleCorrectField = async (fieldId) => {
    try {
      await api.correctField(id, fieldId, correctingValue);
      setCorrectingFieldId(null);
      setCorrectingValue('');
      loadData();
    } catch (err) {
      alert(err.message);
    }
  };

  const handleWithdraw = async () => {
    if (!window.confirm('Are you sure you want to withdraw this request? This cannot be undone.')) return;
    try {
      await api.withdrawRequest(id);
      loadData();
    } catch (err) {
      alert(err.message);
    }
  };

  const handleAskAI = async (e) => {
    e.preventDefault();
    if (!aiQuestion.trim()) return;
    try {
      setAiLoading(true);
      const response = await api.askGenAI(id, aiQuestion);
      setAiAnswer(response.answer);
    } catch (err) {
      setAiAnswer("Unable to load AI response. " + err.message);
    } finally {
      setAiLoading(false);
    }
  };

  const renderConfidence = (val) => {
    if (val === null || val === undefined || val === '' || val === '0.0' || val === 0 || val === '0') {
      return <span className="text-gray-400 italic text-xs">Not available</span>;
    }
    const n = parseFloat(val);
    if (isNaN(n) || n <= 0.0) {
      return <span className="text-gray-400 italic text-xs">Not available</span>;
    }
    const pct = n <= 1.0 ? Math.round(n * 100) : Math.round(n);
    return <span className="text-emerald-700 font-semibold text-xs">{pct}%</span>;
  };

  if (loading) {
    return (
      <div className="flex flex-col justify-center items-center h-64 text-gray-500 gap-3">
        <div className="animate-spin rounded-full h-8 w-8 border-2 border-blue-200 border-t-blue-600" />
        <span className="text-sm">Loading request details...</span>
      </div>
    );
  }
  
  if (error) {
    return (
      <div className="p-6 max-w-xl mx-auto text-center mt-12 bg-red-50 rounded-xl border border-red-200">
        <AlertCircle className="mx-auto text-red-500 mb-2" size={32} />
        <h3 className="text-base font-semibold text-red-800">Unable to load information</h3>
        <p className="text-sm text-red-600 mt-1">{error}</p>
        <button onClick={() => navigate('/')} className="mt-4 px-4 py-2 bg-red-100 text-red-700 rounded-lg hover:bg-red-200 text-xs font-medium">
          Return to Dashboard
        </button>
      </div>
    );
  }
  
  if (!data) return <div className="p-8 text-center text-gray-500">No requests found.</div>;

  const { request, documents, verifications, extractions, history, information_required_reason } = data;
  
  const canEdit = (user.role === 'Submitter') && (request.status === 'Draft' || request.status === 'More Information Required');
  const canReview = ['Reviewer', 'Approver'].includes(user.role) && (request.status === 'Submitted' || request.status === 'Under Review' || request.status === 'Processing Failed');
  const canApprove = ['Reviewer', 'Approver'].includes(user.role) && (request.status === 'Under Review' || request.status === 'Processing Failed');
  const canWithdraw = (user.role === 'Submitter') && request.submitter_id === user.id && !['Approved', 'Rejected', 'Withdrawn'].includes(request.status);

  // Active preview document
  const activeDoc = (documents && documents.length > 0)
    ? (documents.find(d => d.id === selectedDocId) || documents[0])
    : null;

  const getVerificationIcon = (result) => {
    if (result === 'PASS') return <CheckCircle className="text-emerald-500 shrink-0 mt-0.5" size={16} />;
    if (result === 'INCONSISTENT') return <XCircle className="text-rose-500 shrink-0 mt-0.5" size={16} />;
    if (result === 'WARNING') return <AlertTriangle className="text-amber-500 shrink-0 mt-0.5" size={16} />;
    return <AlertCircle className="text-yellow-600 shrink-0 mt-0.5" size={16} />;
  };

  const getVerificationBadge = (result) => {
    if (result === 'PASS') return <span className="bg-emerald-100 text-emerald-800 text-xs px-2.5 py-0.5 rounded-full font-semibold border border-emerald-200">PASS</span>;
    if (result === 'INCONSISTENT') return <span className="bg-rose-100 text-rose-800 text-xs px-2.5 py-0.5 rounded-full font-semibold border border-rose-200">INCONSISTENT</span>;
    if (result === 'WARNING') return <span className="bg-amber-100 text-amber-800 text-xs px-2.5 py-0.5 rounded-full font-semibold border border-amber-200">WARNING</span>;
    return <span className="bg-yellow-100 text-yellow-800 text-xs px-2.5 py-0.5 rounded-full font-medium border border-yellow-200">UNABLE TO VERIFY</span>;
  };

  const getSuggestedAction = (check) => {
    if (check.result === 'PASS') {
      return 'Check passed successfully — no action needed.';
    }
    if (check.category === 'spelling_mismatch') {
      return 'Possible merchant spelling typo: update the claim merchant in form above or re-upload a clearer receipt.';
    }
    if (check.category === 'unusual_amount') {
      return 'High-value expense: flagged for elevated manager review and approval.';
    }
    if (check.rule_name === 'Amount Consistency') {
      return 'Receipt amount differs from claim form: update claim amount or upload corrected invoice.';
    }
    if (check.rule_name === 'Merchant Consistency') {
      return 'Check vendor name on document: update claim form to match receipt or upload matching documentation.';
    }
    if (check.rule_name === 'Date Consistency' || check.rule_name === 'Date Validity' || check.rule_name === 'Date Parsing') {
      return 'Verify transaction date: correct the expense date in claim or attach receipt with valid date.';
    }
    if (check.rule_name === 'Document Readability') {
      return 'OCR extraction failed on document: upload a clearer image/PDF or click Retry OCR.';
    }
    if (check.rule_name === 'Required Field') {
      return 'Ensure Merchant Name, Expense Date, and Expense Amount are filled in the claim.';
    }
    if (check.rule_name === 'Required Document') {
      return 'Attach a valid invoice, bill, or receipt document to support this expense.';
    }
    if (check.rule_name === 'Possible Duplicate') {
      return 'Confirm this expense has not already been submitted in another reimbursement request.';
    }
    return 'Review the evidence details and adjust the claim form or documentation accordingly.';
  };

  return (
    <div className="max-w-7xl mx-auto space-y-6">
      
      {/* Header section */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center bg-white p-5 sm:p-6 rounded-xl shadow-xs border border-gray-200 gap-4">
        <div className="space-y-1">
          <div className="flex items-center gap-2.5 flex-wrap">
            <h2 className="text-xl sm:text-2xl font-bold tracking-tight text-gray-900">Request #{request.id}</h2>
            <StatusBadge status={request.status} />
            {/* Real Claim Verification Badge */}
            {(() => {
              if (!verifications || verifications.length === 0) return null;
              const hasInconsistent = verifications.some(v => v.result === 'INCONSISTENT');
              const hasMissingClaim = verifications.some(v => v.rule_name === 'Required Field' && v.result === 'CANNOT DETERMINE');
              const hasUnreadableDoc = verifications.some(v => v.rule_name === 'Document Readability' && v.result === 'CANNOT DETERMINE');
              const allPassed = verifications.length > 0 && verifications.every(v => v.result === 'PASS');

              if (hasInconsistent) {
                return (
                  <span className="text-xs bg-rose-100 text-rose-800 px-2.5 py-0.5 rounded-full font-semibold border border-rose-200 inline-flex items-center gap-1">
                    <XCircle size={12}/> Claim Mismatch
                  </span>
                );
              }
              if (hasMissingClaim) {
                return (
                  <span className="text-xs bg-amber-100 text-amber-800 px-2.5 py-0.5 rounded-full font-semibold border border-amber-200 inline-flex items-center gap-1">
                    <AlertTriangle size={12}/> Missing Claim Details
                  </span>
                );
              }
              if (hasUnreadableDoc) {
                return (
                  <span className="text-xs bg-yellow-100 text-yellow-800 px-2.5 py-0.5 rounded-full font-semibold border border-yellow-200 inline-flex items-center gap-1">
                    <AlertCircle size={12}/> Document Unreadable
                  </span>
                );
              }
              if (allPassed) {
                return (
                  <span className="text-xs bg-emerald-100 text-emerald-800 px-2.5 py-0.5 rounded-full font-semibold border border-emerald-200 inline-flex items-center gap-1">
                    <CheckCircle size={12}/> Verified
                  </span>
                );
              }
              return null;
            })()}
          </div>
          <p className="text-xs sm:text-sm text-gray-500 font-medium">
            {request.type} Expense {request.category ? `• ${request.category}` : ''}
          </p>
        </div>
        <div className="text-left sm:text-right flex flex-col sm:items-end w-full sm:w-auto pt-3 sm:pt-0 border-t sm:border-t-0 border-gray-100">
          <p className="text-xs text-gray-500 uppercase tracking-wider font-semibold">Claim Amount</p>
          <p className="text-2xl sm:text-3xl font-bold font-mono text-gray-900 mt-0.5">
            {request.expense_amount ? `$${request.expense_amount.toFixed(2)}` : '--'}
          </p>
          {canWithdraw && (
            <button
              onClick={handleWithdraw}
              className="mt-2 text-red-600 hover:text-red-800 text-xs font-semibold hover:underline cursor-pointer"
            >
              Withdraw Request
            </button>
          )}
        </div>
      </div>

      {request.status === 'More Information Required' && information_required_reason && (
        <div className="p-4 bg-yellow-50 border-l-4 border-yellow-500 rounded-lg shadow-xs flex gap-3 items-start">
          <AlertCircle className="text-yellow-600 shrink-0 mt-0.5" size={18} />
          <div className="space-y-0.5">
            <h4 className="font-semibold text-yellow-800 text-sm">Action Required: More Information Requested</h4>
            <p className="text-xs text-yellow-700">Reviewer message: "{information_required_reason}"</p>
          </div>
        </div>
      )}

      {request.status === 'Processing Failed' && (
        <div className="p-4 bg-orange-50 border-l-4 border-orange-500 rounded-lg shadow-xs flex gap-3 items-start">
          <AlertCircle className="text-orange-600 shrink-0 mt-0.5" size={18} />
          <div className="space-y-0.5">
            <h4 className="font-semibold text-orange-800 text-sm">Processing Notice</h4>
            <p className="text-xs text-orange-700">Could not complete automatic document extraction. Reviewers can manually evaluate or submitters can re-upload a clearer image.</p>
          </div>
        </div>
      )}

      {/* Main Grid Split */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        
        {/* LEFT COLUMN: Document & AI */}
        <div className="lg:col-span-5 space-y-5 min-w-0">
          
          <div className="bg-white p-5 sm:p-6 rounded-xl shadow-xs border border-gray-200 space-y-4">
            <div className="flex justify-between items-center flex-wrap gap-2">
              <div>
                <h3 className="text-base sm:text-lg font-bold text-gray-900">Current Document</h3>
                {activeDoc && (
                  <p className="text-xs text-gray-500 font-mono mt-0.5 truncate max-w-[240px]" title={activeDoc.original_filename}>
                    {activeDoc.original_filename}
                  </p>
                )}
              </div>
              {activeDoc && activeDoc.versions && activeDoc.versions.length > 0 && (
                <div className="flex items-center gap-1.5 flex-wrap">
                  <span className="text-[11px] bg-blue-100 text-blue-800 px-2 py-0.5 rounded font-mono font-medium">
                    V{activeDoc.versions.length} (Current)
                  </span>
                  {(() => {
                    const st = activeDoc.versions[0].processing_state;
                    if (st === 'Completed') {
                      return <span className="text-[11px] bg-emerald-100 text-emerald-800 px-2 py-0.5 rounded font-medium border border-emerald-200 flex items-center gap-1"><CheckCircle size={11}/> OCR Extracted</span>;
                    } else if (st === 'Failed') {
                      return <span className="text-[11px] bg-rose-100 text-rose-800 px-2 py-0.5 rounded font-medium border border-rose-200 flex items-center gap-1"><XCircle size={11}/> OCR Failed</span>;
                    } else {
                      return <span className="text-[11px] bg-amber-100 text-amber-800 px-2 py-0.5 rounded font-medium border border-amber-200 flex items-center gap-1"><Clock size={11}/> {st || 'Processing...'}</span>;
                    }
                  })()}
                </div>
              )}
            </div>

            {/* Document Switcher if multiple documents exist */}
            {documents && documents.length > 1 && (
              <div className="space-y-1.5">
                <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Switch Document Preview:</p>
                <div className="flex gap-2 overflow-x-auto pb-1 max-w-full">
                  {documents.map(doc => {
                    const isSelected = (selectedDocId || documents[0].id) === doc.id;
                    return (
                      <button
                        key={doc.id}
                        type="button"
                        onClick={() => fetchDocumentPreview(doc.id, documents)}
                        className={`text-xs px-3 py-1.5 rounded-lg font-medium transition-colors flex items-center gap-1.5 whitespace-nowrap cursor-pointer border ${
                          isSelected 
                            ? 'bg-blue-600 text-white border-blue-600 shadow-xs'
                            : 'bg-gray-50 text-gray-700 border-gray-200 hover:bg-gray-100'
                        }`}
                      >
                        <FileText size={12} />
                        <span className="truncate max-w-[130px]">{doc.original_filename}</span>
                      </button>
                    );
                  })}
                </div>
              </div>
            )}

            {activeDoc && activeDoc.versions && activeDoc.versions.length > 0 && activeDoc.versions[0].processing_state === 'Failed' && (
              <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-xs text-red-800 flex justify-between items-center gap-2">
                <div className="min-w-0">
                  <p className="font-bold">OCR Processing Failed</p>
                  <p className="text-red-600 mt-0.5 truncate">
                    {activeDoc.versions[0].error_message || "Could not parse document. Upload a clearer copy or retry."}
                  </p>
                </div>
                <button
                  type="button"
                  onClick={handleRetryOcr}
                  disabled={retrying}
                  className="px-3 py-1.5 bg-red-600 hover:bg-red-700 text-white text-xs font-semibold rounded-lg shadow-xs transition-colors flex items-center gap-1 whitespace-nowrap disabled:opacity-50 cursor-pointer shrink-0"
                >
                  <RefreshCw size={11} className={retrying ? "animate-spin" : ""} /> Retry OCR
                </button>
              </div>
            )}
            
            {previewUrl ? (
              <div className="w-full h-[320px] sm:h-[420px] md:h-[480px] border border-gray-300 rounded-lg overflow-hidden bg-gray-50 flex items-center justify-center relative">
                {previewType?.includes('pdf') ? (
                  <iframe src={previewUrl} className="w-full h-full" title="Document Preview" />
                ) : (
                  <img src={previewUrl} alt="Document Preview" className="max-w-full max-h-full object-contain" />
                )}
              </div>
            ) : (
              <div className="w-full h-48 border-2 border-dashed border-gray-300 rounded-lg bg-gray-50 flex flex-col items-center justify-center text-gray-400">
                <FileText size={28} className="mb-2 text-gray-400" />
                <p className="text-xs">No document preview available</p>
              </div>
            )}
            
            {canEdit && (
              <div className="pt-3 border-t border-gray-200 space-y-2">
                <p className="text-xs font-semibold text-gray-700">Upload replacement or additional receipt</p>
                <form onSubmit={handleUpload} className="flex flex-col sm:flex-row gap-2">
                  <input 
                    type="file" 
                    onChange={e => {
                      const selected = e.target.files[0];
                      if (selected) {
                        const maxSize = 10 * 1024 * 1024; // 10 MB
                        const allowed = ['application/pdf','image/png','image/jpeg'];
                        if (!allowed.includes(selected.type)) {
                          setUploadError('Unsupported file type. Allowed: PDF, PNG, JPG.');
                          setFile(null);
                          return;
                        }
                        if (selected.size > maxSize) {
                          setUploadError('File size exceeds 10 MB limit.');
                          setFile(null);
                          return;
                        }
                        setUploadError('');
                        setFile(selected);
                      }
                    }} 
                    className="text-xs border border-gray-300 p-2 rounded-lg flex-1 text-gray-700 bg-white focus:outline-none focus:border-blue-500" 
                    accept=".pdf,.png,.jpg,.jpeg"
                  />
                  <button
                    type="submit"
                    disabled={!file || uploading}
                    className="bg-blue-600 text-white px-4 py-2 rounded-lg text-xs font-semibold hover:bg-blue-700 disabled:bg-blue-300 transition-colors flex items-center justify-center gap-1.5 cursor-pointer min-h-[38px] shrink-0"
                  >
                    {uploading && <RefreshCw size={12} className="animate-spin" />}
                    <span>{uploading ? 'Processing OCR...' : 'Upload'}</span>
                  </button>
                </form>
                {uploadError && <p className="text-xs text-red-600 font-medium">{uploadError}</p>}
                <p className="text-[11px] text-gray-400">Supported formats: PDF, JPG, PNG (max 10 MB). Old versions preserved.</p>
              </div>
            )}
          </div>

          {/* AI Assistant */}
          <div className="bg-white p-5 sm:p-6 rounded-xl shadow-xs border border-gray-200 space-y-3">
            <h3 className="text-base font-bold text-gray-900 flex items-center gap-2">
              <Cpu className="text-blue-600" size={18} />
              <span>AI Assistant</span>
            </h3>
            <p className="text-xs text-gray-500">Ask a question about this request's current state and evidence.</p>
            
            <form onSubmit={handleAskAI} className="flex flex-col sm:flex-row gap-2">
              <input 
                type="text" 
                value={aiQuestion}
                onChange={e => setAiQuestion(e.target.value)}
                className="border border-gray-300 p-2 rounded-lg flex-1 text-xs sm:text-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500 outline-none bg-white text-gray-900"
                placeholder="Ask about verification..."
              />
              <button 
                type="submit" 
                disabled={aiLoading}
                className="bg-gray-800 text-white px-4 py-2 rounded-lg text-xs sm:text-sm font-semibold hover:bg-gray-900 disabled:opacity-50 transition-colors cursor-pointer shrink-0 min-h-[38px]"
              >
                {aiLoading ? 'Thinking...' : 'Ask'}
              </button>
            </form>

            {aiAnswer && (
              <div className="p-3.5 bg-gray-50 border border-gray-200 rounded-lg text-xs sm:text-sm text-gray-800 whitespace-pre-wrap leading-relaxed shadow-inner break-words">
                {aiAnswer}
              </div>
            )}
          </div>
        </div>

        {/* RIGHT COLUMN: Actions, Info, Verifications, History */}
        <div className="lg:col-span-7 space-y-5 min-w-0">
          
          {/* Action Box based on role */}
          {canEdit && (
            <div className="bg-white p-5 sm:p-6 rounded-xl shadow-xs border-2 border-blue-200 space-y-4">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-blue-100 pb-3">
                <h3 className="text-base sm:text-lg font-bold text-blue-900">Edit Claim Details</h3>
                {extractions && extractions.length > 0 && (
                  <button
                    type="button"
                    onClick={handleFillFromExtraction}
                    className="text-xs font-semibold bg-blue-50 text-blue-700 hover:bg-blue-100 px-3 py-1.5 rounded-lg border border-blue-200 transition-colors flex items-center gap-1.5 cursor-pointer self-start sm:self-auto"
                  >
                    <Sparkles size={12} />
                    <span>Copy Extracted Data to Form</span>
                  </button>
                )}
              </div>

              {copyNotice && (
                <div className="p-3 bg-blue-50 border border-blue-200 text-blue-900 rounded-lg text-xs font-medium flex items-center justify-between">
                  <span>{copyNotice}</span>
                  <button type="button" onClick={() => setCopyNotice('')} className="text-blue-700 hover:text-blue-900 font-bold ml-2 cursor-pointer">✕</button>
                </div>
              )}

              {formError && (
                <div className="p-3 bg-red-50 border border-red-200 text-red-800 rounded-lg text-xs font-semibold flex items-center justify-between">
                  <span className="flex items-center gap-1.5">
                    <AlertCircle size={14} className="text-red-600 shrink-0" />
                    {formError}
                  </span>
                  <button type="button" onClick={() => setFormError('')} className="text-red-700 hover:text-red-900 font-bold ml-2 cursor-pointer">✕</button>
                </div>
              )}

              {(!editForm.merchant_name && !editForm.expense_date && !editForm.expense_amount) && extractions && extractions.length > 0 && (
                <p className="text-xs text-gray-700 bg-amber-50 p-3 rounded-lg border border-amber-200">
                  Claim details are currently empty. Click <strong>"Copy Extracted Data to Form"</strong> on the document below to populate merchant, date, and amount, then click <strong>"Save Draft Details"</strong> to verify or <strong>"Submit for Review"</strong> to submit.
                </p>
              )}

              <form onSubmit={handleUpdate} className="space-y-4">
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                  <div>
                    <label className="block text-xs font-semibold text-gray-700 uppercase tracking-wider mb-1">Claim Merchant</label>
                    <input 
                      type="text" 
                      placeholder="e.g. CORNER CAFE"
                      className="border border-gray-300 p-2.5 w-full rounded-lg text-sm bg-white text-gray-900 focus:border-blue-500 focus:ring-1 focus:ring-blue-500 outline-none" 
                      value={editForm.merchant_name} 
                      onChange={e => {
                        setFormError('');
                        setEditForm({...editForm, merchant_name: e.target.value});
                      }} 
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-semibold text-gray-700 uppercase tracking-wider mb-1">Claim Date</label>
                    <input 
                      type="date" 
                      className="border border-gray-300 p-2.5 w-full rounded-lg text-sm bg-white text-gray-900 focus:border-blue-500 focus:ring-1 focus:ring-blue-500 outline-none" 
                      value={editForm.expense_date} 
                      onChange={e => {
                        setFormError('');
                        setEditForm({...editForm, expense_date: e.target.value});
                      }} 
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-semibold text-gray-700 uppercase tracking-wider mb-1">Claim Amount ($)</label>
                    <input 
                      type="number" 
                      step="0.01" 
                      placeholder="e.g. 380.00"
                      className="border border-gray-300 p-2.5 w-full rounded-lg text-sm bg-white text-gray-900 focus:border-blue-500 focus:ring-1 focus:ring-blue-500 outline-none font-mono" 
                      value={editForm.expense_amount} 
                      onChange={e => {
                        setFormError('');
                        setEditForm({...editForm, expense_amount: e.target.value});
                      }} 
                    />
                  </div>
                </div>

                <div className="flex flex-col-reverse sm:flex-row justify-end gap-3 pt-3 border-t border-gray-200">
                  <button 
                    type="submit" 
                    disabled={isSavingDraft || isSubmitting}
                    className="w-full sm:w-auto bg-gray-100 text-gray-700 border border-gray-300 px-4 py-2.5 rounded-lg font-semibold hover:bg-gray-200 transition-colors cursor-pointer text-sm disabled:opacity-50 flex items-center justify-center gap-1.5 min-h-[40px]"
                  >
                    {isSavingDraft && <RefreshCw size={13} className="animate-spin" />}
                    <span>{isSavingDraft ? 'Saving Draft...' : 'Save Draft Details'}</span>
                  </button>
                  <button 
                    type="button" 
                    onClick={handleSubmit} 
                    disabled={isSavingDraft || isSubmitting}
                    className="w-full sm:w-auto bg-blue-600 text-white px-6 py-2.5 rounded-lg font-semibold hover:bg-blue-700 transition-colors shadow-xs cursor-pointer text-sm disabled:bg-blue-300 flex items-center justify-center gap-1.5 min-h-[40px]"
                  >
                    {isSubmitting && <RefreshCw size={14} className="animate-spin" />}
                    <span>
                      {isSubmitting 
                        ? 'Submitting...' 
                        : (request.status === 'More Information Required' ? 'Resubmit Request' : 'Submit for Review')
                      }
                    </span>
                  </button>
                </div>
              </form>
            </div>
          )}

          {/* Make Decision Section (Reviewer & Approver) */}
          {(canReview || canApprove) && (request.status === 'Under Review' || request.status === 'Processing Failed') && (
            <div className="bg-white p-5 sm:p-6 rounded-xl shadow-xs border-2 border-purple-200 bg-purple-50/20 space-y-5">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-purple-100 pb-3">
                <div className="flex items-center gap-2">
                  <ShieldCheck className="text-purple-700" size={20} />
                  <div>
                    <h3 className="text-base sm:text-lg font-bold text-purple-950">Make Decision</h3>
                    <p className="text-xs text-purple-800/80">Evaluate documentation and checks, then record your authoritative decision.</p>
                  </div>
                </div>
                <span className="text-xs bg-purple-100 text-purple-800 font-semibold px-2.5 py-1 rounded-full border border-purple-200 self-start sm:self-auto">
                  Role: {user.role}
                </span>
              </div>

              {/* Advisory Verification Findings Summary */}
              {verifications && verifications.length > 0 && (() => {
                const issues = verifications.filter(v => v.result !== 'PASS');
                if (issues.length > 0) {
                  return (
                    <div className="p-3.5 bg-amber-50/90 border border-amber-300 rounded-lg text-xs space-y-1.5">
                      <div className="flex items-center gap-2 font-bold text-amber-900">
                        <AlertTriangle size={15} className="text-amber-600 shrink-0" />
                        <span>Automated Verification Advisory ({issues.length} finding{issues.length > 1 ? 's' : ''} to consider):</span>
                      </div>
                      <ul className="list-disc pl-5 space-y-0.5 text-amber-900/90">
                        {issues.map(iss => (
                          <li key={iss.id || iss.rule_name}>
                            <strong>{iss.rule_name}</strong> ({iss.result}): {iss.evidence}
                          </li>
                        ))}
                      </ul>
                      <p className="text-[11px] text-amber-800 italic pt-0.5">
                        Note: Automated checks do not auto-approve or auto-reject claims. Final decision authority rests with the reviewer.
                      </p>
                    </div>
                  );
                } else {
                  return (
                    <div className="p-3 bg-emerald-50 border border-emerald-200 rounded-lg text-xs flex items-center gap-2 text-emerald-800 font-medium">
                      <CheckCircle size={15} className="text-emerald-600 shrink-0" />
                      <span>All automated verification checks PASSED. Documentation is complete and consistent with claim details.</span>
                    </div>
                  );
                }
              })()}

              {/* Review Error and Notice Banners */}
              {reviewError && (
                <div className="p-3 bg-red-50 border border-red-200 text-red-800 rounded-lg text-xs font-semibold flex items-center justify-between">
                  <span className="flex items-center gap-1.5">
                    <AlertCircle size={14} className="text-red-600 shrink-0" />
                    {reviewError}
                  </span>
                  <button type="button" onClick={() => setReviewError('')} className="text-red-700 hover:text-red-900 font-bold ml-2 cursor-pointer">✕</button>
                </div>
              )}

              {reviewNotice && (
                <div className="p-3 bg-emerald-50 border border-emerald-200 text-emerald-800 rounded-lg text-xs font-semibold flex items-center justify-between">
                  <span className="flex items-center gap-1.5">
                    <CheckCircle size={14} className="text-emerald-600 shrink-0" />
                    {reviewNotice}
                  </span>
                  <button type="button" onClick={() => setReviewNotice('')} className="text-emerald-700 hover:text-emerald-900 font-bold ml-2 cursor-pointer">✕</button>
                </div>
              )}

              {/* 1. Explicit Decision Options (Segmented Radio Cards) */}
              <div>
                <label className="block text-xs font-bold text-gray-700 uppercase tracking-wider mb-2">
                  Select Decision:
                </label>
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                  {/* Option: Approve */}
                  <label
                    onClick={() => { setReviewAction('approve'); setReviewError(''); }}
                    className={`flex flex-col p-3.5 rounded-lg border-2 cursor-pointer transition-all ${
                      reviewAction === 'approve'
                        ? 'border-emerald-600 bg-emerald-50/70 shadow-sm ring-2 ring-emerald-500/20'
                        : 'border-gray-200 bg-white hover:border-emerald-300 hover:bg-emerald-50/20'
                    }`}
                  >
                    <div className="flex items-center justify-between mb-1">
                      <div className="flex items-center gap-2">
                        <input
                          type="radio"
                          name="reviewDecision"
                          value="approve"
                          checked={reviewAction === 'approve'}
                          onChange={() => { setReviewAction('approve'); setReviewError(''); }}
                          className="h-4 w-4 cursor-pointer accent-emerald-600"
                        />
                        <span className="font-bold text-sm text-gray-900">Approve Claim</span>
                      </div>
                      <CheckCircle size={16} className={reviewAction === 'approve' ? 'text-emerald-600' : 'text-gray-400'} />
                    </div>
                    <p className="text-xs text-gray-500 pl-6">Authorize this reimbursement request for payment.</p>
                  </label>

                  {/* Option: Reject */}
                  <label
                    onClick={() => { setReviewAction('reject'); setReviewError(''); }}
                    className={`flex flex-col p-3.5 rounded-lg border-2 cursor-pointer transition-all ${
                      reviewAction === 'reject'
                        ? 'border-rose-600 bg-rose-50/70 shadow-sm ring-2 ring-rose-500/20'
                        : 'border-gray-200 bg-white hover:border-rose-300 hover:bg-rose-50/20'
                    }`}
                  >
                    <div className="flex items-center justify-between mb-1">
                      <div className="flex items-center gap-2">
                        <input
                          type="radio"
                          name="reviewDecision"
                          value="reject"
                          checked={reviewAction === 'reject'}
                          onChange={() => { setReviewAction('reject'); setReviewError(''); }}
                          className="h-4 w-4 cursor-pointer accent-rose-600"
                        />
                        <span className="font-bold text-sm text-gray-900">Reject Claim</span>
                      </div>
                      <XCircle size={16} className={reviewAction === 'reject' ? 'text-rose-600' : 'text-gray-400'} />
                    </div>
                    <p className="text-xs text-gray-500 pl-6">Deny reimbursement based on non-compliance.</p>
                  </label>

                  {/* Option: Request More Info */}
                  <label
                    onClick={() => { setReviewAction('request_correction'); setReviewError(''); }}
                    className={`flex flex-col p-3.5 rounded-lg border-2 cursor-pointer transition-all ${
                      reviewAction === 'request_correction'
                        ? 'border-amber-600 bg-amber-50/70 shadow-sm ring-2 ring-amber-500/20'
                        : 'border-gray-200 bg-white hover:border-amber-300 hover:bg-amber-50/20'
                    }`}
                  >
                    <div className="flex items-center justify-between mb-1">
                      <div className="flex items-center gap-2">
                        <input
                          type="radio"
                          name="reviewDecision"
                          value="request_correction"
                          checked={reviewAction === 'request_correction'}
                          onChange={() => { setReviewAction('request_correction'); setReviewError(''); }}
                          className="h-4 w-4 cursor-pointer accent-amber-600"
                        />
                        <span className="font-bold text-sm text-gray-900">Request More Info</span>
                      </div>
                      <AlertCircle size={16} className={reviewAction === 'request_correction' ? 'text-amber-600' : 'text-gray-400'} />
                    </div>
                    <p className="text-xs text-gray-500 pl-6">Return to submitter for additional evidence.</p>
                  </label>
                </div>
              </div>

              {/* 2. Reviewer Decision / Comments Field */}
              <div>
                <label className="block text-xs font-semibold text-gray-800 uppercase tracking-wider mb-1.5">
                  Reviewer Decision / Comments
                  {reviewAction !== 'approve' ? (
                    <span className="text-rose-600 text-xs font-bold ml-1.5">* (Required for {reviewAction === 'reject' ? 'rejection' : 'requesting more info'})</span>
                  ) : (
                    <span className="text-gray-400 text-xs font-normal ml-1.5">(Optional for approval)</span>
                  )}
                </label>
                <textarea
                  placeholder="Explain your decision, provide justification, or specify what information is missing…"
                  className="w-full p-3 border border-gray-300 rounded-lg focus:border-purple-500 focus:ring-2 focus:ring-purple-200 outline-none resize-none h-24 text-sm bg-white text-gray-900"
                  value={reviewReason}
                  onChange={e => {
                    setReviewError('');
                    setReviewReason(e.target.value);
                  }}
                />
              </div>

              {/* 3. Action-Reflective Submit Button */}
              <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 pt-2 border-t border-purple-100">
                <span className="text-xs text-gray-500">
                  {reviewAction === 'approve' && 'Claim will be marked Approved and recorded in the audit log.'}
                  {reviewAction === 'reject' && 'Claim will be marked Rejected and cannot be edited by submitter.'}
                  {reviewAction === 'request_correction' && 'Claim will be returned to draft state for submitter corrections.'}
                </span>

                <button
                  type="button"
                  onClick={handleReview}
                  disabled={submittingReview}
                  className={`w-full sm:w-auto px-6 py-2.5 rounded-lg font-semibold text-white text-sm shadow-sm transition-all flex items-center justify-center gap-2 cursor-pointer disabled:opacity-50 min-h-[42px] ${
                    reviewAction === 'approve'
                      ? 'bg-emerald-600 hover:bg-emerald-700 shadow-emerald-600/20'
                      : reviewAction === 'reject'
                      ? 'bg-rose-600 hover:bg-rose-700 shadow-rose-600/20'
                      : 'bg-amber-600 hover:bg-amber-700 shadow-amber-600/20'
                  }`}
                >
                  {submittingReview ? (
                    <>
                      <RefreshCw size={14} className="animate-spin" />
                      <span>Submitting Decision...</span>
                    </>
                  ) : (
                    <>
                      {reviewAction === 'approve' && <CheckCircle size={15} />}
                      {reviewAction === 'reject' && <XCircle size={15} />}
                      {reviewAction === 'request_correction' && <AlertCircle size={15} />}
                      <span>
                        {reviewAction === 'approve' && 'Approve Claim'}
                        {reviewAction === 'reject' && 'Reject Claim'}
                        {reviewAction === 'request_correction' && 'Request More Information'}
                      </span>
                    </>
                  )}
                </button>
              </div>
            </div>
          )}

          {(canReview && request.status === 'Submitted') && (
            <div className="bg-white p-5 sm:p-6 rounded-xl shadow-xs border-2 border-indigo-200 bg-indigo-50/30 space-y-3">
              <h3 className="text-base font-bold text-indigo-900">Process Documents</h3>
              <p className="text-xs sm:text-sm text-gray-700">Run OCR extraction and automatic verification on the current document version before human review.</p>
              <button 
                onClick={handleProcess} 
                disabled={processing} 
                className="bg-indigo-600 text-white px-6 py-2.5 rounded-lg font-semibold hover:bg-indigo-700 transition-colors shadow-sm disabled:opacity-50 flex items-center justify-center gap-2 w-full sm:w-auto text-sm cursor-pointer min-h-[40px]"
              >
                {processing ? (
                  <><div className="animate-spin rounded-full h-4 w-4 border-2 border-white border-t-transparent"></div> Processing...</>
                ) : 'Trigger Automated Processing'}
              </button>
            </div>
          )}

          {/* Missing Fields Banner */}
          {data?.missing_fields && data.missing_fields.length > 0 && (
            <div className="p-4 bg-amber-50 border-l-4 border-amber-500 rounded-lg shadow-xs space-y-1">
              <div className="flex items-center gap-2">
                <AlertCircle className="text-amber-600" size={17} />
                <h4 className="font-bold text-amber-900 text-sm">Action Needed: Missing Information</h4>
              </div>
              <ul className="text-xs text-amber-800 pl-6 list-disc space-y-0.5">
                {data.missing_fields.map((mf, idx) => (
                  <li key={idx}>
                    <strong>{mf.label}</strong> ({mf.message || (mf.location === 'claim' ? 'Not filled in claim form' : 'Document unreadable')})
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Extracted Info - Separated by Document and Version */}
          {documents.length > 0 && (
            <div className="bg-white p-5 sm:p-6 rounded-xl shadow-xs border border-gray-200 space-y-4">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-3 border-b border-gray-100 gap-2">
                <div>
                  <h3 className="text-base sm:text-lg font-bold text-gray-900">Extracted Document Information</h3>
                  <p className="text-xs text-gray-500">Structured data extracted by OCR engine linked directly to each document version.</p>
                </div>
              </div>

              {(!data?.document_extractions || data.document_extractions.length === 0) && extractions.length === 0 ? (
                <div className="text-center py-6 text-gray-500 text-xs sm:text-sm">
                  <p>No extracted fields available for this document.</p>
                  {documents[0]?.versions[0]?.processing_state === 'Failed' && (
                    <button
                      onClick={handleRetryOcr}
                      disabled={retrying}
                      className="mt-2 text-xs text-blue-600 font-semibold hover:underline cursor-pointer"
                    >
                      Click here to retry OCR extraction
                    </button>
                  )}
                </div>
              ) : (
                <div className="space-y-4">
                  {(data?.document_extractions && data.document_extractions.length > 0
                    ? data.document_extractions
                    : [{ document_id: 1, document_filename: documents[0]?.original_filename, version_number: 1, engine: 'default', processing_state: 'Completed', fields: extractions }]
                  ).map((docExt, docIdx) => {
                    const semanticFields = (docExt.fields || []).filter(f => ['merchant', 'date', 'amount'].includes(f.field_name));
                    const displayFields = semanticFields.length > 0 ? semanticFields : (docExt.fields || []);
                    return (
                      <div key={docExt.document_id || docIdx} className="border border-gray-200 rounded-lg p-3 sm:p-4 bg-gray-50/50 space-y-3">
                        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-gray-200/60 pb-2.5">
                          <div className="flex items-center gap-2 flex-wrap">
                            <FileText className="text-blue-600" size={15} />
                            <span className="font-semibold text-gray-900 text-sm truncate max-w-[180px] sm:max-w-none" title={docExt.document_filename}>
                              {docExt.document_filename}
                            </span>
                            <span className="text-[11px] bg-blue-100 text-blue-800 px-2 py-0.5 rounded font-mono font-medium">
                              V{docExt.version_number}
                            </span>
                            {docExt.engine && (
                              <span className="text-[11px] bg-gray-200 text-gray-700 px-1.5 py-0.5 rounded font-mono">
                                {docExt.engine}
                              </span>
                            )}
                            <span className="text-[11px] bg-emerald-100 text-emerald-800 px-2 py-0.5 rounded font-medium">
                              {docExt.processing_state === 'Completed' ? 'OCR Extracted' : docExt.processing_state}
                            </span>
                          </div>
                          {canEdit && displayFields.length > 0 && (
                            <button
                              type="button"
                              onClick={() => handleCopyDocToForm(docExt)}
                              className="text-xs font-semibold bg-blue-600 hover:bg-blue-700 text-white px-3 py-1.5 rounded-lg shadow-xs transition-colors flex items-center gap-1.5 self-start sm:self-auto cursor-pointer"
                            >
                              <Sparkles size={12} />
                              <span>Copy Extracted Data to Form</span>
                            </button>
                          )}
                        </div>

                        {displayFields.length === 0 ? (
                          <p className="text-xs text-gray-500 italic py-2">No fields extracted for this document.</p>
                        ) : (
                          <div className="overflow-x-auto bg-white rounded-lg border border-gray-200">
                            <table className="min-w-full text-xs text-left">
                              <thead className="bg-gray-50 border-b border-gray-200 text-gray-600 uppercase tracking-wider text-[10px] font-semibold">
                                <tr>
                                  <th className="px-3 py-2.5">Field</th>
                                  <th className="px-3 py-2.5">Extracted Value</th>
                                  <th className="px-3 py-2.5">Corrected Value</th>
                                  <th className="px-3 py-2.5">Confidence</th>
                                  <th className="px-3 py-2.5 w-32">Action</th>
                                </tr>
                              </thead>
                              <tbody className="divide-y divide-gray-100">
                                {displayFields.map(ex => (
                                  <tr key={ex.id} className="hover:bg-gray-50 transition-colors">
                                    <td className="px-3 py-2.5 capitalize font-semibold text-gray-900 whitespace-nowrap">{ex.field_name}</td>
                                    <td className="px-3 py-2.5 text-gray-800 font-mono font-medium max-w-[150px] truncate" title={ex.original_value}>
                                      {ex.original_value || <span className="italic text-gray-400">Not found</span>}
                                    </td>
                                    <td className="px-3 py-2.5 whitespace-nowrap">
                                      {ex.corrected_value ? (
                                        <span className="font-bold text-indigo-700 bg-indigo-50 px-1.5 py-0.5 rounded border border-indigo-100 font-mono">{ex.corrected_value}</span>
                                      ) : (
                                        <span className="text-gray-400">—</span>
                                      )}
                                    </td>
                                    <td className="px-3 py-2.5 whitespace-nowrap">
                                      {renderConfidence(ex.confidence)}
                                    </td>
                                    <td className="px-3 py-2.5 whitespace-nowrap">
                                      {(canReview && (request.status === 'Under Review' || request.status === 'Processing Failed')) && correctingFieldId !== ex.id && (
                                        <button 
                                          onClick={() => { setCorrectingFieldId(ex.id); setCorrectingValue(ex.corrected_value || ex.original_value || ''); }} 
                                          className="text-[11px] font-semibold text-blue-600 hover:text-blue-800 bg-blue-50 px-2.5 py-1 rounded border border-blue-100 hover:border-blue-200 transition-colors cursor-pointer"
                                        >
                                          Correct
                                        </button>
                                      )}
                                      {correctingFieldId === ex.id && (
                                        <div className="flex gap-1.5 items-center">
                                          <input 
                                            type="text" 
                                            className="border border-blue-300 rounded text-xs p-1 w-20 focus:border-blue-500 focus:ring-1 focus:ring-blue-500 outline-none bg-white text-gray-900" 
                                            value={correctingValue} 
                                            onChange={e => setCorrectingValue(e.target.value)} 
                                            autoFocus
                                          />
                                          <button onClick={() => handleCorrectField(ex.id)} className="text-[11px] font-semibold bg-blue-600 text-white px-2 py-1 rounded hover:bg-blue-700 cursor-pointer">Save</button>
                                          <button onClick={() => setCorrectingFieldId(null)} className="text-[11px] font-medium text-gray-500 hover:text-gray-700 px-1 cursor-pointer">✕</button>
                                        </div>
                                      )}
                                    </td>
                                  </tr>
                                ))}
                              </tbody>
                            </table>
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          )}

          {/* Document Verification & Analysis */}
          {verifications.length > 0 && (
            <div className="bg-white p-5 sm:p-6 rounded-xl shadow-xs border border-gray-200 space-y-4">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-3 border-b border-gray-100 gap-2">
                <div>
                  <h3 className="text-base sm:text-lg font-bold text-gray-900 flex items-center gap-2">
                    <ShieldCheck className="text-blue-600" size={18} />
                    <span>Document Verification & Analysis</span>
                  </h3>
                  <p className="text-xs text-gray-500 mt-0.5">Automated cross-check between claim details and receipt OCR findings.</p>
                </div>
                {/* Verification Stats Summary */}
                <div className="flex items-center gap-1.5 flex-wrap">
                  <span className="text-xs bg-emerald-100 text-emerald-800 font-bold px-2 py-0.5 rounded border border-emerald-200">
                    {verifications.filter(v => v.result === 'PASS').length} Passed
                  </span>
                  {verifications.filter(v => v.result === 'WARNING').length > 0 && (
                    <span className="text-xs bg-amber-100 text-amber-800 font-semibold px-2 py-0.5 rounded border border-amber-200">
                      {verifications.filter(v => v.result === 'WARNING').length} Warning
                    </span>
                  )}
                  {verifications.filter(v => v.result === 'INCONSISTENT').length > 0 && (
                    <span className="text-xs bg-rose-100 text-rose-800 font-bold px-2 py-0.5 rounded border border-rose-200">
                      {verifications.filter(v => v.result === 'INCONSISTENT').length} Inconsistent
                    </span>
                  )}
                  {verifications.filter(v => v.result === 'CANNOT DETERMINE').length > 0 && (
                    <span className="text-xs bg-yellow-100 text-yellow-800 font-medium px-2 py-0.5 rounded border border-yellow-200">
                      {verifications.filter(v => v.result === 'CANNOT DETERMINE').length} Unable to Verify
                    </span>
                  )}
                </div>
              </div>

              {/* Checks Detailed List */}
              <div className="space-y-3">
                {verifications.map((v, idx) => (
                  <div key={v.id || idx} className="p-3.5 rounded-lg border border-gray-100 bg-gray-50/70 space-y-2">
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1.5">
                      <div className="flex items-start gap-2">
                        {getVerificationIcon(v.result)}
                        <div>
                          <span className="font-bold text-gray-900 text-sm">{v.rule_name}</span>
                          <span className="ml-2 text-xs text-gray-400 capitalize">({v.category})</span>
                        </div>
                      </div>
                      <div>
                        {getVerificationBadge(v.result)}
                      </div>
                    </div>
                    
                    {/* Evidence Quote */}
                    <div className="text-xs text-gray-700 bg-white p-2 rounded border border-gray-200/80 font-mono break-all">
                      <span className="text-gray-400 font-sans mr-1">Evidence:</span>
                      {v.evidence}
                    </div>

                    {/* Actionable Next Step if Not Passing */}
                    {v.result !== 'PASS' && (
                      <p className="text-xs text-amber-800 bg-amber-50/80 p-2 rounded border border-amber-200/60">
                        <strong>Suggested Action:</strong> {getSuggestedAction(v)}
                      </p>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Version History & Audit Log */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            
            <div className="bg-white p-5 sm:p-6 rounded-xl shadow-xs border border-gray-200">
              <h3 className="text-base font-bold text-gray-900 mb-4 flex items-center gap-2">
                <FileClock className="text-gray-500" size={18} />
                <span>Document History</span>
              </h3>
              {documents.length === 0 ? (
                <p className="text-xs text-gray-500 italic">No history available.</p>
              ) : (
                <ul className="space-y-4 relative before:absolute before:inset-y-0 before:left-3 before:w-0.5 before:bg-gray-200 pl-8">
                  {documents[0].versions.map((v, i) => (
                    <li key={v.id} className="relative">
                      <div className={`absolute -left-9 w-3 h-3 rounded-full border-2 bg-white ${i === 0 ? 'border-blue-500 bg-blue-500' : 'border-gray-400'} top-1.5`}></div>
                      <div className="flex justify-between items-start mb-1">
                        <span className="font-semibold text-xs sm:text-sm text-gray-900">Version {documents[0].versions.length - i}</span>
                        {i === 0 ? (
                           <span className="text-[10px] font-bold uppercase tracking-wider bg-blue-100 text-blue-800 px-1.5 py-0.5 rounded">Current</span>
                        ) : (
                           <span className="text-[10px] font-bold uppercase tracking-wider bg-gray-100 text-gray-600 px-1.5 py-0.5 rounded border border-gray-200">Historical</span>
                        )}
                      </div>
                      <p className="text-xs text-gray-500 mb-1">{new Date(v.uploaded_at).toLocaleString()}</p>
                      <p className="text-xs text-gray-700 bg-gray-50 px-2 py-1 rounded inline-block border border-gray-100 truncate max-w-full font-mono">{documents[0].original_filename}</p>
                    </li>
                  ))}
                </ul>
              )}
            </div>

            <div className="bg-white p-5 sm:p-6 rounded-xl shadow-xs border border-gray-200">
              <h3 className="text-base font-bold text-gray-900 mb-4 flex items-center gap-2">
                <History className="text-gray-500" size={18} />
                <span>Audit Log</span>
              </h3>
              {history.length === 0 ? (
                <p className="text-xs text-gray-500 italic">No history available.</p>
              ) : (
                <ul className="space-y-4 relative before:absolute before:inset-y-0 before:left-3 before:w-0.5 before:bg-gray-200 pl-8">
                  {history.map((h, i) => (
                    <li key={i} className="relative">
                      <div className="absolute -left-9 w-3 h-3 rounded-full border-2 border-gray-400 bg-white top-1"></div>
                      <p className="text-xs text-gray-500 mb-0.5">{new Date(h.timestamp).toLocaleString()}</p>
                      <p className="text-xs sm:text-sm text-gray-900 font-semibold">{h.action}</p>
                      {h.from_status && h.to_status && h.from_status !== h.to_status && (
                        <p className="text-xs text-gray-600 mt-0.5">{h.from_status} &rarr; <span className="font-semibold text-gray-900">{h.to_status}</span></p>
                      )}
                      {h.reason && (
                        <p className="text-xs text-gray-700 italic bg-gray-50 p-2 rounded mt-1.5 border border-gray-100 text-left break-words">
                          "{h.reason}"
                        </p>
                      )}
                    </li>
                  ))}
                </ul>
              )}
            </div>

          </div>

        </div>
      </div>
    </div>
  );
}
