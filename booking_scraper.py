"""Web scraping logic for automating tennis court bookings."""
import os
import time
from typing import Optional, Dict
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.chrome.service import Service
import logging
import re

logger = logging.getLogger(__name__)


class BookingScraper:
    def __init__(self, url: str, username: str, password: str, headless: bool = True):
        """Initialize the booking scraper with credentials."""
        self.url = url
        self.username = username
        self.password = password
        self.headless = headless
        self.driver = None
    
    def _setup_driver(self):
        """Set up Chrome WebDriver with appropriate options."""
        chrome_options = Options()
        if self.headless:
            chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        
    # Use the environment variables defined in your Dockerfile
        chrome_bin = os.getenv('CHROME_BIN', '/usr/bin/chromium')
        driver_path = os.getenv('CHROMEDRIVER_PATH', '/usr/bin/chromium-driver')
        
        chrome_options.binary_location = chrome_bin
        service = Service(executable_path=driver_path)
        
        try:
            # Pass the service object to the driver
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        except Exception as e:
            logger.error(f"Failed to initialize Chrome driver: {e}")
            raise
    
    def login(self) -> bool:
        """Log in to the booking website. Returns True if successful."""
        if not self.driver:
            self._setup_driver()
        
        try:
            self.driver.get(self.url)
            time.sleep(2)  # Wait for page to load
            
            # Try to find login elements - these selectors may need adjustment
            # Common patterns: username/email input, password input, submit button
            wait = WebDriverWait(self.driver, 10)
            
            # Look for username field (common selectors)
            username_selectors = [
                "#_com_liferay_login_web_portlet_LoginPortlet_login", # Exact match from your screenshot
                "input[name*='login']",
                "input[id*='login']"
            ]
            
            username_field = None
            for selector in username_selectors:
                try:
                    username_field = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))
                    break
                except TimeoutException:
                    continue
            
            if not username_field:
                logger.error("Could not find username field")
                return False
            
            # Look for password field
            password_selectors = [
                "#_com_liferay_login_web_portlet_LoginPortlet_password", # Likely match for password
                "input[type='password']",
                "#password"
            ]
            
            password_field = None
            for selector in password_selectors:
                try:
                    password_field = self.driver.find_element(By.CSS_SELECTOR, selector)
                    break
                except NoSuchElementException:
                    continue
            
            if not password_field:
                logger.error("Could not find password field")
                return False
            
            # Enter credentials
            username_field.clear()
            username_field.send_keys(self.username)
            time.sleep(0.5)
            
            password_field.clear()
            password_field.send_keys(self.password)
            time.sleep(0.5)
            
            # Find and click submit button
            submit_selectors = [
                "button[type='submit']",
                "input[type='submit']",
                "button:contains('Login')",
                "button:contains('Sign in')",
                ".login-button",
                "#login-button"
            ]
            
            submit_button = None
            for selector in submit_selectors:
                try:
                    if 'contains' in selector:
                        # XPath for text contains
                        submit_button = self.driver.find_element(By.XPATH, 
                            f"//button[contains(text(), 'Login') or contains(text(), 'Sign in')]")
                    else:
                        submit_button = self.driver.find_element(By.CSS_SELECTOR, selector)
                    break
                except NoSuchElementException:
                    continue
            
            if submit_button:
                submit_button.click()
            else:
                # Try pressing Enter on password field
                password_field.send_keys("\n")
            
            time.sleep(3)  # Wait for login to complete
            
            # Check if login was successful (verify we're not on login page anymore)
            current_url = self.driver.current_url
            if 'login' in current_url.lower():
                logger.warning("Still on login page, login may have failed")
                return False
            
            logger.info("Login successful")
            return True
            
        except Exception as e:
            logger.error(f"Login failed: {e}")
            return False
    
    def _convert_date_format(self, date_str: str) -> str:
        """Convert date from YYYY-MM-DD to MM/DD/YYYY format."""
        try:
            date_obj = datetime.strptime(date_str, '%Y-%m-%d')
            return date_obj.strftime('%m/%d/%Y')
        except ValueError:
            logger.error(f"Invalid date format: {date_str}")
            return date_str
    
    def _parse_date_for_grid(self, date_str: str) -> tuple:
        """
        Parse date to extract day number and month name for grid selection.
        Returns tuple: (day_number, month_name, month_abbrev)
        """
        try:
            date_obj = datetime.strptime(date_str, '%Y-%m-%d')
            day_number = str(date_obj.day)
            month_name = date_obj.strftime('%B')  # Full month name (e.g., "January")
            month_abbrev = date_obj.strftime('%b')  # Abbreviated (e.g., "Jan")
            return (day_number, month_name, month_abbrev)
        except ValueError:
            logger.error(f"Invalid date format: {date_str}")
            return (None, None, None)
    
    def _convert_time_format(self, time_str: str) -> str:
        """Convert time from HH:MM to HH:MM AM/PM format (e.g., "06:00 AM")."""
        try:
            # Parse time in HH:MM format
            time_obj = datetime.strptime(time_str, '%H:%M')
            # Use %I for 12-hour format with leading zero (01-12)
            return time_obj.strftime('%I:%M %p')
        except ValueError:
            # If already in correct format, return as is
            return time_str
    
    def _parse_court_number(self, court_preference: Optional[str]) -> Optional[int]:
        """Extract court number from court preference string."""
        if not court_preference:
            return None
        
        # Try to extract number from strings like "Court 1", "1", "Indoor Court 1", etc.
        match = re.search(r'\d+', str(court_preference))
        if match:
            return int(match.group())
        return None
    
    def _select_dropdown_option(self, label_id: str, option_text: str, wait_time: int = 10) -> bool:
        """Select an option from a PrimeFaces dropdown menu."""
        try:
            wait = WebDriverWait(self.driver, wait_time)
            
            # Click the label to open the dropdown
            label = wait.until(EC.element_to_be_clickable((By.ID, label_id)))
            label.click()
            time.sleep(0.5)
            
            # Wait for dropdown panel to appear and find the option
            # PrimeFaces dropdowns typically have options in a panel with class 'ui-selectonemenu-items'
            # Try data-label attribute first (more reliable), then fallback to text matching
            option_xpath = (
                f"//li[contains(@class, 'ui-selectonemenu-item') and "
                f"(@data-label='{option_text}' or normalize-space(text())='{option_text}')]"
            )
            
            option = wait.until(EC.element_to_be_clickable((By.XPATH, option_xpath)))
            
            # Use JavaScript click for reliability with PrimeFaces dropdowns
            try:
                option.click()
            except Exception:
                self.driver.execute_script("arguments[0].click();", option)
            
            time.sleep(0.5)
            
            return True
        except Exception as e:
            logger.error(f"Failed to select dropdown option '{option_text}' from {label_id}: {e}")
            return False
    
    def make_booking(self, date: str, time_slot: str, court_preference: Optional[str] = None, duration_minutes: int = 30) -> Dict[str, any]:
        """
        Two-Step Booking:
        1. Target exact entry point (data-area-id="11", 6:00 AM).
        2. Use robust multi-stage click sequence on the parent cell (TD).
        3. Fill form details via dropdowns.
        """
        try:
            self.driver.get(self.url)
            wait = WebDriverWait(self.driver, 15)
            time.sleep(3) 
            
            day_number, month_name, month_abbrev = self._parse_date_for_grid(date)
            
            # --- STEP 1: DATE SELECTION ---
            date_link_xpath = (
                "//div[contains(@class, 'horizontal-dates')]//a["
                f".//span[contains(@class, 'calendar-date') and normalize-space()='{day_number}'] and "
                f".//span[contains(@class, 'calendar-year') and (normalize-space()='{month_name}' or normalize-space()='{month_abbrev}')]"
                "]"
            )
            date_link = wait.until(EC.element_to_be_clickable((By.XPATH, date_link_xpath)))
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center', inline: 'center'});", date_link)
            time.sleep(1)
            self.driver.execute_script("arguments[0].click();", date_link)
            
            logger.info(f"Clicked date: {day_number} {month_name}")
            time.sleep(4) # Wait for AJAX update

            # --- STEP 2: ROBUST ENTRY CLICK (ID: 11 @ 6:00 AM) ---
            ENTRY_TIME = "06:00 AM"
            ENTRY_ID = "11" # As found in your HTML snippet
            
            # Locate the div, then move up to the clickable TD
            target_xpath = f"//div[@data-area-id='{ENTRY_ID}' and @data-start-time='{ENTRY_TIME}']/ancestor::td[1]"
            
            try:
                target_cell = wait.until(EC.presence_of_element_located((By.XPATH, target_xpath)))
                
                # Scroll the cell into view
                self.driver.execute_script("arguments[0].scrollIntoView({block: 'center', inline: 'center'});", target_cell)
                time.sleep(1)
                
                # Multi-stage click fallback from your original reference code
                clicked = False
                try:
                    target_cell.click()
                    logger.info("Clicked grid cell directly")
                    clicked = True
                except Exception:
                    try:
                        logger.info("Direct click failed, trying JavaScript click")
                        self.driver.execute_script("arguments[0].click();", target_cell)
                        clicked = True
                    except Exception as e:
                        logger.error(f"All click methods failed on the grid cell: {e}")

                if not clicked:
                    return {'success': False, 'message': 'Found entry slot but could not trigger the click event.'}
                
            except TimeoutException:
                return {'success': False, 'message': f'Entry slot (ID {ENTRY_ID} at {ENTRY_TIME}) not found in grid.'}

            time.sleep(5) # Wait for Reservation Information screen to fully render

            # --- STEP 3: SELECT ACTUAL DETAILS VIA DROPDOWNS ---
            # 1. Select ACTUAL Court (e.g., 'Outdoor Court 7')
            if court_preference:
                court_label_id = "_activities_WAR_northstarportlet_:activityForm:j_idt1068_label"
                if not self._select_dropdown_option(court_label_id, court_preference):
                    logger.warning(f"Could not select {court_preference}, proceeding with current selection.")
                time.sleep(1)

            # 2. Select ACTUAL Time
            formatted_time = self._convert_time_format(time_slot)
            time_label_id = "_activities_WAR_northstarportlet_:activityForm:fromTime_label"
            if not self._select_dropdown_option(time_label_id, formatted_time):
                return {'success': False, 'message': f'Could not select time {formatted_time} in form dropdown.'}
            time.sleep(1)

            # 3. Select ACTUAL Duration
            duration_label_id = "_activities_WAR_northstarportlet_:activityForm:j_idt1082_label"
            if not self._select_dropdown_option(duration_label_id, str(duration_minutes)):
                logger.warning(f"Could not select duration {duration_minutes}")

            time.sleep(1)
            
            # Submit the booking form
            # Look for submit button - common patterns for PrimeFaces forms
            submit_selectors = [
                # 1. Best: Target by the specific PrimeFaces 'btn-save' class and type
                "button[type='submit'].btn-save", 
                
                # 2. Strong: Target the specific span text 'Save' inside the activity form button
                "//button[contains(@id, 'activityForm')]//span[contains(text(), 'Save')]",
                
                # 3. Flexible: Target by the specific button class used in the screenshot
                "button.ui-area-btn-success", 
                
                # 4. Fallback: Generic PrimeFaces button with 'Save' text
                "//button[contains(@class, 'ui-button')]//span[normalize-space()='Save']",
                
                # Keep the originals as ultimate backups
                "button[type='submit']",
                "//button[contains(@class, 'ui-button')]"
            ]
            
            submitted = False
            for selector in submit_selectors:
                try:
                    if selector.startswith('//'):
                        submit_button = wait.until(EC.presence_of_element_located((By.XPATH, selector)))
                    else:
                        submit_button = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, selector)))
                    
                    # Scroll into view and use JavaScript click for reliability
                    self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", submit_button)
                    time.sleep(0.5)
                    
                    # Try regular click first, fallback to JavaScript click
                    try:
                        submit_button.click()
                        logger.info("Clicked submit button using regular click")
                    except Exception:
                        logger.info("Regular click failed, using JavaScript click")
                        self.driver.execute_script("arguments[0].click();", submit_button)
                    
                    submitted = True
                    break
                except (NoSuchElementException, TimeoutException):
                    continue
                except Exception as e:
                    logger.debug(f"Error with selector {selector}: {e}")
                    continue
            
            if not submitted:
                return {'success': False, 'message': 'Could not find or click submit button'}
            
            time.sleep(2)  # Wait for submission to process
            
            # Check for success/error messages
            # PrimeFaces typically shows messages in specific divs
            success_indicators = [
                # 1. Best: Target the specific ID and class from your HTML
                "//div[@id='_activities_WAR_northstarportlet_:activityForm:activityMessage']//label[contains(@class, 'portlet-msg-success')]",
                
                # 2. Specific: Target the exact success text found in your snippet
                "//label[contains(text(), 'Reservation created successfully')]",
                
                # 3. Flexible: Search for 'successfully' in any label within the activity form
                "//label[contains(@class, 'activity-message') and contains(text(), 'successfully')]",
                
                # 4. Fallbacks for standard PrimeFaces messages
                "//div[contains(@class, 'ui-messages-info')]",
                "//div[contains(@class, 'ui-growl-item')]"
            ]
            
            for indicator in success_indicators:
                try:
                    element = self.driver.find_element(By.XPATH, indicator)
                    if element and element.is_displayed():
                        message_text = element.text
                        return {'success': True, 'message': f'Booking confirmed for {date} at {time_slot}: {message_text}'}
                except NoSuchElementException:
                    continue
            
            # Check for error messages
            error_indicators = [
                "//div[contains(@class, 'ui-messages-error')]",
                "//div[contains(@class, 'ui-message-error')]",
                "//div[contains(@class, 'ui-growl-error')]",
                "//div[contains(text(), 'error')]",
                "//div[contains(text(), 'unavailable')]",
                "//div[contains(text(), 'already booked')]"
            ]
            
            for indicator in error_indicators:
                try:
                    element = self.driver.find_element(By.XPATH, indicator)
                    if element and element.is_displayed():
                        error_text = element.text
                        return {'success': False, 'message': f'Booking failed: {error_text}'}
                except NoSuchElementException:
                    continue
            
            # If we get here, couldn't determine success/failure from messages
            # The form submission may have succeeded but no clear message was displayed
            # Return a neutral result - the user can verify manually
            return {'success': False, 'message': 'Could not determine booking status - no clear success or error message found. Please verify manually.'}
            
        except Exception as e:
            logger.error(f"Booking failed: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return {'success': False, 'message': f'Booking error: {str(e)}'}
    
    def close(self):
        """Close the browser driver."""
        if self.driver:
            self.driver.quit()
            self.driver = None
