-- Teilwortsuche als Ergänzung zur Wortsuche: findet Beugungen und Komposita
-- ("Migration" in "Schemamigrationen"). Wird nur genutzt, um nach den Worttreffern
-- aufzufüllen; Status-, Rückzugs- und Bereichsfilter gelten unverändert.
CREATE VIRTUAL TABLE memories_trigram USING fts5(
    problem, solution, content='memories', content_rowid='id', tokenize='trigram'
);
CREATE TRIGGER memories_trigram_insert AFTER INSERT ON memories BEGIN
    INSERT INTO memories_trigram(rowid, problem, solution)
        VALUES(new.id, new.problem, new.solution);
END;
CREATE TRIGGER memories_trigram_delete AFTER DELETE ON memories BEGIN
    INSERT INTO memories_trigram(memories_trigram, rowid, problem, solution)
        VALUES('delete', old.id, old.problem, old.solution);
END;
CREATE TRIGGER memories_trigram_update AFTER UPDATE OF problem, solution ON memories BEGIN
    INSERT INTO memories_trigram(memories_trigram, rowid, problem, solution)
        VALUES('delete', old.id, old.problem, old.solution);
    INSERT INTO memories_trigram(rowid, problem, solution)
        VALUES(new.id, new.problem, new.solution);
END;
INSERT INTO memories_trigram(memories_trigram) VALUES('rebuild');
