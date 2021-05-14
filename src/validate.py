#!/usr/bin/env python3

import csv
import os
import re
import sys
import valve

from argparse import ArgumentParser


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


def get_pr_id(gate_names, name):
    return gate_names.get(name, None)


def validate(cell_names_file, cell_levels_file, gate_names_file, cell_gate_file):
    """
    :param cell_names_file: path to file containing Cell Ontology IDs & Labels
    :param cell_levels_file: path to file containing Cell Ontology IDs & membrane parts
    :param gate_names_file: path to file containing Protein Ontology IDs & Labels
    :param cell_gate_file: path to file to validate
    """
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


def main():
    parser = ArgumentParser()
    parser.add_argument("cell_names", help="Cell Ontology IDs & labels/synonyms")
    parser.add_argument("cell_levels", help="Cell Ontology IDs & membrane parts")
    parser.add_argument("gate_names", help="Protein Ontology IDs & labels/synonyms")
    parser.add_argument("input", help="File to validate (cell populations & gates)")
    args = parser.parse_args()
    errors = validate(args.cell_names, args.cell_levels, args.gate_names, args.input)
    if errors:
        writer = csv.DictWriter(
            sys.stdout,
            delimiter="\t",
            lineterminator="\n",
            fieldnames=["table", "cell", "level", "message"],
        )
        writer.writeheader()
        writer.writerows(errors)


if __name__ == "__main__":
    main()
