import pandas as pd
import matplotlib.pyplot as plt
from collections import defaultdict

# Read the CSV file into a DataFrame
df = pd.read_csv('dataset/indus-translated.csv', encoding='utf-8')

# Initialize sets for unique substrings in "translation" and unique hex values in "text"
unique_translation_substrings = set()
unique_text_hex_values = set()

# Process the "translation" column
df['translation'].apply(lambda x: unique_translation_substrings.update(x.split('-')))

# Process the "text" column
for text_entry in df['text']:
    # Split by "\" and reattach "\" to each part to restore Unicode format
    substrings = [f'\\{part}' for part in text_entry.split('\\') if part]
    # Update the set with unique hex values
    unique_text_hex_values.update(substrings)

# Print the sets
print("[*] {} unique substrings in translation: {}\n".format(len(unique_translation_substrings), unique_translation_substrings))
print("[*] {} unique PUA codepoints in text: {}\n".format(len(unique_text_hex_values), unique_text_hex_values))

# Initialize a dictionary to store frequency mappings of substrings to Unicode values
substring_unicode_frequency = defaultdict(lambda: defaultdict(int))

# Process each row to populate the mapping
for _, row in df.iterrows():
    # Split "translation" by "-" to get individual substrings
    substrings = row['translation'].split('-')
    
    # Split "text" by "\" and reattach "\" to each part to restore Unicode format
    unicode_values = [f'\\{part}' for part in row['text'].split('\\') if part]
    
    # Map each substring to each Unicode value (assuming each Unicode value corresponds to each substring in parallel)
    for substring, unicode_val in zip(substrings, unicode_values):
        substring_unicode_frequency[substring][unicode_val] += 1

# Convert the mapping into a DataFrame for easier CSV output
output_data = []
for substring, unicode_counts in substring_unicode_frequency.items():
    for unicode_val, count in unicode_counts.items():
        output_data.append([substring, unicode_val, count])

# Create a DataFrame from the output data
frequency_df = pd.DataFrame(output_data, columns=['Substring', 'Unicode', 'Frequency'])

# Save the DataFrame to a CSV file
frequency_df.to_csv('dataset/substring_unicode_frequency.csv', index=False, encoding='utf-8')
print("[*] Output saved to 'substring_unicode_frequency.csv\n\n")
print("[*] Unicode Characters in Order of Their Frequency for Each Substring\n")
# List Unicode characters in order of their frequency for each substring
for substring in frequency_df['Substring'].unique():
    subset = frequency_df[frequency_df['Substring'] == substring]
    sorted_unicode = subset.sort_values(by='Frequency', ascending=False)['Unicode'].tolist()
    print(f"'{substring}': {sorted_unicode}\n")
    
# Prepare data for the LaTeX table with alphabetical sorting by substring
latex_rows = []
for substring, unicode_counts in sorted(substring_unicode_frequency.items()):
    # Sort Unicode values by frequency for each substring
    sorted_unicode = sorted(unicode_counts.items(), key=lambda x: x[1], reverse=True)
    
    # Convert \uXXXX Unicode notation to actual characters
    unicode_values = [chr(int(u[2:], 16)) for u, _ in sorted_unicode]
    
    # Join characters into a string for LaTeX table entry
    unicode_string = ' '.join(unicode_values)
    latex_rows.append(f"{substring} & \\textIndus{{{unicode_string}}} \\\\")

# Write the LaTeX document
with open("results/indus_glyphs_frequency.tex", "w", encoding="utf-8") as f:
    f.write(r"""\documentclass{article}
\usepackage{fontspec}
\usepackage{graphicx} % Import graphicx package for resizing
\usepackage[a4paper, margin=0.5in]{geometry} % Set small margins for maximum table width
\usepackage{longtable} % Import longtable package for multi-page tables
\newfontface\textIndus[Path=./]{IndusFont.ttf} % Define custom font face for Unicode characters
\begin{document}
% Define the table with longtable for multi-page support
\begin{longtable}{|l|p{0.8\textwidth}|}
\hline
\textbf{Substring} & \textbf{Unicode Characters by Frequency (Left to Right in Descending Order)} \\
\hline
\endfirsthead % Define the header for the first page
\hline
\textbf{Substring} & \textbf{Unicode Characters by Frequency (Left to Right in Descending Order)} \\
\hline
\endhead % Define the header for each subsequent page
\hline
\endfoot
\hline
\endlastfoot
""")
    
    # Add each row to the table
    for row in latex_rows:
        f.write(row + "\n")

    # Finish the table and document
    f.write(r"""\end{longtable}
\end{document}
""")

print("[*] LaTeX table saved to 'output_table_one.tex'")