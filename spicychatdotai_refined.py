import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
import time
import json
from datetime import datetime
import re

# ------------------------
# Spicychat.ai Web Scraper
# ------------------------

def initialise_webdriver(browser="safari"):
    """
    Initializes the WebDriver based on the specified browser.
    
    Args:
        browser (str): Browser to use ("safari", "chrome", or "firefox").
        
    Returns:
        WebDriver: A Selenium WebDriver instance for the specified browser.
        
    Raises:
        ValueError: If an unsupported browser is specified.
        Exception: For any WebDriver initialization errors.
    """
    try:
        if browser.lower() == "chrome":
            return webdriver.Chrome()
        elif browser.lower() == "firefox":
            return webdriver.Firefox()
        elif browser.lower() == "safari":
            return webdriver.Safari()
        else:
            raise ValueError(f"Unsupported browser: {browser}")
    except Exception as e:
        raise Exception(f"Failed to initialise WebDriver: {str(e)}")

def get_specialty(url="https://spicychat.ai", browser="safari"):
    """
    Fetch the description from the main page and the help overview content from the help page.
    :param url: URL of the website to scrape
    :param browser: The browser to use ('safari', 'chrome', 'firefox')
    :return: Dictionary with the specialty data
    """
    try:
        # Initialize the WebDriver (modularized)
        driver = initialise_webdriver(browser)
        driver.get(url)

        # Maximize the window for better interaction (optional)
        driver.maximize_window()

        # Step 1: Extract the description from the first tab
        description_div = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".flex.flex-col.justify-undefined.items-undefined.w-full"))
        )
        description = description_div.text.strip()

        # Step 2: Locate and click the help link
        help_link = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//*[@id='root']/div[2]/span/span/span/div[1]/nav/header/ul[1]/a[4]"))
        )
        help_link.click()

        # Allow time for the new tab to load
        time.sleep(2)

        # Switch to the new tab
        driver.switch_to.window(driver.window_handles[1])

        # Step 3: Extract the help overview content
        overview_elements = WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located((By.XPATH, "//*[@id='overview']/following-sibling::*[position()<=2]"))
        )
        help_overview = "\n".join(element.text.strip() for element in overview_elements)

        # Combine results into a dictionary
        specialty_text = {
            "description": description,
            "help_overview": help_overview
        }

        return {"specialty": specialty_text}

    except TimeoutException:
        return {"error": "Timeout occurred while waiting for an element to load."}
    except NoSuchElementException:
        return {"error": "Required element not found on the page."}
    except WebDriverException as e:
        return {"error": f"WebDriver error: {str(e)}"}
    except Exception as e:
        return {"error": f"An unexpected error occurred: {str(e)}"}
    finally:
        # Ensure the WebDriver is closed no matter what
        driver.quit()

def get_nsfw_policy():
    """
    Scrapes policy documents from provided URLs to determine NSFW-related policies.
    :return: A dictionary summarizing the NSFW policy for each document.
    """
    # URLs for policy documents
    policy_urls = {
        "community_guidelines": "https://docs.spicychat.ai/community-guidelines",
        "faqs": "https://docs.spicychat.ai/faqs",
        "terms_of_service": "https://spicychat.ai/terms",
        "privacy_policy": "https://spicychat.ai/privacy",
        "2257_compliance_statement": "https://spicychat.ai/2257",
    }
    
    # NSFW-related keyword categories
    categories = {
        "Advertised": ["explicit content", "nsfw content", "adult content", "nudity"],
        "Allowed but not advertised": ["content moderation", "user responsibility", "user-generated content"],
        "Prohibited": ["prohibited content", "restricted content", "no adult content", "banned"]
    }
    
    # Dictionary to store the results
    policies = {}

    for name, url in policy_urls.items():
        try:
            # Fetch the webpage
            response = requests.get(url, timeout=10)
            response.raise_for_status()  # Raise an exception for HTTP errors
            
            # Parse the HTML content
            soup = BeautifulSoup(response.text, 'html.parser')
            policy_text = soup.get_text(separator=" ").lower()  # Normalize and clean text
            
            # Categorize based on NSFW-related keywords
            nsfw_category = "Unknown"
            for category, keywords in categories.items():
                if any(keyword in policy_text for keyword in keywords):
                    nsfw_category = category
                    break
            
            # Store the results for the current document
            policies[name] = {
                "url": url,
                "nsfw_policy_category": nsfw_category,
                "summary": (
                    f"NSFW policy classified as '{nsfw_category}' based on detected keywords."
                    if nsfw_category != "Unknown" else
                    "NSFW policy not explicitly mentioned."
                )
            }
        except requests.exceptions.RequestException as e:
            # Handle network-related issues
            policies[name] = {
                "url": url,
                "nsfw_policy_category": "Error",
                "summary": f"Failed to fetch policy document: {str(e)}"
            }
        except Exception as e:
            # Handle unexpected issues
            policies[name] = {
                "url": url,
                "nsfw_policy_category": "Error",
                "summary": f"An unexpected error occurred: {str(e)}"
            }

    return {"nsfw_policy": policies}

