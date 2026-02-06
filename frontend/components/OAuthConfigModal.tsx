"use client";

import { useState, useEffect, useCallback } from "react";
import { api } from "@/lib/api";

interface OAuthConfigModalProps {
  onClose: () => void;
  onSave: () => void;
}

export default function OAuthConfigModal({ onClose, onSave }: OAuthConfigModalProps) {
  const [step, setStep] = useState<"loading" | "connected" | "authorize" | "callback">("loading");
  const [authUrl, setAuthUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState(false);
  const [userEmail, setUserEmail] = useState("");
  const [checking, setChecking] = useState(false);
  const [disconnecting, setDisconnecting] = useState(false);

  // 初始化时检查连接状态
  useEffect(() => {
    checkInitialStatus();
  }, []);

  const checkInitialStatus = async () => {
    try {
      const status = await api.getOAuthStatus();
      if (status.connected) {
        setStep("connected");
        setUserEmail(status.user_email || "");
      } else {
        setStep("authorize");
        loadAuthUrl();
      }
    } catch (err) {
      setStep("authorize");
      loadAuthUrl();
    }
  };

  const loadAuthUrl = async () => {
    setLoading(true);
    setError("");
    try {
      const result = await api.getOAuthAuthUrl();
      if (result.auth_url) {
        setAuthUrl(result.auth_url);
      } else {
        setError("OAuth not configured on server. Please contact administrator.");
      }
    } catch (err: any) {
      setError(err.message || "Failed to load authorization URL");
    } finally {
      setLoading(false);
    }
  };

  const checkOAuthStatus = useCallback(async () => {
    setChecking(true);
    try {
      const status = await api.getOAuthStatus();
      if (status.connected) {
        setSuccess(true);
        setUserEmail(status.user_email || "");
        onSave();
        setTimeout(() => {
          onClose();
        }, 1500);
        return true;
      }
      return false;
    } catch (err) {
      return false;
    } finally {
      setChecking(false);
    }
  }, [onSave, onClose]);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const code = params.get("code");
    if (code && step === "authorize") {
      handleCallback(code);
    }

    const handleMessage = (event: MessageEvent) => {
      if (event.origin !== window.location.origin) return;
      if (event.data.type === "oauth_success") {
        setSuccess(true);
        setUserEmail(event.data.data.user_email);
        onSave();
        setTimeout(() => onClose(), 1500);
      } else if (event.data.type === "oauth_error") {
        setError(event.data.error || "Authentication failed");
        setStep("authorize");
      }
    };

    window.addEventListener("message", handleMessage);
    return () => window.removeEventListener("message", handleMessage);
  }, [step, onSave, onClose]);

  const handleAuthorize = () => {
    setError("");
    const width = 600, height = 700;
    const left = (window.screen.width - width) / 2;
    const top = (window.screen.height - height) / 2;
    const popup = window.open(authUrl, "zoho-oauth", `width=${width},height=${height},left=${left},top=${top}`);
    const checkPopup = setInterval(() => {
      if (popup?.closed) {
        clearInterval(checkPopup);
        checkOAuthStatus();
      }
    }, 500);
  };

  const handleCallback = async (code: string) => {
    setStep("callback");
    setLoading(true);
    try {
      const result = await api.oauthCallback(code);
      setSuccess(true);
      setUserEmail(result.user_email);
      window.history.replaceState({}, "", window.location.pathname);
      onSave();
      setTimeout(() => onClose(), 2000);
    } catch (err: any) {
      setError(err.message || "OAuth callback failed");
      setStep("authorize");
    } finally {
      setLoading(false);
    }
  };

  const handleDisconnect = async () => {
    setDisconnecting(true);
    try {
      await api.disconnectOAuth();
      onSave();
      onClose();
    } catch (err: any) {
      setError(err.message || "Failed to disconnect");
    } finally {
      setDisconnecting(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 animate-fadeInUp">
      <div className="bg-[#1a2230] rounded-2xl shadow-2xl w-full max-w-md mx-4 overflow-hidden border border-white/10">
        {/* Header */}
        <div className="relative overflow-hidden">
          <div className={`absolute inset-0 ${step === "connected" ? "bg-gradient-to-r from-emerald-500 via-teal-500 to-cyan-500" : "bg-gradient-to-r from-indigo-500 via-purple-500 to-pink-500"}`}></div>
          <div className="relative px-6 py-5">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 bg-white/20 backdrop-blur rounded-xl flex items-center justify-center">
                  <span className="text-white text-xl">{step === "connected" ? "✓" : "🔗"}</span>
                </div>
                <div>
                  <h2 className="text-xl font-semibold text-white">
                    {step === "connected" ? "Zoho Mail 已连接" : "Connect Zoho Mail"}
                  </h2>
                  <p className="text-white/70 text-sm">
                    {step === "connected" ? "OAuth 2.0 安全连接" : "Secure OAuth 2.0 authentication"}
                  </p>
                </div>
              </div>
              <button onClick={onClose} className="w-8 h-8 rounded-lg bg-white/10 hover:bg-white/20 flex items-center justify-center text-white/80 hover:text-white transition-all">✕</button>
            </div>
          </div>
        </div>

        {/* Content */}
        <div className="p-6">
          {step === "loading" ? (
            <div className="text-center py-8">
              <div className="relative w-14 h-14 mx-auto mb-4">
                <div className="absolute inset-0 rounded-full bg-gradient-to-r from-indigo-500 to-purple-500 animate-spin" style={{ clipPath: 'polygon(50% 0%, 100% 0%, 100% 100%, 50% 100%)' }}></div>
                <div className="absolute inset-1 rounded-full bg-[#1a2230]"></div>
              </div>
              <p className="text-[#cbd5e1]">正在检查连接状态...</p>
            </div>
          ) : step === "connected" ? (
            <div className="space-y-5">
              {/* 已连接状态 */}
              <div className="bg-gradient-to-br from-emerald-900/30 to-teal-900/30 border border-emerald-500/30 rounded-xl p-5 text-center">
                <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-gradient-to-br from-emerald-400 to-teal-500 flex items-center justify-center shadow-lg shadow-emerald-500/30">
                  <span className="text-white text-3xl">✓</span>
                </div>
                <h3 className="font-semibold text-[#f8fafc] mb-1">已成功连接</h3>
                <p className="text-sm text-emerald-400 font-medium">{userEmail}</p>
                <p className="text-xs text-[#64748b] mt-2">您的邮箱已安全连接到邮件助手</p>
              </div>

              {/* 连接信息 */}
              <div className="bg-[#111820] rounded-xl p-4 space-y-2 border border-white/10">
                <div className="flex justify-between text-sm">
                  <span className="text-[#64748b]">连接状态</span>
                  <span className="text-emerald-400 font-medium flex items-center gap-1">
                    <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
                    已连接
                  </span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-[#64748b]">授权类型</span>
                  <span className="text-[#cbd5e1]">OAuth 2.0</span>
                </div>
              </div>

              {error && (
                <div className="bg-red-900/30 border border-red-500/30 text-red-400 px-4 py-3 rounded-xl text-sm">
                  {error}
                </div>
              )}

              {/* 操作按钮 */}
              <div className="flex gap-3">
                <button
                  onClick={onClose}
                  className="flex-1 px-4 py-2.5 bg-[#111820] text-[#cbd5e1] rounded-xl hover:bg-[#222d3d] transition-colors font-medium border border-white/10"
                >
                  关闭
                </button>
                <button
                  onClick={handleDisconnect}
                  disabled={disconnecting}
                  className="flex-1 px-4 py-2.5 bg-red-900/30 text-red-400 border border-red-500/30 rounded-xl hover:bg-red-900/50 transition-colors font-medium disabled:opacity-50"
                >
                  {disconnecting ? "断开中..." : "🔌 断开连接"}
                </button>
              </div>
            </div>
          ) : success ? (
            <div className="text-center py-4 animate-fadeInUp">
              <div className="w-16 h-16 mx-auto mb-4 rounded-2xl bg-gradient-to-br from-emerald-400 to-teal-500 flex items-center justify-center shadow-lg shadow-emerald-500/30">
                <span className="text-white text-3xl">✓</span>
              </div>
              <h3 className="text-lg font-semibold text-[#f8fafc] mb-1">Successfully Connected!</h3>
              <p className="text-sm text-emerald-400 font-medium">{userEmail}</p>
              <p className="text-xs text-[#64748b] mt-3">Redirecting...</p>
            </div>
          ) : step === "callback" ? (
            <div className="text-center py-8">
              <div className="relative w-14 h-14 mx-auto mb-4">
                <div className="absolute inset-0 rounded-full bg-gradient-to-r from-indigo-500 to-purple-500 animate-spin" style={{ clipPath: 'polygon(50% 0%, 100% 0%, 100% 100%, 50% 100%)' }}></div>
                <div className="absolute inset-1 rounded-full bg-[#1a2230]"></div>
              </div>
              <p className="text-[#cbd5e1] font-medium">Completing authentication...</p>
            </div>
          ) : (
            <div className="space-y-5">
              <div className="bg-gradient-to-br from-indigo-900/30 to-purple-900/30 border border-indigo-500/30 rounded-xl p-5 text-center">
                <div className="w-14 h-14 mx-auto mb-3 rounded-2xl bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center shadow-lg shadow-indigo-500/30">
                  <span className="text-white text-2xl">🔐</span>
                </div>
                <h3 className="font-semibold text-[#f8fafc] mb-2">Authorize MailMind AI</h3>
                <p className="text-sm text-[#cbd5e1]">
                  Click the button below to open Zoho's authorization page.
                </p>
              </div>

              {error && (
                <div className="bg-red-900/30 border border-red-500/30 text-red-400 px-4 py-3 rounded-xl text-sm flex items-center gap-3">
                  <div className="w-8 h-8 rounded-lg bg-red-900/50 flex items-center justify-center flex-shrink-0">⚠️</div>
                  <p>{error}</p>
                </div>
              )}

              <div className="text-center">
                <button
                  onClick={handleAuthorize}
                  disabled={loading || !authUrl}
                  className="btn-accent px-8 py-3 rounded-xl font-medium flex items-center gap-2 mx-auto disabled:opacity-50"
                >
                  🔑 {loading ? "Loading..." : "Open Zoho Authorization"}
                </button>
                <p className="text-xs text-[#64748b] mt-3">A popup window will open.</p>
              </div>

              <div className="flex gap-3 pt-2">
                <button onClick={onClose} className="flex-1 px-4 py-2.5 bg-[#111820] text-[#cbd5e1] rounded-xl hover:bg-[#222d3d] transition-colors font-medium border border-white/10">Cancel</button>
                <button onClick={() => checkOAuthStatus()} disabled={checking} className="flex-1 px-4 py-2.5 bg-[#222d3d] border border-white/10 text-[#cbd5e1] rounded-xl hover:bg-[#2d3a4d] transition-all font-medium disabled:opacity-50">
                  {checking ? "Checking..." : "Check Status"}
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

