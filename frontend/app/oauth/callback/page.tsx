"use client";

import { useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { api } from "@/lib/api";

export default function OAuthCallback() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [status, setStatus] = useState<"loading" | "success" | "error">("loading");
  const [message, setMessage] = useState("");

  useEffect(() => {
    const handleCallback = async () => {
      const code = searchParams.get("code");
      const error = searchParams.get("error");

      if (error) {
        setStatus("error");
        setMessage(error === "access_denied" ? "Authorization was denied" : error);
        return;
      }

      if (!code) {
        setStatus("error");
        setMessage("No authorization code received");
        return;
      }

      try {
        // Send code to backend
        const result = await api.oauthCallback(code);

        setStatus("success");
        setMessage(`Connected! Using account: ${result.user_email}`);

        // Notify opener window
        if (window.opener) {
          window.opener.postMessage({ type: "oauth_success", data: result }, "*");
        }

        // Close popup after a delay
        setTimeout(() => {
          window.close();
        }, 1500);
      } catch (err: any) {
        setStatus("error");
        setMessage(err.message || "Failed to complete authentication");

        // Notify opener window of error
        if (window.opener) {
          window.opener.postMessage({ type: "oauth_error", error: err.message }, "*");
        }

        setTimeout(() => {
          window.close();
        }, 3000);
      }
    };

    handleCallback();
  }, [searchParams]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="bg-white rounded-2xl shadow-xl p-8 max-w-md w-full mx-4 text-center">
        {status === "loading" && (
          <>
            <div className="animate-spin rounded-full h-16 w-16 border-b-2 border-blue-500 mx-auto mb-4"></div>
            <h2 className="text-xl font-semibold text-gray-900 mb-2">Completing Authentication...</h2>
            <p className="text-gray-500">Please wait while we connect your Zoho account.</p>
          </>
        )}

        {status === "success" && (
          <>
            <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
              <span className="text-3xl">✅</span>
            </div>
            <h2 className="text-xl font-semibold text-gray-900 mb-2">Successfully Connected!</h2>
            <p className="text-gray-600">{message}</p>
            <p className="text-sm text-gray-400 mt-4">This window will close automatically...</p>
          </>
        )}

        {status === "error" && (
          <>
            <div className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-4">
              <span className="text-3xl">❌</span>
            </div>
            <h2 className="text-xl font-semibold text-gray-900 mb-2">Authentication Failed</h2>
            <p className="text-red-600">{message}</p>
            <p className="text-sm text-gray-400 mt-4">This window will close automatically...</p>
          </>
        )}
      </div>
    </div>
  );
}
