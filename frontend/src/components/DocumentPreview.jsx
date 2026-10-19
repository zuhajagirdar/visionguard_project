import React, { useState, useEffect } from 'react';
import api from '../api';

export default function DocumentPreview({ versionId }) {
  const [url, setUrl] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let objectUrl = null;
    const fetchDoc = async () => {
      setLoading(true);
      setError(null);
      try {
        const { blob, type } = await api.getDocumentContent(versionId);
        objectUrl = URL.createObjectURL(blob);
        setUrl(objectUrl);
      } catch (err) {
        setError('Failed to load document preview');
      } finally {
        setLoading(false);
      }
    };
    if (versionId) {
      fetchDoc();
    }
    return () => {
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [versionId]);

  if (loading) return <div className="animate-pulse bg-gray-200 h-96 rounded flex items-center justify-center">Loading preview...</div>;
  if (error) return <div className="bg-red-50 text-red-600 h-96 rounded flex items-center justify-center border border-red-200">{error}</div>;
  if (!url) return null;

  return (
    <div className="border rounded bg-gray-50 h-96 overflow-hidden">
      <iframe src={url} className="w-full h-full" title="Document Preview" />
    </div>
  );
}
