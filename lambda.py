#!/usr/bin/env python

import time

from datetime import datetime

import boto3
import feedparser
import yaml

from jinja2 import Template


def chunk_list(lst, rows):
    return list((lst[i: i + rows] for i in range(0, len(lst), rows)))


def new_post(post_time, new_post_age_threshold):
    post_time = datetime.now().timetuple() if post_time is None else post_time
    parsed_post_time = time.mktime(post_time)
    current_time = time.mktime(datetime.now().timetuple())
    return abs(current_time - parsed_post_time) < new_post_age_threshold


def get_feeds(config):
    feeds = chunk_list(config['feeds'], config['rows'])

    for group in feeds:
        for feed in group:
            feed['posts'] = []
            feed_data = feedparser.parse(feed['rss_url'])
            for entry in feed_data.entries[:config['posts']]:
                new = new_post(
                    entry.get('published_parsed'),
                    config['new_post_age_threshold']
                )
                feed['posts'].append({
                    'title': entry['title'],
                    'link': entry['link'],
                    'new': new
                })
            print(f"added {len(feed['posts'])} posts for {feed['name']}")

    return feeds


def render_template(data):
    template = Template(open('template.html.j2').read())
    with open('/tmp/index.html', 'w') as f:
        f.write(template.render(data=data))
    print('template rendered locally')


def upload_rendered(bucket):
    s3 = boto3.client('s3')
    s3.upload_file(
        '/tmp/index.html',
        bucket,
        'index.html',
        ExtraArgs={'ContentType': 'text/html'}
    )
    print('rendered file uploaded to s3')


def handler(event, context):
    with open('config.yaml', 'r') as stream:
        config = yaml.safe_load(stream)

    data = {}
    data['site'] = config['site']
    data['feeds'] = get_feeds(config)
    data['extra_links'] = chunk_list(config['extra_links'], config['rows'])

    render_template(data)
    upload_rendered(config['s3_bucket'])


if __name__ == "__main__":
    handler({}, {})
