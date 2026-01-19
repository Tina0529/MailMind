import { useState } from "react";

interface ReplyEditorProps {
  aiReply: string;
  replyId: string;
  onGenerate: () => void;
  onSend: (content: string) => void;
}

export default function ReplyEditor({ aiReply, replyId, onGenerate, onSend }: ReplyEditorProps) {
  const [editedReply, setEditedReply] = useState("");
  const [sending, setSending] = useState(false);
  const [generating, setGenerating] = useState(false);

  const displayReply = editedReply || aiReply;

  const handleGenerate = async () => {
    setGenerating(true);
    try {
      await onGenerate();
    } finally {
      setGenerating(false);
    }
  };

  const handleSend = async () => {
    setSending(true);
    try {
      await onSend(displayReply);
    } finally {
      setSending(false);
    }
  };

  return (
    <div className="border-t border-gray-200/50 bg-gradient-to-b from-gray-50/50 to-gray-100/50 p-5">
      {/* Header */}
      <div className="mb-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-indigo-500 to-purple-500 flex items-center justify-center shadow-md">
            <span className="text-white text-sm">🤖</span>
          </div>
          <div>
            <h3 className="text-sm font-semibold text-gray-900">AI Reply Assistant</h3>
            {aiReply && (
              <span className="text-xs text-emerald-600 font-medium flex items-center gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
                Draft generated
              </span>
            )}
          </div>
        </div>
        
        {!aiReply && (
          <button
            onClick={handleGenerate}
            disabled={generating}
            className="btn-gradient px-4 py-2 rounded-xl text-sm font-medium flex items-center gap-2"
          >
            {generating ? (
              <>
                <div className="animate-spin rounded-full h-4 w-4 border-2 border-white/30 border-t-white"></div>
                Generating...
              </>
            ) : (
              <>
                <span>✨</span>
                Generate Reply
              </>
            )}
          </button>
        )}
      </div>

      {/* Editor */}
      {aiReply && (
        <div className="space-y-4 animate-fadeInUp">
          <div className="relative">
            <textarea
              value={displayReply}
              onChange={(e) => setEditedReply(e.target.value)}
              className="w-full h-44 p-4 bg-white border border-gray-200 rounded-xl focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-400 resize-none text-sm text-gray-700 leading-relaxed transition-all duration-200 shadow-sm"
              placeholder="AI generated reply will appear here..."
            />
            {editedReply && (
              <div className="absolute top-3 right-3 px-2 py-1 bg-amber-100 text-amber-700 text-xs font-medium rounded-md">
                Edited
              </div>
            )}
          </div>
          
          {/* Actions */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 text-xs text-gray-400">
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <span>Review the content before sending</span>
            </div>
            
            <div className="flex items-center gap-3">
              <button
                onClick={handleGenerate}
                disabled={generating}
                className="px-4 py-2.5 bg-white border border-gray-200 text-gray-700 text-sm font-medium rounded-xl hover:bg-gray-50 hover:border-gray-300 transition-all duration-200 flex items-center gap-2"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                </svg>
                Regenerate
              </button>
              
              <button
                onClick={handleSend}
                disabled={sending}
                className="btn-gradient-success px-5 py-2.5 rounded-xl text-sm font-medium flex items-center gap-2 text-white"
              >
                {sending ? (
                  <>
                    <div className="animate-spin rounded-full h-4 w-4 border-2 border-white/30 border-t-white"></div>
                    Sending...
                  </>
                ) : (
                  <>
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
                    </svg>
                    Send Reply
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      )}
      
      {/* Empty State */}
      {!aiReply && (
        <div className="text-center py-8 bg-white/50 rounded-xl border border-dashed border-gray-200">
          <div className="w-12 h-12 mx-auto mb-3 rounded-xl bg-gradient-to-br from-gray-100 to-gray-200 flex items-center justify-center">
            <span className="text-xl">💬</span>
          </div>
          <p className="text-sm text-gray-500">Click "Generate Reply" to create an AI-powered response</p>
        </div>
      )}
    </div>
  );
}
