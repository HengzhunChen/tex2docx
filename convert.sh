#!/bin/bash

# input TeX file
input_file="./texfiles/report.tex"

# bibliography file
bibliography_file="./texfiles/report.bib"

# output Docx file
output_file="report.docx"

# figures directory
figures_dir="./texfiles/figure"

# filter python script
filter_script="filter.py"


# # plain pandoc
# pandoc "$input_file" --from latex --to docx \
#     --citeproc --bibliography "$bibliography_file" \
#     --resource-path "$figures_dir" \
#     -o "$output_file"


# # pandoc output AST
# pandoc "$input_file" --from latex+raw_tex \
#     --citeproc --bibliography "$bibliography_file" \
#     -o AST.json
# python3 -m json.tool AST.json > formatted_AST.json


# pandoc + panflute filter
pandoc "$input_file" --from latex+raw_tex --to docx \
    --citeproc --bibliography "$bibliography_file" \
    --resource-path "$figures_dir" \
    -F "$filter_script" \
    -o "$output_file"
