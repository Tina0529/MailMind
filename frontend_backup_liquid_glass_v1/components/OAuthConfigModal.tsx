"use client";

import { useState, useEffect, useCallback } from "react";
import { api } from "@/lib/api";

interface OAuthConfigModalProps {
  onClose: () => void;
  onSave: () => void;
}

export default function OAuthConfigModal({ onClose, onSave }: OAuthConfigModalProps) {
  const [step, setStep] = useState<"authorize" | "callback">("authorize");
  const [authUrl, setAuthUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState(false);
  const [userEmail, setUserEmail] = useState("");
  const [checking, setChecking] = useState(false);

  // Load auth URL on mount
  useEffect(() => {
    loadAuthUrl();
  }, []);

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

  // 稳定的状态检查函数
  const checkOAuthStatus = useCallback(async () => {
    setChecking(true);
    try {
      const status = await api.getOAuthStatus();
      console.log("OAuth status check:", status);
      if (status.connected) {
        setSuccess(true);
        setUserEmail(status.user_email || "");
        // 立即调用 onSave 确保父组件状态更新
        onSave();
        setTimeout(() => {
          onClose();
        }, 1500);
        return true;
      }
      return false;
    } catch (err) {
      console.error("OAuth status check failed:", err);
      return false;
    } finally {
      setChecking(false);
    }
  }, [onSave, onClose]);

  // Handle OAuth callback from URL and popup messages
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const code = params.get("code");

    if (code && step === "authorize") {
      handleCallback(code);
    }

    // Listen for messages from popup window
    const handleMessage = (event: MessageEvent) => {
      if (event.origin !== window.location.origin) return;

      if (event.data.type === "oauth_success") {
        setSuccess(true);
        setUserEmail(event.data.data.user_email);
        onSave();
        setTimeout(() => {
          onClose();
        }, 1500);
      } else if (event.data.type === "oauth_error") {
        setError(event.data.error || "Authentication failed");
        setStep("authorize");
      }
    };

    window.addEventListener("message", handleMessage);
    return () => window.removeEventListener("message", handleMessage);
  }, [step, onSave, onClose]);

  const handleAuthorize = () => {
    setError(""); // 清除之前的错误
    
    // Open Zoho OAuth in popup
    const width = 600;
    const height = 700;
    const left = (window.screen.width - width) / 2;
    const top = (window.screen.height - height) / 2;

    const popup = window.open(
      authUrl,
      "zoho-oauth",
      `width=${width},height=${height},left=${left},top=${top}`
    );

    // Poll for popup close
    const checkPopup = setInterval(() => {
      if (popup?.closed) {
        clearInterval(checkPopup);
        // Check if we got the token
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

      // Clean URL
      window.history.replaceState({}, "", window.location.pathname);

      onSave();
      setTimeout(() => {
        onClose();
      }, 2000);
    } catch (err: any) {
      setError(err.message || "OAuth callback failed");
      setStep("authorize");
    } finally {
      setLoading(false);
    }
  };

  const handleCheckStatus = async () => {
    await checkOAuthStatus();
  };

  return (
    <div className="fixed inset-0 bg-black/40 backdrop-blur-sm flex items-center justify-center z-50 animate-fadeInUp">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md mx-4 overflow-hidden border border-gray-200/50">
        {/* Header */}
        <div className="relative overflow-hidden">
          <div className="absolute inset-0 bg-gradient-to-r from-indigo-500 via-purple-500 to-pink-500"></div>
          <div className="absolute inset-0 bg-[url('data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNjAiIGhlaWdodD0iNjAiIHZpZXdCb3g9IjAgMCA2MCA2MCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48ZyBmaWxsPSJub25lIiBmaWxsLXJ1bGU9ImV2ZW5vZGQiPjxnIGZpbGw9IiNmZmYiIGZpbGwtb3BhY2l0eT0iMC4xIj48Y2lyY2xlIGN4PSIzMCIgY3k9IjMwIiByPSIyIi8+PC9nPjwvZz48L3N2Zz4=')] opacity-30"></div>
          <div className="relative px-6 py-5">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 bg-white/20 backdrop-blur rounded-xl flex items-center justify-center">
                  <span className="text-white text-xl">🔗</span>
                </div>
                <div>
                  <h2 className="text-xl font-semibold text-white">Connect Zoho Mail</h2>
                  <p className="text-white/70 text-sm">Secure OAuth 2.0 authentication</p>
                </div>
              </div>
              <button
                onClick={onClose}
                className="w-8 h-8 rounded-lg bg-white/10 hover:bg-white/20 flex items-center justify-center text-white/80 hover:text-white transition-all"
              >
                ✕
              </button>
            </div>
          </div>
        </div>

        {/* Progress Steps */}
        <div className="px-6 py-4 bg-gray-50/50 border-b border-gray-100">
          <div className="flex items-center justify-center gap-3">
            <div className={`flex items-center gap-2 ${step === "authorize" && !success ? "text-indigo-600" : success ? "text-emerald-600" : "text-gray-400"}`}>
              <div className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-semibold transition-all ${
                success ? "bg-emerald-500 text-white" : step === "authorize" ? "bg-indigo-500 text-white" : "bg-gray-200"
              }`}>
                {success ? "✓" : "1"}
              </div>
              <span className="text-sm font-medium">Authorize</span>
            </div>
            <div className={`w-12 h-0.5 rounded transition-all ${success ? "bg-emerald-500" : "bg-gray-200"}`}></div>
            <div className={`flex items-center gap-2 ${success ? "text-emerald-600" : "text-gray-400"}`}>
              <div className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-semibold transition-all ${
                success ? "bg-emerald-500 text-white" : "bg-gray-200"
              }`}>
                {success ? "✓" : "2"}
              </div>
              <span className="text-sm font-medium">Connected</span>
            </div>
          </div>
        </div>

        {/* Form */}
        <div className="p-6">
          {success ? (
            <div className="text-center py-4 animate-fadeInUp">
              <div className="w-16 h-16 mx-auto mb-4 rounded-2xl bg-gradient-to-br from-emerald-400 to-teal-500 flex items-center justify-center shadow-lg shadow-emerald-500/30">
                <span className="text-white text-3xl">✓</span>
              </div>
              <h3 className="text-lg font-semibold text-gray-900 mb-1">Successfully Connected!</h3>
              <p className="text-sm text-emerald-600 font-medium">{userEmail}</p>
              <p className="text-xs text-gray-400 mt-3">Redirecting...</p>
            </div>
          ) : step === "callback" ? (
            <div className="text-center py-8">
              <div className="relative w-14 h-14 mx-auto mb-4">
                <div className="absolute inset-0 rounded-full bg-gradient-to-r from-indigo-500 to-purple-500 animate-spin" style={{ clipPath: 'polygon(50% 0%, 100% 0%, 100% 100%, 50% 100%)' }}></div>
                <div className="absolute inset-1 rounded-full bg-white"></div>
                <div className="absolute inset-3 rounded-full bg-gradient-to-r from-indigo-500 to-purple-500 animate-pulse"></div>
              </div>
              <p className="text-gray-600 font-medium">Completing authentication...</p>
            </div>
          ) : (
            <div className="space-y-5">
              <div className="bg-gradient-to-br from-indigo-50 to-purple-50 border border-indigo-100 rounded-xl p-5 text-center">
                <div className="w-14 h-14 mx-auto mb-3 rounded-2xl bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center shadow-lg shadow-indigo-500/30">
                  <span className="text-white text-2xl">🔐</span>
                </div>
                <h3 className="font-semibold text-gray-900 mb-2">Authorize Email Assistant</h3>
                <p className="text-sm text-gray-600">
                  Click the button below to open Zoho's authorization page.
                  You'll be asked to grant permission to access your emails.
                </p>
              </div>

              {error && (
                <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-xl text-sm flex items-center gap-3">
                  <div className="w-8 h-8 rounded-lg bg-red-100 flex items-center justify-center flex-shrink-0">
                    <span>⚠️</span>
                  </div>
                  <p>{error}</p>
                </div>
              )}

              <div className="text-center">
                <button
                  onClick={handleAuthorize}
                  disabled={loading || !authUrl}
                  className="btn-gradient px-8 py-3 rounded-xl font-medium flex items-center gap-2 mx-auto disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <span>🔑</span>
                  {loading ? "Loading..." : "Open Zoho Authorization"}
                </button>
                <p className="text-xs text-gray-400 mt-3">
                  A popup window will open. Please allow popups for this site.
                </p>
              </div>

              <div className="flex gap-3 pt-2">
                <button
                  onClick={onClose}
                  className="flex-1 px-4 py-2.5 bg-gray-100 text-gray-700 rounded-xl hover:bg-gray-200 transition-colors font-medium"
                >
                  Cancel
                </button>
                <button
                  onClick={handleCheckStatus}
                  disabled={checking}
                  className="flex-1 px-4 py-2.5 bg-white border border-gray-200 text-gray-700 rounded-xl hover:bg-gray-50 hover:border-gray-300 transition-all font-medium disabled:opacity-50"
                >
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
