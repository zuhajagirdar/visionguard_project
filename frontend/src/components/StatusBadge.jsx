import React from 'react';
import clsx from 'clsx';

/**
 * Mapping of backend status values to CSS classes defined in theme.css.
 */
const statusClassMap = {
  Draft: 'status-draft',
  Submitted: 'status-submitted',
  Processing: 'status-processing',
  "Under Review": 'status-under-review',
  Approved: 'status-approved',
  Rejected: 'status-rejected',
  "More Information Required": 'status-more-info',
  Withdrawn: 'status-withdrawn',
};

export const StatusBadge = ({ status }) => {
  const className = clsx('status-badge', statusClassMap[status] || 'bg-gray-200 text-gray-800');
  return <span className={className}>{status}</span>;
};
export default StatusBadge;
