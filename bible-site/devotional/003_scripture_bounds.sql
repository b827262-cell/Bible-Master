BEGIN;
-- Limits derived from the four project Bible JSON files, including merged verses.
CREATE TABLE gospel_chapter_limits (
 book_code text NOT NULL, chapter integer NOT NULL, max_verse integer NOT NULL,
 PRIMARY KEY (book_code, chapter)
);
INSERT INTO gospel_chapter_limits VALUES
('MAT', 1, 25),
('MAT', 2, 23),
('MAT', 3, 17),
('MAT', 4, 25),
('MAT', 5, 48),
('MAT', 6, 34),
('MAT', 7, 29),
('MAT', 8, 34),
('MAT', 9, 38),
('MAT', 10, 42),
('MAT', 11, 30),
('MAT', 12, 50),
('MAT', 13, 58),
('MAT', 14, 36),
('MAT', 15, 39),
('MAT', 16, 28),
('MAT', 17, 27),
('MAT', 18, 35),
('MAT', 19, 30),
('MAT', 20, 34),
('MAT', 21, 46),
('MAT', 22, 46),
('MAT', 23, 39),
('MAT', 24, 51),
('MAT', 25, 46),
('MAT', 26, 75),
('MAT', 27, 66),
('MAT', 28, 20),
('MRK', 1, 45),
('MRK', 2, 28),
('MRK', 3, 35),
('MRK', 4, 41),
('MRK', 5, 43),
('MRK', 6, 56),
('MRK', 7, 37),
('MRK', 8, 38),
('MRK', 9, 50),
('MRK', 10, 52),
('MRK', 11, 33),
('MRK', 12, 44),
('MRK', 13, 37),
('MRK', 14, 72),
('MRK', 15, 47),
('MRK', 16, 20),
('LUK', 1, 80),
('LUK', 2, 52),
('LUK', 3, 38),
('LUK', 4, 44),
('LUK', 5, 39),
('LUK', 6, 49),
('LUK', 7, 50),
('LUK', 8, 56),
('LUK', 9, 62),
('LUK', 10, 42),
('LUK', 11, 54),
('LUK', 12, 59),
('LUK', 13, 35),
('LUK', 14, 35),
('LUK', 15, 32),
('LUK', 16, 31),
('LUK', 17, 37),
('LUK', 18, 43),
('LUK', 19, 48),
('LUK', 20, 47),
('LUK', 21, 38),
('LUK', 22, 71),
('LUK', 23, 56),
('LUK', 24, 53),
('JHN', 1, 51),
('JHN', 2, 25),
('JHN', 3, 36),
('JHN', 4, 54),
('JHN', 5, 47),
('JHN', 6, 71),
('JHN', 7, 52),
('JHN', 8, 59),
('JHN', 9, 41),
('JHN', 10, 42),
('JHN', 11, 57),
('JHN', 12, 50),
('JHN', 13, 38),
('JHN', 14, 31),
('JHN', 15, 27),
('JHN', 16, 33),
('JHN', 17, 26),
('JHN', 18, 40),
('JHN', 19, 42),
('JHN', 20, 31),
('JHN', 21, 25);
GRANT SELECT ON gospel_chapter_limits TO bible_devotional_operator;
CREATE FUNCTION enforce_gospel_bounds() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF NEW.book_code IN ('MAT','MRK','LUK','JHN') AND (
   NOT EXISTS (SELECT 1 FROM gospel_chapter_limits WHERE book_code=NEW.book_code AND chapter=NEW.start_chapter AND (NEW.start_verse IS NULL OR NEW.start_verse<=max_verse))
   OR NOT EXISTS (SELECT 1 FROM gospel_chapter_limits WHERE book_code=NEW.book_code AND chapter=NEW.end_chapter AND (NEW.end_verse IS NULL OR NEW.end_verse<=max_verse))
 ) THEN
   RAISE check_violation USING MESSAGE='四福音章節超出範圍';
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER gospel_bounds BEFORE INSERT OR UPDATE ON scripture_ranges
 FOR EACH ROW EXECUTE FUNCTION enforce_gospel_bounds();
DO $$
BEGIN
 IF EXISTS (
   SELECT 1 FROM scripture_ranges r
   LEFT JOIN gospel_chapter_limits a ON a.book_code=r.book_code AND a.chapter=r.start_chapter
   LEFT JOIN gospel_chapter_limits b ON b.book_code=r.book_code AND b.chapter=r.end_chapter
   WHERE r.book_code IN ('MAT','MRK','LUK','JHN')
   AND (a.chapter IS NULL OR b.chapter IS NULL OR r.start_verse>a.max_verse OR r.end_verse>b.max_verse)
 ) THEN
   RAISE check_violation USING MESSAGE='既有經文範圍超出四福音章節上限';
 END IF;
END $$;
COMMIT;
