"""
Zoho Mail OAuth 2.0 Service
Uses Zoho Mail API instead of IMAP/SMTP
"""
import os
import re
import json
import time
import requests
from typing import Dict, Optional, List
from datetime import datetime, timedelta
from config import settings


class ZohoOAuthService:
    """Service for Zoho Mail API OAuth authentication and operations"""

    # Zoho OAuth endpoints - will be set based on region
    AUTH_URL = None
    TOKEN_URL = None
    REVOKE_URL = None

    # Zoho Mail API endpoints
    API_BASE = "https://mail.zoho.com/api"

    # File paths for storing credentials
    CREDS_FILE = "data/zoho_creds.json"
    TOKENS_FILE = "data/zoho_tokens.json"

    # Supported Zoho regions
    ZOHO_REGIONS = {
        "com": {"auth": "https://accounts.zoho.com/oauth/v2/auth",
                "token": "https://accounts.zoho.com/oauth/v2/token",
                "revoke": "https://accounts.zoho.com/oauth/v2/revoke",
                "api": "https://mail.zoho.com/api"},
        "jp": {"auth": "https://accounts.zoho.jp/oauth/v2/auth",
                "token": "https://accounts.zoho.jp/oauth/v2/token",
                "revoke": "https://accounts.zoho.jp/oauth/v2/revoke",
                "api": "https://mail.zoho.jp/api"},
        "eu": {"auth": "https://accounts.zoho.eu/oauth/v2/auth",
                "token": "https://accounts.zoho.eu/oauth/v2/token",
                "revoke": "https://accounts.zoho.eu/oauth/v2/revoke",
                "api": "https://mail.zoho.eu/api"},
        "in": {"auth": "https://accounts.zoho.in/oauth/v2/auth",
                "token": "https://accounts.zoho.in/oauth/v2/token",
                "revoke": "https://accounts.zoho.in/oauth/v2/revoke",
                "api": "https://mail.zoho.in/api"},
        "cn": {"auth": "https://accounts.zoho.cn/oauth/v2/auth",
                "token": "https://accounts.zoho.cn/oauth/v2/token",
                "revoke": "https://accounts.zoho.cn/oauth/v2/revoke",
                "api": "https://mail.zoho.cn/api"},
    }

    def __init__(self, region: str = "jp"):
        """
        Args:
            region: Zoho region code (com, jp, eu, in, cn). Default is 'jp' for Japan.
        """
        self.region = region
        self._set_region_endpoints(region)

        self.client_id = None
        self.client_secret = None
        self.redirect_uri = settings.ZOHO_REDIRECT_URI
        self.access_token = None
        self.refresh_token = None
        self.token_expires_at = None
        self.user_email = None

        # Try to load credentials from file first, then fall back to settings
        self._load_credentials()

    def _set_region_endpoints(self, region: str):
        """Set OAuth endpoints based on region"""
        endpoints = self.ZOHO_REGIONS.get(region, self.ZOHO_REGIONS["com"])
        self.AUTH_URL = endpoints["auth"]
        self.TOKEN_URL = endpoints["token"]
        self.REVOKE_URL = endpoints["revoke"]
        self.API_BASE = endpoints["api"]

    def _load_credentials(self):
        """Load client credentials from file or settings"""
        # Try to load from file first
        try:
            if os.path.exists(self.CREDS_FILE):
                with open(self.CREDS_FILE, "r") as f:
                    data = json.load(f)
                    self.client_id = data.get("client_id")
                    self.client_secret = data.get("client_secret")
                    return
        except:
            pass

        # Fall back to settings
        if settings.ZOHO_CLIENT_ID:
            self.client_id = settings.ZOHO_CLIENT_ID
        if settings.ZOHO_CLIENT_SECRET:
            self.client_secret = settings.ZOHO_CLIENT_SECRET

    def save_credentials(self) -> bool:
        """Save client credentials to file"""
        try:
            os.makedirs(os.path.dirname(self.CREDS_FILE), exist_ok=True)

            data = {
                "client_id": self.client_id,
                "client_secret": self.client_secret
            }

            with open(self.CREDS_FILE, "w") as f:
                json.dump(data, f)
            return True
        except:
            return False

    def get_auth_url(self, state: str = None) -> str:
        """Generate OAuth authorization URL

        Args:
            state: Optional state parameter for CSRF protection

        Returns:
            Authorization URL
        """
        params = {
            "response_type": "code",
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "scope": "ZohoMail.messages.READ,ZohoMail.messages.CREATE,ZohoMail.accounts.READ,ZohoMail.folders.READ",
            "access_type": "offline",
            "state": state or "email_assistant"
        }

        param_str = "&".join([f"{k}={v}" for k, v in params.items()])
        return f"{self.AUTH_URL}?{param_str}"

    def exchange_code_for_token(self, code: str) -> Dict:
        """Exchange authorization code for access token

        Args:
            code: Authorization code from OAuth callback

        Returns:
            Token response with access_token, refresh_token, etc.
        """
        data = {
            "grant_type": "authorization_code",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "code": code,
            "redirect_uri": self.redirect_uri
        }

        print(f"DEBUG: Exchanging token at: {self.TOKEN_URL}")
        print(f"DEBUG: grant_type=authorization_code")
        print(f"DEBUG: client_id={self.client_id[:20]}...")
        print(f"DEBUG: client_secret={'*' * len(self.client_secret) if self.client_secret else 'None'}")
        print(f"DEBUG: code={code[:20]}...")
        print(f"DEBUG: redirect_uri={self.redirect_uri}")

        response = requests.post(self.TOKEN_URL, data=data)
        result = response.json()

        print(f"DEBUG: Response status: {response.status_code}")
        print(f"DEBUG: Response body: {result}")

        if response.status_code != 200 or "error" in result:
            raise Exception(f"Token exchange failed: {result.get('error', 'Unknown error')}")

        # Store tokens
        self.access_token = result.get("access_token")
        self.refresh_token = result.get("refresh_token")
        self.token_expires_at = datetime.now() + timedelta(seconds=result.get("expires_in", 3600))

        return result

    def refresh_access_token(self) -> Dict:
        """Refresh access token using refresh token

        Returns:
            New token response
        """
        if not self.refresh_token:
            raise Exception("No refresh token available")

        data = {
            "grant_type": "refresh_token",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "refresh_token": self.refresh_token
        }

        response = requests.post(self.TOKEN_URL, data=data)
        result = response.json()

        if response.status_code != 200 or "error" in result:
            raise Exception(f"Token refresh failed: {result.get('error', 'Unknown error')}")

        self.access_token = result.get("access_token")
        self.token_expires_at = datetime.now() + timedelta(seconds=result.get("expires_in", 3600))

        return result

    def ensure_valid_token(self) -> str:
        """Ensure we have a valid access token, refresh if needed

        Returns:
            Valid access token
        """
        if not self.access_token:
            raise Exception("Not authenticated. Please authorize first.")

        # Check if token is expired or will expire soon
        if self.token_expires_at and datetime.now() >= self.token_expires_at - timedelta(minutes=5):
            self.refresh_access_token()

        return self.access_token

    def get_headers(self) -> Dict:
        """Get headers for API requests

        Returns:
            Headers dict with Authorization
        """
        token = self.ensure_valid_token()
        return {
            "Authorization": f"Zoho-oauthtoken {token}",
            "Content-Type": "application/json"
        }

    def test_connection(self) -> tuple[bool, str]:
        """Test the API connection

        Returns:
            Tuple of (success, message)
        """
        try:
            headers = self.get_headers()
            response = requests.get(
                f"{self.API_BASE}/accounts",
                headers=headers
            )

            if response.status_code == 200:
                data = response.json()
                # Get user email from first account
                if data.get("data"):
                    self.user_email = data["data"][0].get("accountEmailAddress", "")
                return True, f"Successfully connected! Using account: {self.user_email or 'Unknown'}"
            else:
                return False, f"API error: {response.status_code} - {response.text}"

        except Exception as e:
            return False, f"Connection failed: {str(e)}"

    def fetch_emails(
        self,
        count: int = 100,
        folder: str = "Inbox",
        sync_range: str = None,
        from_date: str = None,
        to_date: str = None
    ) -> List[Dict]:
        """Fetch emails from Zoho Mail API with optional date filtering

        Args:
            count: Number of emails to fetch
            folder: Folder name (default: Inbox)
            sync_range: Predefined range - "today", "3days", "7days", "30days", "all"
            from_date: Start date in YYYY-MM-DD format (for custom range)
            to_date: End date in YYYY-MM-DD format (for custom range)

        Returns:
            List of email dictionaries
        """
        # Calculate date range based on sync_range
        date_filter_start = None
        date_filter_end = None
        
        if sync_range:
            from datetime import timedelta
            today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            today_end = today + timedelta(days=1)
            
            if sync_range == "today":
                date_filter_start = today
                date_filter_end = today_end
            elif sync_range == "3days":
                # 最近3天 = 今天 + 前2天
                date_filter_start = today - timedelta(days=2)
                date_filter_end = today_end
            elif sync_range == "7days":
                # 最近7天 = 今天 + 前6天
                date_filter_start = today - timedelta(days=6)
                date_filter_end = today_end
            elif sync_range == "30days":
                # 最近30天 = 今天 + 前29天
                date_filter_start = today - timedelta(days=29)
                date_filter_end = today_end
            elif sync_range == "custom" and from_date and to_date:
                date_filter_start = datetime.strptime(from_date, "%Y-%m-%d")
                date_filter_end = datetime.strptime(to_date, "%Y-%m-%d") + timedelta(days=1)
            # "all" means no date filter
        
        print(f"DEBUG: Date filter: {date_filter_start} to {date_filter_end}")

        headers = self.get_headers()

        # Get account ID first
        accounts_response = requests.get(
            f"{self.API_BASE}/accounts",
            headers=headers
        )

        if accounts_response.status_code != 200:
            raise Exception(f"Failed to get accounts: {accounts_response.text}")

        accounts = accounts_response.json().get("data", [])
        if not accounts:
            raise Exception("No accounts found")

        account_id = accounts[0]["accountId"]

        # Get folder ID - use correct Zoho Mail API endpoint
        folders_url = f"{self.API_BASE}/accounts/{account_id}/folders"
        print(f"DEBUG: Fetching folders from: {folders_url}")
        folders_response = requests.get(
            folders_url,
            headers=headers
        )
        print(f"DEBUG: Folders response status: {folders_response.status_code}")
        print(f"DEBUG: Folders response: {folders_response.text[:500] if folders_response.text else 'empty'}")

        if folders_response.status_code != 200:
            raise Exception(f"Failed to get folders: {folders_response.text}")

        # Parse folders - Zoho returns data.data[] or data[] depending on endpoint
        folders_data = folders_response.json()
        folders = folders_data.get("data", [])
        print(f"DEBUG: Found {len(folders)} folders")
        folder_id = None
        for f in folders:
            print(f"DEBUG: Folder: {f.get('folderName')} (ID: {f.get('folderId')})")
            if f.get("folderName") == folder or f.get("name") == folder:
                folder_id = f.get("folderId") or f.get("id")
                break

        if not folder_id:
            # Use INBOX as default if no folder found
            print(f"DEBUG: Folder '{folder}' not found, using first inbox-like folder")
            for f in folders:
                if "inbox" in (f.get("folderName", "") or f.get("name", "")).lower():
                    folder_id = f.get("folderId") or f.get("id")
                    break
        
        if not folder_id and folders:
            # Fallback to first folder
            folder_id = folders[0].get("folderId") or folders[0].get("id")
        
        print(f"DEBUG: Using folder_id: {folder_id}")

        # Fetch emails with pagination - Zoho API returns max 50 per request
        messages_url = f"{self.API_BASE}/accounts/{account_id}/messages/view"
        print(f"DEBUG: Fetching messages from: {messages_url}")
        
        all_emails_data = []
        start_index = 0
        page_size = 50  # Zoho's max per request
        max_emails = count if count else 500  # Default max if no count specified
        reached_date_limit = False
        
        while len(all_emails_data) < max_emails and not reached_date_limit:
            print(f"DEBUG: Fetching page starting at index {start_index}")
            emails_response = requests.get(
                messages_url,
                headers=headers,
                params={
                    "folderId": folder_id,
                    "limit": min(page_size, max_emails - len(all_emails_data)),
                    "start": start_index
                }
            )
            print(f"DEBUG: Messages response status: {emails_response.status_code}")

            if emails_response.status_code != 200:
                raise Exception(f"Failed to fetch emails: {emails_response.text}")

            page_data = emails_response.json().get("data", [])
            print(f"DEBUG: Got {len(page_data)} messages in this page")
            
            if not page_data:
                # No more emails to fetch
                break
            
            # Check if oldest email in this page is before our date filter
            if date_filter_start and page_data:
                oldest_msg = page_data[-1]
                oldest_date_str = oldest_msg.get("sentDateInGMT")
                if oldest_date_str:
                    try:
                        oldest_date = datetime.fromtimestamp(int(oldest_date_str) / 1000)
                        if oldest_date < date_filter_start:
                            print(f"DEBUG: Oldest email {oldest_date} is before filter start {date_filter_start}, will stop after this page")
                            reached_date_limit = True
                    except:
                        pass
            
            all_emails_data.extend(page_data)
            start_index += len(page_data)
            
            # If we got less than page_size, there are no more emails
            if len(page_data) < page_size:
                break
        
        print(f"DEBUG: Total messages fetched: {len(all_emails_data)}")

        # Parse emails
        emails = []
        for msg in all_emails_data:
            message_id = msg.get('messageId')
            # Get full message content - use correct endpoint with folderId
            detail_url = f"{self.API_BASE}/accounts/{account_id}/folders/{folder_id}/messages/{message_id}/content"
            detail_response = requests.get(
                detail_url,
                headers=headers
            )

            if detail_response.status_code == 200:
                detail = detail_response.json().get("data", {})
                # Merge the list data with detail data
                merged = {**msg, **detail}
                parsed_email = self._parse_email(merged, message_id)
            else:
                # If content fetch fails, use the summary data from list
                parsed_email = self._parse_email_from_list(msg)
            
            # Apply date filter if specified
            if date_filter_start and date_filter_end:
                email_date = parsed_email.get("received_at")
                if email_date:
                    if email_date < date_filter_start:
                        # Emails are sorted by date desc, so we can stop here
                        print(f"DEBUG: Email {email_date} is before date range, stopping")
                        break
                    if email_date >= date_filter_end:
                        print(f"DEBUG: Skipping email after date range: {email_date}")
                        continue
            
            emails.append(parsed_email)

        print(f"DEBUG: Returning {len(emails)} emails (after date filter)")
        return emails

    def _strip_html(self, html: str) -> str:
        """Strip HTML tags from content and clean up formatting

        Args:
            html: HTML content string

        Returns:
            Clean text without HTML tags
        """
        if not html:
            return ""
        
        import html as html_module
        
        # Remove style and script blocks completely
        text = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.DOTALL | re.IGNORECASE)
        
        # Replace common block elements with newlines
        text = re.sub(r'<br\s*/?>', '\n', text, flags=re.IGNORECASE)
        text = re.sub(r'</p>', '\n\n', text, flags=re.IGNORECASE)
        text = re.sub(r'</div>', '\n', text, flags=re.IGNORECASE)
        text = re.sub(r'</tr>', '\n', text, flags=re.IGNORECASE)
        
        # Remove all remaining HTML tags
        text = re.sub(r'<[^>]+>', '', text)
        
        # Decode HTML entities
        text = html_module.unescape(text)
        
        # Clean up whitespace
        text = re.sub(r'\n\s*\n+', '\n\n', text)  # Multiple newlines to double
        text = re.sub(r'[ \t]+', ' ', text)  # Multiple spaces to single
        text = text.strip()
        
        return text

    def _parse_email(self, detail: Dict, message_id: str) -> Dict:
        """Parse email from API response

        Args:
            detail: Email detail from API (merged from list + content endpoints)
            message_id: Message ID

        Returns:
            Parsed email dictionary
        """
        # Parse sender - handle both 'from' object and 'fromAddress' string formats
        from_email = detail.get("from", {})
        if isinstance(from_email, dict) and from_email.get("address"):
            from_address = from_email.get("address", "")
            from_name = from_email.get("name", "") or from_address.split("@")[0]
        else:
            # Fallback to list API format
            from_address = detail.get("fromAddress", "")
            from_name = detail.get("sender", "") or (from_address.split("@")[0] if from_address else "")
        
        # Parse recipients (To) - handle both 'to' list and 'toAddress' string formats
        to_list = detail.get("to", [])
        if isinstance(to_list, list) and to_list:
            to_addresses = [t.get("address", "") for t in to_list if isinstance(t, dict) and t.get("address")]
        else:
            # Fallback to list API format - toAddress is a string (may contain multiple)
            to_address_str = detail.get("toAddress", "")
            to_addresses = [addr.strip() for addr in to_address_str.split(",") if addr.strip()] if to_address_str else []
        
        # Decode HTML entities in addresses (fix &quot; &lt; &gt; etc.)
        import html
        to_addresses = [html.unescape(addr) for addr in to_addresses]
        to_address = to_addresses[0] if to_addresses else ""
        
        # Parse CC recipients - handle both 'cc' list and 'ccAddress' string formats
        cc_list = detail.get("cc", [])
        if isinstance(cc_list, list) and cc_list:
            cc_addresses = [c.get("address", "") for c in cc_list if isinstance(c, dict) and c.get("address")]
        else:
            # Fallback to list API format
            cc_address_str = detail.get("ccAddress", "")
            cc_addresses = [addr.strip() for addr in cc_address_str.split(",") if addr.strip()] if cc_address_str else []
        
        # Decode HTML entities in CC addresses and ensure empty list (not ["Not Provided"])
        cc_addresses = [html.unescape(addr) for addr in cc_addresses if addr and addr != "Not Provided"]

        # Parse date - check multiple possible time fields from Zoho API
        received_at = datetime.utcnow()
        
        # Debug: print available time fields
        time_fields = {k: v for k, v in detail.items() if 'time' in k.lower() or 'date' in k.lower()}
        if time_fields and len(time_fields) < 10:  # Only print if not too many fields
            print(f"DEBUG: Time fields in email: {time_fields}")
        
        # Try receivedTime first (millisecond timestamp)
        if detail.get("receivedTime"):
            try:
                received_at = datetime.fromtimestamp(int(detail["receivedTime"]) / 1000)
            except Exception as e:
                print(f"DEBUG: Error parsing receivedTime: {e}")
        # Fallback to sentDateInGMT
        elif detail.get("sentDateInGMT"):
            try:
                received_at = datetime.fromtimestamp(int(detail["sentDateInGMT"]) / 1000)
            except Exception as e:
                print(f"DEBUG: Error parsing sentDateInGMT: {e}")
        # Try receivedDate (some Zoho endpoints use this)
        elif detail.get("receivedDate"):
            try:
                received_at = datetime.fromtimestamp(int(detail["receivedDate"]) / 1000)
            except Exception as e:
                print(f"DEBUG: Error parsing receivedDate: {e}")

        # Get body - handle both string and dict content formats
        body = ""
        content = detail.get("content", "")
        if isinstance(content, str):
            # Content is already a string - might be HTML, so strip tags
            body = self._strip_html(content)
        elif isinstance(content, dict):
            if content.get("text"):
                body = content["text"]
            elif content.get("html"):
                # Strip HTML tags
                body = self._strip_html(content["html"])
        
        # Fallback to summary if no body found
        if not body:
            body = detail.get("summary", "")

        return {
            "zoho_id": message_id,
            "from_address": from_address,
            "from_name": from_name,
            "to_address": to_address,
            "to_addresses": to_addresses,
            "cc_addresses": cc_addresses,
            "subject": detail.get("subject", ""),
            "body": body,
            "received_at": received_at
        }

    def _parse_email_from_list(self, msg: Dict) -> Dict:
        """Parse email from list response (fallback when content fetch fails)

        Args:
            msg: Message data from list API

        Returns:
            Parsed email dictionary
        """
        message_id = msg.get("messageId", "")
        
        # Parse sender - list API uses different format
        from_address = msg.get("fromAddress", "")
        from_name = msg.get("sender", "") or from_address.split("@")[0] if from_address else ""
        
        # Parse to address - list API may have different format
        to_address = msg.get("toAddress", "")
        to_addresses = [to_address] if to_address else []
        
        # CC not available in list API, use empty list
        cc_addresses = []
        
        # Parse date
        received_at = datetime.utcnow()
        if msg.get("sentDateInGMT") or msg.get("receivedTime"):
            try:
                timestamp = int(msg.get("sentDateInGMT") or msg.get("receivedTime"))
                received_at = datetime.fromtimestamp(timestamp / 1000)
            except:
                pass

        return {
            "zoho_id": message_id,
            "from_address": from_address,
            "from_name": from_name,
            "to_address": to_address,
            "to_addresses": to_addresses,
            "cc_addresses": cc_addresses,
            "subject": msg.get("subject", ""),
            "body": msg.get("summary", ""),  # Use summary as body fallback
            "received_at": received_at
        }

    def send_email(self, to_address: str, subject: str, body: str, in_reply_to: str = None) -> bool:
        """Send an email via Zoho Mail API

        Args:
            to_address: Recipient email address
            subject: Email subject
            body: Email body
            in_reply_to: Message ID being replied to

        Returns:
            True if successful
        """
        headers = self.get_headers()

        # Get account ID
        accounts_response = requests.get(
            f"{self.API_BASE}/accounts",
            headers=headers
        )

        if accounts_response.status_code != 200:
            raise Exception(f"Failed to get accounts: {accounts_response.text}")

        accounts = accounts_response.json().get("data", [])
        if not accounts:
            raise Exception("No accounts found")

        account_id = accounts[0]["accountId"]

        # Prepare email data
        email_data = {
            "fromAddress": accounts[0]["accountEmailAddress"],
            "toAddress": to_address,
            "subject": subject,
            "content": {
                "text": body
            }
        }

        if in_reply_to:
            email_data["replyToMessageId"] = in_reply_to

        # Send email
        response = requests.post(
            f"{self.API_BASE}/accounts/{account_id}/messages/send",
            headers=headers,
            json=email_data
        )

        if response.status_code != 200:
            raise Exception(f"Failed to send email: {response.text}")

        return True

    def revoke_token(self) -> bool:
        """Revoke the current tokens

        Returns:
            True if successful
        """
        try:
            if self.refresh_token:
                params = {
                    "token": self.refresh_token,
                    "client_id": self.client_id,
                    "client_secret": self.client_secret
                }
                requests.post(self.REVOKE_URL, params=params)

            self.access_token = None
            self.refresh_token = None
            self.token_expires_at = None
            self.user_email = None
            return True
        except:
            return False

    def save_tokens(self) -> bool:
        """Save tokens to file

        Returns:
            True if successful
        """
        try:
            os.makedirs(os.path.dirname(self.TOKENS_FILE), exist_ok=True)

            data = {
                "access_token": self.access_token,
                "refresh_token": self.refresh_token,
                "expires_at": self.token_expires_at.isoformat() if self.token_expires_at else None,
                "user_email": self.user_email
            }

            with open(self.TOKENS_FILE, "w") as f:
                json.dump(data, f)
            return True
        except:
            return False

    def load_tokens(self) -> bool:
        """Load tokens from file

        Returns:
            True if successful
        """
        try:
            if not os.path.exists(self.TOKENS_FILE):
                return False

            with open(self.TOKENS_FILE, "r") as f:
                data = json.load(f)

            self.access_token = data.get("access_token")
            self.refresh_token = data.get("refresh_token")
            self.user_email = data.get("user_email")

            if data.get("expires_at"):
                self.token_expires_at = datetime.fromisoformat(data["expires_at"])

            return True
        except:
            return False


# Global instance - using Japan region for zoho.jp accounts
zoho_oauth_service = ZohoOAuthService(region="jp")
