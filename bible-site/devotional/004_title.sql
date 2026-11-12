BEGIN;
ALTER TABLE entries ADD COLUMN title text;
CREATE OR REPLACE FUNCTION reset_entry_reviews() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF ROW(OLD.source_url,OLD.canonical_url,OLD.devotional_date,OLD.raw_reference,OLD.scope,OLD.is_template) IS DISTINCT FROM ROW(NEW.source_url,NEW.canonical_url,NEW.devotional_date,NEW.raw_reference,NEW.scope,NEW.is_template) THEN
   NEW.source_status:='PENDING'; NEW.source_reviewer:=NULL; NEW.source_reviewed_at:=NULL;
   NEW.theology_status:='PENDING'; NEW.theology_reviewer:=NULL; NEW.theology_reviewed_at:=NULL;
 ELSIF ROW(OLD.title,OLD.summary,OLD.reflection,OLD.prayer) IS DISTINCT FROM ROW(NEW.title,NEW.summary,NEW.reflection,NEW.prayer) OR NEW.source_status <> 'APPROVED' THEN
   NEW.theology_status:='PENDING'; NEW.theology_reviewer:=NULL; NEW.theology_reviewed_at:=NULL;
 END IF;
 RETURN NEW;
END $$;
CREATE OR REPLACE VIEW v_approved_export AS SELECT e.id,e.devotional_date,e.canonical_url AS source_url,e.raw_reference AS scripture_reference,e.summary,e.reflection,e.prayer,
 (SELECT jsonb_agg(jsonb_build_object('book',r.book_code,'start_chapter',r.start_chapter,'start_verse',r.start_verse,'end_chapter',r.end_chapter,'end_verse',r.end_verse) ORDER BY r.sequence_no) FROM scripture_ranges r WHERE r.entry_id=e.id) AS ranges,
 COALESCE((SELECT jsonb_agg(m.canonical_url ORDER BY m.id) FROM media_links m WHERE m.entry_id=e.id AND m.status='VERIFIED' AND NOT m.is_template),'[]'::jsonb) AS media_urls, e.title
 FROM entries e WHERE e.source_status='APPROVED' AND e.theology_status='APPROVED' AND e.scope='IN_SCOPE' AND NOT e.is_template
 AND EXISTS(SELECT 1 FROM scripture_ranges r WHERE r.entry_id=e.id) AND NOT EXISTS(SELECT 1 FROM scripture_ranges r WHERE r.entry_id=e.id AND r.book_code NOT IN ('MAT','MRK','LUK','JHN'));
COMMIT;
