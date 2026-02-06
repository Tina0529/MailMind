import { useState } from "react";
import { Email } from "@/lib/api";

interface EmailListProps {
  emails: Email[];
  selectedEmail: Email | null;
  onSelectEmail: (email: Email) => void;
  onQuickReply?: (email: Email) => void;
}

export default function EmailList({ emails, selectedEmail, onSelectEmail, onQuickReply }: EmailListProps) {
  const [generatingReply, setGeneratingReply] = useState<string | null>(null);
  
  const formatDate = (dateStr: string) => {
    // 确保正确解析 UTC 时间并转换为本地时区
    let date = new Date(dateStr);
    // 如果日期字符串不包含时区信息，假定为 UTC
    if (!dateStr.endsWith('Z') && !dateStr.includes('+') && !dateStr.includes('-', 10)) {
      date = new Date(dateStr + 'Z');
    }

    const now = new Date();
    const tokyoOptions = { timeZone: 'Asia/Tokyo' };

    // 使用东京时区获取日期部分进行比较
    const dateInTokyo = new Date(date.toLocaleString('en-US', tokyoOptions));
    const nowInTokyo = new Date(now.toLocaleString('en-US', tokyoOptions));

    const diffMs = nowInTokyo.getTime() - dateInTokyo.getTime();
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

    if (diffDays === 0) {
      return date.toLocaleTimeString('ja-JP', { hour: "2-digit", minute: "2-digit", timeZone: 'Asia/Tokyo' });
    } else if (diffDays === 1) {
      return "昨天";
    } else if (diffDays < 7) {
      return date.toLocaleDateString('ja-JP', { weekday: "short", timeZone: 'Asia/Tokyo' });
    }
    return date.toLocaleDateString('ja-JP', { month: "short", day: "numeric", timeZone: 'Asia/Tokyo' });
  };

  const handleQuickReply = async (e: React.MouseEvent, email: Email) => {
    e.stopPropagation();
    if (onQuickReply) {
      setGeneratingReply(email.id);
      try {
        await onQuickReply(email);
      } finally {
        setGeneratingReply(null);
      }
    }
  };

  // 获取发件人头像首字母
  const getInitials = (name: string, email: string) => {
    const displayName = name || email;
    return displayName.charAt(0).toUpperCase();
  };

  // 根据邮件生成一致的颜色
  const getAvatarColor = (email: string) => {
    const colors = [
      "from-indigo-400 to-indigo-600",
      "from-purple-400 to-purple-600",
      "from-pink-400 to-pink-600",
      "from-rose-400 to-rose-600",
      "from-orange-400 to-orange-600",
      "from-amber-400 to-amber-600",
      "from-emerald-400 to-emerald-600",
      "from-teal-400 to-teal-600",
      "from-cyan-400 to-cyan-600",
      "from-blue-400 to-blue-600",
    ];
    const index = email.split("").reduce((acc, char) => acc + char.charCodeAt(0), 0) % colors.length;
    return colors[index];
  };

  return (
    <div className="flex-1 overflow-y-auto">
      {emails.length === 0 ? (
        <div className="p-8 text-center">
          <div className="w-16 h-16 mx-auto mb-4 rounded-2xl bg-white/10 flex items-center justify-center">
            <svg className="w-8 h-8 text-white/40" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
            </svg>
          </div>
          <p className="text-white/60 font-medium">还没有邮件</p>
          <p className="text-sm text-white/40 mt-1">点击"同步邮件"开始</p>
        </div>
      ) : (
        <div className="p-2 space-y-1">
          {emails.map((email, index) => (
            <div
              key={email.id}
              onClick={() => onSelectEmail(email)}
              className={`group relative p-3 rounded-xl cursor-pointer transition-all duration-300 animate-fadeInUp hover-lift ${
                selectedEmail?.id === email.id
                  ? "liquid-glass-iridescent shadow-lg"
                  : "hover:bg-white/10 border border-transparent hover:border-white/20"
              }`}
              style={{ animationDelay: `${index * 50}ms` }}
            >
              <div className="flex items-start gap-3">
                {/* Avatar */}
                <div className={`w-10 h-10 rounded-full bg-gradient-to-br ${getAvatarColor(email.from_address)} flex items-center justify-center text-white font-medium text-sm shadow-sm flex-shrink-0`}>
                  {getInitials(email.from_name, email.from_address)}
                </div>
                
                {/* Content */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between mb-0.5">
                    <p className={`text-sm font-medium truncate ${selectedEmail?.id === email.id ? "text-white" : "text-white/90"}`}>
                      {email.from_name || email.from_address}
                    </p>
                    <span className="text-xs text-white/40 whitespace-nowrap ml-2">
                      {formatDate(email.received_at)}
                    </span>
                  </div>
                  
                  <p className={`text-sm truncate mb-1 ${selectedEmail?.id === email.id ? "text-white/80" : "text-white/60"}`}>
                    {email.subject || "(无主题)"}
                  </p>
                  
                  <div className="flex items-center gap-2">
                    {!email.processed && (
                      <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-apple-gradient text-white shadow-sm">
                        新
                      </span>
                    )}
                    
                    {/* Quick Reply Button */}
                    {onQuickReply && !email.processed && (
                      <button
                        onClick={(e) => handleQuickReply(e, email)}
                        disabled={generatingReply === email.id}
                        className={`opacity-0 group-hover:opacity-100 p-1.5 rounded-lg transition-all duration-200 ${
                          generatingReply === email.id
                            ? "bg-white/10 text-white/40"
                            : "bg-white/10 text-[#007AFF] hover:bg-white/20 hover:scale-105"
                        }`}
                        title="生成 AI 回复"
                      >
                        {generatingReply === email.id ? (
                          <div className="animate-spin rounded-full h-3.5 w-3.5 border-2 border-indigo-400/30 border-t-indigo-400"></div>
                        ) : (
                          <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 10h10a8 8 0 018 8v2M3 10l6 6m-6-6l6-6" />
                          </svg>
                        )}
                      </button>
                    )}
                  </div>
                </div>
              </div>
              
              {/* Selection indicator */}
              {selectedEmail?.id === email.id && (
                <div className="absolute left-0 top-1/2 -translate-y-1/2 w-1 h-8 bg-gradient-to-b from-indigo-500 to-purple-500 rounded-r-full"></div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
