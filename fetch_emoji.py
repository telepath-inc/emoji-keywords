#!/usr/bin/env python3
__doc__ = """Fetch emoji and their keywords from unicode.org."""

from bs4 import BeautifulSoup
import click
from collections import defaultdict
import csv
import json
from urllib import request

EMOJI_CATEGORY_MAP = {
    'Smileys & Emotion': 0,
    'People & Body': 0,  # consolidate with Smileys & Emotion
    'Animals & Nature': 1,
    'Food & Drink': 2,
    'Activities': 3,
    'Travel & Places': 4,
    'Objects': 5,
    'Symbols': 6,
    'Flags': 7,
    'Component': None  # ignore
}

SKIN_TONE_COMPONENTS = {
    'light': 'U+1F3FB',
    'medium-light': 'U+1F3FC',
    'medium': 'U+1F3FD',
    'medium-dark': 'U+1F3FE',
    'dark': 'U+1F3FF',
}


@click.command()
@click.option('--url', default='https://www.unicode.org/emoji/charts-13.1/emoji-list.html')
@click.option('--skintone-url', default='https://www.unicode.org/emoji/charts-13.1/full-emoji-modifiers.html')
@click.option('--overlay', help='CSV of additional keywords to include for given emoji')
@click.option('--flatten-keywords', help='enable flattening of phrases to separate keywords', is_flag=True)
def parse(url, skintone_url, overlay, flatten_keywords):
    data = parse_emoji(request.urlopen(url).read(), request.urlopen(skintone_url).read(), flatten_keywords)

    if overlay:
        # add keywords from provided overlay
        with open(overlay) as f:
            for row in csv.reader(f):
                emoji = row[0].strip()
                keyword = row[1].strip()
                for _, cat_emoji in data.items():
                    if any(emoji == ce[0] for ce in cat_emoji):
                        for e, _, kw_list in cat_emoji:
                            if e == emoji:
                                kw_list.append(keyword)
                        break
                else:
                    print(f"WARNING: no matching emoji found for {emoji}")

    with open('data/emoji.json', 'w', encoding='utf8') as f:
        f.write(json.dumps(data, ensure_ascii=False))


def parse_emoji(keyword_stream, skintone_stream, flatten_keywords=False):
    """Parses an HTML Unicode.org emoji keywords table."""
    # parse which emoji take a single skintone modifier
    soup = BeautifulSoup(skintone_stream, 'html.parser')

    skintone_emoji = set()
    for table in soup.find_all('table'):
        rows = table.find_all('tr')
        for row in rows:
            cols = row.find_all('td')
            if len(cols) > 3:
                codepoints = cols[1].get_text().strip()
                modifier_count = sum(codepoints.count(cp) for cp in SKIN_TONE_COMPONENTS.values())
                # only include emoji in set if they have exactly one modifier
                if modifier_count == 1:
                    s = ''.join(
                        f'\\U{cp[2:]:0>8s}'.format(cp)
                        for cp in codepoints.split(' ')
                        if cp not in SKIN_TONE_COMPONENTS.values()
                    ).encode('utf8').decode('unicode-escape')
                    skintone_emoji.add(s)


    # parse the full emoji keyword table
    soup = BeautifulSoup(keyword_stream, 'html.parser')
    result = defaultdict(list)

    for table in soup.find_all('table'):
        rows = table.find_all('tr')

        category = ''
        category_key = None
        subcategory = ''
        for row in rows:
            # check if this row is a category header, and if so, reset the current category
            category_cell = row.find('th', attrs={'class': 'bighead'})
            if category_cell:
                category = category_cell.get_text().strip()
                category_key = EMOJI_CATEGORY_MAP[category]
                subcategory = ''
                continue

            # check if this row is a subcategory, and if so, use it as an additional keyword for all its emoji
            subcategory_cell = row.find('th', attrs={'class': 'mediumhead'})
            if subcategory_cell:
                subcategory = subcategory_cell.get_text().strip().replace('-', ' ')
                continue

            if category_key is None:
                continue

            cols = row.find_all('td')
            if len(cols) == 5:
                # parse encoded emoji from codepoints
                codepoints = cols[1].get_text().strip().split(' ')
                if len(codepoints) == 1 and (int(codepoints[0][2:], 16) < 0x100 or (int(codepoints[0][2:], 16) >= 0x2600 and int(codepoints[0][2:], 16) < 0x2800)):
                    s = ''.join(f'\\U{cp[2:]:0>8s}'.format(cp) for cp in codepoints).encode('utf8').decode('unicode-escape')
                    print(f"found dingbat/symbol: {s} {cols[4].get_text()}")
                    # codepoint is a symbol or dingbat - add FE0F modifier to make it an emoji
                    codepoints.append('U+FE0F')
                    s = ''.join(f'\\U{cp[2:]:0>8s}'.format(cp) for cp in codepoints).encode('utf8').decode('unicode-escape')
                    print(f"annotated dingbat/symbol: {s}")
                s = ''.join(f'\\U{cp[2:]:0>8s}'.format(cp) for cp in codepoints).encode('utf8').decode('unicode-escape')

                short_name = cols[3].get_text().strip()
                keywords = set()
                if flatten_keywords:
                    # flatten keywords from shortname, category, and keyword phrases down to unique lowercase individual words
                    for kw in cols[4].get_text().split('|'):
                        keywords.update(kw.lower().strip().split(' '))
                    keywords.update(short_name.lower().strip().split(' '))
                    if subcategory:
                        keywords.update(subcategory.lower().strip().split(' '))
                else:
                    # lowercase keywords, but keep phrases as phrases
                    keywords.update(kw.strip().lower() for kw in cols[4].get_text().split('|'))
                    keywords.add(short_name.lower().strip())
                    if subcategory:
                        keywords.add(subcategory.lower().strip())
                result[category_key].append([s, int(s in skintone_emoji), list(keywords)])

    return result


if __name__ == '__main__':
    parse()
