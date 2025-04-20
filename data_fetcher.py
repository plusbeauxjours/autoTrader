import os
import pandas as pd
from binance.client import Client
import tweepy
from dotenv import load_dotenv

load_dotenv()

client = Client(os.getenv('BINANCE_API_KEY'), os.getenv('BINANCE_API_SECRET'))
twitter_client = tweepy.Client(bearer_token=os.getenv('TWITTER_BEARER_TOKEN'))

def get_symbols():
    info = client.futures_exchange_info()
    return [s['symbol'] for s in info['symbols'] if s['quoteAsset']=='USDT']

def get_klines(symbol, interval='1m', limit=6):
    cols = ['open_time','open','high','low','close','volume','close_time',
            'quote_vol','trades','taker_buy_base','taker_buy_quote','ignore']
    data = client.futures_klines(symbol=symbol, interval=interval, limit=limit)
    df = pd.DataFrame(data, columns=cols)
    df['open_time'] = pd.to_datetime(df['open_time'], unit='ms')
    df['close'] = df['close'].astype(float)
    df['volume'] = df['volume'].astype(float)
    return df[['open_time','close','volume']]

def get_tweets(query, max_results=50):
    tweets = twitter_client.search_recent_tweets(query=query, max_results=max_results)
    return [t.text for t in tweets.data] if tweets.data else []
