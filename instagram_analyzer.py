import instaloader
from collections import Counter
from datetime import datetime, timedelta

def analyze_profile_interactions(username, password, days_to_analyze=30):
    """
    Analyseert wie het meest interacteert met uw Instagram-profiel
    """
    # Instaloader instantie maken
    L = instaloader.Instaloader()
    
    try:
        # Inloggen op Instagram
        L.login(username, password)
        
        # Eigen profiel ophalen
        profile = instaloader.Profile.from_username(L.context, username)
        
        # Datum berekenen vanaf wanneer we willen analyseren
        since_date = datetime.now() - timedelta(days=days_to_analyze)
        
        # Lijsten voor interacties
        likes_by_user = Counter()
        comments_by_user = Counter()
        
        # Posts ophalen en analyseren
        print(f"Posts analyseren van de laatste {days_to_analyze} dagen...")
        for post in profile.get_posts():
            if post.date < since_date:
                break
                
            # Likes analyseren
            for like in post.get_likes():
                likes_by_user[like.username] += 1
                
            # Comments analyseren
            for comment in post.get_comments():
                comments_by_user[comment.owner.username] += 1
                
        # Resultaten weergeven
        print("\nTop 10 profielen die uw posts liken:")
        for username, count in likes_by_user.most_common(10):
            print(f"{username}: {count} likes")
            
        print("\nTop 10 profielen die commentaar geven:")
        for username, count in comments_by_user.most_common(10):
            print(f"{username}: {count} comments")
            
    except instaloader.exceptions.InstaloaderException as e:
        print(f"Er is een fout opgetreden: {e}")

if __name__ == "__main__":
    username = input("Voer uw Instagram gebruikersnaam in: ")
    password = input("Voer uw Instagram wachtwoord in: ")
    days = int(input("Hoeveel dagen wilt u analyseren? (standaard 30): ") or 30)
    
    analyze_profile_interactions(username, password, days) 