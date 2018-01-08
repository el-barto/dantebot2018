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
import tweepy
from datetime import date

from twitter_credentials import cons_key, cons_secret, access_token, access_token_secret

INTERVAL = 60*60*3

class DanteBot:
    def __init__(self):
        auth = tweepy.OAuthHandler(cons_key, cons_secret)
        auth.set_access_token(access_token, access_token_secret)
        self.tweets = []
        self.api = tweepy.API(auth)

    def run(self, interval):
        while True:
            self.tweet()
            time.sleep(interval)

    def tweet(self):
        self._get_part_canto()
        db = self._make_db()
        for i in range(100):
            tweet = "%s «%s» #Dante2018" % (self._get_prefix(), random.choice(db))
            if tweet not in self.tweets:
                break
            else:
                tweet = None
        try:
            if tweet is None:
                print "Cannot tweet anything new today"
                return 0
            self.api.update_status(tweet)
            print "Tweeted: %s" % tweet
            self.tweets.append(tweet)
            return 0
        except tweepy.TweepError as error:
            print("Tweet failed: %s" % error.reason)
            return 1

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
        return "%s.: %d" % (self._part[:3], self._canto)

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

def main(argv):
    dante = DanteBot()
    dante.run(INTERVAL)
    return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv))
