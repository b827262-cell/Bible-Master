BEGIN;
DO $$
DECLARE e bigint; n integer;
BEGIN
 INSERT INTO entries(source_url,canonical_url,devotional_date,raw_reference,scope) VALUES('https://unit.test/a','https://unit.test/a','2026-01-01','馬太福音 4:1','IN_SCOPE') RETURNING id INTO e;
 INSERT INTO scripture_ranges(entry_id,sequence_no,book_code,start_chapter,start_verse,end_chapter,end_verse) VALUES(e,1,'MAT',4,1,4,1);
 BEGIN
  INSERT INTO scripture_ranges(entry_id,sequence_no,book_code,start_chapter,start_verse,end_chapter,end_verse) VALUES(e,2,'MAT',29,1,29,1);
  RAISE EXCEPTION 'out-of-range chapter accepted';
 EXCEPTION WHEN check_violation THEN NULL; END;
 BEGIN
  UPDATE scripture_ranges SET end_verse=999 WHERE entry_id=e;
  RAISE EXCEPTION 'out-of-range verse accepted';
 EXCEPTION WHEN check_violation THEN NULL; END;
 UPDATE entries SET summary='原創',reflection='反思' WHERE id=e;
 UPDATE entries SET source_status='APPROVED',source_reviewer='審核者',source_reviewed_at=now() WHERE id=e;
 UPDATE entries SET theology_status='APPROVED',theology_reviewer='審核者',theology_reviewed_at=now() WHERE id=e;
 SELECT count(*) INTO n FROM v_approved_export WHERE id=e; IF n<>1 THEN RAISE EXCEPTION 'approved missing'; END IF;
 UPDATE entries SET summary='已修改' WHERE id=e;
 SELECT count(*) INTO n FROM v_approved_export WHERE id=e; IF n<>0 THEN RAISE EXCEPTION 'content edit did not revoke'; END IF;
 UPDATE entries SET theology_status='APPROVED',theology_reviewer='審核者',theology_reviewed_at=now() WHERE id=e;
 UPDATE scripture_ranges SET end_verse=2 WHERE entry_id=e;
 SELECT count(*) INTO n FROM v_approved_export WHERE id=e; IF n<>0 THEN RAISE EXCEPTION 'range edit did not revoke'; END IF;
 IF (SELECT source_status FROM entries WHERE id=e) <> 'PENDING' THEN RAISE EXCEPTION 'source not revoked'; END IF;
 SELECT count(*) INTO n FROM review_audit_logs WHERE target_id=e; IF n<4 THEN RAISE EXCEPTION 'missing audit'; END IF;
 BEGIN INSERT INTO media_links(canonical_url,scope,status,reviewer,reviewed_at) VALUES('https://unit.test/media','IN_SCOPE','VERIFIED','reviewer',now()); RAISE EXCEPTION 'null book passed'; EXCEPTION WHEN check_violation THEN NULL; END;
 BEGIN INSERT INTO entries(source_url,canonical_url,devotional_date,raw_reference,scope,is_template,source_status,source_reviewer,source_reviewed_at) VALUES('https://unit.test/t','https://unit.test/t','2026-01-01','馬太福音 1:1','IN_SCOPE',true,'APPROVED','a',now()); RAISE EXCEPTION 'template passed'; EXCEPTION WHEN check_violation THEN NULL; END;
 INSERT INTO entries(source_url,canonical_url,raw_reference,scope) VALUES('https://unit.test/u','https://unit.test/u','','UNPARSED');
 BEGIN INSERT INTO entries(source_url,canonical_url,raw_reference,scope) VALUES('https://unit.test/u','https://unit.test/u','','UNPARSED'); RAISE EXCEPTION 'undated duplicate passed'; EXCEPTION WHEN unique_violation THEN NULL; END;
 IF has_table_privilege('bible_devotional_export_reader','entries','SELECT') THEN RAISE EXCEPTION 'reader has base table access'; END IF;
 IF NOT has_table_privilege('bible_devotional_export_reader','v_approved_export','SELECT') THEN RAISE EXCEPTION 'reader missing view access'; END IF;
END $$;
ROLLBACK;
