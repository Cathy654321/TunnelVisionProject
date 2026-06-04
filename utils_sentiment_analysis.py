from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

def get_vader_sentiment_score(text):
    analyzer = SentimentIntensityAnalyzer()
    sentiment_score = analyzer.polarity_scores(text)['compound']
    return sentiment_score

if __name__ == '__main__':
    text1 = "I like this book very much"
    text2 = "I find this book just ok"
    text3 = "I hate this one"

    print(text1, get_vader_sentiment_score(text1))
    print(text2, get_vader_sentiment_score(text2))
    print(text3, get_vader_sentiment_score(text3))
