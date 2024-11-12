import pandas as pd
import re
from indic_transliteration import sanscript
from indic_transliteration.sanscript import transliterate

# Read xlits.csv, filling missing regex values with an empty string
xlits_df = pd.read_csv('dataset/xlits_updated.csv', dtype=str, keep_default_na=False)
xlits_df['regex'] = xlits_df['regex'].fillna('')  # Fill NaN values in regex with empty string

# Build xlitmap dictionary from xlits.csv
xlitmap = {}
for idx, row in xlits_df.iterrows():
    sign = row['sign']
    xlit = row['xlit'] if 'xlit' in row else ''
    canonical = row['canonical'] if 'canonical' in row else ''
    regex = row['regex']
    xlitmap[sign] = {
        'xlit': xlit,
        'random': xlit,  # 'random' not provided, so use 'xlit'
        'canonical': canonical,
        'regex': regex
    }

# Read the main data file
df = pd.read_csv('dataset/indus-inscriptions.csv', dtype=str, keep_default_na=False)

# Define the xlitize function to transliterate based on xlitmap
def xlitize(text):
    re_digits = re.compile(r'(\d+)')
    results = re_digits.findall(text)
    results = results[::-1]  # Reverse the list
    if not results:
        return {'str': '', 'regex': '', 'description': '', 'random': ''}
    if results[0] not in xlitmap:
        print('Warning: Missing sign', results[0])
        return None

    sign = xlitmap[results[0]]
    str_xlit = sign['xlit']
    rnd = sign['random']
    regex = str_xlit
    results = results[1:]  # Remove the first element

    fullrandom = False  # Assuming 'fullrandom' is False

    for row in results:
        sign = xlitmap.get(row)
        if sign:
            if (re.match(r'^.*([iu]|an|as)$', str_xlit) is None and
                re.match(r'^[aiu]$', sign['xlit']) is None and
                not str_xlit.endswith('.')):
                str_xlit += 'a'
                regex += 'a?'
            if (not fullrandom and
                re.match(r'^.*([iueofFxX]|an|as)$', rnd) is None and
                re.match(r'^[aiu]$', sign['random']) is None and
                not rnd.endswith('.')):
                rnd += 'a'
            str_xlit += '-' + sign['xlit']
            rnd += '-' + sign['random']
            regex += sign['xlit']
        else:
            print('Warning: Missing sign', row)

    if re.match(r'.*([iu]|an|as)$', str_xlit) is None:
        str_xlit += 'a'
        regex += 'a?'
    if not fullrandom and re.match(r'.*([iueo]|an|as)$', rnd) is None:
        rnd += 'a'

    str_xlit = '-'.join(str_xlit.split('-')[::-1])
    rnd = '-'.join(rnd.split('-')[::-1])
    description = '-'.join(str_xlit.split('-'))
    random_str = '⚄ random: ' + rnd

    return {'str': str_xlit, 'regex': regex, 'description': description, 'random': random_str}

# Define the canonize function to process canonical mappings
def canonize(text):
    text = text.replace('/', '-999-999-999-999-')
    re_digits = re.compile(r'(\d+)')
    results = re_digits.findall(text)
    str_chars = ''
    canon_chars = ''
    for row in results:
        thisChar = chr(0xE000 + int(row))
        str_chars += thisChar
        sign = xlitmap.get(row)
        if sign and row != sign['canonical']:
            if not sign['canonical']:
                return row
            canel = sign['canonical'].split('-')
            for a in canel:
                canon_chars += chr(0xE000 + int(a))
        else:
            canon_chars += thisChar
    return {'str': str_chars, 'canon': canon_chars}

# Define a placeholder for resolve function, if needed
def resolve(sanskrit):
    # Implement the resolve function as needed
    # For now, return an empty dict
    return {}

# Initialize counters
totalLen = 0
totalCount = 0
decipheredLen = 0
decipheredCount = 0

# Process each row in the DataFrame
for idx, el in df.iterrows():
    text = str(el['text']) if 'text' in el and el['text'] else ''
    analyzed = xlitize(text)
    if analyzed is None:
        continue  # Skip this row if xlitize returned None
    df.at[idx, 'description'] = analyzed['description']
    df.at[idx, 'random'] = analyzed['random']
    df.at[idx, 'regex'] = analyzed['regex']
    # canonized = canonize(text)
    # if canonized is None:
    #     continue
    # df.at[idx, 'text'] = canonized['str']
    df.at[idx, 'textlength'] = int(el['text length']) if 'text length' in el and el['text length'] else 0
    if 'sanskrit' in el and el['sanskrit']:
        df.at[idx, 'sanskrit'] = el['sanskrit'].replace('-', '—')
    totalLen += df.at[idx, 'textlength'] if 'complete' in el and el['complete'] == 'Y' else 0
    totalCount += 1 if 'complete' in el and el['complete'] else 0
    decipheredLen += df.at[idx, 'textlength'] if 'complete' in el and el['complete'] == 'Y' and 'translation' in el and el['translation'] else 0
    decipheredCount += 1 if 'translation' in el and el['translation'] else 0
    # df.at[idx, 'canonized'] = canonized['canon']
    # Handle Sanskrit transliteration
    sanskrit = el['sanskrit'] if 'sanskrit' in el and el['sanskrit'] else ''
    if sanskrit:
        if sanskrit.startswith('ref:'):
            resolved = resolve(sanskrit)
            for key, value in resolved.items():
                df.at[idx, key] = value
        else:
            dev_text = transliterate(sanskrit, sanscript.SLP1, sanscript.DEVANAGARI)
            iast_text = transliterate(sanskrit, sanscript.SLP1, sanscript.IAST)
            df.at[idx, 'sanskrit'] = dev_text + '\n' + iast_text
    else:
        df.at[idx, 'sanskrit'] = '*' + '-'.join(analyzed['str'].split('-')[::-1])



# Display the updated DataFrame
for _, row in df.iterrows():
    print(row['id'], row['text'], row['description'])
