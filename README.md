# Cell Name and Marker Validator Demo

[![Build Status](https://travis-ci.com/jamesaoverton/cell-name-and-marker-validator.svg?branch=master)](https://travis-ci.com/jamesaoverton/cell-name-and-marker-validator)

This project demonstrates how data about cell populations and gating strategies can be transformed into semantically rich linked data and validated, using ontologies such as the [Protein Ontology](https://pir.georgetown.edu/pro/) and [Cell Ontology](http://obofoundry.org/ontology/cl.html). This validator is designed to implement the [Cytometry Data Standard](https://docs.google.com/document/d/1vGg3R745uuSH7bcKjukf_Mm5CIt5kgImU79wZbD-8zE).

There are two ways to use this code:

1. as a web application that validates a cell population name and gate definition against our proposed standard (under development), and compares them using information from the Protein Ontology and Cell Ontology
2. as a script that processes an existing table of cell population names and gate definitions, used as a reference for developing the proposed standard

## Usage

See the [`Makefile`](Makefile) for software requirements and build tasks.

First, install requirements (optionally, use a virtual environment):
```
python3 -m pip install -r requirements.txt
```

Then, `make` all dependencies:
```
make all
```

The first time you run this, it must download the full Protein Ontology which can take some time. Subsequent builds with an existing `build/` directory will be faster.

### Web Service

Once dependencies are complete (see above), set the `FLASK_APP` variable, and start the server:

```
export FLASK_APP=src/run.py
flask run
```

### Command Line Utility

The validation service can also be run over a file directly from the command line using `src/validate.py`:

```
python3 src/validate.py [CELL_NAMES] [CELL_LEVELS] [GATE_NAMES] [INPUT] > [OUTPUT_TSV]
```

The first three input files can be found in the `build/` directory after building the dependencies:
* **CELL_NAMES** (`build/cell.tsv`): Cell Ontology IDs & labels and/or synonyms (each distinct label or synonym has its own line, and IDs may be repeated)
* **CELL_LEVELS** (`build/cl-levels.tsv`): Membrane parts for each Cell Ontology term (positive, negative, high, and low)
* **GATE_NAMES** (`build/marker.tsv`): Protein Ontology IDs & labels and/or synonyms (each distinct label or synonym has its own line, and IDs may be repeated)

The input file should be the cell population & gates to validate. This file requires two columns:
* **Cell Population Name**: The cell type from the Cell Ontology
* **Gating Definition**: Comma-separated gates from the Protein Ontology
