#!/usr/bin/env python3

from normalize import tokenize, normalize


suffixsymbs = {
    'high': '++',
    'medium': '+~',
    'low': '+-',
    'positive': '+',
    'negative': '-'
}

suffixsyns = {
    'high': 'high',
    'hi': 'high',
    'bright': 'high',
    'Bright': 'high',
    'bri': 'high',
    'br': 'high',
    '(high)': 'high',
    'medium': 'medium',
    'med': 'medium',
    'intermediate': 'medium',
    'int': 'medium',
    '(medium)': 'medium',
    'low': 'low',
    'lo': 'low',
    'LO': 'low',
    'dim': 'low',
    'di': 'low',
    '(low)': 'low',
    'positive': 'positive',
    'negative': 'negative'
}


def main():
    reported = 'CD14-CD56-CD3+CD4+CD8-CD45RA+CCR7+'
    tokens = tokenize('LaJolla', suffixsymbs, suffixsyns, reported)
    assert tokens == ['CD14-', 'CD56-', 'CD3+', 'CD4+', 'CD8-', 'CD45RA+', 'CCR7+']

    reported = 'CD3-, CD19+, CD20-, CD27hi, CD38hi'
    tokens = tokenize('Emory', suffixsymbs, suffixsyns, reported)
    assert tokens == ['CD3-', 'CD19+', 'CD20-', 'CD27++', 'CD38++']

    reported = 'CD3-/CD19+/CD20lo/CD38hi/CD27hi'
    tokens = tokenize('IPIRC', suffixsymbs, suffixsyns, reported)
    assert tokens == ['CD3-', 'CD19+', 'CD20+-', 'CD38++', 'CD27++']

    reported = 'CD21hi/CD24int'
    tokens = tokenize('Watson', suffixsymbs, suffixsyns, reported)
    assert tokens == ['CD21++', 'CD24+~']

    reported = 'Annexin negative'
    tokens = tokenize('Ltest', suffixsymbs, suffixsyns, reported)
    assert tokens == ['Annexin-']

    reported = 'CD3+ AND CD4+ AND small lymphocyte'
    tokens = tokenize('VRC', suffixsymbs, suffixsyns, reported)
    assert tokens == ['CD3+', 'CD4+', 'small_lymphocyte']

    reported = 'Lymphocytes and CD8+ and NP tet+'
    tokens = tokenize('Ertl', suffixsymbs, suffixsyns, reported)
    assert tokens == ['Lymphocytes', 'CD8+', 'NP_tet+']

    reported = 'Activated T: viable/singlets/Lymph/CD3+'
    tokens = tokenize('Stanford', suffixsymbs, suffixsyns, reported)
    assert tokens == ['viable', 'singlets', 'Lymph', 'CD3+']

    # TODO: Is this right?
    reported = 'CD14-CD33-/CD3-/CD16+CD56+/CD94+'
    tokens = tokenize('Stanford', suffixsymbs, suffixsyns, reported)
    assert tokens == ['CD14-', 'CD33-', 'CD3-', 'CD16+', 'CD56+', 'CD94+']

    # TODO: Is this right?
    reported = 'Live cells/CD4 T cells/CD4+ CD45RA-/Uninfected/SSC low'
    tokens = tokenize('Mayo', suffixsymbs, suffixsyns, reported)
    assert tokens == ['Live_cells', 'CD4_T_cells', 'CD4+', 'CD45RA-', 'Uninfected', 'SSC+-']

    reported = 'B220- live,doublet excluded,CD4+ CD44highCXCR5highPD1high,ICOS+'
    tokens = tokenize('New York Influenza', suffixsymbs, suffixsyns, reported)
    assert tokens == ['B220-_live', 'doublet_excluded', 'CD4+', 'CD44++', 'CXCR5++', 'PD1++',
                      'ICOS+']

    reported = 'lymphocytes/singlets/live/CD19-CD14-/CD3+/CD8+/CD69+IFNg+IL2+TNFa+'
    tokens = tokenize('New York Influenza', suffixsymbs, suffixsyns, reported)
    assert tokens == ['lymphocytes', 'singlets', 'live', 'CD19-', 'CD14-', 'CD3+', 'CD8+', 'CD69+',
                      'IFNg+', 'IL2+', 'TNFa+']

    reported = 'Alexa350 (high) + Alexa750 (medium)'
    tokens = tokenize('Modeling Viral', suffixsymbs, suffixsyns, reported)
    assert tokens == ['Alexa350++', 'Alexa750+~']

    reported = 'TNFa+IFNg-'
    tokens = tokenize('Flow Cytometry Analysis', suffixsymbs, suffixsyns, reported)
    assert tokens == ['TNFa+', 'IFNg-']


if __name__ == "__main__":
    main()
