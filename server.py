#!/usr/bin/env python3
"""
Today X! Backend Server
Proxies XRSS feeds and serves the frontend
"""

import os
import json
import xml.etree.ElementTree as ET
from datetime import datetime
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError
from urllib.parse import urlparse, parse_qs
import ssl
import html

# Configuration
RSSHUB_URL = os.getenv('RSSHUB_URL', 'http://localhost:1200')
ACCESS_KEY = os.getenv('ACCESS_KEY', 'todayx2026')
PORT = int(os.getenv('PORT', 8000))

# Top 10 Crypto Accounts
ACCOUNTS = [
    {'id': 'VitalikButerin', 'name': 'Vitalik Buterin', 'handle': '@VitalikButerin', 'bio': 'Ethereum co-founder'},
    {'id': 'CryptoHayes', 'name': 'Arthur Hayes', 'handle': '@CryptoHayes', 'bio': 'BitMEX co-founder'},
    {'id': 'justinsuntron', 'name': 'Justin Sun', 'handle': '@justinsuntron', 'bio': 'TRON founder'},
    {'id': 'jack', 'name': 'Jack Dorsey', 'handle': '@jack', 'bio': 'Block CEO, Bitcoin advocate'},
    {'id': 'aantonop', 'name': 'Andreas Antonopoulos', 'handle': '@aantonop', 'bio': 'Bitcoin educator'},
    {'id': 'MMCrypto', 'name': 'MMCrypto', 'handle': '@MMCrypto', 'bio': 'Crypto trader'},
    {'id': 'cabornetwho', 'name': 'CZ Binance', 'handle': '@cabornetwho', 'bio': 'Former Binance CEO'},
    {'id': 'MessariCrypto', 'name': 'Messari', 'handle': '@MessariCrypto', 'bio': 'Crypto research'},
    {'id': 'TheBlock__', 'name': 'The Block', 'handle': '@TheBlock__', 'bio': 'Crypto news'},
    {'id': 'WatcherGuru', 'name': 'Watcher.Guru', 'handle': '@WatcherGuru', 'bio': 'Breaking crypto news'},
]

def fetch_rsshub_feed(username):
    """Fetch RSS feed from RSSHub for a single user"""
    # RSSHub Twitter路由: /twitter/user/:id
    url = f"{RSSHUB_URL}/twitter/user/{username}?key={ACCESS_KEY}"

    try:
        req = Request(url, headers={'User-Agent': 'TodayX/1.0'})
        # Create SSL context for HTTPS
        ctx = ssl.create_default_context()
        with urlopen(req, timeout=30, context=ctx) as response:
            return response.read().decode('utf-8')
    except (URLError, HTTPError) as e:
        print(f"Error fetching RSSHub feed for {username}: {e}")
        return None
    except Exception as e:
        print(f"Unexpected error fetching feed for {username}: {e}")
        return None

def fetch_all_feeds():
    """Fetch RSS feeds for all accounts"""
    all_tweets = []
    for account in ACCOUNTS:
        rss_xml = fetch_rsshub_feed(account['id'])
        if rss_xml:
            tweets = parse_rss_to_json(rss_xml, account)
            all_tweets.extend(tweets)
    return all_tweets

def parse_rss_to_json(rss_xml, account=None):
    """Parse RSS XML to JSON format"""
    if not rss_xml:
        return []

    tweets = []
    try:
        root = ET.fromstring(rss_xml)
        channel = root.find('channel')
        if channel is None:
            return []

        for item in channel.findall('item'):
            title = item.find('title')
            link = item.find('link')
            description = item.find('description')
            pub_date = item.find('pubDate')

            # Use provided account or try to extract from link
            if account is None:
                account_id = None
                if link is not None and link.text:
                    parts = link.text.split('/')
                    if len(parts) >= 4:
                        account_id = parts[3]
                account = next((a for a in ACCOUNTS if a['id'].lower() == (account_id or '').lower()), None)

            content = ''
            if description is not None and description.text:
                content = html.unescape(description.text)
                # Remove HTML tags
                content = content.replace('<br>', ' ').replace('</p>', ' ')
                import re
                content = re.sub('<[^<]+?>', '', content)
            elif title is not None and title.text:
                content = html.unescape(title.text)

            # Truncate to 500 chars
            if len(content) > 500:
                content = content[:497] + '...'

            tweet = {
                'id': link.text if link is not None else str(len(tweets)),
                'accountId': account['id'] if account else 'unknown',
                'accountName': account['name'] if account else 'Unknown',
                'accountHandle': account['handle'] if account else '@unknown',
                'content': content.strip(),
                'url': link.text if link is not None else '#',
                'time': pub_date.text if pub_date is not None else datetime.now().isoformat(),
            }
            tweets.append(tweet)
    except ET.ParseError as e:
        print(f"Error parsing RSS: {e}")

    return tweets

