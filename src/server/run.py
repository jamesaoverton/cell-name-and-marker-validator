#!/usr/bin/env python3

import csv
import gizmos.search
import gizmos.tree
import logging
import os
import re
import sqlite3
import subprocess
import valve

from flask import abort, Flask, render_template, request, Response
from jinja2 import Template
from tempfile import TemporaryDirectory
from tsv2html import tsv2html

app = Flask(__name__)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/examples")
def examples():
    # TODO
    return render_template("examples.html")


@app.route("/instructions")
def instructions():
    return render_template("instructions.html")


@app.route("/terminology")
def terminology():
    # TODO
    html = "<h1>Terminology</h1>"
    html += '\n<ul><li><a href="/terminology/pr">Protein Ontology</a></li>'
    html += '\n<li><a href="/terminology/cl">Cell Ontology</a></li></ul>'
    return render_template("base.html", default=html)


@app.route("/terminology/<ont>")
def show_tree(ont):
    content = get_tree(ont, None)
    return render_template("base.html", default=content)


@app.route("/terminology/<ont>/<term_id>")
def show_tree_at(ont, term_id):
    content = get_tree(ont, term_id)
    return render_template("base.html", default=content)


@app.route("/validator", methods=["GET", "POST"])
def validator():
    if request.method == "GET":
        return render_template("validator.html")
    else:
        if "file" not in request.files:
            message = "<p class='alert alert-danger'>Please upload a file.</p>"
            return render_template("validator.html", message=message)
        f = request.files["file"]
        filename = f.filename
        if filename.endswith(".csv"):
            suffix = ".csv"
        elif filename.endswith(".tsv"):
            suffix = ".tsv"
        else:
            message = f"<p class='alert alert-danger'>Unrecognized file type for '{filename}'. Please use CSV or TSV format.</p>"
            return render_template("validator.html", message=message)

        tempdir = TemporaryDirectory()
        path = os.path.join(tempdir.name, "cell-names-and-markers" + suffix)
        f.save(path)

        messages = validate(
            "../../build/cell.tsv", "../../build/cl-levels.tsv", "../../build/marker.tsv", path
        )

        if messages:
            message = "<p class='alert alert-danger'>This template contains errors.</p>"
        else:
            message = "<p class='alert alert-success'>This template is valid.</p>"

        table = tsv2html(path, messages)
        message += "\n\n" + table
        return render_template("validator.html", message=message)


def get_cl_id(cell_names, name):
    name = re.sub(r"(DC|B|M|NK|T): ", "", name)
    if " & " in name:
        name = name.split(" & ")[0]
    return cell_names.get(name, None)


def get_clean_marker(name):
    if name.endswith("++"):
        return name[:-2], "high"
    elif name.endswith("+-"):
        return name[:-2], "low"
    elif name.endswith("+"):
        return name[:-1], "positive"
    elif name.endswith("-"):
        return name[:-1], "negative"
    return name, None


def get_database(resource):
    db_name = resource.lower()
    db = f"../../build/{db_name}.db"
    if not os.path.exists("../../build"):
        os.mkdir("../../build")
    if not os.path.exists(db):
        # TODO - make database
        logging.info("Building database for " + resource)
        rc = subprocess.call(f"cd ../.. && make build/{db_name}.db", shell=True)
        if rc != 0:
            return abort(500, description="Unable to create database for " + resource)
    return db


def get_pr_id(gate_names, name):
    return gate_names.get(name, None)


def get_tree(ont, term_id):
    db = get_database(ont)
    fmt = request.args.get("format", "")
    if fmt == "json":
        label = request.args.get("text", "")
        return gizmos.search.search(db, label, limit=30)
    href = "./{curie}"
    if not term_id:
        href = ont + "/{curie}"
    if ont == "cl":
        title = "Cell Ontology Browser"
    elif ont == "pr":
        title = "Protein Ontology Browser"
    else:
        return "Unknown ontology: " + title
    return gizmos.tree.tree(
        db, term_id, title=title, href=href, include_search=True, standalone=True
    )


