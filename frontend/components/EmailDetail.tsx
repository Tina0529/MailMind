import { Email } from "@/lib/api";

interface EmailDetailProps {
  email: Email;
}

export default function EmailDetail({ email }: EmailDetailProps) {
  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleString([], {
      weekday: "short",
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  // 获取发件人头像首字母
  const getInitials = (name: string, email: string) => {
    const displayName = name || email;
    return displayName.charAt(0).toUpperCase();
  };

  // 根据邮件生成一致的颜色
  const getAvatarColor = (emailAddr: string) => {
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
    const index = emailAddr.split("").reduce((acc, char) => acc + char.charCodeAt(0), 0) % colors.length;
    return colors[index];
  };

  // 格式化收件人/抄送人显示
  const formatRecipients = (addresses: string[]) => {
    if (!addresses || addresses.length === 0) return null;
    if (addresses.length <= 2) {
      return addresses.join(", ");
    }
    return `${addresses.slice(0, 2).join(", ")} 等 ${addresses.length} 人`;
  };

  return (
    <div className="flex-1 overflow-y-auto">
      {/* Email Header */}
      <div className="p-6 border-b border-white/10">
        <h2 className="text-xl font-semibold text-white mb-4 leading-tight">
          {email.subject || "(无主题)"}
        </h2>
        
        <div className="flex items-start gap-4">
          {/* Avatar */}
          <div className={`w-12 h-12 rounded-full bg-gradient-to-br ${getAvatarColor(email.from_address)} flex items-center justify-center text-white font-semibold text-lg shadow-md flex-shrink-0`}>
            {getInitials(email.from_name, email.from_address)}
          </div>
          
          {/* Sender Info */}
          <div className="flex-1 min-w-0">
            {/* From */}
            <div className="flex items-center gap-2 mb-1">
              <span className="font-medium text-white">
                {email.from_name || email.from_address}
              </span>
              {email.from_name && (
                <span className="text-sm text-white/50 truncate">
                  &lt;{email.from_address}&gt;
                </span>
              )}
            </div>
            
            {/* Date and Status */}
            <div className="flex items-center gap-3 text-sm text-white/50 mb-2">
              <span className="flex items-center gap-1">
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                {formatDate(email.received_at)}
              </span>
              {!email.processed && (
                <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-[#FF9500] text-white shadow-sm">
                  待回复
                </span>
              )}
              {email.processed && (
                <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-[#34C759] text-white shadow-sm">
                  已回复
                </span>
              )}
            </div>
            
            {/* To and CC - 收件人和抄送人信息 */}
            <div className="text-sm text-white/50 space-y-1">
              {/* To Recipients */}
              {email.to_addresses && email.to_addresses.length > 0 && (
                <div className="flex items-start gap-2">
                  <span className="text-white/40 font-medium min-w-[3rem]">收件人:</span>
                  <span className="text-white/60 truncate flex-1">
                    {formatRecipients(email.to_addresses)}
                  </span>
                </div>
              )}
              
              {/* CC Recipients */}
              {email.cc_addresses && email.cc_addresses.length > 0 && (
                <div className="flex items-start gap-2">
                  <span className="text-white/40 font-medium min-w-[3rem]">抄  送:</span>
                  <span className="text-white/60 truncate flex-1">
                    {formatRecipients(email.cc_addresses)}
                  </span>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Email Body */}
      <div className="p-6">
        <div className="prose prose-sm max-w-none prose-invert">
          <div className="whitespace-pre-wrap text-white/80 leading-relaxed liquid-glass-card rounded-xl p-5">
            {email.body}
          </div>
        </div>
      </div>
    </div>
  );
}