class RequestHandler(SimpleHTTPRequestHandler):
    """Custom HTTP request handler"""

    def do_GET(self):
        parsed = urlparse(self.path)

        # API endpoint for tweets
        if parsed.path == '/api/tweets':
            self.send_json_response(self.get_tweets())
        # API endpoint for accounts
        elif parsed.path == '/api/accounts':
            self.send_json_response(ACCOUNTS)
        # Serve static files
        else:
            # Default to index.html for root
            if self.path == '/':
                self.path = '/index.html'
            super().do_GET()

    def get_tweets(self):
        """Get tweets from RSSHub or return mock data"""
        tweets = fetch_all_feeds()

        if tweets:
            # Sort by time descending
            tweets.sort(key=lambda x: x.get('time', ''), reverse=True)
            return {'success': True, 'tweets': tweets, 'source': 'rsshub'}

        # Return mock data if RSSHub is not available
        return {
            'success': True,
            'tweets': get_mock_tweets(),
            'source': 'mock',
            'message': 'RSSHub not available, showing mock data'
        }

    def send_json_response(self, data):
        """Send JSON response with CORS headers"""
        response = json.dumps(data, ensure_ascii=False)
        self.send_response(200)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Cache-Control', 'no-cache')
        self.end_headers()
        self.wfile.write(response.encode('utf-8'))

    def log_message(self, format, *args):
        """Custom log format"""
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {args[0]}")

def get_mock_tweets():
    """Return mock tweets for demo"""
    now = datetime.now()
    return [
        {
            'id': '1',
            'accountId': 'VitalikButerin',
            'accountName': 'Vitalik Buterin',
            'accountHandle': '@VitalikButerin',
            'content': 'The future of Ethereum is about more than just scaling. Layer 2 solutions are just the beginning of a much larger vision for decentralized systems.',
            'url': 'https://x.com/VitalikButerin/status/1',
            'time': now.isoformat(),
        },
        {
            'id': '2',
            'accountId': 'CryptoHayes',
            'accountName': 'Arthur Hayes',
            'accountHandle': '@CryptoHayes',
            'content': 'Markets are pricing in the macro narrative shift. The liquidity cycle is turning. Watch the DXY closely this week.',
            'url': 'https://x.com/CryptoHayes/status/2',
            'time': now.isoformat(),
        },
        {
            'id': '3',
            'accountId': 'WatcherGuru',
            'accountName': 'Watcher.Guru',
            'accountHandle': '@WatcherGuru',
            'content': 'JUST IN: Bitcoin ETF daily inflows hit new highs, marking significant institutional adoption.',
            'url': 'https://x.com/WatcherGuru/status/3',
            'time': now.isoformat(),
        },
        {
            'id': '4',
            'accountId': 'jack',
            'accountName': 'Jack Dorsey',
            'accountHandle': '@jack',
            'content': 'Bitcoin is the only technology that can truly separate money from state.',
            'url': 'https://x.com/jack/status/4',
            'time': now.isoformat(),
        },
        {
            'id': '5',
            'accountId': 'MessariCrypto',
            'accountName': 'Messari',
            'accountHandle': '@MessariCrypto',
            'content': 'New research: DeFi TVL continues to recover, driven by restaking protocols and real-world asset tokenization.',
            'url': 'https://x.com/MessariCrypto/status/5',
            'time': now.isoformat(),
        },
    ]

def main():
    """Start the server"""
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    server = HTTPServer(('0.0.0.0', PORT), RequestHandler)
    print(f"Today X! Server started on port {PORT}")
    print(f"RSSHub: {RSSHUB_URL}")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
        server.shutdown()

if __name__ == '__main__':
    main()
