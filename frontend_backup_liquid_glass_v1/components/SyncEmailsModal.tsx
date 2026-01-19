"use client";

import { useState } from "react";

interface SyncEmailsModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSync: (options: SyncOptions) => Promise<void>;
  onClear?: () => Promise<void>;
  isSyncing: boolean;
  isClearing?: boolean;
}

export interface SyncOptions {
  syncRange: "today" | "3days" | "7days" | "30days" | "custom" | "all";
  fromDate?: string;
  toDate?: string;
  count?: number;
}

const SYNC_RANGE_OPTIONS = [
  { value: "today", label: "今日邮件", description: "同步今天收到的邮件" },
  { value: "3days", label: "最近 3 天", description: "同步最近 3 天的邮件" },
  { value: "7days", label: "最近 7 天", description: "同步最近一周的邮件" },
  { value: "30days", label: "最近 30 天", description: "同步最近一个月的邮件" },
  { value: "custom", label: "自定义范围", description: "选择指定的日期范围" },
  { value: "all", label: "全部邮件", description: "同步所有邮件（可能较慢）" },
] as const;

export default function SyncEmailsModal({
  isOpen,
  onClose,
  onSync,
  onClear,
  isSyncing,
  isClearing = false,
}: SyncEmailsModalProps) {
  const [selectedRange, setSelectedRange] = useState<SyncOptions["syncRange"]>("3days");
  const [fromDate, setFromDate] = useState("");
  const [toDate, setToDate] = useState("");

  // 设置默认日期（自定义范围时）
  const today = new Date().toISOString().split("T")[0];
  const weekAgo = new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString().split("T")[0];

  const handleSync = async () => {
    const options: SyncOptions = {
      syncRange: selectedRange,
    };

    if (selectedRange === "custom") {
      options.fromDate = fromDate || weekAgo;
      options.toDate = toDate || today;
    }

    await onSync(options);
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/30 backdrop-blur-xl"
        onClick={onClose}
      />

      {/* Modal */}
      <div className="relative liquid-glass rounded-2xl shadow-2xl w-full max-w-md mx-4 overflow-hidden border border-white/40">
        {/* Header */}
        <div className="bg-gradient-to-r from-indigo-500 to-purple-500 px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-white/20 rounded-xl flex items-center justify-center">
                <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                </svg>
              </div>
              <div>
                <h2 className="text-lg font-semibold text-white">同步邮件</h2>
                <p className="text-white/80 text-sm">选择要同步的邮件范围</p>
              </div>
            </div>
            <button
              onClick={onClose}
              className="text-white/80 hover:text-white transition-colors"
              disabled={isSyncing}
            >
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="px-6 py-5">
          {/* Sync Range Options */}
          <div className="space-y-2">
            {SYNC_RANGE_OPTIONS.map((option) => (
              <label
                key={option.value}
                className={`flex items-center gap-3 p-3 rounded-xl cursor-pointer transition-all ${
                  selectedRange === option.value
                    ? "bg-gradient-to-r from-indigo-50 to-purple-50 border-2 border-indigo-300"
                    : "bg-gray-50 border-2 border-transparent hover:bg-gray-100"
                }`}
              >
                <input
                  type="radio"
                  name="syncRange"
                  value={option.value}
                  checked={selectedRange === option.value}
                  onChange={(e) => setSelectedRange(e.target.value as SyncOptions["syncRange"])}
                  className="w-4 h-4 text-indigo-600 focus:ring-indigo-500"
                  disabled={isSyncing}
                />
                <div className="flex-1">
                  <div className="font-medium text-gray-900">{option.label}</div>
                  <div className="text-sm text-gray-500">{option.description}</div>
                </div>
                {selectedRange === option.value && (
                  <svg className="w-5 h-5 text-indigo-500" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                  </svg>
                )}
              </label>
            ))}
          </div>

          {/* Custom Date Range */}
          {selectedRange === "custom" && (
            <div className="mt-4 p-4 bg-gray-50 rounded-xl space-y-3">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    开始日期
                  </label>
                  <input
                    type="date"
                    value={fromDate || weekAgo}
                    onChange={(e) => setFromDate(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
                    disabled={isSyncing}
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    结束日期
                  </label>
                  <input
                    type="date"
                    value={toDate || today}
                    onChange={(e) => setToDate(e.target.value)}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
                    disabled={isSyncing}
                  />
                </div>
              </div>
            </div>
          )}

          {/* Warning for "All" option */}
          {selectedRange === "all" && (
            <div className="mt-4 p-3 bg-amber-50 border border-amber-200 rounded-xl">
              <div className="flex items-start gap-2">
                <svg className="w-5 h-5 text-amber-500 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                </svg>
                <div className="text-sm text-amber-800">
                  <strong>注意：</strong>同步所有邮件可能需要较长时间，请耐心等待。
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-4 bg-gray-50 border-t border-gray-100 flex justify-between">
          {/* Clear button */}
          {onClear && (
            <button
              onClick={onClear}
              disabled={isSyncing || isClearing}
              className="px-4 py-2 text-red-600 hover:text-red-700 hover:bg-red-50 font-medium rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
            >
              {isClearing ? (
                <>
                  <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                  </svg>
                  清空中...
                </>
              ) : (
                <>
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                  </svg>
                  清空收件箱
                </>
              )}
            </button>
          )}
          
          <div className="flex gap-3 ml-auto">
            <button
              onClick={onClose}
              className="px-4 py-2 text-gray-700 hover:text-gray-900 font-medium transition-colors"
              disabled={isSyncing || isClearing}
            >
              取消
            </button>
            <button
              onClick={handleSync}
              disabled={isSyncing || isClearing}
              className="px-6 py-2 bg-gradient-to-r from-indigo-500 to-purple-500 text-white font-medium rounded-xl hover:from-indigo-600 hover:to-purple-600 transition-all shadow-md hover:shadow-lg disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
            >
              {isSyncing ? (
                <>
                  <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                  </svg>
                  同步中...
                </>
              ) : (
                <>
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                  </svg>
                  开始同步
                </>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
