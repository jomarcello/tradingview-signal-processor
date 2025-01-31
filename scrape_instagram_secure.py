import os
import instaloader
from instaloader import Profile

# Initialize Instaloader
L = instaloader.Instaloader()

# Retrieve credentials from environment variables
USERNAME = os.getenv("INSTAGRAM_USERNAME")
PASSWORD = os.getenv("INSTAGRAM_PASSWORD")

# Login to Instagram
if USERNAME and PASSWORD:
    L.login(USERNAME, PASSWORD)
else:
    print("Error: Instagram credentials not found in environment variables.")
    exit()

# Function to scrape profiles by hashtag
def scrape_villa_profiles(hashtag, max_profiles=10):
    results = []
    hashtag_posts = L.get_hashtag_posts(hashtag)

    print(f"Scraping profiles for hashtag: #{hashtag}...")
    count = 0

    for post in hashtag_posts:
        if count >= max_profiles:  # Limit the number of profiles to scrape
            break

        try:
            profile = Profile.from_username(L.context, post.owner_username)
            profile_data = {
                "villa_name": profile.full_name,  # Villa name or full name
                "username": profile.username,
                "external_url": profile.external_url,
            }
            results.append(profile_data)
            print(f"Scraped: {profile_data}")

            count += 1
        except Exception as e:
            print(f"Error scraping profile: {e}")

    return results

# Call the function and scrape profiles for a hashtag
hashtag_to_scrape = "villacrete"  # Example: "villacrete"
villa_profiles = scrape_villa_profiles(hashtag_to_scrape, max_profiles=20)

# Save results to a file or print them
for villa in villa_profiles:
    print(villa)