"use client";

import { useEffect, useState, useCallback } from "react";
import EmailList from "@/components/EmailList";
import EmailDetail from "@/components/EmailDetail";
import ReplyEditor from "@/components/ReplyEditor";
import SkillLibrary from "@/components/SkillLibrary";
import OAuthConfigModal from "@/components/OAuthConfigModal";
import SyncEmailsModal from "@/components/SyncEmailsModal";
import LanguageSwitch from "@/components/LanguageSwitch";
import { useLanguage } from "@/lib/LanguageContext";
import { api, Email, Skill } from "@/lib/api";

export default function Home() {
  const { t } = useLanguage();
  const [emails, setEmails] = useState<Email[]>([]);
  const [selectedEmail, setSelectedEmail] = useState<Email | null>(null);
  const [skills, setSkills] = useState<Skill[]>([]);
  const [status, setStatus] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [learning, setLearning] = useState(false);
  const [aiReply, setAiReply] = useState<string>("");
  const [replyId, setReplyId] = useState<string>("");
  const [filter, setFilter] = useState<"all" | "pending" | "processed" | "priority">("all");
  const [priorityCount, setPriorityCount] = useState(0);
  const [analyzing, setAnalyzing] = useState(false);
  const [showConfigModal, setShowConfigModal] = useState(false);
  const [oauthConnected, setOAuthConnected] = useState(false);
  const [oauthEmail, setOAuthEmail] = useState<string>("");

  // 检查 OAuth 状态
  const checkOAuthStatus = useCallback(async () => {
    try {
      const oauthStatus = await api.getOAuthStatus();
      setOAuthConnected(oauthStatus.connected);
      setOAuthEmail(oauthStatus.user_email || "");
      console.log("OAuth Status:", oauthStatus.connected ? "✅ Connected" : "❌ Not connected");
      return oauthStatus.connected;
    } catch {
      setOAuthConnected(false);
      return false;
    }
  }, []);

  useEffect(() => {
    loadInitialData();
  }, []);

  const loadInitialData = async () => {
    try {
      // Check OAuth status first
      await checkOAuthStatus();

      // Load status
      const statusData = await api.getStatus();
      setStatus(statusData);

      // Load emails
      const emailsData = await api.getEmails();
      setEmails(emailsData.emails);

      // Load skills
      const skillsData = await api.getSkills();
      setSkills(skillsData.skills);
    } catch (error) {
      console.error("Error loading data:", error);
    } finally {
      setLoading(false);
    }
  };

  const [showSyncModal, setShowSyncModal] = useState(false);

  // ... (previous code)

  const handleSync = async (options?: any) => {
    // If called without options (event), show modal
    if (!options || options.nativeEvent) {
      setShowSyncModal(true);
      return;
    }

    setSyncing(true);
    setShowSyncModal(false);
    
    try {
      await api.syncEmails(options);
      const emailsData = await api.getEmails();
      setEmails(emailsData.emails);

      // Refresh skills after sync
      const skillsData = await api.getSkills();
      setSkills(skillsData.skills);
      
      // Show success message (optional, could be a toast)
      console.log(`Synced ${options.sync_range || 'emails'} successfully`);
    } catch (error) {
      console.error("Sync error:", error);
      alert("Failed to sync emails. Please try again.");
    } finally {
      setSyncing(false);
    }
  };

  const [clearing, setClearing] = useState(false);

  const handleClear = async () => {
    if (!confirm("确定要清空所有已同步的邮件吗？此操作不可恢复。")) {
      return;
    }
    
    setClearing(true);
    try {
      const result = await api.clearEmails();
      console.log(`Cleared ${result.deleted} emails`);
      setEmails([]);
      setSelectedEmail(null);
    } catch (error) {
      console.error("Clear error:", error);
      alert("Failed to clear emails. Please try again.");
    } finally {
      setClearing(false);
    }
  };

  const handleSyncAndLearn = async () => {
    setSyncing(true);
    setLearning(true);
    try {
      // First sync emails
      await api.syncEmails(100);
      const emailsData = await api.getEmails();
      setEmails(emailsData.emails);

      // Then trigger learning
      const learnResult = await api.learnFromEmails(100, false);

      // Refresh skills after learning starts
      setTimeout(async () => {
        const skillsData = await api.getSkills();
        setSkills(skillsData.skills);
      }, 2000);

      alert(`Learning started: ${learnResult.message}\n\nSkills will be updated in the background.`);
    } catch (error: any) {
      console.error("Sync & Learn error:", error);
      alert("Failed: " + (error.message || "Unknown error"));
    } finally {
      setSyncing(false);
      setLearning(false);
    }
  };

  const handleSelectEmail = (email: Email) => {
    setSelectedEmail(email);
    setAiReply("");
    setReplyId("");
  };

  const handleQuickReply = async (email: Email) => {
    // Select the email first
    setSelectedEmail(email);
    setAiReply("");
    setReplyId("");

    // Generate reply
    try {
      const result = await api.generateReply(email.id);
      setAiReply(result.ai_draft);
      setReplyId(result.reply_id);
    } catch (error) {
      console.error("Error generating quick reply:", error);
      alert("Failed to generate reply. Please try again.");
    }
  };

  const handleGenerateReply = async () => {
    if (!selectedEmail) return;

    try {
      const result = await api.generateReply(selectedEmail.id);
      setAiReply(result.ai_draft);
      setReplyId(result.reply_id);
    } catch (error) {
      console.error("Error generating reply:", error);
    }
  };

  const handleSendReply = async (content: string) => {
    if (!replyId) return;

    try {
      await api.sendReply(replyId, content);
      // Refresh emails
      const emailsData = await api.getEmails();
      setEmails(emailsData.emails);
      setAiReply("");
      setReplyId("");
    } catch (error) {
      console.error("Error sending reply:", error);
    }
  };

  // 修复：OAuth 配置保存后强制刷新状态（带重试）
  const handleConfigSave = useCallback(async () => {
    // 立即检查一次
    let connected = await checkOAuthStatus();
    
    // 如果第一次检查失败，等待一秒后重试
    if (!connected) {
      await new Promise(resolve => setTimeout(resolve, 1000));
      connected = await checkOAuthStatus();
    }
    
    if (connected) {
      console.log("✅ OAuth successfully connected");
    } else {
      console.log("⚠️ OAuth status check returned not connected");
    }
  }, [checkOAuthStatus]);

  const filteredEmails = emails.filter((email: any) => {
    if (filter === "pending") return !email.processed;
    if (filter === "processed") return email.processed;
    if (filter === "priority") return email.is_priority;
    return true;
  });

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[#0a0e14]">
        <div className="text-center">
          <div className="relative w-16 h-16 mx-auto mb-6">
            <div className="absolute inset-0 rounded-full bg-gradient-to-r from-[#2d91fa] to-[#5bb5ff] animate-spin" style={{ clipPath: 'polygon(50% 0%, 100% 0%, 100% 100%, 50% 100%)' }}></div>
            <div className="absolute inset-1 rounded-full bg-[#0a0e14]"></div>
            <div className="absolute inset-3 rounded-full bg-gradient-to-r from-[#2d91fa] to-[#5bb5ff] animate-pulse"></div>
          </div>
          <p className="text-[#64748b] font-medium">{t('loadingInbox')}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen relative bg-[#0a0e14]">
      {/* Header */}
      <header className="header-bar sticky top-0 z-40">
        <div className="px-6 py-4">
          <div className="flex items-center justify-between">
            {/* Logo & Brand */}
            <div className="flex items-center gap-4">
              <div className="relative group">
                <div className="absolute -inset-1 bg-gradient-to-r from-[#2d91fa] to-[#5bb5ff] rounded-xl blur opacity-30 group-hover:opacity-50 transition duration-300"></div>
                <div className="relative w-11 h-11 bg-gradient-to-r from-[#2d91fa] to-[#5bb5ff] rounded-xl flex items-center justify-center shadow-lg">
                  <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                  </svg>
                </div>
              </div>
              <div>
                <h1 className="text-xl font-semibold text-[#f8fafc] tracking-tight">
                  MailMind
                  <span className="ml-2 text-xs font-medium px-2 py-0.5 bg-gradient-to-r from-[#2d91fa] to-[#5bb5ff] text-white rounded-full">AI</span>
                </h1>
                <div className="flex items-center gap-2 mt-0.5">
                  {oauthConnected ? (
                    <>
                      <span className="relative flex h-2 w-2">
                        <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-[#22c55e] opacity-75"></span>
                        <span className="relative inline-flex rounded-full h-2 w-2 bg-[#22c55e]"></span>
                      </span>
                      <span className="text-sm text-[#4ade80] font-medium">{t('connected')} • {oauthEmail}</span>
                    </>
                  ) : (
                    <>
                      <span className="relative flex h-2 w-2">
                        <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-[#e86803] opacity-75"></span>
                        <span className="relative inline-flex rounded-full h-2 w-2 bg-[#e86803]"></span>
                      </span>
                      <span className="text-sm text-[#ff8c3a] font-medium">{t('notConnected')}</span>
                    </>
                  )}
                </div>
              </div>
            </div>

            {/* Action Buttons */}
            <div className="flex items-center gap-3">
              {/* Language Switch */}
              <LanguageSwitch />

              <button
                onClick={() => setShowConfigModal(true)}
                className={`px-4 py-2.5 rounded-xl font-medium transition-all duration-300 flex items-center gap-2 ${
                  oauthConnected
                    ? "btn-outline"
                    : "btn-primary"
                }`}
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  {oauthConnected ? (
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                  ) : (
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
                  )}
                </svg>
                {oauthConnected ? t('settings') : t('connectZoho')}
              </button>

              <button
                onClick={handleSync}
                disabled={syncing || !oauthConnected}
                className={`px-5 py-2.5 rounded-xl font-medium transition-all duration-300 flex items-center gap-2 ${
                  oauthConnected
                    ? "btn-primary"
                    : "bg-gray-100 text-gray-400 cursor-not-allowed"
                }`}
              >
                {syncing ? (
                  <>
                    <div className="animate-spin rounded-full h-4 w-4 border-2 border-white/30 border-t-white"></div>
                    {t('syncing')}
                  </>
                ) : (
                  <>
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                    </svg>
                    {t('syncEmails')}
                  </>
                )}
              </button>

              <button
                onClick={handleSyncAndLearn}
                disabled={syncing || learning || !oauthConnected}
                className={`px-5 py-2.5 rounded-xl font-medium transition-all duration-300 flex items-center gap-2 ${
                  oauthConnected
                    ? "btn-accent"
                    : "bg-gray-100 text-gray-400 cursor-not-allowed"
                }`}
              >
                {syncing || learning ? (
                  <>
                    <div className="animate-spin rounded-full h-4 w-4 border-2 border-white/30 border-t-white"></div>
                    {t('analyzing')}
                  </>
                ) : (
                  <>
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                    </svg>
                    {t('syncAndLearn')}
                  </>
                )}
              </button>

              <button
                onClick={async () => {
                  setAnalyzing(true);
                  try {
                    await api.analyzePriority(100);
                    let attempts = 0;
                    const maxAttempts = 10;
                    const pollInterval = setInterval(async () => {
                      attempts++;
                      const emailsData = await api.getEmails(undefined, 500);
                      setEmails(emailsData.emails);
                      setPriorityCount(emailsData.priority || 0);

                      if ((emailsData.priority || 0) > 0 || attempts >= maxAttempts) {
                        clearInterval(pollInterval);
                        setAnalyzing(false);
                      }
                    }, 3000);
                  } catch (error) {
                    console.error("Failed to analyze priority:", error);
                    setAnalyzing(false);
                  }
                }}
                disabled={analyzing || emails.length === 0}
                className={`px-5 py-2.5 rounded-xl font-medium transition-all duration-300 flex items-center gap-2 ${
                  emails.length > 0
                    ? "btn-highlight"
                    : "bg-gray-100 text-gray-400 cursor-not-allowed"
                }`}
              >
                {analyzing ? (
                  <>
                    <div className="animate-spin rounded-full h-4 w-4 border-2 border-[#2f2d31]/30 border-t-[#2f2d31]"></div>
                    {t('analyzing')}
                  </>
                ) : (
                  <>
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                    </svg>
                    {t('analyzePriority')}
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <div className="flex h-[calc(100vh-81px)]">
        {/* Email List Sidebar */}
        <div className="w-80 sidebar-dark flex flex-col">
          {/* Filter Tabs */}
          <div className="p-4 border-b border-white/10">
            <div className="filter-tabs">
              {[
                { key: "all", label: t('all'), count: emails.length },
                { key: "pending", label: t('pending'), count: emails.filter((e: any) => !e.processed).length },
                { key: "processed", label: t('processed'), count: emails.filter((e: any) => e.processed).length },
                { key: "priority", label: t('priority'), count: emails.filter((e: any) => e.is_priority).length, isPriority: true },
              ].map((tab) => (
                <button
                  key={tab.key}
                  onClick={() => setFilter(tab.key as any)}
                  className={`filter-tab ${filter === tab.key ? 'active' : ''} ${tab.isPriority ? 'priority' : ''}`}
                >
                  {tab.isPriority && <svg className="w-3 h-3 inline mr-1" fill="currentColor" viewBox="0 0 20 20"><path fillRule="evenodd" d="M12.395 2.553a1 1 0 00-1.45-.385c-.345.23-.614.558-.822.88-.214.33-.403.713-.57 1.116-.334.804-.614 1.768-.84 2.734a31.365 31.365 0 00-.613 3.58 2.64 2.64 0 01-.945-1.067c-.328-.68-.398-1.534-.398-2.654A1 1 0 005.05 6.05 6.981 6.981 0 003 11a7 7 0 1011.95-4.95c-.592-.591-.98-.985-1.348-1.467-.363-.476-.724-1.063-1.207-2.03zM12.12 15.12A3 3 0 017 13s.879.5 2.5.5c0-1 .5-4 1.25-4.5.5 1 .786 1.293 1.371 1.879A2.99 2.99 0 0113 13a2.99 2.99 0 01-.879 2.121z" clipRule="evenodd" /></svg>}
                  {tab.label}
                  <span className="ml-1.5 text-xs opacity-70">{tab.count}</span>
                </button>
              ))}
            </div>
          </div>
          
          <EmailList
            emails={filteredEmails}
            selectedEmail={selectedEmail}
            onSelectEmail={handleSelectEmail}
            onQuickReply={handleQuickReply}
          />
        </div>

        {/* Email Detail */}
        <div className="flex-1 flex flex-col bg-[#0a0e14]">
          {selectedEmail ? (
            <>
              <EmailDetail email={selectedEmail} />
              <ReplyEditor
                aiReply={aiReply}
                replyId={replyId}
                onGenerate={handleGenerateReply}
                onSend={handleSendReply}
              />
            </>
          ) : (
            <div className="flex-1 flex items-center justify-center">
              <div className="text-center animate-fadeInUp">
                <div className="w-20 h-20 mx-auto mb-4 rounded-2xl bg-[#1a2230] flex items-center justify-center">
                  <svg className="w-10 h-10 text-[#64748b]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                  </svg>
                </div>
                <h3 className="text-lg font-medium text-[#f8fafc] mb-1">{t('noEmailSelected')}</h3>
                <p className="text-sm text-[#64748b]">{t('selectEmailHint')}</p>
              </div>
            </div>
          )}
        </div>

        {/* Skills Panel */}
        <SkillLibrary skills={skills} />
      </div>

      {/* Config Modal */}
      {showConfigModal && (
        <OAuthConfigModal
          onClose={() => setShowConfigModal(false)}
          onSave={handleConfigSave}
        />
      )}

      {/* Sync Modal */}
      <SyncEmailsModal
        isOpen={showSyncModal}
        onClose={() => setShowSyncModal(false)}
        onSync={handleSync}
        onClear={handleClear}
        isSyncing={syncing}
        isClearing={clearing}
      />
    </div>
  );
}
