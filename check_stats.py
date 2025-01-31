from email_campaign import check_tracking_stats

stats = check_tracking_stats()
for stat in stats:
    print(f"""
    Lead ID: {stat[0]}
    Email: {stat[1]}
    Opens: {stat[2]}
    Clicks: {stat[3]}
    """)
