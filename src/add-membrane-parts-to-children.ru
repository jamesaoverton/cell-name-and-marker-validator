PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX owl: <http://www.w3.org/2002/07/owl#>
PREFIX obo: <http://purl.obolibrary.org/obo/>
PREFIX cl: <http://purl.obolibrary.org/obo/cl#>

INSERT {
  ?child rdfs:subClassOf ?part .
}
WHERE {
  VALUES ?parts {
    obo:RO_0002104                     # has plasma membrane part
    cl:lacks_plasma_membrane_part      # lacks plasma membrane part
    cl:has_high_plasma_membrane_amount # has high plasma membrane amount
    cl:has_low_plasma_membrane_amount  # has low plasma membrane amount
  }
  ?child rdfs:subClassOf+ ?parent .
  ?parent rdfs:subClassOf ?part .
  ?part a owl:Restriction ;
    owl:onProperty ?parts ;
    owl:someValuesFrom ?some .
}
