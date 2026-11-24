-- 145 每日禱讀內容管理後端：草稿表與固定 SQL 函式
-- 只新增 admin_devotional_drafts 與本任務需要的函式；不改既有 entries/trigger/view 定義，
-- 不更新舊資料。正式安裝由 PM 在隔離驗收後執行。
BEGIN;

CREATE TABLE admin_devotional_drafts (
  id uuid PRIMARY KEY,
  version integer NOT NULL DEFAULT 1 CHECK (version > 0),
  entry_id bigint REFERENCES entries(id) ON DELETE SET NULL,
  base_version text,
  payload jsonb NOT NULL CHECK (jsonb_typeof(payload) = 'object'),
  status text NOT NULL DEFAULT 'DRAFT' CHECK (status IN ('DRAFT', 'APPLIED')),
  updated_at timestamptz NOT NULL DEFAULT now(),
  reviewer text,
  applied_at timestamptz,
  CHECK (status <> 'APPLIED' OR (NULLIF(btrim(reviewer), '') IS NOT NULL AND applied_at IS NOT NULL))
);

CREATE INDEX admin_devotional_drafts_updated_idx ON admin_devotional_drafts(updated_at DESC);
CREATE INDEX admin_devotional_drafts_entry_idx ON admin_devotional_drafts(entry_id);
-- 每個日期最多一份活草稿；併發時由 index 擋下第二份，不依賴先 SELECT 再 INSERT。
CREATE UNIQUE INDEX admin_devotional_drafts_active_date_uidx
  ON admin_devotional_drafts ((payload->'content'->>'date'))
  WHERE status = 'DRAFT';

GRANT SELECT, INSERT, UPDATE ON admin_devotional_drafts TO bible_devotional_operator;

-- 穩定 digest：日期、來源、出處、四文字欄、兩項審核狀態與 ranges。
-- 用 jsonb_build_object 的結構化文字做 md5，避免使用者正文含分隔符造成欄位邊界歧義。
CREATE FUNCTION admin_devotional_entry_version(p_entry_id bigint)
RETURNS text
LANGUAGE sql
SECURITY INVOKER
SET search_path = pg_catalog, public
AS $$
  SELECT md5(jsonb_build_object(
    'date', e.devotional_date::text,
    'source_url', e.source_url,
    'canonical_url', e.canonical_url,
    'reference', e.raw_reference,
    'title', COALESCE(e.title, ''),
    'summary', COALESCE(e.summary, ''),
    'reflection', COALESCE(e.reflection, ''),
    'prayer', COALESCE(e.prayer, ''),
    'source_status', e.source_status,
    'theology_status', e.theology_status,
    'scope', e.scope,
    'is_template', e.is_template,
    'ranges', COALESCE((
      SELECT jsonb_agg(jsonb_build_object(
        'book', r.book_code, 'start_chapter', r.start_chapter, 'start_verse', r.start_verse,
        'end_chapter', r.end_chapter, 'end_verse', r.end_verse
      ) ORDER BY r.sequence_no)
      FROM public.scripture_ranges r WHERE r.entry_id = e.id
    ), '[]'::jsonb)
  )::text)
  FROM public.entries e
  WHERE e.id = p_entry_id
$$;

REVOKE ALL ON FUNCTION admin_devotional_entry_version(bigint) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION admin_devotional_entry_version(bigint) TO bible_devotional_operator;

-- 儲存草稿：只寫 admin_devotional_drafts，不碰已核准 entries。
CREATE FUNCTION admin_devotional_draft_save(
  p_id uuid,
  p_version integer,
  p_entry_id bigint,
  p_base_version text,
  p_payload jsonb
)
RETURNS jsonb
LANGUAGE plpgsql
SECURITY INVOKER
SET search_path = pg_catalog, public
AS $$
DECLARE
  v_row public.admin_devotional_drafts%ROWTYPE;
  v_content jsonb;
  v_current text;
  v_date date;
  v_existing bigint;
  v_exists boolean;
  v_target public.entries%ROWTYPE;
