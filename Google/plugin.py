###
# Copyright (c) 2002-2004, Jeremiah Fincher
# Copyright (c) 2008-2009, James Vega
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
###

import re
import cgi
import time
import socket
import urllib
import random

import supybot.conf as conf
import supybot.utils as utils
import supybot.world as world
from supybot.commands import *
import supybot.ircmsgs as ircmsgs
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks

try:
    simplejson = utils.python.universalImport('json', 'simplejson',
                                              'local.simplejson')
    # The 3rd party simplejson module was included in Python 2.6 and renamed to
    # json.  Unfortunately, this conflicts with the 3rd party json module.
    # Luckily, the 3rd party json module has a different interface so we test
    # to make sure we aren't using it.
    if hasattr(simplejson, 'read'):
        raise ImportError
except ImportError:
    raise callbacks.Error, \
            'You need Python2.6 or the simplejson module installed to use ' \
            'this plugin.  Download the module at ' \
            '<http://undefined.org/python/#simplejson>.'

class Google(callbacks.PluginRegexp):
    threaded = True
    callBefore = ['Web']
    regexps = ['googleSnarfer', 'googleGroups']

    _colorGoogles = {}
    def _getColorGoogle(self, m):
        s = m.group(1)
        ret = self._colorGoogles.get(s)
        if not ret:
            L = list(s)
            L[0] = ircutils.mircColor(L[0], 'blue')[:-1]
            L[1] = ircutils.mircColor(L[1], 'red')[:-1]
            L[2] = ircutils.mircColor(L[2], 'yellow')[:-1]
            L[3] = ircutils.mircColor(L[3], 'blue')[:-1]
            L[4] = ircutils.mircColor(L[4], 'green')[:-1]
            L[5] = ircutils.mircColor(L[5], 'red')
            ret = ''.join(L)
            self._colorGoogles[s] = ret
        return ircutils.bold(ret)

    _googleRe = re.compile(r'\b(google)\b', re.I)
    def outFilter(self, irc, msg):
        if msg.command == 'PRIVMSG' and \
           self.registryValue('colorfulFilter', msg.args[0]):
            s = msg.args[1]
            s = re.sub(self._googleRe, self._getColorGoogle, s)
            msg = ircmsgs.privmsg(msg.args[0], s, msg=msg)
        return msg

    _gsearchUrl = 'http://ajax.googleapis.com/ajax/services/search/web'
    def search(self, query, channel, options={}):
        """Perform a search using Google's AJAX API.
        search("search phrase", options={})

        Valid options are:
            smallsearch - True/False (Default: False)
            filter - {active,moderate,off} (Default: "moderate")
            language - Restrict search to documents in the given language
                       (Default: "lang_en")
        """
        ref = self.registryValue('referer')
        if not ref:
            ref = 'http://%s/%s' % (dynamic.irc.server,
                                    dynamic.irc.nick)
        headers = utils.web.defaultHeaders
        headers['Referer'] = ref
        opts = {'q': query, 'v': '1.0'}
        for (k, v) in options.iteritems():
            if k == 'smallsearch':
                if v:
                    opts['rsz'] = 'small'
                else:
                    opts['rsz'] = 'large'
            elif k == 'filter':
                opts['safe'] = v
            elif k == 'language':
                opts['lr'] = v
        defLang = self.registryValue('defaultLanguage', channel)
        if 'lr' not in opts and defLang:
            opts['lr'] = defLang
        if 'safe' not in opts:
            opts['safe'] = self.registryValue('searchFilter', dynamic.channel)
        if 'rsz' not in opts:
            opts['rsz'] = 'large'

        fd = utils.web.getUrlFd('%s?%s' % (self._gsearchUrl,
                                           urllib.urlencode(opts)),
                                headers)
        json = simplejson.load(fd)
        fd.close()
        if json['responseStatus'] != 200:
            status = json['responseStatus']
            message = json['responseDetails']
            raise callbacks.Error, 'We broke The Google! (%s, %s)' % (status,
                                                                      message)
        return json

    _gimagesearchUrl = 'http://ajax.googleapis.com/ajax/services/search/images'
    def imagesearch(self, query, channel, options={}):
        """Perform a image search using Google's AJAX API.
        search("search phrase", options={})

        Valid options are:
            smallsearch - True/False (Default: False)
            filter - {active,moderate,off} (Default: "moderate")
            language - Restrict search to documents in the given language
                       (Default: "lang_en")
        """
        ref = self.registryValue('referer')
        if not ref:
            ref = 'http://%s/%s' % (dynamic.irc.server,
                                    dynamic.irc.nick)
        headers = utils.web.defaultHeaders
        headers['Referer'] = ref
        opts = {'q': query, 'v': '1.0'}
        for (k, v) in options.iteritems():
            if k == 'smallsearch':
                if v:
                    opts['rsz'] = 'small'
                else:
                    opts['rsz'] = 'large'
            elif k == 'filter':
                opts['safe'] = v
            elif k == 'language':
                opts['lr'] = v
        defLang = self.registryValue('defaultLanguage', channel)
        if 'lr' not in opts and defLang:
            opts['lr'] = defLang
        if 'safe' not in opts:
            opts['safe'] = self.registryValue('searchFilter', dynamic.channel)
        if 'rsz' not in opts:
            opts['rsz'] = 'large'

        fd = utils.web.getUrlFd('%s?%s' % (self._gimagesearchUrl,
                                           urllib.urlencode(opts)),
                                headers)
        json = simplejson.load(fd)
        fd.close()
        if json['responseStatus'] != 200:
            status = json['responseStatus']
            message = json['responseDetails']
            raise callbacks.Error, 'We broke The Google! (%s, %s)' % (status,
                                                                      message)
        return json

    def formatData(self, data, bold=True, max=0):
        if isinstance(data, basestring):
            return data
        results = []
        if max:
            data = data[:max]
        for result in data:
            title = utils.web.htmlToText(result['titleNoFormatting']\
                                         .encode('utf-8'))
            url = result['unescapedUrl'].encode('utf-8')
            if title:
                if bold:
                    title = ircutils.bold(title)
                results.append(format('%s: %u', title, url))
            else:
                results.append(url)
        if not results:
            return format('No matches found.')
        else:
            return format('; '.join(results))

    def lucky(self, irc, msg, args, text):
        """<search>

        Does a google search, but only returns the first result.
        """
        data = self.search(text, msg.args[0], {'smallsearch': True})
        if data['responseData']['results']:
            url = data['responseData']['results'][0]['unescapedUrl']
            irc.reply(url.encode('utf-8'))
        else:
            irc.reply('Google found nothing.')
    lucky = wrap(lucky, ['text'])

    def google(self, irc, msg, args, optlist, text):
        """<search> [--{filter,language} <value>]

        Searches google.com for the given string.  As many results as can fit
        are included.  --language accepts a language abbreviation; --filter
        accepts a filtering level ('active', 'moderate', 'off').
        """
        if 'language' in optlist and optlist['language'].lower() not in \
           conf.supybot.plugins.Google.safesearch.validStrings:
            irc.errorInvalid('language')
        data = self.search(text, msg.args[0], dict(optlist))
        if data['responseStatus'] != 200:
            irc.reply('We broke The Google!')
            return
        bold = self.registryValue('bold', msg.args[0])
        max = self.registryValue('maximumResults', msg.args[0])
        irc.reply(self.formatData(data['responseData']['results'],
                                  bold=bold, max=max))
    google = wrap(google, [getopts({'language':'something',
                                    'filter':''}),
                           'text'])

    def image(self, irc, msg, args, text):
        """<search>

        Does a google image search, and returns a random image URL.
        """
        text = re.sub(r'^\s*me\s*', '', text)
        data = self.imagesearch(text, msg.args[0])
        results = data['responseData']['results'];
        if results:
            index = random.randint(0, len(results) - 1)
            url = results[index]['unescapedUrl']
            irc.reply(url.encode('utf-8'))
        else:
            irc.reply('Google found nothing.')
    image = wrap(image, ['text'])

    def animate(self, irc, msg, args, text):
        """<search>

        Does a google image search, and returns a random image URL.
        """
        text = re.sub(r'^\s*me\s*', '', text) + ' inurl:\.gif'
        data = self.imagesearch(text, msg.args[0])
        results = data['responseData']['results'];
        if results:
            index = random.randint(0, len(results) - 1)
            url = results[index]['unescapedUrl']
            irc.reply(url.encode('utf-8'))
        else:
            irc.reply('Google found nothing.')
    animate = wrap(animate, ['text'])

    def mustache(self, irc, msg, args, text):
        """<search>

        Does a google image search, and returns a random image passed to mustachify.me.
        """
        text = re.sub(r'^\s*me\s*', '', text)
        data = self.imagesearch(text, msg.args[0])
        results = data['responseData']['results'];
        if results:
            index = random.randint(0, len(results) - 1)
            url = results[index]['unescapedUrl'].encode('utf-8')
            url = 'http://mustachify.me/?src=' + url
            irc.reply(url)
        else:
            irc.reply('Google found nothing.')
    mustache = wrap(mustache, ['text'])

    def cache(self, irc, msg, args, url):
        """<url>

        Returns a link to the cached version of <url> if it is available.
        """
        data = self.search(url, msg.args[0], {'smallsearch': True})
        if data['responseData']['results']:
            m = data['responseData']['results'][0]
            if m['cacheUrl']:
                url = m['cacheUrl'].encode('utf-8')
                irc.reply(url)
                return
        irc.error('Google seems to have no cache for that site.')
    cache = wrap(cache, ['url'])

    def fight(self, irc, msg, args):
        """<search string> <search string> [<search string> ...]

        Returns the results of each search, in order, from greatest number
        of results to least.
        """
        channel = msg.args[0]
        results = []
        for arg in args:
            data = self.search(arg, channel, {'smallsearch': True})
            count = data['responseData']['cursor']['estimatedResultCount']
            results.append((int(count), arg))
        results.sort()
        results.reverse()
        if self.registryValue('bold', msg.args[0]):
            bold = ircutils.bold
        else:
            bold = repr
        s = ', '.join([format('%s: %i', bold(s), i) for (i, s) in results])
        irc.reply(s)

    _gtranslateUrl='http://ajax.googleapis.com/ajax/services/language/translate'
    _transLangs = {'Arabic': 'ar', 'Bulgarian': 'bg',
                   'Chinese_simplified': 'zh-CN',
                   'Chinese_traditional': 'zh-TW', 'Croatian': 'hr',
                   'Czech': 'cs', 'Danish': 'da', 'Dutch': 'nl',
                   'English': 'en', 'Finnish': 'fi', 'French': 'fr',
                   'German': 'de', 'Greek': 'el', 'Hindi': 'hi',
                   'Italian': 'it', 'Japanese': 'ja', 'Korean': 'ko',
                   'Norwegian': 'no', 'Polish': 'pl', 'Portuguese': 'pt',
                   'Romanian': 'ro', 'Russian': 'ru', 'Spanish': 'es',
                   'Swedish': 'sv'}
    def translate(self, irc, msg, args, fromLang, toLang, text):
        """<from-language> [to] <to-language> <text>

        Returns <text> translated from <from-language> into <to-language>.
        Beware that translating to or from languages that use multi-byte
        characters may result in some very odd results.
        """
        channel = msg.args[0]
        ref = self.registryValue('referer')
        if not ref:
            ref = 'http://%s/%s' % (dynamic.irc.server,
                                    dynamic.irc.nick)
        headers = utils.web.defaultHeaders
        headers['Referer'] = ref
        opts = {'q': text, 'v': '1.0'}
        lang = conf.supybot.plugins.Google.defaultLanguage
        if fromLang.capitalize() in self._transLangs:
            fromLang = self._transLangs[fromLang.capitalize()]
        elif lang.normalize('lang_'+fromLang)[5:] \
                not in self._transLangs.values():
            irc.errorInvalid('from language', fromLang,
                             format('Valid languages are: %L',
                                    self._transLangs.keys()))
        else:
            fromLang = lang.normalize('lang_'+fromLang)[5:]
        if toLang.capitalize() in self._transLangs:
            toLang = self._transLangs[toLang.capitalize()]
        elif lang.normalize('lang_'+toLang)[5:] \
                not in self._transLangs.values():
            irc.errorInvalid('to language', toLang,
                             format('Valid languages are: %L',
                                    self._transLangs.keys()))
        else:
            toLang = lang.normalize('lang_'+toLang)[5:]
        opts['langpair'] = '%s|%s' % (fromLang, toLang)
        fd = utils.web.getUrlFd('%s?%s' % (self._gtranslateUrl,
                                           urllib.urlencode(opts)),
                                headers)
        json = simplejson.load(fd)
        fd.close()
        if json['responseStatus'] != 200:
            status = json['responseStatus']
            message = json['responseDetails']
            raise callbacks.Error, 'We broke The Google! (%s, %s)' % (status,
                                                                      message)
        irc.reply(json['responseData']['translatedText'].encode('utf-8'))
    translate = wrap(translate, ['something', 'to', 'something', 'text'])

    def googleSnarfer(self, irc, msg, match):
        r"^google\s+(.*)$"
        if not self.registryValue('searchSnarfer', msg.args[0]):
            return
        searchString = match.group(1)
        data = self.search(searchString, msg.args[0], {'smallsearch': True})
        if data['responseData']['results']:
            url = data['responseData']['results'][0]['unescapedUrl']
            irc.reply(url.encode('utf-8'), prefixNick=False)
    googleSnarfer = urlSnarfer(googleSnarfer)

    _ggThread = re.compile(r'Subject: <b>([^<]+)</b>', re.I)
    _ggGroup = re.compile(r'<TITLE>Google Groups :\s*([^<]+)</TITLE>', re.I)
    _ggThreadm = re.compile(r'src="(/group[^"]+)">', re.I)
    _ggSelm = re.compile(r'selm=[^&]+', re.I)
    _threadmThread = re.compile(r'TITLE="([^"]+)">', re.I)
    _threadmGroup = re.compile(r'class=groupname[^>]+>([^<]+)<', re.I)
    def googleGroups(self, irc, msg, match):
        r"http://groups.google.[\w.]+/\S+\?(\S+)"
        if not self.registryValue('groupsSnarfer', msg.args[0]):
            return
        queries = cgi.parse_qsl(match.group(1))
        queries = [q for q in queries if q[0] in ('threadm', 'selm')]
        if not queries:
            return
        queries.append(('hl', 'en'))
        url = 'http://groups.google.com/groups?' + urllib.urlencode(queries)
        text = utils.web.getUrl(url)
        mThread = None
        mGroup = None
        if 'threadm=' in url:
            path = self._ggThreadm.search(text)
            if path is not None:
                url = 'http://groups-beta.google.com' + path.group(1)
                text = utils.web.getUrl(url)
                mThread = self._threadmThread.search(text)
                mGroup = self._threadmGroup.search(text)
        else:
            mThread = self._ggThread.search(text)
            mGroup = self._ggGroup.search(text)
        if mThread and mGroup:
            irc.reply(format('Google Groups: %s, %s',
                             mGroup.group(1), mThread.group(1)),
                      prefixNick=False)
        else:
            self.log.debug('Unable to snarf.  %s doesn\'t appear to be a '
                           'proper Google Groups page.', match.group(1))
    googleGroups = urlSnarfer(googleGroups)

    def _googleUrl(self, s):
        s = s.replace('+', '%2B')
        s = s.replace(' ', '+')
        url = r'http://google.com/search?q=' + s
        return url

    _calcRe = re.compile(r'<img src=/images/calc_img\.gif.*?<b>(.*?)</b>', re.I)
    _calcSupRe = re.compile(r'<sup>(.*?)</sup>', re.I)
    _calcFontRe = re.compile(r'<font size=-2>(.*?)</font>')
    _calcTimesRe = re.compile(r'&(?:times|#215);')
    def calc(self, irc, msg, args, expr):
        """<expression>

        Uses Google's calculator to calculate the value of <expression>.
        """
        url = self._googleUrl(expr)
        html = utils.web.getUrl(url)
        match = self._calcRe.search(html)
        if match is not None:
            s = match.group(1)
            s = self._calcSupRe.sub(r'^(\1)', s)
            s = self._calcFontRe.sub(r',', s)
            s = self._calcTimesRe.sub(r'*', s)
            irc.reply(s)
        else:
            irc.reply('Google\'s calculator didn\'t come up with anything.')
    calc = wrap(calc, ['text'])

    _phoneRe = re.compile(r'Phonebook.*?<font size=-1>(.*?)<a href')
    def phonebook(self, irc, msg, args, phonenumber):
        """<phone number>

        Looks <phone number> up on Google.
        """
        url = self._googleUrl(phonenumber)
        html = utils.web.getUrl(url)
        m = self._phoneRe.search(html)
        if m is not None:
            s = m.group(1)
            s = s.replace('<b>', '')
            s = s.replace('</b>', '')
            s = utils.web.htmlToText(s)
            irc.reply(s)
        else:
            irc.reply('Google\'s phonebook didn\'t come up with anything.')
    phonebook = wrap(phonebook, ['text'])


Class = Google


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
