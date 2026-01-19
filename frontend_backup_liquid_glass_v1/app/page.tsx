"use client";

import { useEffect, useState, useCallback } from "react";
import EmailList from "@/components/EmailList";
import EmailDetail from "@/components/EmailDetail";
import ReplyEditor from "@/components/ReplyEditor";
import SkillLibrary from "@/components/SkillLibrary";
import OAuthConfigModal from "@/components/OAuthConfigModal";
import SyncEmailsModal from "@/components/SyncEmailsModal";
import { api } from "@/lib/api";

interface Email {
  id: string;
  zoho_id: string;
  from_address: string;
  from_name: string;
  subject: string;
  body: string;
  received_at: string;
  processed: boolean;
}

interface Skill {
  id: string;
  name: string;
  name_en: string;
  category: string;
  trigger_keywords: string[];
  usage_count: number;
}

export default function Home() {
  const [emails, setEmails] = useState<Email[]>([]);
  const [selectedEmail, setSelectedEmail] = useState<Email | null>(null);
  const [skills, setSkills] = useState<Skill[]>([]);
  const [status, setStatus] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [learning, setLearning] = useState(false);
  const [aiReply, setAiReply] = useState<string>("");
  const [replyId, setReplyId] = useState<string>("");
  const [filter, setFilter] = useState<"all" | "pending" | "processed">("all");
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

  const filteredEmails = emails.filter((email) => {
    if (filter === "pending") return !email.processed;
    if (filter === "processed") return email.processed;
    return true;
  });

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-indigo-50 via-white to-purple-50">
        <div className="text-center">
          <div className="relative w-16 h-16 mx-auto mb-6">
            <div className="absolute inset-0 rounded-full bg-gradient-to-r from-indigo-500 to-purple-500 animate-spin" style={{ clipPath: 'polygon(50% 0%, 100% 0%, 100% 100%, 50% 100%)' }}></div>
            <div className="absolute inset-1 rounded-full bg-white"></div>
            <div className="absolute inset-3 rounded-full bg-gradient-to-r from-indigo-500 to-purple-500 animate-pulse"></div>
          </div>
          <p className="text-gray-500 font-medium">Loading your inbox...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-white to-indigo-50/30 relative">
      {/* Dynamic Background Orbs */}
      <div className="bg-orbs">
        <div className="bg-orb bg-orb-1"></div>
        <div className="bg-orb bg-orb-2"></div>
        <div className="bg-orb bg-orb-3"></div>
      </div>

      {/* Premium Liquid Glass Header */}
      <header className="liquid-glass sticky top-0 z-40 border-b border-white/30">
        <div className="px-6 py-4">
          <div className="flex items-center justify-between">
            {/* Logo & Brand */}
            <div className="flex items-center gap-4">
              <div className="relative group">
                <div className="absolute -inset-1 bg-gradient-to-r from-indigo-500 to-purple-500 rounded-xl blur opacity-30 group-hover:opacity-50 transition duration-300"></div>
                <div className="relative w-11 h-11 bg-gradient-to-br from-indigo-500 to-purple-600 rounded-xl flex items-center justify-center shadow-lg">
                  <span className="text-white text-xl">✉️</span>
                </div>
              </div>
              <div>
                <h1 className="text-xl font-semibold text-gray-900 tracking-tight">
                  Email Assistant
                  <span className="ml-2 text-xs font-medium px-2 py-0.5 bg-gradient-to-r from-indigo-500 to-purple-500 text-white rounded-full">AI</span>
                </h1>
                <div className="flex items-center gap-2 mt-0.5">
                  {oauthConnected ? (
                    <>
                      <span className="relative flex h-2 w-2">
                        <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                        <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
                      </span>
                      <span className="text-sm text-emerald-600 font-medium">Connected • {oauthEmail}</span>
                    </>
                  ) : (
                    <>
                      <span className="relative flex h-2 w-2">
                        <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-amber-400 opacity-75"></span>
                        <span className="relative inline-flex rounded-full h-2 w-2 bg-amber-500"></span>
                      </span>
                      <span className="text-sm text-amber-600 font-medium">Not connected</span>
                    </>
                  )}
                </div>
              </div>
            </div>

            {/* Action Buttons */}
            <div className="flex items-center gap-3">
              <button
                onClick={() => setShowConfigModal(true)}
                className={`px-4 py-2.5 rounded-xl font-medium transition-all duration-300 flex items-center gap-2 ${
                  oauthConnected
                    ? "bg-white/80 hover:bg-white text-gray-700 border border-gray-200 hover:border-gray-300 shadow-sm"
                    : "btn-gradient text-white"
                }`}
              >
                <span>{oauthConnected ? "⚙️" : "🔗"}</span>
                {oauthConnected ? "Settings" : "Connect Zoho"}
              </button>
              
              <button
                onClick={handleSync}
                disabled={syncing || !oauthConnected}
                className={`px-5 py-2.5 rounded-xl font-medium transition-all duration-300 flex items-center gap-2 ${
                  oauthConnected
                    ? "btn-liquid-primary"
                    : "bg-gray-100 text-gray-400 cursor-not-allowed"
                }`}
              >
                {syncing ? (
                  <>
                    <div className="animate-spin rounded-full h-4 w-4 border-2 border-white/30 border-t-white"></div>
                    Syncing...
                  </>
                ) : (
                  <>
                    <span>📬</span>
                    Sync Emails
                  </>
                )}
              </button>
              
              <button
                onClick={handleSyncAndLearn}
                disabled={syncing || learning || !oauthConnected}
                className={`px-5 py-2.5 rounded-xl font-medium transition-all duration-300 flex items-center gap-2 ${
                  oauthConnected
                    ? "btn-liquid-purple"
                    : "bg-gray-100 text-gray-400 cursor-not-allowed"
                }`}
              >
                {syncing || learning ? (
                  <>
                    <div className="animate-spin rounded-full h-4 w-4 border-2 border-white/30 border-t-white"></div>
                    Analyzing...
                  </>
                ) : (
                  <>
                    <span>🧠</span>
                    Sync & Learn
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
        <div className="w-80 liquid-glass-panel border-r border-white/30 flex flex-col">
          {/* Filter Tabs */}
          <div className="p-4 border-b border-gray-200/50">
            <div className="flex gap-1 p-1 bg-gray-100/80 rounded-xl">
              {[
                { key: "all", label: "All", count: emails.length },
                { key: "pending", label: "Pending", count: emails.filter((e) => !e.processed).length },
                { key: "processed", label: "Done", count: emails.filter((e) => e.processed).length },
              ].map((tab) => (
                <button
                  key={tab.key}
                  onClick={() => setFilter(tab.key as any)}
                  className={`flex-1 px-3 py-2 rounded-lg text-sm font-medium transition-all duration-200 ${
                    filter === tab.key
                      ? "bg-white text-gray-900 shadow-sm"
                      : "text-gray-600 hover:text-gray-900"
                  }`}
                >
                  {tab.label}
                  <span className={`ml-1.5 text-xs ${filter === tab.key ? "text-indigo-600" : "text-gray-400"}`}>
                    {tab.count}
                  </span>
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
        <div className="flex-1 flex flex-col liquid-glass-card border-0">
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
                <div className="w-20 h-20 mx-auto mb-4 rounded-2xl bg-gradient-to-br from-indigo-100 to-purple-100 flex items-center justify-center">
                  <span className="text-4xl">📭</span>
                </div>
                <h3 className="text-lg font-medium text-gray-700 mb-1">No email selected</h3>
                <p className="text-sm text-gray-400">Choose an email from the list to view details</p>
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
