import datetime
import os
import platform
import pytz
import subprocess

import feedgen.feed
import lxml.html
import requests


# This script requires OSX's `say`, so require a Mac
assert platform.system().lower() == 'darwin', "`say` command unavailable outside of OSX"

# Identify which fanfiction.net story to access
# This can be found in the URL for that story's chapters
STORY_ID = os.getenv('STORY_ID')

# Identify the Dropbox user whose `Public` folder this feed will live in
# This can be found in the URL created by the "Copy Public Link" Dropbox feature
DROPBOX_USER_ID = os.getenv('DROPBOX_USER_ID')
DROPBOX_PUBLIC_SUBDIRECTORY = 'ffn_podcast'


fg = feedgen.feed.FeedGenerator()
fg.load_extension('podcast')

# Identify the available chapters of the fanfic
url = 'https://www.fanfiction.net/s/{}'.format(STORY_ID)
doc = lxml.html.fromstring(requests.get(url).text)
chapters = doc.xpath('//select[@id="chap_select"]')
if chapters:
    chapters = chapters[0].xpath('option/text()')
else:
    chapters = ['Chapter 1']

# Set metadata for the podcast as a whole
fg.title(doc.xpath('//div[@id="profile_top"]//b/text()')[0])
fg.link(href=url, rel='self')
fg.description('Computer-voiced podcast of fanfiction.net story {}'.format(STORY_ID))
image = doc.xpath('//div[@id="profile_top"]/span/img[@class="cimage"]/src')
fg.image(image[0] if image else 'https://www.fanfiction.net/static/images/favicon_2010_iphone.png')

fg.podcast.itunes_author(doc.xpath('//a[@class="xcontrast_txt" and starts-with(@href, "/u/")]/text()')[0])
fg.podcast.itunes_category(itunes_category='Arts', itunes_subcategory='Literature')

# Voice and index a podcast episode for each chapter
for chapter_index, chapter_name in enumerate(chapters):
    fe = fg.add_entry()
    chapter_num = chapter_index + 1

    url = 'https://www.fanfiction.net/s/{}/{}'.format(STORY_ID, chapter_num)
    doc = lxml.html.fromstring(requests.get(url).text)

    story_text = doc.xpath('//div[@id="storytext"][1]/p')
    story_text = [x.text_content() for x in story_text]
    chapter_text = '\n'.join(story_text)
    with open('chapter.txt', 'w') as f:
        f.write(chapter_text.encode('utf8'))
    filename = 'ffn-story{}-chapter{}.m4a'.format(STORY_ID, chapter_num)

    print('Writing {} audio file to disk'.format(filename))
    process = subprocess.Popen([
        'say',
        '--input-file={}'.format('chapter.txt'),
        '--output-file={}'.format(filename)
    ])
    process.wait()
    file_url = 'https://dl.dropboxusercontent.com/u/{}/{}/{}'.format(DROPBOX_USER_ID, DROPBOX_PUBLIC_SUBDIRECTORY, filename)

    fe.title(chapter_name)
    fe.description(chapter_name)
    fe.id(file_url)
    fe.pubdate(pytz.utc.localize(datetime.datetime.now() - datetime.timedelta(days=(len(chapters) - chapter_index))))
    fe.enclosure(url=file_url, length=str(os.path.getsize(filename)), type='audio/m4a')

# Write the RSS XML document to publish the podcast
fg.rss_file(filename='index.xml', pretty=True)

os.remove('chapter.txt')
