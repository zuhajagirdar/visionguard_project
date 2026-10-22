import React, { useEffect, useState, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { api } from '../api';
import { useAuth } from '../AuthContext';
import StatusBadge from '../components/StatusBadge';
import { AlertCircle, CheckCircle, XCircle, FileText, Cpu, FileClock, History } from 'lucide-react';


export default function RequestDetail() {
  const { id } = useParams();
  const { user } = useAuth();
  const navigate = useNavigate();
  
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [processing, setProcessing] = useState(false);
  const [error, setError] = useState('');
  
  const [editForm, setEditForm] = useState({ merchant_name: '', expense_date: '', expense_amount: '' });
  const [file, setFile] = useState(null);
  const [reviewAction, setReviewAction] = useState('approve');
  const [reviewReason, setReviewReason] = useState('');
  
  const [correctingFieldId, setCorrectingFieldId] = useState(null);
  const [correctingValue, setCorrectingValue] = useState('');
  const [previewUrl, setPreviewUrl] = useState(null);
  const [previewType, setPreviewType] = useState(null);

  // GenAI State
  const [aiQuestion, setAiQuestion] = useState('Explain this request');
  const [aiAnswer, setAiAnswer] = useState('');
  const [aiLoading, setAiLoading] = useState(false);

  useEffect(() => {
    loadData();
  }, [id]);

  const loadData = async () => {
    try {
      setLoading(true);
      const details = await api.getRequestDetails(id);
      setData(details);
      
      if (details.documents.length > 0 && details.documents[0].versions.length > 0) {
        const latestVersion = details.documents[0].versions[0];
        try {
          const res = await api.getDocumentContent(latestVersion.id);
          setPreviewUrl(URL.createObjectURL(res.blob));
          setPreviewType(res.type);
        } catch (e) {
          console.error('Failed to load document preview', e);
        }
      }
      setEditForm({
        merchant_name: details.request.merchant_name || '',
        expense_date: details.request.expense_date || '',
        expense_amount: details.request.expense_amount || ''
      });
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleUpdate = async (e) => {
    e.preventDefault();
    try {
      await api.updateRequest(id, {
        merchant_name: editForm.merchant_name || null,
        expense_date: editForm.expense_date || null,
        expense_amount: editForm.expense_amount ? parseFloat(editForm.expense_amount) : null
      });
      loadData();
    } catch (err) {
      alert(err.message);
    }
  };

  const handleUpload = async (e) => {
    e.preventDefault();
    if (!file) return;
    try {
      await api.uploadDocument(id, file);
      setFile(null);
      loadData();
    } catch (err) {
      alert(err.message);
    }
  };

  const handleSubmit = async () => {
    try {
      if (data.request.status === 'More Information Required') {
        await api.resubmitRequest(id);
      } else {
        await api.submitRequest(id);
      }
      loadData();
    } catch (err) {
      alert(err.message);
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

  // handleGenerateMessage removed – not used in UI
  const handleReview = async () => {
    try {
      await api.reviewRequest(id, { action: reviewAction, reason: reviewReason });
      loadData();
    } catch (err) {
      alert(err.message);
    }
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

  if (loading) {
    return (
      <div className="flex justify-center items-center h-64 text-gray-500 flex-col gap-4">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900"></div>
        Loading request details...
      </div>
    );
  }
  
  if (error) {
    return (
      <div className="p-8 max-w-2xl mx-auto text-center mt-12 bg-red-50 rounded-lg border border-red-200">
        <AlertCircle className="mx-auto text-red-500 mb-2" size={32} />
        <h3 className="text-lg font-semibold text-red-800">Unable to load information</h3>
        <p className="text-red-600 mt-1">{error}</p>
        <button onClick={() => navigate('/')} className="mt-4 px-4 py-2 bg-red-100 text-red-700 rounded hover:bg-red-200">Return to Dashboard</button>
      </div>
    );
  }
  
  if (!data) return <div className="p-8">No requests found.</div>;

  const { request, documents, verifications, extractions, history, information_required_reason } = data; // comments removed
  
  const canEdit = (user.role === 'Submitter') && (request.status === 'Draft' || request.status === 'More Information Required');
  const canReview = (user.role === 'Reviewer') && (request.status === 'Submitted' || request.status === 'Under Review' || request.status === 'Processing Failed');
  const canApprove = (user.role === 'Approver') && (request.status === 'Under Review');
  const canWithdraw = (user.role === 'Submitter') && request.submitter_id === user.id && !['Approved', 'Rejected', 'Withdrawn'].includes(request.status);

// Status badge is rendered via <StatusBadge status={status} /> component

  const getVerificationIcon = (result) => {
    if (result === 'PASS') return <CheckCircle className="text-green-500 flex-shrink-0 mt-0.5" size={18} />;
    if (result === 'INCONSISTENT') return <XCircle className="text-red-500 flex-shrink-0 mt-0.5" size={18} />;
    return <AlertCircle className="text-yellow-500 flex-shrink-0 mt-0.5" size={18} />;
  };

  const getVerificationBadge = (result) => {
    if (result === 'PASS') return <span className="bg-green-100 text-green-800 text-xs px-2 py-0.5 rounded font-medium border border-green-200">PASS</span>;
    if (result === 'INCONSISTENT') return <span className="bg-red-100 text-red-800 text-xs px-2 py-0.5 rounded font-medium border border-red-200">INCONSISTENT</span>;
    return <span className="bg-yellow-100 text-yellow-800 text-xs px-2 py-0.5 rounded font-medium border border-yellow-200">CANNOT DETERMINE</span>;
  };

  return (
    <div className="p-4 md:p-8 max-w-7xl mx-auto space-y-6">
      
      {/* Header section */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center bg-white p-6 rounded-xl shadow-sm border border-gray-200">
        <div>
          <div className="flex items-center gap-3 mb-1">
            <h2 className="text-2xl font-bold text-gray-900">Request #{request.id}</h2>
            <StatusBadge status={request.status} />
          </div>
          <p className="text-gray-500 font-medium">{request.type} Expense {request.category ? `• ${request.category}` : ''}</p>
        </div>
        <div className="mt-4 md:mt-0 text-left md:text-right flex flex-col md:items-end">
          <p className="text-sm text-gray-500 uppercase tracking-wide font-medium">Requested Amount</p>
          <p className="text-3xl font-bold text-gray-900 mt-1">
            {request.expense_amount ? `$${request.expense_amount.toFixed(2)}` : '--'}
          </p>
          {canWithdraw && (
            <button
              onClick={handleWithdraw}
              className="mt-3 text-red-600 hover:text-red-800 text-sm font-medium hover:underline"
            >
              Withdraw Request
            </button>
          )}
        </div>
      </div>

      {request.status === 'More Information Required' && information_required_reason && (
        <div className="p-4 bg-yellow-50 border-l-4 border-yellow-500 rounded shadow-sm flex gap-3 items-start">
          <AlertCircle className="text-yellow-600 flex-shrink-0 mt-0.5" size={20} />
          <div>
            <h4 className="font-semibold text-yellow-800">Action Required: More Information Requested</h4>
            <p className="text-yellow-700 mt-1">Reviewer message: "{information_required_reason}"</p>
          </div>
        </div>
      )}

      {request.status === 'Processing Failed' && (
        <div className="p-4 bg-orange-50 border-l-4 border-orange-500 rounded shadow-sm flex gap-3 items-start">
          <AlertCircle className="text-orange-600 flex-shrink-0 mt-0.5" size={20} />
          <div>
            <h4 className="font-semibold text-orange-800">Processing Failed</h4>
            <p className="text-orange-700 mt-1">We couldn't process this document. Reviewers can manually review or submitters can upload a clearer version.</p>
          </div>
        </div>
      )}

      {/* Main Grid Split */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        
        {/* LEFT COLUMN: Document & AI */}
        <div className="lg:col-span-5 space-y-6">
          
          <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-200">
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-lg font-semibold text-gray-900">Current Document</h3>
              {documents.length > 0 && documents[0].versions.length > 0 && (
                <span className="text-xs bg-blue-100 text-blue-800 px-2 py-1 rounded font-medium">
                  V{documents[0].versions.length} (Current)
                </span>
              )}
            </div>
            
            {previewUrl ? (
              <div className="w-full h-[500px] border border-gray-300 rounded-lg overflow-hidden bg-gray-50 flex items-center justify-center relative group">
                {previewType?.includes('pdf') ? (
                  <iframe src={previewUrl} className="w-full h-full" title="Document Preview" />
                ) : (
                  <img src={previewUrl} alt="Document Preview" className="max-w-full max-h-full object-contain" />
                )}
              </div>
            ) : (
              <div className="w-full h-48 border-2 border-dashed border-gray-300 rounded-lg bg-gray-50 flex flex-col items-center justify-center text-gray-400">
                <FileText size={32} className="mb-2" />
                <p>No document available</p>
              </div>
            )}
            
            {canEdit && (
              <div className="mt-4 pt-4 border-t border-gray-100">
                <p className="text-sm text-gray-600 mb-2 font-medium">Upload replacement document</p>
                <form onSubmit={handleUpload} className="flex gap-2">
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
                          setUploadError('File size exceeds 10 MB limit.');
                          setFile(null);
                          return;
                        }
                        setUploadError('');
                        setFile(selected);
                      }
                    }} 
                    className="text-sm border p-1.5 rounded flex-1 text-gray-700 focus:outline-none focus:border-blue-500" 
                    accept=".pdf,.png,.jpg,.jpeg"
                  />
                  <button type="submit" disabled={!file} className="bg-blue-600 text-white px-4 py-1.5 rounded text-sm font-medium hover:bg-blue-700 disabled:opacity-50 transition-colors">
                    Upload
                  </button>
                </form>
                {uploadError && <p className="text-xs text-red-600 mt-1">{uploadError}</p>}
                <p className="text-xs text-gray-400 mt-1">Supported formats: PDF, JPG, PNG (max 10 MB). Old versions will be preserved.</p>
              </div>
            )}
          </div>

          <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-200">
            <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
              <Cpu className="text-blue-600" size={20} />
              AI Assistant
            </h3>
            <p className="text-sm text-gray-600 mb-4">Ask a question about this request's current state and evidence.</p>
            
            <form onSubmit={handleAskAI} className="flex gap-2 mb-4">
              <input 
                type="text" 
                value={aiQuestion}
                onChange={e => setAiQuestion(e.target.value)}
                className="border p-2 rounded flex-1 text-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500 outline-none"
                placeholder="Ask about verification..."
              />
              <button 
                type="submit" 
                disabled={aiLoading}
                className="bg-gray-800 text-white px-4 py-2 rounded text-sm font-medium hover:bg-gray-900 disabled:opacity-50 transition-colors"
              >
                {aiLoading ? 'Thinking...' : 'Ask'}
              </button>
            </form>

            {aiAnswer && (
              <div className="p-4 bg-gray-50 border rounded-lg text-sm text-gray-800 whitespace-pre-wrap leading-relaxed shadow-inner">
                {aiAnswer}
              </div>
            )}
          </div>
        </div>

        {/* RIGHT COLUMN: Actions, Info, Verifications, History */}
        <div className="lg:col-span-7 space-y-6">
          
          {/* Action Box based on role */}
          {canEdit && (
            <div className="bg-white p-6 rounded-xl shadow-sm border-2 border-blue-200">
              <h3 className="text-lg font-semibold text-blue-900 mb-4">Edit Request Information</h3>
              <form onSubmit={handleUpdate} className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Merchant</label>
                  <input type="text" className="border p-2 w-full rounded focus:border-blue-500 focus:ring-1 focus:ring-blue-500 outline-none" value={editForm.merchant_name} onChange={e => setEditForm({...editForm, merchant_name: e.target.value})} />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Date</label>
                  <input type="date" className="border p-2 w-full rounded focus:border-blue-500 focus:ring-1 focus:ring-blue-500 outline-none" value={editForm.expense_date} onChange={e => setEditForm({...editForm, expense_date: e.target.value})} />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Amount</label>
                  <input type="number" step="0.01" className="border p-2 w-full rounded focus:border-blue-500 focus:ring-1 focus:ring-blue-500 outline-none" value={editForm.expense_amount} onChange={e => setEditForm({...editForm, expense_amount: e.target.value})} />
                </div>
                <div className="md:col-span-3 flex justify-end gap-3 mt-2 border-t pt-4">
                  <button type="submit" className="bg-gray-100 text-gray-700 px-4 py-2 rounded font-medium hover:bg-gray-200 transition-colors">Save Draft Details</button>
                  <button type="button" onClick={handleSubmit} className="bg-blue-600 text-white px-6 py-2 rounded font-medium hover:bg-blue-700 transition-colors shadow-sm">
                    {request.status === 'More Information Required' ? 'Resubmit Request' : 'Submit for Review'}
                  </button>
                </div>
              </form>
            </div>
          )}

          {(canReview || canApprove) && request.status === 'Under Review' && (
            <div className="bg-white p-6 rounded-xl shadow-sm border-2 border-purple-200 bg-purple-50/30">
              <h3 className="text-lg font-semibold text-purple-900 mb-4">Make Decision</h3>
              <div className="flex flex-col gap-4">
                <div className="flex flex-col sm:flex-row gap-4">
                  <select 
                    value={reviewAction} 
                    onChange={e => setReviewAction(e.target.value)} 
                    className="flex-1 p-2 border border-purple-300 rounded focus:border-purple-500 focus:ring-1 focus:ring-purple-500 outline-none font-medium text-purple-900"
                  >
                    {canApprove && <option value="approve">Approve Request</option>}
                    {canApprove && <option value="reject">Reject Request</option>}
                    {canReview && <option value="request_correction">Request More Information</option>}
                  </select>
                  <button onClick={handleReview} className="bg-purple-600 text-white px-8 py-2 rounded font-medium hover:bg-purple-700 transition-colors shadow-sm whitespace-nowrap">
                    Submit Decision
                  </button>
                </div>
                {reviewAction !== 'approve' && (
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Reason (Visible to submitter)</label>
                    <textarea 
                      placeholder={reviewAction === 'request_correction' ? "Please explain what needs to be fixed or re-uploaded..." : "Reason for rejection..."}
                      className="w-full p-3 border border-gray-300 rounded focus:border-purple-500 focus:ring-1 focus:ring-purple-500 outline-none resize-none h-24"
                      value={reviewReason}
                      onChange={e => setReviewReason(e.target.value)}
                    />
                  </div>
                )}
              </div>
            </div>
          )}

          {(canReview && request.status === 'Submitted') && (
            <div className="bg-white p-6 rounded-xl shadow-sm border-2 border-indigo-200 bg-indigo-50/30">
              <h3 className="text-lg font-semibold text-indigo-900 mb-2">Process Documents</h3>
              <p className="text-sm text-gray-700 mb-4">Run OCR extraction and automatic verification on the current document version. This must be done before human review.</p>
              <button 
                onClick={handleProcess} 
                disabled={processing} 
                className="bg-indigo-600 text-white px-6 py-2 rounded font-medium hover:bg-indigo-700 transition-colors shadow-sm disabled:opacity-50 flex items-center justify-center gap-2 w-full md:w-auto"
              >
                {processing ? (
                  <><div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div> Processing...</>
                ) : 'Trigger Automated Processing'}
              </button>
            </div>
          )}

          {/* Extracted Info */}
          {extractions.length > 0 && (
            <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-200 overflow-hidden">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">Extracted Information</h3>
              <div className="overflow-x-auto">
                <table className="w-full text-sm text-left">
                  <thead className="bg-gray-50 border-b text-gray-500 uppercase tracking-wider text-xs font-semibold">
                    <tr>
                      <th className="px-4 py-3 rounded-tl-lg">Field</th>
                      <th className="px-4 py-3">Original OCR</th>
                      <th className="px-4 py-3">Corrected Value</th>
                      <th className="px-4 py-3 rounded-tr-lg">Action</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {extractions.map(ex => (
                      <tr key={ex.id} className="hover:bg-gray-50 transition-colors">
                        <td className="px-4 py-3 capitalize font-medium text-gray-900">{ex.field_name}</td>
                        <td className="px-4 py-3 text-gray-600">{ex.original_value || <span className="italic text-gray-400">Not found</span>}</td>
                        <td className="px-4 py-3">
                          {ex.corrected_value ? (
                            <span className="font-bold text-indigo-700 bg-indigo-50 px-2 py-1 rounded border border-indigo-100">{ex.corrected_value}</span>
                          ) : (
                            <span className="text-gray-400">-</span>
                          )}
                        </td>
                        <td className="px-4 py-3 w-48">
                          {(canReview && (request.status === 'Under Review' || request.status === 'Processing Failed')) && correctingFieldId !== ex.id && (
                            <button 
                              onClick={() => { setCorrectingFieldId(ex.id); setCorrectingValue(ex.corrected_value || ex.original_value || ''); }} 
                              className="text-xs font-medium text-blue-600 hover:text-blue-800 bg-blue-50 px-3 py-1.5 rounded border border-blue-100 hover:border-blue-200 transition-colors"
                            >
                              Correct Field
                            </button>
                          )}
                          {correctingFieldId === ex.id && (
                            <div className="flex gap-2">
                              <input 
                                type="text" 
                                className="border border-blue-300 rounded text-xs p-1.5 w-24 focus:border-blue-500 focus:ring-1 focus:ring-blue-500 outline-none" 
                                value={correctingValue} 
                                onChange={e => setCorrectingValue(e.target.value)} 
                                autoFocus
                              />
                              <button onClick={() => handleCorrectField(ex.id)} className="text-xs font-medium bg-blue-600 text-white px-2 py-1.5 rounded hover:bg-blue-700">Save</button>
                              <button onClick={() => setCorrectingFieldId(null)} className="text-xs font-medium text-gray-500 hover:text-gray-700 px-1">Cancel</button>
                            </div>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Verifications */}
          {verifications.length > 0 && (
            <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-200">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">Verification Results</h3>
              <div className="space-y-4">
                {verifications.map(v => (
                  <div key={v.id} className={`p-4 rounded-lg border ${v.result === 'PASS' ? 'bg-green-50/50 border-green-200' : v.result === 'INCONSISTENT' ? 'bg-red-50/50 border-red-200' : 'bg-yellow-50/50 border-yellow-200'}`}>
                    <div className="flex items-start justify-between mb-2">
                      <div className="flex items-center gap-2">
                        {getVerificationIcon(v.result)}
                        <h4 className="font-semibold text-gray-900">{v.rule_name}</h4>
                      </div>
                      {getVerificationBadge(v.result)}
                    </div>
                    <div className="pl-7 space-y-1 text-sm mt-1">
                      <p className="text-gray-700"><strong>Evidence:</strong> {v.evidence}</p>
                      {v.category && <p className="text-gray-500"><strong>Category:</strong> <span className="capitalize">{v.category}</span></p>}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Version History & Audit Log */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            
            <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-200">
              <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
                <FileClock className="text-gray-500" size={20} />
                Document History
              </h3>
              {documents.length === 0 ? (
                <p className="text-sm text-gray-500 italic">No history available.</p>
              ) : (
                <ul className="space-y-4 relative before:absolute before:inset-y-0 before:left-3 before:w-0.5 before:bg-gray-200 pl-8">
                  {documents[0].versions.map((v, i) => (
                    <li key={v.id} className="relative">
                      <div className={`absolute -left-9 w-3 h-3 rounded-full border-2 bg-white ${i === 0 ? 'border-blue-500' : 'border-gray-400'} top-1.5`}></div>
                      <div className="flex justify-between items-start mb-1">
                        <span className="font-semibold text-gray-900">Version {documents[0].versions.length - i}</span>
                        {i === 0 ? (
                           <span className="text-[10px] font-bold uppercase tracking-wider bg-blue-100 text-blue-800 px-1.5 py-0.5 rounded">Current</span>
                        ) : (
                           <span className="text-[10px] font-bold uppercase tracking-wider bg-gray-100 text-gray-600 px-1.5 py-0.5 rounded">Historical</span>
                        )}
                      </div>
                      <p className="text-xs text-gray-500 mb-1">{new Date(v.uploaded_at).toLocaleString()}</p>
                      <p className="text-sm text-gray-700 bg-gray-50 px-2 py-1 rounded inline-block border border-gray-100 truncate max-w-full">{documents[0].original_filename}</p>
                    </li>
                  ))}
                </ul>
              )}
            </div>

            <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-200">
              <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
                <History className="text-gray-500" size={20} />
                Audit Log
              </h3>
              {history.length === 0 ? (
                <p className="text-sm text-gray-500 italic">No history available.</p>
              ) : (
                <ul className="space-y-4 relative before:absolute before:inset-y-0 before:left-3 before:w-0.5 before:bg-gray-200 pl-8">
                  {history.map((h, i) => (
                    <li key={i} className="relative">
                      <div className="absolute -left-9 w-3 h-3 rounded-full border-2 border-gray-400 bg-white top-1"></div>
                      <p className="text-xs text-gray-500 mb-1">{new Date(h.timestamp).toLocaleString()}</p>
                      <p className="text-sm text-gray-800 font-medium">{h.action}</p>
                      {h.from_status && h.to_status && h.from_status !== h.to_status && (
                        <p className="text-xs text-gray-600 mt-1">{h.from_status} &rarr; <span className="font-semibold">{h.to_status}</span></p>
                      )}
                      {h.reason && (
                        <p className="text-xs text-gray-700 italic bg-gray-50 p-1.5 rounded mt-1.5 border border-gray-100 text-left">
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
