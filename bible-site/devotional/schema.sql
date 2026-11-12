BEGIN;
CREATE TABLE entries (
 id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 source_url text NOT NULL, canonical_url text NOT NULL, devotional_date date,
 raw_reference text NOT NULL, scope text NOT NULL CHECK(scope IN ('IN_SCOPE','OUT_OF_SCOPE','UNPARSED')),
 is_template boolean NOT NULL DEFAULT false,
 source_status text NOT NULL DEFAULT 'PENDING' CHECK(source_status IN ('PENDING','NEEDS_FIX','APPROVED','REJECTED')),
 source_reviewer text, source_reviewed_at timestamptz,
 summary text, reflection text, prayer text,
 theology_status text NOT NULL DEFAULT 'PENDING' CHECK(theology_status IN ('PENDING','APPROVED','REJECTED')),
 theology_reviewer text, theology_reviewed_at timestamptz,
 CHECK (source_status <> 'APPROVED' OR (devotional_date IS NOT NULL AND scope='IN_SCOPE' AND NOT is_template AND NULLIF(btrim(source_reviewer),'') IS NOT NULL AND source_reviewed_at IS NOT NULL)),
 CHECK (theology_status <> 'APPROVED' OR (source_status='APPROVED' AND NOT is_template AND NULLIF(btrim(summary),'') IS NOT NULL AND NULLIF(btrim(reflection),'') IS NOT NULL AND NULLIF(btrim(theology_reviewer),'') IS NOT NULL AND theology_reviewed_at IS NOT NULL)),
 UNIQUE(canonical_url,devotional_date)
);
CREATE UNIQUE INDEX entries_undated ON entries(canonical_url) WHERE devotional_date IS NULL;
CREATE TABLE scripture_ranges (
 id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY, entry_id bigint NOT NULL REFERENCES entries ON DELETE CASCADE,
 sequence_no int NOT NULL CHECK(sequence_no>0), book_code text NOT NULL,
 start_chapter int NOT NULL CHECK(start_chapter>0), start_verse int CHECK(start_verse>0),
 end_chapter int NOT NULL CHECK(end_chapter>=start_chapter), end_verse int CHECK(end_verse>0),
 CHECK ((start_verse IS NULL AND end_verse IS NULL) OR (start_verse IS NOT NULL AND end_verse IS NOT NULL AND (end_chapter>start_chapter OR end_verse>=start_verse))), UNIQUE(entry_id,sequence_no)
);
CREATE TABLE media_links (
 id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY, entry_id bigint REFERENCES entries ON DELETE SET NULL,
 canonical_url text NOT NULL UNIQUE, recorded_date date, raw_reference text, scope text NOT NULL CHECK(scope IN ('IN_SCOPE','OUT_OF_SCOPE','UNPARSED')),
 book_code text, is_template boolean NOT NULL DEFAULT false, status text NOT NULL DEFAULT 'UNVERIFIED' CHECK(status IN ('UNVERIFIED','VERIFIED','REJECTED')),
 reviewer text, reviewed_at timestamptz,
 CHECK(status <> 'VERIFIED' OR (scope='IN_SCOPE' AND book_code IS NOT NULL AND book_code IN ('MAT','MRK','LUK','JHN') AND NOT is_template AND NULLIF(btrim(reviewer),'') IS NOT NULL AND reviewed_at IS NOT NULL))
);
CREATE TABLE review_audit_logs(id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY, target text NOT NULL, target_id bigint NOT NULL, review_type text NOT NULL, previous_status text, new_status text NOT NULL, reviewer text NOT NULL, notes text, reviewed_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE source_policy(id int PRIMARY KEY DEFAULT 1 CHECK(id=1), mode text NOT NULL DEFAULT 'MANUAL_ONLY' CHECK(mode IN ('MANUAL_ONLY','DISABLED','APPROVED')), robots_allowed boolean NOT NULL DEFAULT false, robots_checked_at timestamptz, authorization_basis text, approved_by text, approved_at timestamptz, CHECK(mode <> 'APPROVED' OR (robots_allowed AND robots_checked_at IS NOT NULL AND NULLIF(btrim(authorization_basis),'') IS NOT NULL AND NULLIF(btrim(approved_by),'') IS NOT NULL AND approved_at IS NOT NULL)));
INSERT INTO source_policy(id) VALUES(1);
CREATE FUNCTION reset_entry_reviews() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF ROW(OLD.source_url,OLD.canonical_url,OLD.devotional_date,OLD.raw_reference,OLD.scope,OLD.is_template) IS DISTINCT FROM ROW(NEW.source_url,NEW.canonical_url,NEW.devotional_date,NEW.raw_reference,NEW.scope,NEW.is_template) THEN
   NEW.source_status:='PENDING'; NEW.source_reviewer:=NULL; NEW.source_reviewed_at:=NULL;
   NEW.theology_status:='PENDING'; NEW.theology_reviewer:=NULL; NEW.theology_reviewed_at:=NULL;
 ELSIF ROW(OLD.summary,OLD.reflection,OLD.prayer) IS DISTINCT FROM ROW(NEW.summary,NEW.reflection,NEW.prayer) OR NEW.source_status <> 'APPROVED' THEN
   NEW.theology_status:='PENDING'; NEW.theology_reviewer:=NULL; NEW.theology_reviewed_at:=NULL;
 END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER entry_reset BEFORE UPDATE ON entries FOR EACH ROW EXECUTE FUNCTION reset_entry_reviews();
CREATE FUNCTION range_reset() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE eid bigint;
BEGIN
 eid:=CASE WHEN TG_OP='DELETE' THEN OLD.entry_id ELSE NEW.entry_id END;
 UPDATE entries SET source_status='PENDING',source_reviewer=NULL,source_reviewed_at=NULL,theology_status='PENDING',theology_reviewer=NULL,theology_reviewed_at=NULL WHERE id=eid;
 IF TG_OP='UPDATE' AND OLD.entry_id<>NEW.entry_id THEN UPDATE entries SET source_status='PENDING',source_reviewer=NULL,source_reviewed_at=NULL,theology_status='PENDING',theology_reviewer=NULL,theology_reviewed_at=NULL WHERE id=OLD.entry_id; END IF;
 RETURN NULL;
END $$;
CREATE TRIGGER ranges_reset AFTER INSERT OR UPDATE OR DELETE ON scripture_ranges FOR EACH ROW EXECUTE FUNCTION range_reset();
CREATE FUNCTION audit_entry() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF OLD.source_status IS DISTINCT FROM NEW.source_status THEN INSERT INTO review_audit_logs(target,target_id,review_type,previous_status,new_status,reviewer) VALUES('entries',NEW.id,'SOURCE',OLD.source_status,NEW.source_status,COALESCE(NULLIF(NEW.source_reviewer,''),current_user)); END IF;
 IF OLD.theology_status IS DISTINCT FROM NEW.theology_status THEN INSERT INTO review_audit_logs(target,target_id,review_type,previous_status,new_status,reviewer) VALUES('entries',NEW.id,'THEOLOGY',OLD.theology_status,NEW.theology_status,COALESCE(NULLIF(NEW.theology_reviewer,''),current_user)); END IF;
 RETURN NULL;
END $$;
CREATE TRIGGER entry_audit AFTER UPDATE ON entries FOR EACH ROW EXECUTE FUNCTION audit_entry();
CREATE VIEW v_approved_export AS SELECT e.id,e.devotional_date,e.canonical_url AS source_url,e.raw_reference AS scripture_reference,e.summary,e.reflection,e.prayer,
 (SELECT jsonb_agg(jsonb_build_object('book',r.book_code,'start_chapter',r.start_chapter,'start_verse',r.start_verse,'end_chapter',r.end_chapter,'end_verse',r.end_verse) ORDER BY r.sequence_no) FROM scripture_ranges r WHERE r.entry_id=e.id) AS ranges,
 COALESCE((SELECT jsonb_agg(m.canonical_url ORDER BY m.id) FROM media_links m WHERE m.entry_id=e.id AND m.status='VERIFIED' AND NOT m.is_template),'[]'::jsonb) AS media_urls
 FROM entries e WHERE e.source_status='APPROVED' AND e.theology_status='APPROVED' AND e.scope='IN_SCOPE' AND NOT e.is_template
 AND EXISTS(SELECT 1 FROM scripture_ranges r WHERE r.entry_id=e.id) AND NOT EXISTS(SELECT 1 FROM scripture_ranges r WHERE r.entry_id=e.id AND r.book_code NOT IN ('MAT','MRK','LUK','JHN'));
COMMIT;
CREATE FUNCTION guard_media() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF ROW(OLD.entry_id,OLD.canonical_url,OLD.recorded_date,OLD.raw_reference,OLD.scope,OLD.book_code,OLD.is_template) IS DISTINCT FROM ROW(NEW.entry_id,NEW.canonical_url,NEW.recorded_date,NEW.raw_reference,NEW.scope,NEW.book_code,NEW.is_template) THEN NEW.status:='UNVERIFIED'; NEW.reviewer:=NULL; NEW.reviewed_at:=NULL; END IF;
 RETURN NEW;
END $$;
CREATE TRIGGER media_reset BEFORE UPDATE ON media_links FOR EACH ROW EXECUTE FUNCTION guard_media();
CREATE FUNCTION audit_media() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF OLD.status IS DISTINCT FROM NEW.status THEN INSERT INTO review_audit_logs(target,target_id,review_type,previous_status,new_status,reviewer) VALUES('media_links',NEW.id,'MEDIA',OLD.status,NEW.status,COALESCE(NULLIF(NEW.reviewer,''),current_user)); END IF;
 RETURN NULL;
END $$;
CREATE TRIGGER media_audit AFTER UPDATE ON media_links FOR EACH ROW EXECUTE FUNCTION audit_media();
