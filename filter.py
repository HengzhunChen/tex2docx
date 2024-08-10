"""
Pandoc filter using panflute
"""

import panflute as pf
import sys
import re


# *****************************************************************************
# Utility functions
# *****************************************************************************

def find_first_str(elem: pf.Element) -> pf.Str | None:
    """
    Find the first Str element contained in the input element.
    """
    if isinstance(elem, pf.Str):
        return elem
    elif hasattr(elem, 'content'):
        for child in elem.content:
            if isinstance(child, pf.Str):
                return child
            else:
                t = find_first_str(child)
                if t is not None:
                    return t
    return None

def find_ref_label(elem: pf.Element) -> pf.Str | None:
    """
    Extract the label from the latex command \label{}.
    """
    if isinstance(elem, pf.RawInline):
        matches = re.search(r"\\label\{(.*)\}", elem.text)
        if matches:
            label = matches.group(1)
            return label
    elif hasattr(elem, 'content'):
        for child in elem.content:
            t = find_ref_label(child)
            if t is not None:
                return t
    return None


# *****************************************************************************
# Headers
# Add section number to the header text in format "1.2.3  Header text".
# Add a section heading for the references section.
# *****************************************************************************

# Note: We use a stack to manage the serial number in different levels of headers.

header_stack = []  # index for level, value for number
headers = {}  # record the header and its number

def number_headers(elem: pf.Element, doc: pf.Doc) -> pf.Element:
    """
    Compute the header number based on the header level and the parent header.
    """
    if isinstance(elem, pf.Header):
        level = elem.level
        if level == 1:
            if elem.classes == ['unnumbered']:
                # skip numbering those sections not numbered
                return elem
            # print(elem.classes, file=sys.stderr)
        if level > len(header_stack):
            # go to next level
            header_stack.append(1)
        elif level == len(header_stack):
            # increase the number of current level
            header_stack[-1] += 1
        else:
            # go back to the correct level
            while len(header_stack) > level:
                header_stack.pop()
            header_stack[-1] += 1

        header_number = '.'.join(str(header_stack[i]) for i in range(0, len(header_stack)))
        headers[elem.identifier] = header_number
        t = find_first_str(elem)

        # FIXME: format of the header number
        t.text = header_number + '  ' + t.text
        return elem
    
def add_heading_for_references_section(elem: pf.Element, doc: pf.Doc) -> pf.Element:
    """
    Add a section heading for the references, which is missing in the docx output.
    """
    # FIXME: format of the section heading for references
    reference_heading = pf.Str('References')
    if isinstance(elem, pf.Div) and elem.identifier == 'refs':
        return [pf.Header(reference_heading, identifier='references'), elem]
    return elem


# *****************************************************************************
# Figures and Tables
# Add figure and table number to the caption text in format "Figure 1: Caption"
# *****************************************************************************

# NOTE: We assume that the path to the images use relative path in latex file. 
# Thus, we have to add extra info so that the filter can find the images.
path_to_texfiles = 'texfiles/'

def adjust_images(elem: pf.Element, doc: pf.Doc) -> pf.Element:
    """
    Adjustment of latex command for images to match the docx format.
    
    (1) Specify the path of the image file.

    (2) Remove the width annotations made in the latex file since the
    latex command for image size can not be translated into command
    in docx directly now.

    (3) Check the format of the image file. PDF images are not supported.
    """
    if isinstance(elem, pf.Image):
        elem.url = path_to_texfiles + elem.url

        if 'width' in elem.attributes:
            del elem.attributes['width']

        if elem.url.endswith('.pdf'):
            print('PDF images are not supported in docx. Please convert into PNG or JPEG first.', 
                  file=sys.stderr)
    return elem

# NOTE: Figures and tables are floats in latex without serial numbers. 
# We use global dictionaries to store the serial numbers of figures and tables,
# and then add the serial numbers to the caption text.

figures = {}

def number_figures(elem: pf.Element, doc: pf.Doc) -> pf.Element:
    if isinstance(elem, pf.Figure):
        # FIXME: format of the figure number
        fignum = f"Figure {len(figures) + 1}"
        figures[elem.identifier] = f"{len(figures) + 1}"
        t = find_first_str(elem.caption)
        t.text = fignum + ': ' + t.text
        return elem

tables = {}

def number_tables(elem: pf.Element, doc: pf.Doc) -> pf.Element:
    if isinstance(elem, pf.Table):
        # FIXME: format of the table number
        tabnum = f"Table {len(tables) + 1}"
        tables[elem.parent.identifier] = f"{len(tables) + 1}"
        t = find_first_str(elem.caption)
        t.text = tabnum + ': ' + t.text
        return elem


