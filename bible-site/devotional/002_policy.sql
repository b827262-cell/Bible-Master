BEGIN;
ALTER TABLE source_policy ADD COLUMN last_fetch_at timestamptz;
CREATE FUNCTION claim_source_fetch() RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path=pg_catalog,public AS $$
DECLARE s public.source_policy%ROWTYPE;
BEGIN
 SELECT * INTO s FROM public.source_policy WHERE id=1 FOR UPDATE;
 IF s.mode <> 'APPROVED' THEN RAISE EXCEPTION 'source policy not approved'; END IF;
 IF s.last_fetch_at IS NOT NULL AND s.last_fetch_at > clock_timestamp()-interval '15 seconds' THEN RAISE EXCEPTION 'minimum interval is 15 seconds'; END IF;
 UPDATE public.source_policy SET last_fetch_at=clock_timestamp() WHERE id=1;
END $$;
REVOKE ALL ON FUNCTION claim_source_fetch() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION claim_source_fetch() TO bible_devotional_operator;
CREATE FUNCTION audit_policy() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 IF ROW(OLD.mode,OLD.robots_allowed,OLD.robots_checked_at,OLD.authorization_basis,OLD.approved_by,OLD.approved_at) IS DISTINCT FROM ROW(NEW.mode,NEW.robots_allowed,NEW.robots_checked_at,NEW.authorization_basis,NEW.approved_by,NEW.approved_at) THEN
 INSERT INTO review_audit_logs(target,target_id,review_type,previous_status,new_status,reviewer,notes) VALUES('source_policy',1,'POLICY',OLD.mode,NEW.mode,COALESCE(NULLIF(NEW.approved_by,''),current_user),NEW.authorization_basis);
 END IF;
 RETURN NULL;
END $$;
CREATE TRIGGER policy_audit AFTER UPDATE ON source_policy FOR EACH ROW EXECUTE FUNCTION audit_policy();
COMMIT;