# *********************************************************************************************************************************
def clean_plan_data(plan_str, pricing_type="month"):
    """Cleans and organizes plan data from the input string."""
    plans = {}

    # Split the input by 'Subscribe' to capture each pricing tier
    tier_sections = plan_str.split("Subscribe")

    # Define tier prices dynamically
    tier_prices = {
        "Free": "$ 0.00/ month" if pricing_type == "month" else "$ 0.00/ year",
        "Get a Taste": "$ 5.00/ month" if pricing_type == "month" else "$ 39.95/ year",
        "True Supporter": "$ 14.95/ month" if pricing_type == "month" else "$ 115.00/ year",
        "I'm All In": "$ 24.95/ month" if pricing_type == "month" else "$ 175.00/ year",
    }

    for section in tier_sections:
        section = section.strip()
        if section:
            # Match tier name dynamically using known tier names
            tier_name = next((name for name in tier_prices if f" {name} " in section), None)
            if not tier_name:
                continue

            # Extract the price based on the tier name
            price = tier_prices.get(tier_name, "Unknown")

            # Extract features dynamically
            features = extract_features(section)

            # Add the tier's data to the dictionary
            plans[tier_name] = {
                "price": price,
                "features": features
            }

    return plans

def extract_features(tier_section):
    """Extracts features from the section of the tier string."""
    features = []

    # Define patterns and their feature names for dynamic extraction
    feature_patterns = {
        r"Unlimited Messages": "Unlimited Messages",
        r"Full Library Of Chatbots": "Full Library Of Chatbots",
        r"NSFW Content": "NSFW Content",
        r"Create Your Own Character": "Create Your Own Character",
        r"Save Chats, Favourite Chatbots": "Save Chats, Favourite Chatbots",
        r"No Ads": "No Ads",
        r"Skip the Waiting Lines": "Skip the Waiting Lines",
        r"Memory Manager": "Memory Manager",
        r"User Personas - upto (\\d+)": "User Personas - up to {0}",
        r"4K Context \(Memory\)": "4K Context (Memory)",
        r"Semantic Memory 2\.0": "Semantic Memory 2.0",
        r"Longer Responses": "Longer Responses",
        r"Conversation Images": "Conversation Images",
        r"Access to additional Models": "Access to additional Models",
        r"Priority Generation Queue": "Priority Generation Queue",
        r"Access to advanced models": "Access to advanced models",
        r"Conversation Images on private Chatbots": "Conversation Images on private Chatbots",
        r"Up to 16K Context \(Memory\)": "Up to 16K Context (Memory)",
    }

    # Check for matching patterns in the section
    for pattern, feature_name in feature_patterns.items():
        match = re.search(pattern, tier_section)
        if match:
            features.append(feature_name.format(*match.groups()))

    return features

def get_pricing_info():
    """Extracts and organizes pricing information from the website."""
    driver = webdriver.Safari()
    url = "https://spicychat.ai/subscribe"

    try:
        driver.get(url)

        # Get monthly pricing info
        monthly_pricing_info = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".flex.justify-undefined.items-undefined.flex-wrap.justify-center.items-end"))
        ).text

        # Click on the annual plans button
        annual_plans_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//button[@data-key='annual_plans']"))
        )
        annual_plans_button.click()

        # Get annual pricing info after the annual plans button is clicked
        annual_pricing_info = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".flex.justify-undefined.items-undefined.flex-wrap.justify-center.items-end"))
        ).text

        # Clean up the pricing data for both monthly and annual plans
        monthly_data = clean_plan_data(monthly_pricing_info, pricing_type="month")
        annual_data = clean_plan_data(annual_pricing_info, pricing_type="year")

        # Combine and format the pricing information
        pricing_info = {
            "monthly subscription info": monthly_data,
            "annual subscription info": annual_data,
        }

        return {"pricing": pricing_info}

    except Exception as e:
        return {"error": str(e)}

    finally:
        driver.quit()
# *********************************************************************************************************************************

def get_useful_links():
    """
    Returns a dictionary of useful links, ensuring all URLs are valid and reachable.
    """
    links = {
        "docs": "https://docs.spicychat.ai",
        "community_guidelines": "https://docs.spicychat.ai/community-guidelines",
        "faqs": "https://docs.spicychat.ai/faqs",
        "terms_of_service": "https://spicychat.ai/terms",
        "privacy_policy": "https://spicychat.ai/privacy",
        "refund_policy": "https://spicychat.ai/refund",
        "report_content": "https://spicychat.ai/report",
        "2257_Record_Keeping_Requirements_Compliance_Statement": "https://spicychat.ai/2257",
        "discord": "https://discord.com/invite/spicychatai",
        "x_twitter": "https://x.com/SpicyChatAI",
        "reddit": "https://www.reddit.com/r/SpicyChatAI/",
        "affiliate_program": "https://promote.spicychat.ai",
        "external_links": "https://docs.spicychat.ai/external-links"
    }

    # Validate URLs
    validated_links = {}
    for name, url in links.items():
        try:
            # Make a request to check if the URL is accessible
            response = requests.get(url, timeout=5)
            response.raise_for_status()  # Will raise an error for 4xx or 5xx status codes
            
            validated_links[name] = {
                "url": url,
                "status": "valid",
                "status_code": response.status_code
            }
        except requests.exceptions.RequestException as e:
            # Handle connection errors and invalid URLs
            validated_links[name] = {
                "url": url,
                "status": "invalid",
                "error_message": str(e)
            }

    return {"useful_links": validated_links}

