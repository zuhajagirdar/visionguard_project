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

  if (loading) return <div className="p-8 text-center text-gray-500 text-sm">Loading SROIE Evaluation Results...</div>;
  if (error) return <div className="p-8 text-center text-red-600 text-sm">Error: {error}</div>;
  if (!data) return <div className="p-8 text-center text-gray-500 text-sm">No data found</div>;

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      <div className="border-b border-gray-200 pb-4">
        <h2 className="text-xl sm:text-2xl font-bold tracking-tight text-gray-900">SROIE Evaluation Results</h2>
        <p className="text-xs sm:text-sm text-gray-500 mt-0.5">Benchmark accuracy against {data.dataset_used}.</p>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 sm:gap-4">
        <div className="card">
          <div className="text-gray-500 text-xs font-semibold uppercase tracking-wider">Total Documents</div>
          <div className="text-2xl sm:text-3xl font-bold text-gray-900 mt-1">{data.total_documents}</div>
        </div>
        <div className="bg-white p-4 rounded-xl shadow-xs border border-green-200">
          <div className="text-green-700 text-xs font-semibold uppercase tracking-wider">Exact Merchants</div>
          <div className="text-2xl sm:text-3xl font-bold text-green-700 mt-1">{data.fields.merchant.exact}</div>
        </div>
        <div className="bg-white p-4 rounded-xl shadow-xs border border-blue-200">
          <div className="text-blue-700 text-xs font-semibold uppercase tracking-wider">Exact Dates</div>
          <div className="text-2xl sm:text-3xl font-bold text-blue-700 mt-1">{data.fields.date.exact}</div>
        </div>
        <div className="bg-white p-4 rounded-xl shadow-xs border border-purple-200">
          <div className="text-purple-700 text-xs font-semibold uppercase tracking-wider">Exact Amounts</div>
          <div className="text-2xl sm:text-3xl font-bold text-purple-700 mt-1">{data.fields.amount.exact}</div>
        </div>
      </div>
    </div>
  );
}
