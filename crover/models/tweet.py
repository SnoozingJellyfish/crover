#from sqlalchemy import create_engine
from sqlalchemy import Column, Integer, String, Float, DateTime, Text
#from crover import db
from crover import Base
from datetime import datetime

#engine = create_engine('sqlite://', echo=False)

class Tweet(Base):
    __tablename__ = 'tweet'
    __table_args__ = {'extend_existing': True}
    id = Column('id', Integer, primary_key=True)
    text = Column('text', Text())
    tweeted_at = Column('tweeted_at', DateTime)
    word = Column('word', Text())

    def __init__(self, tweeted_at=None, text=None, word=None):
        self.text = text
        self.tweeted_at = tweeted_at
        self.word = word

    def __repr__(self):
        return '<id:{} tweeted_at:{} text:{} word: {}>'.format(self.id, self.tweeted_at, self.text, self.word)


class ClusterTweet(Base):
    __tablename__ = 'cluster_tweet'
    __table_args__ = {'extend_existing': True}
    id = Column('id', Integer, primary_key=True)
    text = Column('text', Text())
    tweeted_at = Column('tweeted_at', DateTime)
    emotion = Column('emotion', Integer)

    def __init__(self, tweeted_at=None, text=None, emotion=None):
        self.text = text
        self.tweeted_at = tweeted_at
        self.emotion = emotion

    def __repr__(self):
        return '<id:{} tweeted_at:{} text:{} emotion: {}>'.format(self.id, self.tweeted_at, self.text, self.emotion)



class WordCount(Base):
    __tablename__ = 'all_word_count'
    __table_args__ = {'extend_existing': True}
    id = Column('id', Integer, primary_key=True)
    word = Column('word', String(20), unique=True)
    #count = db.Column(db.Integer)
    relative_frequent_rate = Column('relative_frequent_rate', Float)

    def __init__(self, word=None, count=None, relative_frequent_rate=None):
        self.word = word
        #self.count = count
        self.relative_frequent_rate = relative_frequent_rate

    def __repr__(self):
        #return '<id:{} word:{} count:{}>'.format(self.id, self.word, self.count)
        return '<id:{} word:{} relative_frequent_rate:{}>'.format(self.id, self.word, self.relative_frequent_rate)

