#-*- coding: utf-8 -*-
"""
Dante Bot 2018
==============

Extremely basic Twitter bot that uses @DanteBot2018 to tweet a stanza of
Dante's Divina Commedia every 3 hours in line with #Dante2018.

author: Andrés Gattinoni <andresgattinoni@gmail.com>
"""

import sys
import os
import re
import time
import random
import json
import urllib2
import tempfile
import tweepy
from datetime import date

from twitter_credentials import cons_key, cons_secret, access_token, access_token_secret

INTERVAL = 60*30
HISTORY = 'tweet_history.json'
IMAGES = 'images.json'

class TweetHistory:

    def __init__(self):
        self.cantos = []
        self.images = []
        self.file = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                                 HISTORY)
        self.load_history()

    def load_history(self):
        if not os.path.exists(self.file):
            return True
        fp = open(self.file, 'r')
        js = json.load(fp)
        self.cantos = js['cantos']
        self.images = js['images']
        fp.close()

    def save_history(self):
        js = {'cantos': self.cantos, 'images': self.images}
        fp = open(self.file, 'w')
        json.dump(js, fp)
        fp.close()
        return True

    def add_canto(self, canto):
        self.cantos.append(canto)
        return self.save_history()

    def add_image(self, image):
        self.images.append(image)
        return self.save_history()

    def was_tweeted(self, t, v):
        if t == 'canto':
            return v in self.cantos
        else:
            return v in self.images

class DanteBot:
    def __init__(self):
        auth = tweepy.OAuthHandler(cons_key, cons_secret)
        auth.set_access_token(access_token, access_token_secret)
        self.history = TweetHistory()
        self.api = tweepy.API(auth)

    def run(self):
        while True:
            self.tweet()
            interval = INTERVAL * random.randint(1,6)
            print "Sleeping for %d seconds" % interval
            time.sleep(interval)

    def tweet(self):
        self._get_part_canto()
        return random.choice([self._tweet_canto, self._tweet_image])()

    def _compose_tweet(self,txt):
        return "%s %s #Dante2018" % (self._get_prefix(), txt)

    def _tweet_canto(self):
        db = self._make_db()
        tweet = None
        for i in range(100):
            tweet = self._compose_tweet("«%s»" % random.choice(db))
            if not self.history.was_tweeted('canto', tweet):
                break

        if tweet is None:
            print "Cannot tweet anything new today"
            return 0
        try:
            self.api.update_status(tweet)
            print "Tweeted: %s" % tweet
            self.history.add_canto(tweet)
            return 0
        except tweepy.TweepError as error:
            print("Tweet failed: %s" % error.reason)
            return 1

    def _tweet_image(self):
        db = self._make_images_db()
        img = None
        if db:
            for image in db:
                if image['part'] == self._part and \
                   int(image['canto']) == self._canto and \
                   not self.history.was_tweeted('image', image['id']):
                   img = image
                   break
        if img is None:
            print "Cannot tweet any new image today"
            return 0
        img_file = self._download_image(img['image_url'])
        tweet = self._compose_tweet('"%s" por %s (%s) [v. %s]' %
                                    (img['title'],
                                     img['creator'],
                                     img['date'],
                                     img['verse']))
        try:
            self.api.update_with_media(img_file, tweet)
            print "Tweeted image: %s" % img['title']
            self.history.add_image(img['id'])
            os.remove(img_file)
            return 0
        except tweepy.TweepError as error:
            print("Image tweet failed: %s" % error.reason)
            return 1

    def _download_image(self, url):
        tmp_file = tempfile.mkstemp('.jpg', 'dbot_',
                                    os.path.dirname(os.path.abspath(__file__)))
        fp = open(tmp_file[1], 'wb')
        fp.write(urllib2.urlopen(url).read())
        fp.close()
        return tmp_file[1]


    def _get_part_canto(self):
        delta = date.today() - date(2018, 1, 1)
        self._part = ''
        days = delta.days + 1
        self._canto = 0
        if (days <= 34):
            self._part = 'Inferno'
            self._canto = days
        elif (days > 34 and days <= 67):
            self._part = 'Purgatorio'
            self._canto = days - 34
        elif (days > 67 and days <= 100):
            self._part = 'Paradiso'
            self._canto = days - 67

    def _get_prefix(self):
        return "%s. %d:" % (self._part[:3], self._canto)

    def _get_file(self):
        return os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                            'cantos',
                                            self._part,
                                            'Canto_%d.txt' % self._canto)

    def _make_db(self):
        f = self._get_file()
        rx = re.compile('^(Inferno|Purgatorio|Paradiso)')
        db = []
        stanza = []
        ln = 0
        with open(f) as fp:
            for line in fp:
                if rx.search(line):
                    # Skip title line
                    continue
                line = line.strip()
                if line == '':
                    if len(stanza) > 0:
                        txt = " / ".join([i.values()[0] for i in stanza])
                        if len(stanza) == 1:
                            txt = '%s (%s)' % (txt, stanza[0].keys()[0])
                        else:
                            txt = '%s (%s-%s)' % (txt, stanza[0].keys()[0], stanza[-1].keys()[0])
                        db.append(txt)
                        stanza = []
                else:
                    ln +=1
                    stanza.append({ln: line})
        return db

    def _make_images_db(self):
        f = os.path.join(os.path.dirname(os.path.abspath(__file__)), IMAGES)
        db = []
        with open(f, 'r') as fp:
            db = json.load(fp)
        return db

def main(argv):
    dante = DanteBot()
    dante.run()
    return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv))
