import feedparser
from supabase import create_client, Client
from dotenv import load_dotenv
import os
from dateutil import parser
import re

# Load environment variables
load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

# Define your RSS sources
RSS_FEEDS = [
    {
        "name": "arXiv cs.LG",
        "url": "https://rss.arxiv.org/rss/cs.LG",
        "article_type": "Paper"
    },
    {
        "name": "arXiv cs.AI",
        "url": "https://rss.arxiv.org/rss/cs.AI",
        "article_type": "Paper"
    },
    {
        "name": "Google AI Blog",
        "url": "https://blog.google/technology/ai/rss/",
        "article_type": "Blog"
    },
    {
        "name": "HuggingFace Blog",
        "url": "https://huggingface.co/blog/feed.xml",
        "article_type": "Blog"
    },
    {
        "name": "DeepMind Blog",
        "url": "https://deepmind.com/blog/rss.xml",
        "article_type": "Blog"
    },
    {
        "name": "BAIR Blog",
        "url": "https://bair.berkeley.edu/blog/feed.xml",
        "article_type": "Blog"
    }
]

def strip_html(raw_text):
    """Remove HTML tags from summary text"""
    clean = re.compile('<.*?>')
    return re.sub(clean, '', raw_text)

def ingest_feed(feed_config):
    print(f"Parsing: {feed_config['name']}")
    feed = feedparser.parse(feed_config["url"])
    entries = feed.entries

    records = []
    skipped = 0
    for entry in entries:
        title = entry.get("title", "No Title")
        link = entry.get("link")
        summary_raw = entry.get("summary", "")
        published_str = entry.get("published")

        if not link or not published_str:
            skipped += 1
            continue

        try:
            # Flexible universal date parser (handles GMT, UTC, +0000 etc.)
            published_dt = parser.parse(published_str)
        except Exception as e:
            print(f"⚠️ Failed parse date: {published_str} | Skip entry: {title[:40]}...")
            skipped += 1
            continue

        clean_summary = strip_html(summary_raw)

        record = {
            "title": title,
            "url": link,
            "summary": clean_summary,
            "source": feed_config["name"],
            "published_at": published_dt.isoformat(),
            "article_type": feed_config["article_type"]
        }
        records.append(record)

    # Upsert into DB, ignore duplicate urls
    if records:
        response = supabase.table("research_articles").upsert(records, on_conflict="url").execute()
        print(f"✅ Upserted {len(records)} entries | Skipped {skipped} for {feed_config['name']}")
    else:
        print(f"No valid entries for {feed_config['name']}")

if __name__ == "__main__":
    for feed in RSS_FEEDS:
        ingest_feed(feed)
    print("\n🎉 All feed ingestion complete")