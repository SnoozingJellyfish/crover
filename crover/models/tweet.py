from crover import db
from datetime import datetime

class Tweet(db.Model):
    __tablename__ = 'tweet'
    id = db.Column(db.Integer, primary_key = True)
    text = db.Column(db.Text)
    tweeted_at = db.Column(db.DateTime)

    def __init__(self, tweeted_at=None, text=None):
        self.text = text
        self.tweeted_at = tweeted_at

    def __repr__(self):
        return '<id:{} tweeted_at:{} text:{}>'.format(self.id, self.tweeted_at, self.text)


class WordCount(db.Model):
    __tablename__ = 'all_word_count'
    id = db.Column(db.Integer, primary_key=True)
    word = db.Column(db.String(50), unique=True)
    #count = db.Column(db.Integer)
    relative_frequent_rate = db.Column(db.Float)

    def __init__(self, word=None, count=None, relative_frequent_rate=None):
        self.word = word
        #self.count = count
        self.relative_frequent_rate = relative_frequent_rate

    def __repr__(self):
        #return '<id:{} word:{} count:{}>'.format(self.id, self.word, self.count)
        return '<id:{} word:{} relative_frequent_rate:{}>'.format(self.id, self.word, self.relative_frequent_rate)

