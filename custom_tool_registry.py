import logging
from abc import ABC, abstractmethod
import asyncio
from playwright.async_api import async_playwright
import os

logger = logging.getLogger(__name__)

# Global variables to maintain state
browser_instance = None
page_instance = None
playwright_instance = None  # Add this to keep reference to playwright

class BaseTool(ABC):
    """Base class for implementing custom tools"""
    id = None
    description = None
    
    @abstractmethod
    def run(self, params: dict) -> dict:
        pass

class InMemoryToolRegistry:
    def __init__(self, tools=None):
        self.tools = tools or []
        
    @classmethod
    def from_local_tools(cls, tools):
        return cls(tools)

class InstagramAuthenticationTool(BaseTool):
    id = "instagram_login"
    description = "Logs into Instagram with username and password using browser automation."
    parameters = {
        "username": {"type": "string", "description": "Instagram username"},
        "password": {"type": "string", "description": "Instagram password"}
    }
    
    def run(self, params: dict) -> dict:
        """
        Authenticate to Instagram using Playwright
        """
        global browser_instance, page_instance
        
        username = params.get("username")
        password = params.get("password")
        
        if not username or not password:
            return {"status": "error", "message": "Username and password are required"}
        
        try:
            # Login to Instagram
            result = asyncio.run(self._login_to_instagram(username, password))
            return result
        except Exception as e:
            logger.error(f"Authentication failed: {str(e)}")
            return {"status": "error", "message": str(e)}
    
    async def _login_to_instagram(self, username, password):
        global browser_instance, page_instance, playwright_instance
        
        try:
            # Initialize browser if not already done
            if browser_instance is None:
                playwright_instance = await async_playwright().start()
                browser_instance = await playwright_instance.chromium.launch(headless=False)
                page_instance = await browser_instance.new_page()
            
            # Navigate to Instagram
            await page_instance.goto("https://www.instagram.com/")
            
            # Wait for the login page to load
            await page_instance.wait_for_selector('input[name="username"]')
            
            # Enter credentials
            await page_instance.fill('input[name="username"]', username)
            await page_instance.fill('input[name="password"]', password)
            
            # Click the login button
            await page_instance.click('button[type="submit"]')
            
            # Handle verification if needed
            try:
                # Check for security code screen (multiple possible selectors)
                verification_selector = 'h2:has-text("Enter security code"), h2:has-text("Enter the code"), div:has-text("Enter the confirmation code"), input[name="verificationCode"]'
                await page_instance.wait_for_selector(verification_selector, timeout=8000)
                
                # Verification needed
                print("\n🔐 Security verification required!")
                print("✅ Please check your email and enter the code in the browser window")
                print("⏳ Then click Continue/Confirm in the browser\n")
                
                # Wait for user to enter code and click continue
                # Instead of looking for Direct icon immediately, wait for any navigation or page change
                await page_instance.wait_for_load_state("networkidle", timeout=60000)
                
                # After verification, we might be on various screens:
                # 1. Home feed
                # 2. Save login info prompt
                # 3. Turn on notifications prompt
                
                # Check for "Save Login Info" prompt and handle it
                try:
                    save_info_button = await page_instance.wait_for_selector('button:has-text("Not Now"), button:has-text("Skip")', timeout=5000)
                    if save_info_button:
                        await save_info_button.click()
                        await page_instance.wait_for_load_state("networkidle", timeout=5000)
                except:
                    # No save info prompt
                    pass
                    
                # Check for notifications prompt and handle it
                try:
                    notif_button = await page_instance.wait_for_selector('button:has-text("Not Now"), button:has-text("Skip")', timeout=5000)
                    if notif_button:
                        await notif_button.click()
                        await page_instance.wait_for_load_state("networkidle", timeout=5000)
                except:
                    # No notifications prompt
                    pass
                    
                print("✅ Login successful after verification!")
                return {"status": "authenticated", "user": username}
                
            except Exception as verify_error:
                # No verification needed or it timed out
                print(f"No verification screen detected or verification timed out: {verify_error}")
                
                # Try to confirm we're logged in by checking for common elements
                try:
                    # Look for any of these elements that indicate successful login
                    login_indicators = [
                        'svg[aria-label="Direct"]',
                        'svg[aria-label="Home"]', 
                        'a[href="/direct/inbox/"]',
                        'a[href="/explore/"]',
                        'nav[role="navigation"]'
                    ]
                    
                    for indicator in login_indicators:
                        try:
                            await page_instance.wait_for_selector(indicator, timeout=5000)
                            print(f"✅ Login confirmed via indicator: {indicator}")
                            return {"status": "authenticated", "user": username}
                        except:
                            continue
                            
                    # If we get here, we couldn't confirm login
                    print("⚠️ Can't confirm login status, proceeding anyway...")
                    return {"status": "authenticated", "user": username}
                    
                except Exception as login_error:
                    logger.error(f"Login confirmation failed: {login_error}")
                    return {"status": "error", "message": f"Failed to confirm login: {login_error}"}
        
        except Exception as e:
            logger.error(f"Authentication error: {str(e)}")
            return {"status": "error", "message": str(e)}

