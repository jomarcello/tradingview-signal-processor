from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time

# Instagram credentials
USERNAME = "itsjomarcello"
PASSWORD = "JmT!102510"

# Path to the ChromeDriver executable
CHROMEDRIVER_PATH = "/usr/local/bin/chromedriver"

def login_to_instagram(driver):
    """Log in to Instagram and handle popups."""
    driver.get("https://www.instagram.com/")
    WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.NAME, "username")))

    # Input username
    username_input = driver.find_element(By.NAME, "username")
    username_input.send_keys(USERNAME)

    # Input password
    password_input = driver.find_element(By.NAME, "password")
    password_input.send_keys(PASSWORD)

    # Submit login
    password_input.send_keys(Keys.RETURN)

    # Handle "Save Login Info" popup dynamically
    try:
        WebDriverWait(driver, 15).until(
            EC.element_to_be_clickable(
                (By.XPATH, "//div[@role='button' and (text()='Niet nu' or text()='Not Now')]")
            )
        ).click()
        print("Dismissed 'Save Login Info' popup.")
    except Exception:
        print("No 'Save Login Info' popup appeared or failed to dismiss it.")

    # Wait for the homepage or "Home" element
    try:
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.XPATH, "//div[text()='Home']"))
        )
        print("Successfully logged in and navigated to the home page.")
    except Exception as e:
        print(f"Failed to navigate to the home page after login: {e}")

def search_and_scrape_profiles(driver, query):
    """Search for profiles and scrape their data."""
    # Open Instagram search
    WebDriverWait(driver, 15).until(
        EC.presence_of_element_located((By.XPATH, "//input[@placeholder='Zoeken' or @placeholder='Search']"))
    )
    search_input = driver.find_element(By.XPATH, "//input[@placeholder='Zoeken' or @placeholder='Search']")
    search_input.send_keys(query)
    time.sleep(2)  # Wait for suggestions to load
    search_input.send_keys(Keys.RETURN)
    search_input.send_keys(Keys.RETURN)  # Open the first search result
    print(f"Searching for: {query}")

    # Wait for the profile page to load
    WebDriverWait(driver, 15).until(
        EC.presence_of_element_located((By.XPATH, "//h2[contains(@class, '_aacl')]"))
    )
    print(f"Scraping profile information for: {query}")

    # Scrape profile information
    try:
        profile_name = driver.find_element(By.XPATH, "//h1").text
        external_url = driver.find_element(By.XPATH, "//a[contains(@href, 'http')]").get_attribute("href")
        print(f"Profile Name: {profile_name}")
        print(f"External URL: {external_url}")
    except Exception as e:
        print(f"Error scraping profile information: {e}")

def main():
    """Main function to execute the script."""
    options = webdriver.ChromeOptions()
    options.add_argument("--disable-notifications")  # Disable pop-ups

    # Set up WebDriver
    driver = webdriver.Chrome(executable_path=CHROMEDRIVER_PATH, options=options)

    try:
        # Log in to Instagram
        login_to_instagram(driver)

        # Search and scrape profiles
        query = "villa_crete"  # Replace with your desired search term
        search_and_scrape_profiles(driver, query)

    except Exception as e:
        print(f"An error occurred: {e}")

    finally:
        # Close the browser
        driver.quit()

if __name__ == "__main__":
    main()