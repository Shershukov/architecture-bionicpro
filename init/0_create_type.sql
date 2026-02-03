DO $$ BEGIN
CREATE TYPE manufacturing_status AS ENUM (
        'ORDER_ACCEPTED',
        'MANUFACTURING',
        'READY_FOR_TRYING_ON',
        'DONE'
    );
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;