SELECT DISTINCT s1.stanza, s2.value
FROM statements s1
JOIN statements s2 ON s1.subject = s2.subject WHERE
	s1.subject LIKE '_:%' AND
	s1.stanza LIKE 'PR:%' AND
	s1.predicate = 'oio:hasSynonymType' AND 
	s1.object = 'obo:pr#PRO-short-label' AND 
	s2.predicate = 'owl:annotatedTarget'
ORDER BY s1.stanza;
