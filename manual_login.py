from selenium import webdriver
from selenium.webdriver.chrome.service import Service
import time

# Path to ChromeDriver
CHROMEDRIVER_PATH = "/usr/local/bin/chromedriver"

# Start the ChromeDriver service
service = Service(CHROMEDRIVER_PATH)

# Set up WebDriver
driver = webdriver.Chrome(service=service)

# Open Instagram
driver.get("https://www.instagram.com/")

# Pause to allow manual login
print("Log in manually and handle any pop-ups. Press ENTER in the terminal when done.")
input()  # Wait for user input in terminal

# Confirm manual login and keep the session open
print("Logged in successfully! You can now save cookies or continue automation.")
time.sleep(30)  # Keep the browser open for additional checks if needed

# Close the browser
driver.quit()