BEGIN
  IF p_id IS NULL THEN
    RAISE EXCEPTION 'INVALID_PAYLOAD' USING ERRCODE = '22023';
  END IF;
  IF p_version IS NULL OR p_version < 0 THEN
    RAISE EXCEPTION 'VERSION_CONFLICT' USING ERRCODE = 'P0001';
  END IF;
  IF p_payload IS NULL OR jsonb_typeof(p_payload) <> 'object' THEN
    RAISE EXCEPTION 'INVALID_PAYLOAD' USING ERRCODE = '22023';
  END IF;

  v_content := p_payload->'content';
  IF v_content IS NULL OR jsonb_typeof(v_content) <> 'object'
     OR NULLIF(btrim(v_content->>'date'), '') IS NULL
     OR NULLIF(btrim(v_content->>'reference'), '') IS NULL
     OR NULLIF(btrim(v_content->>'title'), '') IS NULL
     OR NULLIF(btrim(v_content->>'summary'), '') IS NULL
     OR NULLIF(btrim(v_content->>'reflection'), '') IS NULL
     OR NULLIF(btrim(v_content->>'prayer'), '') IS NULL
     OR NULLIF(btrim(v_content->>'source_url'), '') IS NULL
     OR NULLIF(btrim(p_payload->>'canonical_url'), '') IS NULL
     OR p_payload->'ranges' IS NULL
     OR jsonb_typeof(p_payload->'ranges') <> 'array'
     OR jsonb_array_length(p_payload->'ranges') = 0 THEN
    RAISE EXCEPTION 'INVALID_PAYLOAD' USING ERRCODE = '22023';
  END IF;

  v_date := (v_content->>'date')::date;

  IF lower(COALESCE(p_payload->>'canonical_url', '')) LIKE '%example.com%'
     OR lower(COALESCE(p_payload->>'canonical_url', '')) LIKE '%example.org%'
     OR lower(COALESCE(p_payload->>'canonical_url', '')) LIKE '%localhost%'
     OR lower(COALESCE(p_payload->>'canonical_url', '')) LIKE '%127.0.0.1%'
     OR lower(COALESCE(v_content->>'source_url', '')) LIKE '%example.com%'
     OR lower(COALESCE(v_content->>'source_url', '')) LIKE '%example.org%'
     OR lower(COALESCE(v_content->>'source_url', '')) LIKE '%localhost%'
     OR lower(COALESCE(v_content->>'source_url', '')) LIKE '%127.0.0.1%' THEN
    RAISE EXCEPTION 'SAMPLE_SOURCE' USING ERRCODE = '22023';
  END IF;

  SELECT * INTO v_row FROM public.admin_devotional_drafts WHERE id = p_id FOR UPDATE;
  v_exists := FOUND;
  IF v_exists THEN
    IF v_row.status <> 'DRAFT' THEN
      RAISE EXCEPTION 'DRAFT_APPLIED' USING ERRCODE = 'P0001';
    END IF;
    IF v_row.version <> p_version THEN
      RAISE EXCEPTION 'VERSION_CONFLICT' USING ERRCODE = 'P0001';
    END IF;
    IF v_row.entry_id IS DISTINCT FROM p_entry_id THEN
      RAISE EXCEPTION 'ENTRY_CHANGE_CONFLICT' USING ERRCODE = 'P0001';
    END IF;
  ELSE
    IF p_version <> 0 THEN
      RAISE EXCEPTION 'VERSION_CONFLICT' USING ERRCODE = 'P0001';
    END IF;
  END IF;

  IF p_entry_id IS NOT NULL THEN
    SELECT * INTO v_target FROM public.entries WHERE id = p_entry_id FOR UPDATE;
    IF NOT FOUND THEN
      RAISE EXCEPTION 'ENTRY_NOT_FOUND' USING ERRCODE = 'P0002';
    END IF;
    IF v_target.scope <> 'IN_SCOPE' OR v_target.is_template
       OR lower(v_target.canonical_url) LIKE '%example.com%'
       OR lower(v_target.canonical_url) LIKE '%example.org%'
       OR lower(v_target.canonical_url) LIKE '%localhost%'
       OR lower(v_target.canonical_url) LIKE '%127.0.0.1%'
       OR lower(v_target.source_url) LIKE '%example.com%'
       OR lower(v_target.source_url) LIKE '%example.org%'
       OR lower(v_target.source_url) LIKE '%localhost%'
       OR lower(v_target.source_url) LIKE '%127.0.0.1%' THEN
      RAISE EXCEPTION 'ENTRY_NOT_EDITABLE' USING ERRCODE = 'P0002';
    END IF;
  END IF;

  SELECT id INTO v_existing FROM public.entries
   WHERE devotional_date = v_date AND id <> COALESCE(p_entry_id, -1) LIMIT 1;
  IF v_existing IS NOT NULL THEN
    RAISE EXCEPTION 'DATE_CONFLICT' USING ERRCODE = 'P0001';
  END IF;

  IF EXISTS (
    SELECT 1 FROM public.admin_devotional_drafts
     WHERE id <> p_id AND status = 'DRAFT'
       AND payload->'content'->>'date' = v_date::text
  ) THEN
    RAISE EXCEPTION 'DATE_CONFLICT' USING ERRCODE = 'P0001';
  END IF;

  IF p_entry_id IS NOT NULL THEN
    SELECT * INTO v_target FROM public.entries WHERE id = p_entry_id;
    IF NOT FOUND THEN
      RAISE EXCEPTION 'ENTRY_NOT_FOUND' USING ERRCODE = 'P0002';
    END IF;
    v_current := public.admin_devotional_entry_version(p_entry_id);
    IF p_base_version IS NULL OR p_base_version = '' OR p_base_version <> v_current THEN
      RAISE EXCEPTION 'BASE_VERSION_CONFLICT' USING ERRCODE = 'P0001';
    END IF;
    IF v_target.scope <> 'IN_SCOPE' OR v_target.is_template
       OR lower(v_target.canonical_url) LIKE '%example.com%'
       OR lower(v_target.canonical_url) LIKE '%example.org%'
       OR lower(v_target.canonical_url) LIKE '%localhost%'
       OR lower(v_target.canonical_url) LIKE '%127.0.0.1%'
       OR lower(v_target.source_url) LIKE '%example.com%'
       OR lower(v_target.source_url) LIKE '%example.org%'
       OR lower(v_target.source_url) LIKE '%localhost%'
       OR lower(v_target.source_url) LIKE '%127.0.0.1%' THEN
      RAISE EXCEPTION 'ENTRY_NOT_EDITABLE' USING ERRCODE = 'P0002';
    END IF;
  ELSE
    IF p_base_version IS NOT NULL AND btrim(p_base_version) <> '' THEN
      RAISE EXCEPTION 'BASE_VERSION_CONFLICT' USING ERRCODE = 'P0001';
    END IF;
  END IF;

  IF v_exists THEN
    UPDATE public.admin_devotional_drafts
       SET version = v_row.version + 1, entry_id = p_entry_id, base_version = p_base_version,
           payload = p_payload, status = 'DRAFT', updated_at = now(), reviewer = NULL, applied_at = NULL
     WHERE id = p_id
     RETURNING * INTO v_row;
  ELSE
    INSERT INTO public.admin_devotional_drafts(id, version, entry_id, base_version, payload, status)
    VALUES (p_id, 1, p_entry_id, p_base_version, p_payload, 'DRAFT')
    RETURNING * INTO v_row;
  END IF;

  RETURN jsonb_build_object(
    'id', v_row.id, 'version', v_row.version, 'entry_id', v_row.entry_id,
    'base_version', v_row.base_version, 'payload', v_row.payload,
    'status', v_row.status, 'updated_at', v_row.updated_at
  );
