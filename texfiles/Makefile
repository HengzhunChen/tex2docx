name=report

all: $(name).pdf

$(name).pdf: $(name).tex $(name).bib
	pdflatex $(name)
	bibtex   $(name).aux
	pdflatex $(name)
	pdflatex $(name)

clean:
	rm -f $~ *.aux *.idx *.log *.blg *.bbl *.toc *.dvi *.ps *.out *.gz \
			 *.fdb_latexmk *.fls *.thm
cleanall:
	rm -f $~ *.aux *.idx *.log *.blg *.bbl *.toc *.dvi *.ps *.out *.gz \
			 *.fdb_latexmk *.fls *.thm \
	         figure/*-eps-converted-to.pdf $(name).pdf
