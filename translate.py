import re
import csv
import random
import logging
from pathlib import Path
from dataclasses import dataclass
from typing import Dict, List, Optional, TypedDict


try:
    from indic_transliteration import sanscript
except ImportError:
    raise ImportError("Please install indic_transliteration: pip install indic_transliteration")


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class TransliterationConfig:
    """Configuration for transliteration process."""
    fullrandom: bool = False
    slp: str = 'aiukgcjtdnpbmyrlvsmst'
    iso: str = sanscript.transliterate(
        'aAiIuUoOfFxXEOMHkKgGNcCjJYwWqQRtTdDnpPbBmyrlvSzshL',
        'slp1', 
        'iast'
    )


class SignData(TypedDict):
    """Type definition for sign data."""
    xlit: str
    canonical: str
    random: str
    regex: str


class IndusTextProcessor:
    def __init__(self, dataset_dir: str = 'dataset'):
        self.dataset_dir = Path(dataset_dir)
        self.canon_map: Dict[str, str] = {}
        self.xlit_map: Dict[str, SignData] = {}
        self.inx_map: Dict[str, Dict] = {}
        self.missing_signs: set = set()
        self.config = TransliterationConfig()
        # Statistics
        self.total_len = 0
        self.total_count = 0
        self.deciphered_len = 0
        self.deciphered_count = 0
        # Ensure dataset directory exists
        self.dataset_dir.mkdir(exist_ok=True)


    def csv_to_dict(self, file_path: Path, required_fields: Optional[List[str]] = None) -> List[Dict]:
        """Read CSV file and return list of dictionaries."""
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                logger.info(f"Columns found in {file_path.name}: {reader.fieldnames}")   
                result = []
                for row in reader:
                    # Keep all fields, including empty ones
                    result.append(row)         
                if result:
                    logger.info(f"Sample row from {file_path.name}: {result[0]}")
                return result
        except FileNotFoundError:
            logger.error(f"File not found: {file_path}")
            return []
        except Exception as e:
            logger.error(f"Error reading {file_path}: {e}")
            return []


    def make_random(self, alphabet: str) -> str:
        """Generate a random character from given alphabet."""
        return random.choice(alphabet)


    def characterize(self, points: str) -> str:
        """
        Convert point string to Unicode characters.
        Matches Vue code's characterize function exactly.
        """
        if not points:
            return ""
        charset = str(points).split('-')
        result = ''
        for point in charset:
            if point.isdigit():
                result += chr(0xE000 + int(point))
        return result


    def canonize(self, text: str) -> Dict[str, str]:
        """Canonize the input text."""
        text = text.replace('/', '-999-999-999-999-')
        results = re.findall(r'(\d+)', text)
        if not results:
            return {'str': '', 'canon': ''}
        str_result = ''
        canon_result = ''
        for row in results:
            this_char = chr(0xE000 + int(row))
            str_result += this_char
            if row in self.xlit_map:
                canonical = self.xlit_map[row]['canonical']
                if row != canonical:
                    if not canonical:
                        continue
                    canel = canonical.split('-')
                    for a in canel:
                        if a.isdigit():
                            canon_result += chr(0xE000 + int(a))
                else:
                    canon_result += this_char
            else:
                logger.warning(f'Missing sign {row} in xlit_map')
                canon_result += this_char
        return {'str': str_result, 'canon': canon_result}


    def xlitize(self, text: str) -> Dict[str, str]:
        """
        Transliterate the input text.
        Matches Vue code's xlitize function exactly.
        """
        results = re.findall(r'(\d+)', text)
        if not results:
            return {'str': '', 'description': '', 'random': '', 'regex': ''}
        results = results[::-1]  # reverse the list
        if results[0] not in self.xlit_map:
            logger.warning(f'Warning: Missing sign {results[0]}')
            return {'str': '', 'description': '', 'random': '', 'regex': ''}
        str_result = self.xlit_map[results[0]]['xlit']
        rnd_result = self.xlit_map[results[0]]['random']
        regex_result = str_result
        for row in results[1:]:
            sign = self.xlit_map.get(row)
            if sign:
                # Check if vowel needs to be added
                if (not re.search(r'([iu]|an|as)$', str_result) and 
                    not re.match(r'^[aiu]$', sign['xlit']) and 
                    not str_result.endswith('.')):
                    str_result += 'a'
                    regex_result += 'a?'
                # Handle random part
                if (not self.config.fullrandom and 
                    not re.search(r'([iueofFxX]|an|as)$', rnd_result) and 
                    not re.match(r'^[aiu]$', sign['random']) and 
                    not rnd_result.endswith('.')):
                    rnd_result += 'a'
                str_result += '-' + sign['xlit']
                rnd_result += '-' + sign['random']
                regex_result += sign['xlit']
            else:
                logger.warning(f'Warning: Missing sign {row}')
        # Final vowel check
        if not re.search(r'([iu]|an|as)$', str_result):
            str_result += 'a'
            regex_result += 'a?'
        if not self.config.fullrandom and not re.search(r'([iueo]|an|as)$', rnd_result):
            rnd_result += 'a'
        # Split, reverse, and join
        str_result = '-'.join(str_result.split('-')[::-1])
        rnd_result = '-'.join(rnd_result.split('-')[::-1])
        description = str_result
        random = '⚄ random: ' + rnd_result
        return {
            'str': str_result,
            'regex': regex_result,
            'description': description,
            'random': random
        }


    def process_data(self) -> None:
        """Main processing function."""
        try:
            # Load input data
            incx = self.csv_to_dict(self.dataset_dir / 'indus-inscriptions.csv')
            xlits = self.csv_to_dict(self.dataset_dir / 'xlits.csv')
            if not incx or not xlits:
                logger.error("Required data files could not be loaded.")
                return     
            logger.info(f"Loaded {len(incx)} inscriptions and {len(xlits)} transliterations")
            # Process xlit mappings
            for element in xlits:
                sign = element.get('sign', '')
                if not sign:
                    continue
                self.xlit_map[sign] = {
                    'xlit': element.get('xlit', '.'),
                    'canonical': element.get('canonical', ''),
                    'random': self.make_random(
                        self.config.iso if self.config.fullrandom else self.config.slp
                    ),
                    'regex': element.get('regex', '') or element.get('xlit', '.')
                }    
                if element.get('canonical'):
                    self.canon_map[self.characterize(sign)] = \
                        self.characterize(element['canonical'])
            # Process inscriptions
            output_data = []
            for el in incx:
                analyzed = self.xlitize(el.get('text', ''))
                el['description'] = analyzed['description']
                el['random'] = analyzed['random']
                el['regex'] = analyzed['regex']
                canonized = self.canonize(el.get('text', ''))
                el['text'] = canonized['str']
                el['text_length'] = int(el.get('text length', '0')) if el.get('text length', '').isdigit() else 0
                # Handle Sanskrit
                sanskrit = el.get('sanskrit', '')
                if sanskrit:
                    el['sanskrit'] = sanskrit.replace('-', '—')
                    if sanskrit.startswith('ref:'):
                        ref_id = sanskrit[4:]
                        if ref_id in self.inx_map:
                            referred = self.inx_map[ref_id]
                            el['sanskrit'] = referred.get('sanskrit', '')
                            el['translation'] = referred.get('translation', '')
                    else:
                        try:
                            el['sanskrit'] = (
                                sanscript.transliterate(sanskrit, 'slp1', 'devanagari') +
                                '\n' + 
                                sanscript.transliterate(sanskrit, 'slp1', 'iast')
                            )
                        except Exception as e:
                            logger.warning(f"Error transliterating Sanskrit for {el.get('id')}: {e}")
                            el['sanskrit'] = sanskrit
                else:
                    el['sanskrit'] = '*' + ''.join(analyzed['str'].split('-')[::-1])
                # Update statistics
                if el.get('complete') == 'Y':
                    self.total_len += el['text_length']
                    self.total_count += 1
                    if el.get('translation'):
                        self.deciphered_len += el['text_length']
                        self.deciphered_count += 1
                el['canonized'] = canonized['canon']
                self.inx_map[el['id']] = el
                output_data.append(el)
            # Write output
            self._write_output(output_data)
            self._report_statistics()
        except Exception as e:
            logger.error(f"Error processing data: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise


    def _write_output(self, output_data: List[Dict]) -> None:
        """Write processed data to CSV file."""
        output_file = self.dataset_dir / 'indus-translated.csv'
        fieldnames = ['id', 'text', 'canonized', 'text_length', 'description', 
                     'random', 'regex', 'sanskrit', 'translation', 'notes']
        try:
            with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                for row in output_data:
                    # Only write the fields we specified in fieldnames
                    cleaned_row = {k: row.get(k, '') for k in fieldnames}
                    writer.writerow(cleaned_row)
            logger.info(f"Output successfully written to {output_file}")
        except Exception as e:
            logger.error(f"Error writing to output file: {e}")
            raise


    def _report_statistics(self) -> None:
        """Report processing statistics."""
        logger.info("\nProcessing Statistics:")
        logger.info(f"Total complete inscriptions: {self.total_count}")
        logger.info(f"Total length of complete inscriptions: {self.total_len}")
        logger.info(f"Deciphered inscriptions: {self.deciphered_count}")
        logger.info(f"Total length of deciphered inscriptions: {self.deciphered_len}")
        if self.total_len > 0:
            completion_rate = (self.deciphered_len / self.total_len) * 100
            logger.info(f"Completion rate: {completion_rate:.2f}%")


def main():
    """Main entry point."""
    try:
        processor = IndusTextProcessor()
        processor.process_data()
    except Exception as e:
        logger.error(f"Program terminated with error: {e}")
        raise


if __name__ == '__main__':
    main()