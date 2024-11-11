import logging
import pandas as pd
from pathlib import Path
from dataclasses import dataclass
from collections import defaultdict
from typing import Dict, List, Set, Tuple, DefaultDict


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class DirectoryConfig:
    """Configuration for directory paths."""
    dataset_dir: Path = Path('dataset')
    results_dir: Path = Path('results')
    input_file: str = 'indus-translated.csv'
    frequency_file: str = 'substring_unicode_frequency.csv'
    latex_file: str = 'indus_glyphs_frequency.tex'


class IndusAnalyzer:
    """Analyzer for Indus script translations and frequencies."""
    def __init__(self, config: DirectoryConfig):
        self.config = config
        self.unique_translation_substrings: Set[str] = set()
        self.unique_text_hex_values: Set[str] = set()
        self.substring_unicode_frequency: DefaultDict = defaultdict(lambda: defaultdict(int))
        # Ensure directories exist
        self.config.dataset_dir.mkdir(exist_ok=True)
        self.config.results_dir.mkdir(exist_ok=True)


    def read_data(self) -> pd.DataFrame:
        """Read and validate the input CSV file."""
        try:
            file_path = self.config.dataset_dir / self.config.input_file
            df = pd.read_csv(file_path, encoding='utf-8')
            # The columns should match our first script's output
            required_columns = ['id', 'text', 'description', 'canonized']
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                raise ValueError(f"Missing required columns: {missing_columns}")
            logger.info(f"Successfully loaded data with columns: {df.columns.tolist()}")
            return df
        except FileNotFoundError:
            logger.error(f"File not found: {file_path}")
            raise
        except Exception as e:
            logger.error(f"Error reading CSV file: {e}")
            raise


    def process_unique_elements(self, df: pd.DataFrame) -> None:
        """Process and collect unique elements from the DataFrame."""
        # Process description (transliteration) column
        descriptions = df['description'].dropna()
        for desc in descriptions:
            if desc and isinstance(desc, str):
                parts = desc.split('-')
                self.unique_translation_substrings.update(parts)
                logger.debug(f"Added substrings from description: {parts}")
        # Process text column for Unicode values
        for text_entry in df['text'].dropna():
            if text_entry and isinstance(text_entry, str):
                unicode_values = [f'\\u{ord(c):04x}' for c in text_entry]
                self.unique_text_hex_values.update(unicode_values)
                logger.debug(f"Added Unicode values: {unicode_values}")
        logger.info(f"Found {len(self.unique_translation_substrings)} unique substrings")
        logger.info(f"Found {len(self.unique_text_hex_values)} unique PUA codepoints")


    def process_frequency_mapping(self, df: pd.DataFrame) -> None:
        """Process frequency mapping between substrings and Unicode values."""
        for idx, row in df.iterrows():
            if pd.isnull(row['description']) or pd.isnull(row['text']):
                logger.debug(f"Skipping row {idx} due to missing data")
                continue
            # Get substrings from description (these are our transliterations)
            substrings = row['description'].split('-')
            # Get Unicode values from the text
            unicode_values = [f'\\u{ord(c):04x}' for c in row['text']]
            if len(substrings) != len(unicode_values):
                logger.warning(
                    f"Length mismatch in row {row['id']}: "
                    f"substrings={len(substrings)}, unicode={len(unicode_values)}"
                )
                continue
            # Map regular forms
            for substring, unicode_val in zip(substrings, unicode_values):
                if substring and unicode_val:
                    self.substring_unicode_frequency[substring][unicode_val] += 1
                    logger.debug(f"Mapped {substring} -> {unicode_val}")
            # Map canonical forms if available
            if not pd.isnull(row['canonized']):
                canonical_unicode = [f'\\u{ord(c):04x}' for c in row['canonized']]
                if len(substrings) == len(canonical_unicode):
                    for substring, unicode_val in zip(substrings, canonical_unicode):
                        if substring and unicode_val:
                            self.substring_unicode_frequency[f"{substring}_canonical"][unicode_val] += 1
                            logger.debug(f"Mapped canonical {substring} -> {unicode_val}")


    def create_frequency_dataframe(self) -> pd.DataFrame:
        """Create a DataFrame from frequency mapping."""
        output_data = []
        for substring, unicode_counts in self.substring_unicode_frequency.items():
            is_canonical = substring.endswith('_canonical')
            base_substring = substring.replace('_canonical', '') if is_canonical else substring
            # Sort unicode values by frequency for this substring
            sorted_counts = sorted(unicode_counts.items(), key=lambda x: (-x[1], x[0]))
            for unicode_val, count in sorted_counts:
                output_data.append([
                    base_substring,
                    unicode_val,
                    count,
                    is_canonical
                ])
        # Form a dataframe
        df = pd.DataFrame(
            output_data, 
            columns=['Substring', 'Unicode', 'Frequency', 'IsCanonical']
        )
        return df.sort_values(
            ['Substring', 'IsCanonical', 'Frequency'], 
            ascending=[True, True, False]
        )


    def escape_latex(self, s: str) -> str:
        """Escape special characters for LaTeX."""
        latex_special_chars = {
            '&': r'\&',
            '%': r'\%',
            '$': r'\$',
            '#': r'\#',
            '_': r'\_',
            '{': r'\{',
            '}': r'\}',
            '~': r'\textasciitilde{}',
            '^': r'\^{}',
            '\\': r'\textbackslash{}'
        }
        return ''.join(latex_special_chars.get(c, c) for c in s)


    def generate_latex_rows(self) -> List[str]:
        """Generate LaTeX table rows."""
        latex_rows = []
        df = self.create_frequency_dataframe()
        for substring in df['Substring'].unique():
            # Regular forms
            regular_forms = df[(df['Substring'] == substring) & (~df['IsCanonical'])]
            if not regular_forms.empty:
                unicode_values = [chr(int(u[2:], 16)) for u in regular_forms['Unicode']]
                escaped_substring = self.escape_latex(substring)
                unicode_string = ''.join(unicode_values)
                escaped_unicode_string = self.escape_latex(unicode_string)
                latex_rows.append(
                    f"/{escaped_substring}/ & \\textIndus{{{escaped_unicode_string}}} \\\\ \\hline"
                )
            # Canonical forms
            canonical_forms = df[(df['Substring'] == substring) & (df['IsCanonical'])]
            if not canonical_forms.empty:
                unicode_values = [chr(int(u[2:], 16)) for u in canonical_forms['Unicode']]
                escaped_substring = self.escape_latex(f"{substring}")
                unicode_string = ''.join(unicode_values)
                escaped_unicode_string = self.escape_latex(unicode_string)
                latex_rows.append(
                    f"/{escaped_substring}/ (canonical) & \\textIndus{{{escaped_unicode_string}}} \\\\ \\hline"
                )
        return latex_rows


    def write_latex_document(self, latex_rows: List[str]) -> None:
        """Write the LaTeX document with the frequency table."""
        latex_template = r"""\documentclass{article}
\usepackage{fontspec}
\usepackage{graphicx}
\usepackage[a4paper, margin=0.5in]{geometry}
\usepackage{longtable}
\newfontface\textIndus[Path=./]{IndusFont.ttf}
\begin{document}
\begin{center}
\section*{Indus Glyphs in Order of Their Frequency for Each Substring}
\end{center}
\begin{longtable}{|l|p{0.8\textwidth}|}
\hline
\textbf{Substring} & \textbf{Indus Glyphs by Frequency (Left to Right in Descending Order)} \\
\hline
\endfirsthead
\hline
\textbf{Substring} & \textbf{Indus Glyphs by Frequency (Left to Right in Descending Order)} \\
\hline
\endhead
\hline
\endfoot
\hline
\endlastfoot
%s
\end{longtable}
\end{document}"""
        try:
            latex_content = latex_template % '\n'.join(latex_rows)
            latex_file_path = self.config.results_dir / self.config.latex_file
            with open(latex_file_path, 'w', encoding='utf-8') as f:
                f.write(latex_content)
            logger.info(f"LaTeX document written to {latex_file_path}")
        except Exception as e:
            logger.error(f"Error writing LaTeX file: {e}")
            raise


    def process(self) -> None:
        """Main processing function."""
        try:
            df = self.read_data()
            self.process_unique_elements(df)
            self.process_frequency_mapping(df)
            frequency_df = self.create_frequency_dataframe()
            # Save frequency data
            output_path = self.config.dataset_dir / self.config.frequency_file
            frequency_df.to_csv(output_path, index=False, encoding='utf-8')
            logger.info(f"Frequency data saved to {output_path}")
            # Generate LaTeX document
            latex_rows = self.generate_latex_rows()
            self.write_latex_document(latex_rows)
            # Print summary statistics
            self.print_statistics(frequency_df)
        except Exception as e:
            logger.error(f"Error during processing: {e}")
            raise


    def print_statistics(self, frequency_df: pd.DataFrame) -> None:
        """Print summary statistics."""
        print("\nFrequency Analysis Summary:")
        for substring in sorted(frequency_df['Substring'].unique()):
            print(f"\nSubstring '{substring}':")
            # Regular forms
            regular = frequency_df[
                (frequency_df['Substring'] == substring) & 
                (~frequency_df['IsCanonical'])
            ]
            if not regular.empty:
                print("Regular forms:")
                print(f"Total occurrences: {regular['Frequency'].sum()}")
                print(f"Unique glyphs: {len(regular)}")
                most_frequent = regular.iloc[0]
                print(f"Most frequent glyph: {chr(int(most_frequent['Unicode'][2:], 16))} "
                      f"({most_frequent['Frequency']} occurrences)")
            # Canonical forms
            canonical = frequency_df[
                (frequency_df['Substring'] == substring) & 
                (frequency_df['IsCanonical'])
            ]
            if not canonical.empty:
                print("\nCanonical forms:")
                print(f"Total occurrences: {canonical['Frequency'].sum()}")
                print(f"Unique glyphs: {len(canonical)}")
                most_frequent = canonical.iloc[0]
                print(f"Most frequent glyph: {chr(int(most_frequent['Unicode'][2:], 16))} "
                      f"({most_frequent['Frequency']} occurrences)")


def main():
    """Main entry point."""
    try:
        config = DirectoryConfig()
        analyzer = IndusAnalyzer(config)
        analyzer.process()
    except Exception as e:
        logger.error(f"Program terminated with error: {e}")
        raise


if __name__ == '__main__':
    main()