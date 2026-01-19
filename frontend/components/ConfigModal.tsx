"use client";

import { useState, useEffect } from "react";
import { api } from "@/lib/api";

export default function ConfigModal({ onClose, onSave }: { onClose: () => void; onSave: () => void }) {
  const [email, setEmail] = useState("");
  const [appPassword, setAppPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError("");
    setSuccess(false);

    try {
      const response = await fetch("http://localhost:8000/api/emails/config", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, app_password: appPassword }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || "Configuration failed");
      }

      setSuccess(true);
      setTimeout(() => {
        onSave();
        onClose();
      }, 1500);
    } catch (err: any) {
      setError(err.message || "Failed to configure Zoho Mail");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-md mx-4 overflow-hidden">
        {/* Header */}
        <div className="bg-gradient-to-r from-blue-500 to-blue-600 px-6 py-4">
          <div className="flex items-center justify-between">
            <h2 className="text-xl font-semibold text-white">Connect Zoho Mail</h2>
            <button
              onClick={onClose}
              className="text-white/80 hover:text-white transition-colors"
            >
              ✕
            </button>
          </div>
          <p className="text-blue-100 text-sm mt-1">
            Configure your Zoho Mail account to sync emails
          </p>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          {/* Important Notice */}
          {!success && (
            <div className="bg-amber-50 border border-amber-200 text-amber-800 px-4 py-3 rounded-lg text-sm">
              <p className="font-medium flex items-center gap-2">
                <span>⚠️</span>
                Important: Use App Password, NOT your login password
              </p>
            </div>
          )}

          {success ? (
            <div className="bg-green-50 border border-green-200 text-green-700 px-4 py-3 rounded-lg flex items-center gap-2">
              <span className="text-green-500">✓</span>
              <span>Successfully connected to Zoho Mail!</span>
            </div>
          ) : (
            <>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Zoho Email Address
                </label>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="you@zoho.com"
                  required
                  className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  disabled={loading}
                />
                <p className="text-xs text-gray-500 mt-1">
                  Your Zoho Mail email address
                </p>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  App Password <span className="text-red-500">*</span>
                </label>
                <input
                  type="password"
                  value={appPassword}
                  onChange={(e) => setAppPassword(e.target.value)}
                  placeholder="xxxx-xxxx-xxxx-xxxx"
                  required
                  className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  disabled={loading}
                />
                <p className="text-xs text-amber-600 mt-1 font-medium">
                  This is NOT your regular login password!
                </p>
              </div>

              {error && (
                <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg text-sm whitespace-pre-line">
                  <p className="font-medium mb-2">❌ Connection Failed</p>
                  <p className="text-xs">{error}</p>
                </div>
              )}

              <div className="flex gap-3 pt-2">
                <button
                  type="button"
                  onClick={onClose}
                  className="flex-1 px-4 py-2.5 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors"
                  disabled={loading}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={loading}
                  className="flex-1 px-4 py-2.5 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center justify-center gap-2"
                >
                  {loading ? (
                    <>
                      <div className="animate-spin rounded-full h-4 w-4 border-2 border-white/30 border-t-white"></div>
                      Connecting...
                    </>
                  ) : (
                    <>
                      <span>🔗</span>
                      Connect
                    </>
                  )}
                </button>
              </div>
            </>
          )}

          {/* Instructions */}
          {!success && (
            <div className="mt-4 pt-4 border-t border-gray-100">
              <details className="group">
                <summary className="text-xs font-medium text-gray-700 cursor-pointer hover:text-gray-900 flex items-center gap-1">
                  <span className="transform group-open:rotate-90 transition-transform">▶</span>
                  How to generate App Password in Zoho Mail
                </summary>
                <div className="mt-2 text-xs text-gray-600 space-y-1.5 list-decimal list-inside pl-4">
                  <p>1. Log in to Zoho Mail on web (mail.zoho.com)</p>
                  <p>2. Click your profile icon → <strong>Settings</strong></p>
                  <p>3. Go to <strong>Mail Accounts</strong> → <strong>App Passwords</strong></p>
                  <p>4. Click <strong>"Generate App Password"</strong></p>
                  <p>5. Enter a name (e.g., "MailMind AI") and save</p>
                  <p>6. Copy the <strong>16-character password</strong> (format: xxxx-xxxx-xxxx-xxxx)</p>
                  <p className="text-amber-700 mt-2 bg-amber-50 px-2 py-1.5 rounded">
                    Note: If you don't see "App Passwords" option, you may need to enable 2-Factor Authentication first.
                  </p>
                </div>
              </details>

              <details className="group mt-3">
                <summary className="text-xs font-medium text-gray-700 cursor-pointer hover:text-gray-900 flex items-center gap-1">
                  <span className="transform group-open:rotate-90 transition-transform">▶</span>
                  Troubleshooting tips
                </summary>
                <div className="mt-2 text-xs text-gray-600 space-y-1.5 pl-4">
                  <p>• Make sure you copy the <strong>entire</strong> 16-character password including dashes</p>
                  <p>• Double-check there are no extra spaces when copying</p>
                  <p>• Try regenerating the App Password in Zoho and use the new one</p>
                  <p>• Verify your email address is exactly as shown in Zoho</p>
                  <p>• Some Zoho plans require enabling IMAP access in Settings → POP/IMAP</p>
                </div>
              </details>
            </div>
          )}
        </form>
      </div>
    </div>
  );
}
