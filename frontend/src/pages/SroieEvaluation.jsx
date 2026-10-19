import React, { useEffect, useState } from 'react';
import { api } from '../api';
import { useAuth } from '../AuthContext';

export default function SroieEvaluation() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const { user } = useAuth();

  useEffect(() => {
    loadEval();
  }, []);

  const loadEval = async () => {
    try {
      setLoading(true);
      const res = await api.getEvalResults();
      setData(res);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  if (loading) return <div className="p-8 text-center text-gray-500">Loading SROIE Evaluation Results...</div>;
  if (error) return <div className="p-8 text-center text-red-600">Error: {error}</div>;
  if (!data) return <div className="p-8 text-center">No data found</div>;

  return (
    <div className="p-8 max-w-6xl mx-auto space-y-8">
      <div>
        <h2 className="text-2xl font-bold text-gray-900">SROIE Evaluation Results</h2>
        <p className="text-gray-600 mt-1">Authentic regex-bounds against {data.dataset_used}.</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-white p-4 rounded-lg shadow border border-gray-200">
          <div className="text-gray-500 text-sm font-medium">Total Documents</div>
          <div className="text-2xl font-bold text-gray-900">{data.total_documents}</div>
        </div>
        <div className="bg-white p-4 rounded-lg shadow border border-green-200">
          <div className="text-green-700 text-sm font-medium">Exact Merchants</div>
          <div className="text-2xl font-bold text-green-700">{data.fields.merchant.exact}</div>
        </div>
        <div className="bg-white p-4 rounded-lg shadow border border-blue-200">
          <div className="text-blue-700 text-sm font-medium">Exact Dates</div>
          <div className="text-2xl font-bold text-blue-700">{data.fields.date.exact}</div>
        </div>
        <div className="bg-white p-4 rounded-lg shadow border border-purple-200">
          <div className="text-purple-700 text-sm font-medium">Exact Amounts</div>
          <div className="text-2xl font-bold text-purple-700">{data.fields.amount.exact}</div>
        </div>
      </div>

      <div className="bg-white p-6 rounded-lg shadow border border-gray-200">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Known Limitations (From Evaluation)</h3>
        <ul className="list-disc pl-5 space-y-2 text-sm text-gray-700">
          <li>Merchant extraction is highly sensitive to varied receipt layouts and background noise.</li>
          <li>Date formats vary substantially across vendors, requiring normalized parsing.</li>
          <li>Receipts contain many numeric candidates (taxes, subtotals, item lines), making exact totals challenging.</li>
          <li>OCR quality inherently affects downstream regex/heuristic extraction caps.</li>
        </ul>
      </div>

      <div className="bg-white p-6 rounded-lg shadow border border-gray-200">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Error Breakdown</h3>
        {data.error_cases && data.error_cases.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-sm text-left">
              <thead className="bg-gray-50 border-b text-gray-500 font-semibold uppercase text-xs">
                <tr>
                  <th className="px-4 py-3">Document ID</th>
                  <th className="px-4 py-3">Error Type</th>
                  <th className="px-4 py-3">Expected Ground Truth</th>
                  <th className="px-4 py-3">Extracted Value</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {data.error_cases.map((err, i) => (
                  <tr key={i} className="hover:bg-gray-50">
                    <td className="px-4 py-3 font-medium text-gray-900">{err.document_id}</td>
                    <td className="px-4 py-3 text-red-600 font-medium capitalize">{err.error_type}</td>
                    <td className="px-4 py-3 text-gray-700">{err.expected}</td>
                    <td className="px-4 py-3 text-gray-500 italic">{err.extracted || '-'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="text-gray-500">No error cases recorded.</p>
        )}
      </div>

    </div>
  );
}
