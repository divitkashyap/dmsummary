from dotenv import load_dotenv
from custom_config import get_my_config
from portia import Config, LogLevel, Portia, StorageClass
import asyncio
import os
import time
from playwright.async_api import async_playwright

load_dotenv()

# Get Instagram credentials from environment variables
INSTAGRAM_USERNAME = os.environ.get("INSTAGRAM_USERNAME")
INSTAGRAM_PASSWORD = os.environ.get("INSTAGRAM_PASSWORD")

print("\n🔒 Starting Instagram DM Summary Tool")

async def run_instagram_workflow():
    """Run the complete Instagram workflow with proper error handling"""
    
    print("Starting browser...")
    playwright = await async_playwright().start()
    browser = await playwright.chromium.launch(headless=False)
    page = await browser.new_page()
    
    try:
        # Step 1: Login to Instagram
        print("\n📱 Logging into Instagram...")
        await page.goto("https://www.instagram.com/")
        
        # Wait for and fill login form
        await page.wait_for_selector('input[name="username"]')
        await page.fill('input[name="username"]', INSTAGRAM_USERNAME)
        await page.fill('input[name="password"]', INSTAGRAM_PASSWORD)
        
        # Take screenshot of login page
        await page.screenshot(path="1_login_page.png")
        print("✅ Screenshot saved: 1_login_page.png")
        
        # Click login button
        await page.click('button[type="submit"]')
        print("Clicked login button, waiting for home page...")
        
        # Wait for either homepage or verification page
        try:
            # Check if verification needed
            verification_selector = 'input[name="verificationCode"], input[placeholder*="code"]'
            verify_element = await page.wait_for_selector(verification_selector, timeout=8000)
            
            if verify_element:
                await page.screenshot(path="2_verification_page.png")
                print("\n⚠️ Verification required!")
                print("✅ Screenshot saved: 2_verification_page.png")
                print("Please check your email for a code, enter it in the browser")
                print("Waiting for you to complete verification (60 seconds)...")
                
                # Wait for user to enter verification code and click continue
                await page.wait_for_selector('svg[aria-label="Home"], a[href="/direct/inbox/"]', timeout=60000)
        except:
            # No verification needed, continue
            print("No verification needed, continuing...")
        
        # Wait for home page to load
        await page.wait_for_selector('svg[aria-label="Home"]', timeout=10000)
        await page.screenshot(path="3_home_page.png")
        print("✅ Screenshot saved: 3_home_page.png")
        print("Successfully logged in!")
        
        # Step 2: Navigate to Direct Messages
        print("\n📨 Navigating to Direct Messages...")
        
        # Direct URL navigation is most reliable
        await page.goto("https://www.instagram.com/direct/inbox/")
        await page.wait_for_load_state("networkidle")
        
        # Take screenshot of DM page
        await page.screenshot(path="4_messages_page.png")
        print("✅ Screenshot saved: 4_messages_page.png")
        
        # Step 3: Extract message info
        print("\n🔍 Extracting message information...")
        messages_data = await page.evaluate('''
        () => {
            // Get all visible text that might be messages
            const allText = document.body.innerText;
            
            // Are we on the direct messages page?
            const onDMPage = window.location.href.includes('/direct/');
            
            // Get all elements that might contain message info
            const messageElements = Array.from(document.querySelectorAll('div')).filter(div => {
                const style = window.getComputedStyle(div);
                return div.childElementCount > 0 && 
                       style.display !== 'none' &&
                       div.clientHeight > 20 &&
                       div.innerText.length > 5 &&
                       div.innerText.length < 200;
            });
            
            // Extract message text
            const messages = messageElements.map(el => el.innerText.trim())
                .filter(text => text.length > 0)
                .filter((text, i, arr) => arr.indexOf(text) === i)  // Remove duplicates
                .slice(0, 20);  // Limit to 20 items
                
            return {
                url: window.location.href,
                title: document.title,
                on_dm_page: onDMPage,
                messages: messages
            };
        }
        ''')
        
        # Step 4: Save report
        print("\n📝 Creating DM summary report...")
        
        with open('instagram_messages_report.txt', 'w') as f:
            f.write("INSTAGRAM DIRECT MESSAGES REPORT\n")
            f.write("===============================\n\n")
            f.write(f"Date: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Username: {INSTAGRAM_USERNAME}\n")
            f.write(f"Page URL: {messages_data.get('url')}\n")
            f.write(f"Page Title: {messages_data.get('title')}\n")
            f.write(f"On DM Page: {'Yes' if messages_data.get('on_dm_page') else 'No'}\n\n")
            
            f.write("MESSAGE PREVIEWS:\n")
            f.write("----------------\n\n")
            
            for i, message in enumerate(messages_data.get('messages', [])):
                f.write(f"{i+1}. {message}\n\n")
        
        print("✅ Report saved to instagram_messages_report.txt")
        
        # Print summary to console
        print("\n📊 INSTAGRAM DM SUMMARY")
        print("=" * 50)
        print(f"Found {len(messages_data.get('messages', []))} potential message items")
        print(f"On DM page: {'Yes' if messages_data.get('on_dm_page') else 'No'}")
        print("=" * 50)
        
        # Sample of messages
        for i, msg in enumerate(messages_data.get('messages', [])[:5]):
            if i == 0:
                print("\nSample messages:")
            print(f"{i+1}. {msg[:75]}{'...' if len(msg) > 75 else ''}")
        
        if len(messages_data.get('messages', [])) > 5:
            print(f"...and {len(messages_data.get('messages', [])) - 5} more in the report")
        
        print("\n✅ Process complete! Check the screenshots and report file.")
        
    except Exception as e:
        # Handle errors and take error screenshot
        print(f"\n❌ Error: {e}")
        try:
            await page.screenshot(path="error_state.png")
            print("Error screenshot saved to error_state.png")
        except:
            print("Could not save error screenshot")
    
    finally:
        # Keep browser open for inspection
        print("\nPress Enter to close the browser and exit...")
        input()
        
        # Close browser
        await browser.close()
        await playwright.stop()

# Run the main function
asyncio.run(run_instagram_workflow())