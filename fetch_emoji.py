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

EMOJI_VARIATION_SEL = 'U+FE0F'


@click.command()
@click.option('--url', default='https://www.unicode.org/emoji/charts-13.1/emoji-list.html')
@click.option('--skintone-url', default='https://www.unicode.org/emoji/charts-13.1/full-emoji-modifiers.html')
@click.option('--extra-keywords', help='CSV of extra keywords', required=True)
@click.option('--fe0f', help='CSV of characters that require an emoji variation selector to render correctly', required=True)
@click.option('--exclude', help='CSV of characters to exclude', required=True)
@click.option('--flatten-keywords', help='enable flattening of phrases to separate keywords', is_flag=True, default=True)
@click.option('--indent', help='indentation to use in JSON output', type=int)
def parse(url, skintone_url, extra_keywords, fe0f, exclude, flatten_keywords, indent):
    data = parse_emoji(request.urlopen(url).read(), request.urlopen(skintone_url).read(), flatten_keywords)

    with open(extra_keywords) as f:
        for row in csv.reader(f):
            emoji = row[0].strip()
            keyword = row[1].strip()
            for _, category_emojis in data.items():
                if any(emoji == ce[0] for ce in category_emojis):
                    for e, _, kw_list in category_emojis:
                        if e == emoji:
                            kw_list.append(keyword)
                    break
            else:
                print(f"% WARNING: unable to add extra keywords for missing emoji: {emoji}")

    with open(fe0f) as f:
        sel_cp = bytes(f'\\U{EMOJI_VARIATION_SEL[2:]:0>8s}'.format(EMOJI_VARIATION_SEL).encode('utf-8'))
        for row in csv.reader(f):
            emoji = row[0].strip()
            for category, category_emojis in data.items():
                for i, emoji_data in enumerate(category_emojis):
                    if emoji_data[0] == emoji:
                        cp = emoji_data[0].encode('unicode-escape')
                        cp += sel_cp
                        data[category][i][0] = cp.decode('unicode-escape')

    with open(exclude) as f:
        new_data = defaultdict(list)
        exclude_set = set()
        for row in csv.reader(f):
            exclude_set.add(row[0].strip())
        for category, category_emojis in data.items():
            for emoji_data in category_emojis:
                if emoji_data[0] not in exclude_set:
                    new_data[category].append(emoji_data)
                else:
                    print(f"% excluding emoji: {emoji_data[0]}")
        data = new_data

    with open('data/emoji.json', 'w', encoding='utf8') as f:
        f.write(json.dumps(data, indent=indent, ensure_ascii=False))


def parse_emoji(keyword_stream, skintone_stream, flatten_keywords=False):
    """Parses an HTML Unicode.org emoji keywords table."""
    # parse which emoji take a single skintone modifier
    soup = BeautifulSoup(skintone_stream, 'html.parser')
    skintone_variations = defaultdict(list)

    for table in soup.find_all('table'):
        rows = table.find_all('tr')
        for row in rows:
            cols = row.find_all('td')
            if len(cols) > 3:
                codepoints = cols[1].get_text().strip()
                modifier_count = sum(codepoints.count(cp) for cp in SKIN_TONE_COMPONENTS.values())
                # only include emoji in set if they have exactly one modifier
                if modifier_count == 1:
                    key = ''.join(
                        f'\\U{cp[2:]:0>8s}'.format(cp)
                        for cp in codepoints.split(' ')
                        if cp not in SKIN_TONE_COMPONENTS.values()
                    ).encode('utf8').decode('unicode-escape')

                    # some emoji expect the variation selector instead of the skin tone modifier
                    substitute_codepoints = codepoints
                    for modifier in SKIN_TONE_COMPONENTS.values():
                        substitute_codepoints = substitute_codepoints.replace(modifier, EMOJI_VARIATION_SEL)

                    substitute_key = ''.join(
                        f'\\U{cp[2:]:0>8s}'.format(cp)
                        for cp in substitute_codepoints.split(' ')
                    ).encode('utf8').decode('unicode-escape')

                    value = ''.join(
                        f'\\U{cp[2:]:0>8s}'.format(cp)
                        for cp in codepoints.split(' ')
                    ).encode('utf8').decode('unicode-escape')

                    skintone_variations[key].append(value)
                    skintone_variations[substitute_key].append(value)

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
                s = ''.join(f'\\U{cp[2:]:0>8s}'.format(cp) for cp in codepoints).encode('utf8').decode('unicode-escape')

                short_name = cols[3].get_text().strip()
                keywords = set()
                if flatten_keywords:
                    # flatten keywords from shortname, category, and keyword phrases down to unique lowercase individual words
                    for kw in cols[4].get_text().split('|'):
                        keywords.update(kw.lower().strip().replace(':', '').split(' '))
                    keywords.update(short_name.lower().strip().replace(':', '').split(' '))
                    if subcategory:
                        keywords.update(subcategory.lower().strip().replace(':', '').split(' '))
                else:
                    # lowercase keywords, but keep phrases as phrases
                    keywords.update(kw.strip().lower() for kw in cols[4].get_text().split('|'))
                    keywords.add(short_name.lower().strip())
                    if subcategory:
                        keywords.add(subcategory.lower().strip())

                sk_list = skintone_variations[s]
                kw_list = list(keywords)
                result[category_key].append([s, sk_list, kw_list])

    return result


if __name__ == '__main__':
    parse()
