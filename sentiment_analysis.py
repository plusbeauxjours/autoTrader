from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import numpy as np

_analyzer = SentimentIntensityAnalyzer()

def sentiment_score(texts):
    if not texts: return 0.0
    scores = [_analyzer.polarity_scores(t)['compound'] for t in texts]
    return float(np.mean(scores))
