import logging
from abc import ABC, abstractmethod
import asyncio
from playwright.async_api import async_playwright
import os

logger = logging.getLogger(__name__)

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

# Shared browser instance and page for tools
browser_instance = None
page_instance = None

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
        global browser_instance, page_instance
        
        try:
            # Initialize browser if not already done
            if browser_instance is None:
                playwright = await async_playwright().start()
                browser_instance = await playwright.chromium.launch(headless=False)
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
            
            # Wait for login to complete (look for Direct Messages icon)
            try:
                await page_instance.wait_for_selector('svg[aria-label="Direct"]', timeout=10000)
                logger.info(f"Successfully authenticated Instagram user: {username}")
                return {"status": "authenticated", "user": username}
            except Exception as e:
                logger.error(f"Login failed or timed out: {str(e)}")
                return {"status": "error", "message": "Failed to log in to Instagram"}
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
            
            result = asyncio.run(self._get_instagram_messages())
            return result
            
        except Exception as e:
            logger.error(f"Failed to get Instagram messages: {str(e)}")
            return {"status": "error", "message": str(e)}
    
    async def _get_instagram_messages(self):
        global page_instance
        
        # Navigate to Direct Messages
        await page_instance.click('svg[aria-label="Direct"]')
        
        # Wait for DMs to load
        await page_instance.wait_for_selector('div[role="listbox"]', timeout=5000)
        
        # Extract message data using evaluate
        unread_data = await page_instance.evaluate('''
        () => {
            const conversations = Array.from(document.querySelectorAll('div[role="listbox"] > div'));
            const unreadConvs = conversations.filter(conv => 
                conv.querySelector('div.unread') || conv.querySelector('span.unread'));
            
            return {
                unread_count: unreadConvs.length,
                message_previews: conversations.slice(0, 5).map(conv => {
                    const nameEl = conv.querySelector('span.username') || conv.querySelector('div.username');
                    const previewEl = conv.querySelector('div.preview') || conv.querySelector('span.preview');
                    return {
                        sender: nameEl ? nameEl.textContent : 'Unknown',
                        preview: previewEl ? previewEl.textContent : 'No preview'
                    };
                })
            };
        }
        ''')
        
        # Format the summary
        summary = {
            "unread_count": unread_data.get("unread_count", 0),
            "message_previews": unread_data.get("message_previews", []),
            "summary": f"You have {unread_data.get('unread_count', 0)} unread messages."
        }
        
        return summary

# Create custom registry with Instagram tools
custom_tool_registry = InMemoryToolRegistry.from_local_tools(
    [
        InstagramAuthenticationTool(),
        InstagramMessagesSummaryTool()
    ]
)
