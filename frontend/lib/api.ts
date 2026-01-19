/**
 * API client for communicating with backend
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface Email {
  id: string;
  zoho_id: string;
  from_address: string;
  from_name: string;
  to_address: string;
  to_addresses: string[];  // 收件人列表
  cc_addresses: string[];  // 抄送人列表
  subject: string;
  body: string;
  received_at: string;
  is_customer_service: boolean;
  category: string | null;
  processed: boolean;
}

export interface EmailListResponse {
  emails: Email[];
  total: number;
  pending: number;
  processed: number;
}

export interface Skill {
  id: string;
  name: string;
  name_en: string;
  category: string;
  description: string | null;
  trigger_keywords: string[];
  rules: any[];
  usage_count: number;
  success_count: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface StatusResponse {
  status: string;
  zoho_connected: boolean;
  zoho_email: string;
  total_emails: number;
  total_skills: number;
  pending_replies: number;
}

export const api = {
  // OAuth methods
  async getOAuthAuthUrl(): Promise<{ configured: boolean; auth_url: string | null }> {
    const res = await fetch(`${API_BASE_URL}/api/oauth/auth-url`);
    if (!res.ok) throw new Error("Failed to get auth URL");
    return res.json();
  },

  async configureOAuth(clientId: string, clientSecret: string): Promise<{ configured: boolean; auth_url: string }> {
    const res = await fetch(`${API_BASE_URL}/api/oauth/config`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ client_id: clientId, client_secret: clientSecret }),
    });
    if (!res.ok) throw new Error("Failed to configure OAuth");
    return res.json();
  },

  async oauthCallback(code: string): Promise<{ success: boolean; message: string; user_email: string }> {
    const res = await fetch(`${API_BASE_URL}/api/oauth/callback?code=${code}`, {
      method: "POST",
    });
    if (!res.ok) throw new Error("OAuth callback failed");
    return res.json();
  },

  async getOAuthStatus(): Promise<{ connected: boolean; user_email: string | null }> {
    const res = await fetch(`${API_BASE_URL}/api/oauth/status`);
    if (!res.ok) throw new Error("Failed to get OAuth status");
    return res.json();
  },

  async disconnectOAuth(): Promise<{ success: boolean; message: string }> {
    const res = await fetch(`${API_BASE_URL}/api/oauth/disconnect`, {
      method: "POST",
    });
    if (!res.ok) throw new Error("Failed to disconnect");
    return res.json();
  },

  async getStatus(): Promise<StatusResponse> {
    const res = await fetch(`${API_BASE_URL}/api/status`);
    if (!res.ok) throw new Error("Failed to fetch status");
    return res.json();
  },

  async getEmails(status?: string, limit = 500, priorityOnly = false): Promise<EmailListResponse & { priority: number }> {
    const params = new URLSearchParams({ limit: limit.toString() });
    if (status) params.append("status", status);
    if (priorityOnly) params.append("priority_only", "true");
    const res = await fetch(`${API_BASE_URL}/api/emails?${params.toString()}`);
    if (!res.ok) throw new Error("Failed to fetch emails");
    return res.json();
  },

  async getEmail(id: string): Promise<Email> {
    const res = await fetch(`${API_BASE_URL}/api/emails/${id}`);
    if (!res.ok) throw new Error("Failed to fetch email");
    return res.json();
  },

  async clearEmails(): Promise<{ deleted: number; message: string }> {
    const res = await fetch(`${API_BASE_URL}/api/emails/clear`, {
      method: "DELETE",
    });
    if (!res.ok) throw new Error("Failed to clear emails");
    return res.json();
  },

  async analyzePriority(limit = 100): Promise<{ status: string; message: string }> {
    const res = await fetch(`${API_BASE_URL}/api/emails/analyze-priority?limit=${limit}`, {
      method: "POST",
    });
    if (!res.ok) throw new Error("Failed to analyze priority");
    return res.json();
  },

  async syncEmails(options: number | { count?: number; syncRange?: string; sync_range?: string; fromDate?: string; from_date?: string; toDate?: string; to_date?: string }): Promise<{ synced: number; new: number; total: number }> {
    let body = {};
    if (typeof options === 'number') {
      body = { count: options };
    } else {
      body = {
        count: options.count || 500,
        sync_range: options.sync_range || options.syncRange,  // Handle both naming conventions
        from_date: options.from_date || options.fromDate,
        to_date: options.to_date || options.toDate
      };
    }
    const res = await fetch(`${API_BASE_URL}/api/emails/sync`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (!res.ok) throw new Error("Failed to sync emails");
    return res.json();
  },

  async getSkills(activeOnly = true): Promise<{ skills: Skill[]; total: number; categories: string[] }> {
    const res = await fetch(`${API_BASE_URL}/api/skills?active_only=${activeOnly}`);
    if (!res.ok) throw new Error("Failed to fetch skills");
    return res.json();
  },

  async getSkillSourceEmails(skillId: string, limit = 20): Promise<{
    skill_id: string;
    skill_name: string;
    total_source_emails: number;
    source_emails: {
      id: string;
      email_id: string;
      from_address: string;
      from_name: string | null;
      subject: string;
      received_at: string | null;
      category: string | null;
      contribution_type: string;
      contribution_detail: string | null;
      linked_at: string | null;
    }[];
  }> {
    const res = await fetch(`${API_BASE_URL}/api/skills/${skillId}/source-emails?limit=${limit}`);
    if (!res.ok) throw new Error("Failed to fetch skill source emails");
    return res.json();
  },

  async generateReply(emailId: string): Promise<{
    email_id: string;
    reply_id: string;
    ai_draft: string;
    matched_skills: string[];
    confidence: number;
    requires_review: boolean;
  }> {
    const res = await fetch(`${API_BASE_URL}/api/replies/generate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email_id: emailId }),
    });
    if (!res.ok) throw new Error("Failed to generate reply");
    return res.json();
  },

  async sendReply(replyId: string, content: string): Promise<any> {
    const res = await fetch(`${API_BASE_URL}/api/replies/send`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ reply_id: replyId, content }),
    });
    if (!res.ok) throw new Error("Failed to send reply");
    return res.json();
  },

  async learnFromEmails(emailCount = 100, force = false): Promise<{
    status: string;
    message: string;
    emails_processed: number;
    customer_service_emails: number;
    skills_created: number;
    skills_updated: number;
  }> {
    const res = await fetch(`${API_BASE_URL}/api/skills/learn`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email_count: emailCount, force }),
    });
    if (!res.ok) throw new Error("Failed to start learning");
    return res.json();
  },
};
