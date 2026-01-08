#!/usr/bin/env python3
"""
Twitter Listener for Marketing OS

Searches Twitter for conversations matching configured keywords using Apify.
Outputs markdown signal files for further processing by Scorer and Drafter.

Usage:
    python twitter_listener.py /path/to/config.yaml

The config.yaml should contain:
    - Apify API credentials
    - Search queries
    - Output paths
    - Listener settings

See README.md for full configuration options.
"""

import argparse
import hashlib
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml
from apify_client import ApifyClient


def load_config(config_path: str) -> dict:
    """Load configuration from YAML file."""
    config_file = Path(config_path)
    if not config_file.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")
    
    with open(config_file) as f:
        return yaml.safe_load(f)


def generate_signal_id(tweet_url: str) -> str:
    """Generate a unique ID for a signal based on tweet URL."""
    return hashlib.md5(tweet_url.encode()).hexdigest()[:12]


def tweet_to_markdown(tweet: dict, matched_query: str) -> str:
    """Convert a tweet to markdown signal format."""
    
    # Extract tweet data with safe defaults
    tweet_id = tweet.get('id', '')
    author = tweet.get('author', {})
    author_username = author.get('userName', 'unknown')
    author_name = author.get('name', author_username)
    author_followers = author.get('followers', 0)
    author_bio = author.get('description', '')
    
    tweet_text = tweet.get('text', '')
    tweet_url = tweet.get('url', f"https://twitter.com/{author_username}/status/{tweet_id}")
    
    created_at = tweet.get('createdAt', '')
    likes = tweet.get('likeCount', 0)
    retweets = tweet.get('retweetCount', 0)
    replies = tweet.get('replyCount', 0)
    
    is_reply = tweet.get('isReply', False)
    
    signal_id = generate_signal_id(tweet_url)
    detected_at = datetime.now(timezone.utc).isoformat()
    
    # Escape quotes in strings for YAML
    author_name_escaped = author_name.replace('"', '\\"')
    author_bio_escaped = (author_bio or "No bio").replace('"', '\\"')
    
    frontmatter = f"""---
id: {signal_id}
source: twitter
url: {tweet_url}
author: "@{author_username}"
author_name: "{author_name_escaped}"
author_followers: {author_followers}
detected_at: {detected_at}
tweet_created_at: {created_at}
keywords_matched:
  - "{matched_query}"
engagement:
  likes: {likes}
  retweets: {retweets}
  replies: {replies}
is_reply: {str(is_reply).lower()}
status: unscored
---"""

    body = f"""
## Original Tweet

{tweet_text}

## Author Context

**@{author_username}** ({author_name})
- Followers: {author_followers:,}
- Bio: {author_bio if author_bio else "No bio"}

## Engagement

- Likes: {likes}
- Retweets: {retweets}
- Replies: {replies}

## Matched Query

`{matched_query}`

## Thread Context

{"This is a reply to another tweet." if is_reply else "This is an original tweet (not a reply)."}
"""

    return frontmatter + body


def load_existing_urls(inbox_path: Path) -> set:
    """Load URLs of existing signals to avoid duplicates."""
    existing_urls = set()
    
    if not inbox_path.exists():
        return existing_urls
    
    for file in inbox_path.glob("*.md"):
        try:
            content = file.read_text()
            for line in content.split('\n'):
                if line.startswith('url:'):
                    url = line.replace('url:', '').strip()
                    existing_urls.add(url)
                    break
        except Exception as e:
            print(f"Warning: Could not read {file}: {e}")
    
    return existing_urls


def save_signal(signal_content: str, tweet_url: str, inbox_path: Path) -> Path:
    """Save a signal to the inbox folder."""
    signal_id = generate_signal_id(tweet_url)
    timestamp = datetime.now().strftime("%Y-%m-%d-%H%M")
    filename = f"{timestamp}-twitter-{signal_id}.md"
    filepath = inbox_path / filename
    
    filepath.write_text(signal_content)
    return filepath


def run_listener(config: dict, config_dir: Path):
    """Run the Twitter listener with given configuration."""
    
    print("=" * 60)
    print("TWITTER LISTENER - Marketing OS")
    print("=" * 60)
    print(f"Started at: {datetime.now().isoformat()}")
    
    # Resolve paths relative to config file location
    inbox_path = (config_dir / config['paths']['signals_inbox']).resolve()
    print(f"Signals inbox: {inbox_path}")
    
    # Get Twitter config
    twitter_config = config.get('twitter', {})
    search_queries = twitter_config.get('search_queries', [])
    tweets_per_query = twitter_config.get('tweets_per_query', 20)
    min_likes = twitter_config.get('min_likes', 0)
    min_replies = twitter_config.get('min_replies', 0)
    language = twitter_config.get('language', 'en')
    
    print(f"Queries to run: {len(search_queries)}")
    print()
    
    # Ensure inbox exists
    inbox_path.mkdir(parents=True, exist_ok=True)
    
    # Load existing signals to avoid duplicates
    existing_urls = load_existing_urls(inbox_path)
    print(f"Existing signals in inbox: {len(existing_urls)}")
    print()
    
    # Initialize Apify client
    api_token = config['apify']['api_token']
    client = ApifyClient(api_token)
    
    # Track results
    total_found = 0
    total_new = 0
    total_saved = 0
    
    for query in search_queries:
        print(f"Searching: {query}")
        
        try:
            # Run the Twitter search scraper
            run_input = {
                "searchTerms": [query],
                "maxTweets": tweets_per_query,
                "sort": "Latest",
                "tweetLanguage": language,
            }
            
            run = client.actor("apidojo/twitter-scraper-v2").call(run_input=run_input)
            
            # Get results from the dataset
            tweets = list(client.dataset(run["defaultDatasetId"]).iterate_items())
            
            print(f"  Found: {len(tweets)} tweets")
            total_found += len(tweets)
            
            for tweet in tweets:
                tweet_url = tweet.get('url', '')
                
                # Skip duplicates
                if tweet_url in existing_urls:
                    continue
                
                # Skip if below engagement threshold
                likes = tweet.get('likeCount', 0)
                replies = tweet.get('replyCount', 0)
                if likes < min_likes or replies < min_replies:
                    continue
                
                total_new += 1
                
                # Convert to markdown and save
                signal_md = tweet_to_markdown(tweet, query)
                filepath = save_signal(signal_md, tweet_url, inbox_path)
                total_saved += 1
                existing_urls.add(tweet_url)
                
                print(f"  + Saved: {filepath.name}")
        
        except Exception as e:
            print(f"  ERROR: {e}")
            continue
        
        print()
    
    # Summary
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Total tweets found: {total_found}")
    print(f"New (not duplicates): {total_new}")
    print(f"Saved to inbox: {total_saved}")
    print(f"Finished at: {datetime.now().isoformat()}")
    
    return total_saved


def main():
    parser = argparse.ArgumentParser(
        description="Twitter Listener for Marketing OS",
        epilog="Example: python twitter_listener.py /path/to/config.yaml"
    )
    parser.add_argument(
        "config",
        help="Path to config.yaml file"
    )
    
    args = parser.parse_args()
    
    try:
        config = load_config(args.config)
        config_dir = Path(args.config).parent
        signals_saved = run_listener(config, config_dir)
        
        if signals_saved > 0:
            print(f"\nNext step: Run the Scorer on the new signals")
        else:
            print("\nNo new signals found.")
            
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except KeyError as e:
        print(f"Error: Missing config key: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
