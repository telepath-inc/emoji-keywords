# emoji-keywords

This is a script to scrape the HTML table of emoji keywords provided for each Unicode version at
[unicode.org](https://www.unicode.org/emoji/charts-14.0/emoji-list.html), and produce a JSON file
designed for easy use by applications to provide emoji search.

The output format is a single JSON object keyed on categories, where values are lists with one entry
for each emoji:
```
["emoji character", ["skintone","variations","of","character"], ["keywords","for","character"]]
```
