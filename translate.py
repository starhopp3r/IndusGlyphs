import csv
import json
import random
import re
from indic_transliteration import sanscript


canon_map = {}
xlit_map = {}

# Constants and initial variables
fullrandom = False
slp = 'aiukgcjtdnpbmyrlvsmst'
iso = sanscript.transliterate('aAiIuUoOfFxXEOMHkKgGNcCjJYwWqQRtTdDnpPbBmyrlvSzshL', sanscript.SLP1, sanscript.IAST)


# Function to read CSV files
def csv_to_dict(file_path, keys=None):
    with open(file_path, 'r') as file:
        reader = csv.DictReader(file)
        if keys:
            return [dict((key, row[key]) for key in keys) for row in reader]
        return [row for row in reader]

# Data files
incx = csv_to_dict('dataset/indus-inscriptions.csv')
xlits = csv_to_dict('dataset/xlits.csv')


# Define the characterize function
def characterize(points):
    charset = points.split('-')
    result = ''.join(f'\\u{0xE000 + int(point):04x}' for point in charset)
    return json.loads(f'"{result}"')


def canonize(text):
    text = text.replace('/', '-999-999-999-999-')
    results = re.findall(r'(\d+)', text)
    str_result = ''
    canon = ''
    
    for row in results:
        this_char = f'\\u{0xE000 + int(row):04x}'
        str_result += this_char
        if row != xlit_map[row]['canonical']:
            if not xlit_map[row]['canonical']:
                return row
            canel = xlit_map[row]['canonical'].split('-')
            canon += ''.join(f'\\u{0xE000 + int(a):04x}' for a in canel)
        else:
            canon += this_char

    # Return the hex codes as raw strings without JSON parsing
    return {'str': str_result, 'canon': canon}


# xlitize function as defined
def xlitize(text):
    # Match all digit sequences in text, reversed order
    results = re.findall(r'(\d+)', text)[::-1]

    # Check for missing sign in xlit_map
    if results[0] not in xlit_map:
        print('Warning: Missing sign', results[0])
        return {}

    # Initialize str_result, rnd, and regex with the first sign's xlit and random
    str_result = xlit_map[results[0]]['xlit']
    rnd = xlit_map[results[0]]['random']
    regex = str_result

    # Remove the first element from results
    results.pop(0)

    # Process remaining elements
    for row in results:
        sign = xlit_map.get(row)
        if sign:
            if not re.match(r'^.*([iu]|an|as)$', str_result) and not re.match(r'^[aiu]$', sign['xlit']) and not str_result.endswith('.'):
                str_result += 'a'
                regex += 'a?'
            if not fullrandom and not re.match(r'^.*([iueofFxX]|an|as)$', rnd) and not re.match(r'^[aiu]$', sign['random']) and not str_result.endswith('.'):
                rnd += 'a'

            str_result += '-' + sign['xlit']
            rnd += '-' + sign['random']
            regex += sign['xlit']
        else:
            print('Warning: Missing sign', row)

    # Final adjustments to str_result and rnd
    if not re.match(r'.*([iu]|an|as)$', str_result):
        str_result += 'a'
        regex += 'a?'
    if not fullrandom and not re.match(r'.*([iueo]|an|as)$', rnd):
        rnd += 'a'

    # Reverse and join the result strings
    str_result = '-'.join(str_result.split('-')[::-1])
    rnd = '-'.join(rnd.split('-')[::-1])
    description = '-'.join(str_result.split('-'))
    random_description = '⚄ random: ' + rnd

    # Return the results as a dictionary
    return {
        'str': str_result,
        'regex': regex,
        'description': description,
        'random': random_description
    }


if __name__ == '__main__':
    # Collect data for the CSV output
    output_data = []

    # Generate xlit_map and canon_map
    for element in xlits:
        xlit_map[element['sign']] = {
            'xlit': element['xlit'],
            'canonical': element['canonical'],
            'random': random.choice(iso if fullrandom else slp),
            'regex': element.get('regex') or element['xlit']
        }
        canon_map[characterize(element['sign'])] = characterize(element['canonical'])

    # Process inx data
    for el in incx:
        analyzed = xlitize(el['text'])
        el['translation'] = analyzed['description']
        canonized = canonize(el['text'])
        el['text'] = canonized['str']

        # Collect only the required columns for output
        output_data.append({
            'id': el['id'],
            'text': el['text'],
            'translation': el['translation']
        })

    # Write the output to a CSV file
    with open('dataset/indus-translated.csv', 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['id', 'text', 'translation']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(output_data)