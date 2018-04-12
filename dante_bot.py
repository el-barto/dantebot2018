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
        self.rts = []
        self.highlights = []
        self.file = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                                 HISTORY)
        self.load_history()

    def load_history(self):
        if not os.path.exists(self.file):
            return True
        fp = open(self.file, 'r')
        js = json.load(fp)
        for k in ('cantos', 'images', 'rts', 'highlights'):
            if k in js.keys():
                self.__dict__[k] = js[k]
        fp.close()

    def save_history(self):
        js = {'cantos': self.cantos, 
              'images': self.images, 
              'rts': self.rts, 
              'highlights': self.highlights}
        fp = open(self.file, 'w')
        json.dump(js, fp)
        fp.close()
        return True

    def _add(self, k, v):
        # To-Do: implement @property decorator
        self.__dict__[k].append(v)
        return self.save_history()

    def add_canto(self, canto):
        return self._add('cantos', canto)

    def add_image(self, image):
        return self._add('images', image)

    def add_rt(self, status_id):
        return self._add('rts', status_id)

    def add_highlight(self, status_id):
        return self._add('highlights', status_id)

    def was_tweeted(self, t, v):
        if t in self.__dict__:
            return v in self.__dict__[t]
        return False

class DanteBot:
    def __init__(self):
        self.old_posts = []
        auth = tweepy.OAuthHandler(cons_key, cons_secret)
        auth.set_access_token(access_token, access_token_secret)
        self.history = TweetHistory()
        self.api = tweepy.API(auth)

    def run(self):
        while True:
            self.handle_retweets()
            self.tweet()
            interval = INTERVAL * random.randint(1,6)
            print "Sleeping for %d seconds" % interval
            time.sleep(interval)

    def tweet(self):
        active = self._get_part_canto()
        if active:            
            return random.choice([self._tweet_canto, self._tweet_image])()
        else:
            return self._highlight()

    def handle_retweets(self):
        return self._rt_autodante()

    def _rt_autodante(self):
        delta = date.today() - date(2018, 1, 1)
        if (delta.days > 100):
            # #Dante2018 is over
            return True

        ad = self.api.get_user('autodante')
        if ad and not self.history.was_tweeted('rts', ad.status.id):
            try:
                self.api.retweet(ad.status.id)
                print "Retweeted last tweet from @autodante. ID: '%s'" % ad.status.id
                self.history.add_rt(ad.status.id)
                print "Sleeping for 5 minutes"
                time.sleep(60*5)
            except tweepy.TweepError as error:
                print("Tweet failed: %s" % error.reason)
                return False
        return True

    def _compose_tweet(self,txt):
        return "%s %s #Dante2018" % (self._get_prefix(), txt)

    def _tweet_canto(self):
        db = self._make_db()
        tweet = None
        for i in range(100):
            tweet = self._compose_tweet(random.choice(db))
            if not self.history.was_tweeted('canto', tweet):
                break

        if tweet is None:
            print "Cannot tweet anything new today"
            return 0
        try:
            self.api.update_status(tweet)
            print "Tweeted: %s" % tweet
            self.history.add_canto(tweet)
            return True
        except tweepy.TweepError as error:
            print("Tweet failed: %s" % error.reason)
            return False

    def _tweet_image(self):
        db = self._make_images_db()
        img = None
        if db:
            img_choices = []
            for image in db:
                if image['part'] == self._part and \
                   int(image['canto']) == self._canto and \
                   not self.history.was_tweeted('images', image['id']):
                   img_choices.append(image)
            if img_choices:
                img = random.choice(img_choices)
        if img is None:
            print "Cannot tweet any new image today"
            return False
        img_file = self._download_image(img['image_url'])
        tweet = self._compose_tweet('"%s" por %s (%s) [v. %s]. Fuente: %s' %
                                    (img['title'],
                                     img['creator'],
                                     img['date'],
                                     img['verse'],
                                     img['link_url']))
        try:
            self.api.update_with_media(img_file, tweet)
            print "Tweeted image: %s" % img['title']
            self.history.add_image(img['id'])
            os.remove(img_file)
            return True
        except tweepy.TweepError as error:
            print("Image tweet failed: %s" % error.reason)
            return False

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
        active = False
        if (days <= 34):
            self._part = 'Inferno'
            self._canto = days
            active = True
        elif (days > 34 and days <= 67):
            self._part = 'Purgatorio'
            self._canto = days - 34
            active = True
        elif (days > 67 and days <= 100):
            self._part = 'Paradiso'
            self._canto = days - 67
            active = True
        return active

    def _highlight(self):
        posts = self._make_old_db()
        found = False
        tweet = None
        n = 0
        print "Posts: %d" % len(posts)
        while not found:
            n += 1
            tweet = random.choice(posts)
            if not self.history.was_tweeted('highlights', tweet.id):
                if tweet.retweet_count > 0 or tweet.favorite_count > 0:
                    print "Found untweeted highlight: %s" % tweet.id
                    found = True
            if n > len(posts):
                break
        if found:
            print "Retweeting ID: %s" % tweet.id
            try:
                if self.api.retweet(tweet.id):
                    self.history.add_highlight(tweet.id)
                    print "Retweeted highlight: %s" % tweet.id
            except tweepy.TweepError as error:
                print("Failed to retweet highlight: %s" % error.reason)
                return False
        return True

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
                            txt = '"%s" (%s)' % (txt, stanza[0].keys()[0])
                        else:
                            txt = '"%s" (%s-%s)' % (txt, stanza[0].keys()[0], stanza[-1].keys()[0])
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

    def _make_old_db(self):
        if not self.old_posts:
            last_id = None
            while True:
                tweets = self.api.user_timeline(screen_name='dantebot2018', since_id=last_id)
                if not tweets:
                    break
                self.old_posts = self.old_posts + tweets
                last_id = tweets[-1].id
        return self.old_posts


def main(argv):
    dante = DanteBot()
    dante.run()
    return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv))