def get_server_status():
    # Set up the Selenium WebDriver (using Safari in this case)
    driver = webdriver.Safari()
    status_url = "<https://www.isitdownrightnow.com/downorjustme.php>"
    first_checked = datetime.now().strftime("%Y-%m-%d %H:%M:%S")  # Timestamp for the first check
    response_time = 0
    status_message = "Status not determined."

    try:
        # Open the URL
        driver.get(status_url)

        # Wait for the input field to be present and interactable
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.NAME, "url"))
        )
        input_field = driver.find_element(By.NAME, "url")

        # Clear the field and type the website to check
        input_field.clear()
        input_field.send_keys("spicychat.ai")

        # Record the time before submitting
        submit_time_start = time.time()
        input_field.send_keys(Keys.RETURN)  # Simulates pressing the Enter key

        # Wait for either "statusup" or "statusdown" element to appear
        WebDriverWait(driver, 10).until(
            lambda d: d.find_elements(By.CLASS_NAME, "statusup") or d.find_elements(By.CLASS_NAME, "statusdown")
        )

        # Check which status element is present and extract the status message
        if driver.find_elements(By.CLASS_NAME, "statusup"):
            status_message = driver.find_element(By.CLASS_NAME, "statusup").text.strip()
        elif driver.find_elements(By.CLASS_NAME, "statusdown"):
            status_message = driver.find_element(By.CLASS_NAME, "statusdown").text.strip()
        else:
            status_message = "[Error] Unable to determine server status (due to element with specified class not found)."

        # Calculate response time
        response_time = round(time.time() - submit_time_start, 3)  # Time in seconds, rounded to 3 decimal places

    except TimeoutException:
        status_message = "Timeout occurred while waiting for server status element to load."
    except NoSuchElementException:
        status_message = "Required element not found on the page."
    except Exception as e:
        status_message = f"An unexpected error occurred: {str(e)}"
    finally:
        last_checked = datetime.now().strftime("%Y-%m-%d %H:%M:%S")  # Timestamp for the last check
        driver.quit()  # Ensure WebDriver closes properly

    # Return the result as a structured dictionary
    return {
        "server_status": {
            "url": "<https://www.spicychat.ai>",  # The URL being checked
            "first_checked": first_checked,    # First checked timestamp
            "status": status_message,          # The extracted or fallback status message
            "response_time": response_time,    # Time taken to get the status
            "error": None if "error" not in status_message.lower() else status_message,  # Set error if present
            "last_checked": last_checked       # Last checked timestamp
        }
    }

def get_language_support():
    url = "https://aimojo.io/tools/spicychat-ai/"
    
    # Initialize WebDriver
    driver = webdriver.Safari()
    language_support = "Language support information not found."  # Default message
    
    try:
        # Open the URL
        driver.get(url)
        
        # Wait for the page to load and stabilize
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div#faq-question-1726732104611 p"))
        )
        
        # Get the page source after ensuring the element is loaded
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        
        # Extract the text content of the specific element
        target_element = soup.select_one("div#faq-question-1726732104611 p")
        if target_element:
            language_support = target_element.text.strip()
        else:
            language_support = "Language support details not found in the specified element."
    
    except TimeoutException:
        language_support = "Failed to load the page or locate the language support element within the timeout period."
    except Exception as e:
        language_support = f"An unexpected error occurred: {str(e)}"
    finally:
        # Ensure the browser closes properly
        driver.quit()
    
    return {"languages_supported": language_support}

# ------------------------
# Save Data to JSON
# ------------------------

def save_to_json(data, filename="spicychat_dot_ai_data.json"):
    with open(f"./{filename}", "w") as json_file:
        json.dump(data, json_file, indent=4)

# ------------------------
# Main Program
# ------------------------

def main():
    data = {}

    data.update(get_specialty())
    # print(data)

    data.update(get_nsfw_policy())
    # print(data["nsfw_policy"])

    data.update(get_pricing_info())
    # print(data["pricing"])

    data.update(get_useful_links())
    # print(data["useful_links"])

    data.update(get_server_status())
    # print(data["server_status"])

    data.update(get_language_support())
    # print(data["languages_supported"])
    
    save_to_json(data)

if __name__ == "__main__":
    main()
