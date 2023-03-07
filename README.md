# emoji-keywords

This is a script to scrape the HTML table of emoji keywords provided for each Unicode version at
[unicode.org](https://www.unicode.org/emoji/charts-14.0/emoji-list.html), and produce a JSON file
that allows an application to implement emoji search.

The output format is a single JSON object keyed on categories, where values are lists with one entry
for each emoji like this:

```
["emoji character", ["skintone","variations","of","character"], ["keywords","for","character"]]
```

To rebuild the `data/emoji.json` file included in this repo, execute `fetch_emoji.py` like this:

```
./fetch_emoji.py --fe0f data/fe0f.csv --extra-keywords data/extra_keywords.csv --exclude data/exclude.csv --out data/emoji.json --no-indent
```
