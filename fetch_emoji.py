#!/usr/bin/env python3
__doc__ = """Fetch emoji and their keywords from unicode.org."""

from bs4 import BeautifulSoup
import click
from collections import defaultdict
import csv
import json
from urllib import request


@click.command()
@click.option('--url', default='https://www.unicode.org/emoji/charts-13.1/emoji-list.html')
@click.option('--overlay', help='CSV of additional keywords to include for given emoji')
def parse(url, overlay):
    data = parse_emoji(request.urlopen(url).read())

    if overlay:
        # add keywords from provided overlay
        with open(overlay) as f:
            for row in csv.reader(f):
                emoji = row[0].strip()
                keyword = row[1].strip()
                for _, cat_emoji in data.items():
                    if emoji in dict(cat_emoji):
                        for e, kw_list in cat_emoji:
                            if e == emoji:
                                kw_list.append(keyword)
                        break
                else:
                    print(f"WARNING: no matching emoji found for {emoji}")

    with open('data/emoji.json', 'w', encoding='utf8') as f:
        f.write(json.dumps(data, ensure_ascii=False))


def parse_emoji(stream):
    """Parses an HTML Unicode.org emoji keywords table."""
    soup = BeautifulSoup(stream, 'html.parser')
    result = defaultdict(list)

    for table in soup.find_all('table'):
        rows = table.find_all('tr')

        category = ''
        subcategory = ''
        for row in rows:
            # check if this row is a category header, and if so, reset the current category
            category_cell = row.find('th', attrs={'class': 'bighead'})
            if category_cell:
                category = category_cell.get_text().strip()
                subcategory = ''
                continue

            # check if this row is a subcategory, and if so, use it as an additional keyword for all its emoji
            subcategory_cell = row.find('th', attrs={'class': 'mediumhead'})
            if subcategory_cell:
                subcategory = subcategory_cell.get_text().strip().replace('-', ' ')
                continue

            cols = row.find_all('td')
            if len(cols) == 5:
                # parse encoded emoji from codepoints
                codepoints = cols[1].get_text().strip().split(' ')
                s = ''.join(f'\\U{cp[2:]:0>8s}'.format(cp) for cp in codepoints).encode('utf8').decode('unicode-escape')

                short_name = cols[3].get_text().strip()
                keywords = [kw.strip() for kw in cols[4].get_text().split('|')]
                keywords.append(short_name)
                if subcategory:
                    keywords.append(subcategory)
                result[category].append([s, keywords])

    return result


if __name__ == '__main__':
    parse()
