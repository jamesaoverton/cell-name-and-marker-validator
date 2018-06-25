

build:
	mkdir $@

# Extract a table of oio:hasExactSynonyms for (proper) PR terms.
# We want the "PRO-short-label" but unfortunately that's in an OWL annotation property.
build/pr-exact-synonyms.tsv: build/pr.owl | build
	rapper $< \
	| grep '^<http://purl.obolibrary.org/obo/PR_0' \
	| grep '> <http://www.geneontology.org/formats/oboInOwl#hasExactSynonym> "' \
	| sed 's/^<\(.*\)> <.*> "\(.*\)".*$$/\1	\2/' \
	| sed 's!^http://purl.obolibrary.org/obo/PR_!PR:!' \
	> $@

# Download a Google Sheet as TSV
# https://docs.google.com/spreadsheets/d/1jCieXeH_T83d0K3n_3W8QFiCrN4AASw5FlP0nezPhOI/edit#gid=0
build/special-gates.tsv: | build
	curl -L -o $@ "https://docs.google.com/spreadsheets/u/0/d/1jCieXeH_T83d0K3n_3W8QFiCrN4AASw5FlP0nezPhOI/export?format=tsv"

build/normalized.tsv: src/normalize.py build/special-gates.tsv source.tsv | build
	$^ $@

build/known-gates.tsv: build/special-gates.tsv build/pr-exact-synonyms.tsv
	cat $^ | cut -f 1-2 > $@

build/gates.tsv: src/find-gates.py build/known-gates.tsv build/normalized.tsv
	$^ $@

build/report.tsv: src/report.py build/normalized.tsv build/gates.tsv
	$^ $@

build/summary.tsv: src/summarize.py build/report.tsv
	$^ $@