def validate(cell_names_file, cell_levels_file, gate_names_file, cell_gate_file):
    # Map of CL ID
    # - {positive: gates, negative: gates, high: gates, low: gates}
    # positive: obo:RO_0002104
    # negative: obo:cl#lacks_plasma_membrane_part
    # high: obo:cl#has_high_plasma_membrane_amount
    # low: obo:cl#has_low_plasma_membrane_amount
    errors = []
    cell_names = {}
    with open(cell_names_file, "r") as f:
        reader = csv.reader(f, delimiter="\t")
        next(reader)
        for row in reader:
            cell_names[row[1]] = row[0]

    gate_names = {}
    with open(gate_names_file, "r") as f:
        reader = csv.reader(f, delimiter="\t")
        next(reader)
        for row in reader:
            gate_names[row[1]] = row[0]

    cell_levels = {}
    with open(cell_levels_file, "r") as f:
        reader = csv.reader(f, delimiter="\t")
        next(reader)
        for row in reader:
            curie = row[0]
            has_part = row[1]
            lacks_part = row[2]
            high_amount = row[3]
            low_amount = row[4]
            valid_gates = {}
            if has_part:
                for p in has_part.split("|"):
                    valid_gates[p] = "positive"
            if lacks_part:
                for p in lacks_part.split("|"):
                    valid_gates[p] = "negative"
            if high_amount:
                for p in high_amount.split("|"):
                    valid_gates[p] = "high"
            if low_amount:
                for p in low_amount.split("|"):
                    valid_gates[p] = "low"
            cell_levels[curie] = valid_gates

    table = os.path.splitext(os.path.basename(cell_gate_file))[0]
    with open(cell_gate_file, "r") as f:
        reader = csv.reader(f, delimiter="\t")
        next(reader)
        idx = 1
        for line in reader:
            idx += 1
            cell_pop_name = line[0].strip()
            cell = get_cl_id(cell_names, cell_pop_name)
            if not cell:
                errors.append(
                    {
                        "table": table,
                        "cell": valve.idx_to_a1(idx, 1),
                        "level": "ERROR",
                        "message": f"'{cell_pop_name}' must be a name or synonym from Cell Ontology",
                    }
                )
                continue
            valid_gates = cell_levels.get(cell, {})

            # Compare to provided gates
            for marker_name in [x.strip() for x in line[1].split(",")]:
                marker_name_clean, level = get_clean_marker(marker_name)
                marker = get_pr_id(gate_names, marker_name_clean)
                if not marker:
                    errors.append(
                        {
                            "table": table,
                            "cell": valve.idx_to_a1(idx, 2),
                            "level": "ERROR",
                            "message": f"'{marker_name}' must be a name or synonym from Protein Ontology",
                        }
                    )
                    continue
                if marker not in valid_gates:
                    # TODO - is this OK?
                    continue
                expected_level = valid_gates[marker]
                if level == "positive" and expected_level in ["high", "low"]:
                    errors.append(
                        {
                            "table": table,
                            "cell": valve.idx_to_a1(idx, 2),
                            "level": "INFO",
                            "message": f"For this cell population, {marker_name_clean} has {expected_level} expression",
                        }
                    )
                elif level in ["high", "low"] and expected_level == "positive":
                    errors.append(
                        {
                            "table": table,
                            "cell": valve.idx_to_a1(idx, 2),
                            "level": "INFO",
                            "message": f"For this cell population, {marker_name_clean} is positive, but not {level}",
                        }
                    )
                elif level != expected_level:
                    errors.append(
                        {
                            "table": table,
                            "cell": valve.idx_to_a1(idx, 2),
                            "level": "ERROR",
                            "message": f"For this cell population, {marker_name_clean} must be {expected_level}",
                        }
                    )
    return errors