# *****************************************************************************
# Theorems
# *****************************************************************************

# NOTE: Other environment like lemma, etc. can be handled in the same way. 
theorems = {}

def extract_theorem_label(elem: pf.Element, doc: pf.Doc) -> pf.Element:
    """
    Find the label of the theorems and store in global dictionary for later use. 
    """
    if isinstance(elem, pf.Div):
        if 'theorem' in elem.classes:
            thm_num = len(theorems) + 1
            label = find_ref_label(elem)
            if label is not None:
                theorems[label] = f"{len(theorems) + 1}"
                return elem
            else:
                theorems[thm_num] = f"{len(theorems) + 1}"
                return elem


# *****************************************************************************
# Cross references
# Resolve the cross references in the text.
# *****************************************************************************

# NOTE: We use regular expression to match the latex command \ref{...}. 
# Other ref commands can be added.
ref_pattern = re.compile(r"\\ref\{(.*)\}")

def resolve_cross_reference(elem: pf.Element, doc: pf.Doc) -> pf.Str | None:
    """
    Resolve the cross references of sections, figures, tables and theorems.
    """
    if isinstance(elem, pf.RawInline):
        matches = ref_pattern.match(elem.text)
        if matches:
            identifier = matches.group(1)
            if identifier in headers:
                return pf.Str(headers[identifier])
            elif identifier in figures:
                return pf.Str(figures[identifier])
            elif identifier in tables:
                return pf.Str(tables[identifier])
            elif identifier in theorems:
                return pf.Str(theorems[identifier])
        else:
            return None
        

# *****************************************************************************
# Equations
# Number the labeled equations in format "(section.equation)" and 
# resolve their references.
# *****************************************************************************

equation_counter = []  # index for section, value for number
equations = {}

def number_equations(elem: pf.Element, doc: pf.Doc) -> pf.Element:
    """
    Number the equations with labels in the text in format "(section.equation)".
    Extract the labels and store with the equation numbers in global dictionary.
    """
    # global section_number
    if isinstance(elem, pf.Header):
        level = elem.level
        if level == 1:
            equation_counter.append(0)
        return elem
    if isinstance(elem, pf.Math):
        if elem.format == 'DisplayMath':
            text = elem.text
            # extract \label{...} from elem.text if it exists
            matches = re.search(r"\\label\{(.*)\}", text)
            if matches:
                label = matches.group(1)
                equation_counter[-1] += 1
                sec_num = len(equation_counter)
                eq_num = equation_counter[-1]

                # FIXME: format of the equation number
                equation_number = f"({sec_num}.{eq_num})"
                equations[label] = equation_number
                
                # remove the \label{...} from the text
                text = text.replace(matches.group(0), '')
                # add the equation number in docx format to the text
                text = text + " \\#" + equation_number
                elem.text = text

                return elem

def resolve_equation_reference(elem: pf.Element, doc: pf.Doc) -> pf.Str | None:
    """
    Resolve the equation references of those labeled equations.
    """
    if isinstance(elem, pf.RawInline):
        # NOTE: We only match the latex command \eqref{...} here. 
        matches = re.search(r"\\eqref\{(.*)\}", elem.text)
        if matches:
            label = matches.group(1)
            if label in equations:
                return pf.Str(equations[label])
        else:
            return None


# *****************************************************************************
# Indentation for paragraphs
# *****************************************************************************

# FIXME: The switch of indenting the first line of each paragraph.
is_paragraph_with_indent = False

def indent_paragraph(elem: pf.Element, doc: pf.Doc) -> pf.Element:
    """
    Indent the first line of paragraphs in abstract and main body.
    """
    if is_paragraph_with_indent:
        # FIXME: format of the indentation
        indent = '        '
        if isinstance(elem, pf.Para):
            if isinstance(elem.parent, pf.Doc) or isinstance(elem.parent, pf.MetaBlocks):
                first_word = find_first_str(elem)
                first_word.text = indent + first_word.text
        return elem


# *****************************************************************************
# Main function
# *****************************************************************************

def main(doc: pf.Doc = None):
    return pf.run_filters([number_headers,
                           add_heading_for_references_section, 
                           adjust_images, 
                           number_figures, 
                           number_tables,
                           extract_theorem_label,
                           resolve_cross_reference,
                           number_equations,
                           resolve_equation_reference,
                           indent_paragraph,
                        ], 
                        doc=doc)


if __name__ == '__main__':
    main()
