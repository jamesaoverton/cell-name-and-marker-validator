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

Once dependencies are complete (see above), navigate to the `src/server` directory, set the `FLASK_APP` variable, and start the server:

```
cd src/server
export FLASK_APP=run.py
flask run
```