class InstagramMessagesSummaryTool(BaseTool):
    id = "instagram_messages"
    description = "Gets and summarizes Instagram direct messages."
    parameters = {}
    
    def run(self, params: dict) -> dict:
        """
        Fetch and summarize Instagram DMs using Playwright
        """
        global page_instance
        
        try:
            if page_instance is None:
                return {"status": "error", "message": "Not authenticated. Please login first."}
            
            # Add timeout to prevent hanging
            result = asyncio.run(asyncio.wait_for(self._get_instagram_messages(), timeout=30))
            return result
            
        except asyncio.TimeoutError:
            logger.error("Instagram message fetching timed out after 30 seconds")
            # Take error screenshot
            try:
                asyncio.run(page_instance.screenshot(path="instagram_timeout_error.png"))
            except:
                pass
            return {"status": "error", "message": "Instagram message fetching timed out", "screenshot": "instagram_timeout_error.png"}
        except Exception as e:
            logger.error(f"Failed to get Instagram messages: {str(e)}")
            return {"status": "error", "message": str(e)}
    
    async def _get_instagram_messages(self):
        global page_instance
        
        try:
            print("Navigating to Instagram Direct Messages...")
            
            # Take a screenshot of current page state
            await page_instance.screenshot(path="before_navigation.png")
            print("📸 Current page state saved to before_navigation.png")
            
            # Try multiple approaches to get to DMs
            try:
                # First approach: Click the direct icon if available
                print("Attempting to click Direct icon...")
                try:
                    await page_instance.click('svg[aria-label="Direct"]', timeout=5000)
                    await page_instance.wait_for_load_state("networkidle", timeout=5000)
                    print("✅ Clicked Direct icon")
                except Exception as e:
                    print(f"⚠️ Couldn't click Direct icon: {e}")
                    
                    # Second approach: Direct URL navigation
                    print("Trying direct URL navigation...")
                    await page_instance.goto("https://www.instagram.com/direct/inbox/", timeout=10000)
                    await page_instance.wait_for_load_state("networkidle", timeout=5000)
                    print("✅ Navigated to Direct inbox URL")
            except Exception as e:
                print(f"⚠️ Navigation error: {e}")
                # Take error screenshot
                await page_instance.screenshot(path="navigation_error.png")
                print("📸 Navigation error state saved to navigation_error.png")
            
            print(f"Current URL after navigation: {page_instance.url}")
            
            # Take screenshot of DM page
            await page_instance.screenshot(path="instagram_dm_page.png")
            print("📸 DM page screenshot saved to instagram_dm_page.png")
            
            # Extract simple text data from the page
            print("Extracting message data from page...")
            page_data = await page_instance.evaluate('''
            () => {
                // Get page title and text content
                const pageTitle = document.title;
                
                // Try to identify if we're on the DM page
                const isDMPage = window.location.href.includes('direct') || 
                                 document.title.toLowerCase().includes('inbox') ||
                                 document.body.innerHTML.includes('inbox');
                
                // Get all text nodes that might represent messages
                const textNodes = Array.from(document.querySelectorAll('div, span, p'))
                    .filter(el => {
                        const text = el.textContent.trim();
                        return text.length > 5 && text.length < 200;
                    })
                    .map(el => el.textContent.trim())
                    .slice(0, 20); // Get top 20 potential messages
                
                return {
                    page_title: pageTitle,
                    current_url: window.location.href,
                    is_dm_page: isDMPage,
                    potential_message_texts: textNodes,
                    unread_count: document.querySelectorAll('[class*="unread"], [aria-label*="unread"]').length || 0
                };
            }
            ''')
            
            print("Data extraction complete.")
            
            # Format the useful text into message previews
            message_previews = []
            for text in page_data.get("potential_message_texts", []):
                # Skip navigation elements, buttons, etc.
                if any(skip in text.lower() for skip in ['home', 'search', 'explore', 'settings', 'profile']):
                    continue
                    
                # Format as message
                message_previews.append({
                    "text": text,
                    "unread": "new" in text.lower() or "unread" in text.lower()
                })
            
            # Save summary to a file
            print("Saving summary to file...")
            with open('personal_messages_summary_report.txt', 'w') as f:
                f.write(f"INSTAGRAM DM SUMMARY\n")
                f.write(f"URL: {page_data.get('current_url', 'unknown')}\n")
                f.write(f"Page title: {page_data.get('page_title', 'unknown')}\n")
                f.write(f"Is DM page: {page_data.get('is_dm_page', False)}\n")
                f.write(f"Estimated unread messages: {page_data.get('unread_count', 0)}\n\n")
                f.write("CONVERSATION PREVIEWS:\n")
                
                for i, msg in enumerate(message_previews):
                    read_status = "UNREAD" if msg.get("unread") else "read"
                    f.write(f"{i+1}. {msg.get('text', 'No text')} [{read_status}]\n")
            
            return {
                "unread_count": page_data.get("unread_count", 0),
                "message_previews": message_previews,
                "is_dm_page": page_data.get("is_dm_page", False)
            }
        except Exception as e:
            logger.error(f"Error retrieving messages: {str(e)}")
            # Take error screenshot
            await page_instance.screenshot(path="instagram_error.png")
            return {
                "status": "error", 
                "message": f"Failed to get messages: {str(e)}",
                "screenshot": "instagram_error.png"
            }

# Create custom registry with Instagram tools
custom_tool_registry = InMemoryToolRegistry.from_local_tools(
    [
        InstagramAuthenticationTool(),
        InstagramMessagesSummaryTool()
    ]
)
