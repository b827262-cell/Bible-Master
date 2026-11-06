REVOKE ALL ON ALL TABLES IN SCHEMA public FROM PUBLIC;
GRANT USAGE ON SCHEMA public TO bible_devotional_export_reader, bible_devotional_operator;
GRANT SELECT ON v_approved_export TO bible_devotional_export_reader;
GRANT SELECT, INSERT, UPDATE ON entries, scripture_ranges, media_links TO bible_devotional_operator;
GRANT DELETE ON scripture_ranges TO bible_devotional_operator;
GRANT SELECT, INSERT ON review_audit_logs TO bible_devotional_operator;
GRANT SELECT ON source_policy TO bible_devotional_operator;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO bible_devotional_operator;