END $$;

REVOKE ALL ON FUNCTION admin_devotional_draft_save(uuid, integer, bigint, text, jsonb) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION admin_devotional_draft_save(uuid, integer, bigint, text, jsonb) TO bible_devotional_operator;

-- 核准：單一 transaction 內鎖定 draft/entry、重核 base_version、更新內容與 ranges，
-- 再依序寫入來源與神學核准，最後把 draft 標 APPLIED。
CREATE FUNCTION admin_devotional_draft_approve(
  p_id uuid,
  p_version integer,
  p_reviewer text,
  p_source_confirmed boolean,
  p_theology_confirmed boolean
)
RETURNS jsonb
LANGUAGE plpgsql
SECURITY INVOKER
SET search_path = pg_catalog, public
AS $$
DECLARE
  v_draft public.admin_devotional_drafts%ROWTYPE;
  v_entry public.entries%ROWTYPE;
  v_content jsonb;
  v_ranges jsonb;
  v_new_ranges jsonb;
  v_old_ranges jsonb;
  v_canonical text;
  v_current text;
  v_version text;
  v_entry_id bigint;
  v_date date;
  v_existing bigint;
BEGIN
  IF p_id IS NULL THEN
    RAISE EXCEPTION 'DRAFT_NOT_FOUND' USING ERRCODE = 'P0002';
  END IF;
  IF p_version IS NULL OR p_version < 0 THEN
    RAISE EXCEPTION 'VERSION_CONFLICT' USING ERRCODE = 'P0001';
  END IF;
  IF p_reviewer IS NULL OR btrim(p_reviewer) = '' OR length(p_reviewer) > 120 THEN
    RAISE EXCEPTION 'APPROVAL_REQUIRED' USING ERRCODE = '22023';
  END IF;
  IF p_source_confirmed IS NOT TRUE OR p_theology_confirmed IS NOT TRUE THEN
    RAISE EXCEPTION 'APPROVAL_REQUIRED' USING ERRCODE = '22023';
  END IF;

  -- 短暫鎖定，避免同日競態；逾時就回衝突，不長時間持鎖。
  PERFORM set_config('lock_timeout', '2s', true);
  PERFORM set_config('statement_timeout', '8s', true);
  LOCK TABLE public.entries IN SHARE ROW EXCLUSIVE MODE;

  SELECT * INTO v_draft FROM public.admin_devotional_drafts WHERE id = p_id FOR UPDATE;
  IF NOT FOUND THEN
    RAISE EXCEPTION 'DRAFT_NOT_FOUND' USING ERRCODE = 'P0002';
  END IF;
  IF v_draft.status <> 'DRAFT' THEN
    RAISE EXCEPTION 'DRAFT_APPLIED' USING ERRCODE = 'P0001';
  END IF;
  IF v_draft.version <> p_version THEN
    RAISE EXCEPTION 'VERSION_CONFLICT' USING ERRCODE = 'P0001';
  END IF;

  v_content := v_draft.payload->'content';
  v_ranges := v_draft.payload->'ranges';
  v_canonical := v_draft.payload->>'canonical_url';
  IF v_content IS NULL OR jsonb_typeof(v_content) <> 'object'
     OR NULLIF(btrim(v_content->>'date'), '') IS NULL
     OR NULLIF(btrim(v_content->>'reference'), '') IS NULL
     OR NULLIF(btrim(v_content->>'title'), '') IS NULL
     OR NULLIF(btrim(v_content->>'summary'), '') IS NULL
     OR NULLIF(btrim(v_content->>'reflection'), '') IS NULL
     OR NULLIF(btrim(v_content->>'prayer'), '') IS NULL
     OR NULLIF(btrim(v_content->>'source_url'), '') IS NULL
     OR NULLIF(btrim(v_canonical), '') IS NULL
     OR v_ranges IS NULL OR jsonb_typeof(v_ranges) <> 'array'
     OR jsonb_array_length(v_ranges) = 0 THEN
    RAISE EXCEPTION 'INVALID_PAYLOAD' USING ERRCODE = '22023';
  END IF;
  IF EXISTS (
    SELECT 1 FROM jsonb_to_recordset(v_ranges)
      AS x(sequence_no int, book_code text, start_chapter int, start_verse int, end_chapter int, end_verse int)
    WHERE x.book_code NOT IN ('MAT', 'MRK', 'LUK', 'JHN')
  ) THEN
    RAISE EXCEPTION 'INVALID_PAYLOAD' USING ERRCODE = '22023';
  END IF;

  v_date := (v_content->>'date')::date;

  IF lower(COALESCE(v_canonical, '')) LIKE '%example.com%'
     OR lower(COALESCE(v_canonical, '')) LIKE '%example.org%'
     OR lower(COALESCE(v_canonical, '')) LIKE '%localhost%'
     OR lower(COALESCE(v_canonical, '')) LIKE '%127.0.0.1%'
     OR lower(COALESCE(v_content->>'source_url', '')) LIKE '%example.com%'
     OR lower(COALESCE(v_content->>'source_url', '')) LIKE '%example.org%'
     OR lower(COALESCE(v_content->>'source_url', '')) LIKE '%localhost%'
     OR lower(COALESCE(v_content->>'source_url', '')) LIKE '%127.0.0.1%' THEN
    RAISE EXCEPTION 'SAMPLE_SOURCE' USING ERRCODE = '22023';
  END IF;

  SELECT id INTO v_existing FROM public.entries
   WHERE devotional_date = v_date AND id <> COALESCE(v_draft.entry_id, -1) LIMIT 1;
  IF v_existing IS NOT NULL THEN
    RAISE EXCEPTION 'DATE_CONFLICT' USING ERRCODE = 'P0001';
  END IF;

  IF v_draft.entry_id IS NULL THEN
    INSERT INTO public.entries(
      source_url, canonical_url, devotional_date, raw_reference, scope, is_template,
      source_status, title, summary, reflection, prayer
    ) VALUES (
      v_content->>'source_url', v_canonical, v_date, v_content->>'reference', 'IN_SCOPE', false,
      'PENDING', v_content->>'title', v_content->>'summary', v_content->>'reflection', v_content->>'prayer'
    )
    RETURNING * INTO v_entry;
    v_entry_id := v_entry.id;
    v_old_ranges := '[]'::jsonb;
  ELSE
    SELECT * INTO v_entry FROM public.entries WHERE id = v_draft.entry_id FOR UPDATE;
    IF NOT FOUND THEN
      RAISE EXCEPTION 'ENTRY_NOT_FOUND' USING ERRCODE = 'P0002';
    END IF;
    v_current := public.admin_devotional_entry_version(v_draft.entry_id);
    IF v_draft.base_version IS NULL OR v_draft.base_version = '' OR v_draft.base_version <> v_current THEN
      RAISE EXCEPTION 'BASE_VERSION_CONFLICT' USING ERRCODE = 'P0001';
    END IF;
    IF v_entry.scope <> 'IN_SCOPE' OR v_entry.is_template
       OR lower(v_entry.canonical_url) LIKE '%example.com%'
       OR lower(v_entry.canonical_url) LIKE '%example.org%'
       OR lower(v_entry.canonical_url) LIKE '%localhost%'
       OR lower(v_entry.canonical_url) LIKE '%127.0.0.1%'
       OR lower(v_entry.source_url) LIKE '%example.com%'
       OR lower(v_entry.source_url) LIKE '%example.org%'
       OR lower(v_entry.source_url) LIKE '%localhost%'
       OR lower(v_entry.source_url) LIKE '%127.0.0.1%' THEN
      RAISE EXCEPTION 'ENTRY_NOT_EDITABLE' USING ERRCODE = 'P0002';
    END IF;
    v_entry_id := v_entry.id;

    SELECT COALESCE(jsonb_agg(jsonb_build_array(r.book_code, r.start_chapter, r.start_verse, r.end_chapter, r.end_verse)
                              ORDER BY r.sequence_no), '[]'::jsonb)
      INTO v_old_ranges
      FROM public.scripture_ranges r WHERE r.entry_id = v_entry_id;

    UPDATE public.entries
       SET source_url = v_content->>'source_url', canonical_url = v_canonical,
           devotional_date = v_date, raw_reference = v_content->>'reference',
           scope = 'IN_SCOPE', is_template = false,
           title = v_content->>'title', summary = v_content->>'summary',
           reflection = v_content->>'reflection', prayer = v_content->>'prayer'
     WHERE id = v_entry_id
     RETURNING * INTO v_entry;
  END IF;

  SELECT COALESCE(jsonb_agg(jsonb_build_array(x.book_code, x.start_chapter, x.start_verse, x.end_chapter, x.end_verse)
                            ORDER BY x.sequence_no), '[]'::jsonb)
    INTO v_new_ranges
    FROM jsonb_to_recordset(v_ranges)
      AS x(sequence_no int, book_code text, start_chapter int, start_verse int, end_chapter int, end_verse int);
  IF jsonb_array_length(v_new_ranges) = 0 THEN
    RAISE EXCEPTION 'INVALID_PAYLOAD' USING ERRCODE = '22023';
  END IF;

  IF v_old_ranges IS DISTINCT FROM v_new_ranges THEN
    UPDATE public.media_links
       SET status = 'UNVERIFIED', reviewer = NULL, reviewed_at = NULL
     WHERE entry_id = v_entry_id;
  END IF;

  DELETE FROM public.scripture_ranges WHERE entry_id = v_entry_id;
  INSERT INTO public.scripture_ranges(
    entry_id, sequence_no, book_code, start_chapter, start_verse, end_chapter, end_verse
  )
  SELECT v_entry_id, x.sequence_no, x.book_code, x.start_chapter, x.start_verse, x.end_chapter, x.end_verse
    FROM jsonb_to_recordset(v_ranges)
      AS x(sequence_no int, book_code text, start_chapter int, start_verse int, end_chapter int, end_verse int);

  -- 觸發器會先重設審核狀態；再依序寫入來源與神學核准。
  UPDATE public.entries
     SET source_status = 'APPROVED', source_reviewer = p_reviewer, source_reviewed_at = now()
   WHERE id = v_entry_id;
  UPDATE public.entries
     SET theology_status = 'APPROVED', theology_reviewer = p_reviewer, theology_reviewed_at = now()
   WHERE id = v_entry_id;

  v_version := public.admin_devotional_entry_version(v_entry_id);
  UPDATE public.admin_devotional_drafts
     SET version = version + 1, status = 'APPLIED', reviewer = p_reviewer,
         applied_at = now(), updated_at = now()
   WHERE id = p_id
   RETURNING * INTO v_draft;
  SELECT * INTO v_entry FROM public.entries WHERE id = v_entry_id;

  RETURN jsonb_build_object(
    'entry', jsonb_build_object(
      'id', v_entry.id, 'version', v_version,
      'content', jsonb_build_object(
        'date', v_entry.devotional_date, 'reference', v_entry.raw_reference,
        'title', COALESCE(v_entry.title, ''), 'source_url', COALESCE(v_entry.source_url, ''),
        'summary', COALESCE(v_entry.summary, ''), 'reflection', COALESCE(v_entry.reflection, ''),
        'prayer', COALESCE(v_entry.prayer, '')
      ),
      'source_status', v_entry.source_status, 'theology_status', v_entry.theology_status
    ),
    'draft', jsonb_build_object('id', v_draft.id, 'version', v_draft.version, 'status', v_draft.status)
  );
END $$;

REVOKE ALL ON FUNCTION admin_devotional_draft_approve(uuid, integer, text, boolean, boolean) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION admin_devotional_draft_approve(uuid, integer, text, boolean, boolean) TO bible_devotional_operator;

COMMIT;
