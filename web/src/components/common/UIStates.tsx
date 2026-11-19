import React from 'react';
import { Loader2, AlertCircle, Inbox } from 'lucide-react';

export const LoadingState: React.FC<{ message?: string }> = ({ message = 'Loading details...' }) => (
  <div className="flex flex-col items-center justify-center p-12 text-center">
    <Loader2 className="w-8 h-8 animate-spin text-saffron mb-3" />
    <p className="text-slate-600 text-sm font-medium">{message}</p>
  </div>
);

export const EmptyState: React.FC<{
  title: string;
  description: string;
  actionText?: string;
  onAction?: () => void;
  icon?: React.ReactNode;
}> = ({ title, description, actionText, onAction, icon }) => (
  <div className="flex flex-col items-center justify-center p-8 bg-white border border-slate-200 rounded-card shadow-soft text-center my-4">
    <div className="w-12 h-12 bg-slate-100 rounded-full flex items-center justify-center text-slate-500 mb-3">
      {icon || <Inbox className="w-6 h-6" />}
    </div>
    <h3 className="text-base font-semibold text-slate-900 mb-1">{title}</h3>
    <p className="text-sm text-slate-500 max-w-sm mb-4">{description}</p>
    {actionText && onAction && (
      <button
        onClick={onAction}
        className="px-4 py-2 bg-saffron text-white rounded-lg text-sm font-medium hover:bg-saffron-600 transition min-h-[44px]"
      >
        {actionText}
      </button>
    )}
  </div>
);

export const ErrorState: React.FC<{
  title?: string;
  message?: string;
  onRetry?: () => void;
}> = ({ title = 'Something went wrong', message = 'Unable to fetch data from the server. Please check your network.', onRetry }) => (
  <div className="flex flex-col items-center justify-center p-8 bg-red-50 border border-red-200 rounded-card text-center my-4">
    <AlertCircle className="w-8 h-8 text-danger mb-2" />
    <h3 className="text-base font-semibold text-red-900 mb-1">{title}</h3>
    <p className="text-sm text-red-700 max-w-sm mb-4">{message}</p>
    {onRetry && (
      <button
        onClick={onRetry}
        className="px-4 py-2 bg-red-600 text-white rounded-lg text-sm font-medium hover:bg-red-700 transition min-h-[44px]"
      >
        Retry
      </button>
    )}
  </div>
);
