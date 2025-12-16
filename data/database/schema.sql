CREATE TABLE roles (
    "role_id" INTEGER PRIMARY KEY,
    "role_name" TEXT,
    "description" TEXT,
    "permisions" TEXT
);

CREATE TABLE users (
    "user_id" INTEGER PRIMARY KEY,
    "user_name" TEXT UNIQUE,
    "full_name" TEXT,
    "email" TEXT,
    "active_flag" INTEGER,
    "password_hash" TEXT
);

CREATE TABLE users_roles (
    "user" INTEGER,
    "role" INTEGER,
    PRIMARY KEY("user", "role")
    FOREIGN KEY("user") REFERENCES "users"("user_id"),
    FOREIGN KEY("role") REFERENCES "roles"("role_id")
);

CREATE TABLE documents (
    "doc_id" INTEGER,
    "doc_num" TEXT UNIQUE,
    "title" TEXT,
    "owner_id" INTEGER,
    "type" TEXT,
    PRIMARY KEY("doc_id"),
    FOREIGN KEY("owner_id") REFERENCES "users"("user_id")
);

CREATE TABLE versions (
    "version_id" INTEGER PRIMARY KEY,
    "doc" INTEGER,
    "version" TEXT,
    "status" TEXT,
    "file_path" TEXT,
    "effective_date" TEXT,
    FOREIGN KEY("doc") REFERENCES "documents"("doc_id"),
    UNIQUE("doc", "version")
);

CREATE TABLE audit_log (
    "log_id" INTEGER,
    "table_affected" TEXT,
    "record_id" INTEGER,
    "user" INTEGER,
    "action" TEXT,
    "old_val" TEXT,
    "new_val" TEXT,
    "timestamp" TEXT,
    "hash" TEXT,
    PRIMARY KEY("log_id"),
    FOREIGN KEY("user") REFERENCES "users"("user_id")
);

CREATE TABLE approvals (
    "approval_id" INTEGER,
    "version_id" INTEGER,
    "approver_id" INTEGER,
    "date_signature" TEXT,
    "status" TEXT,
    "signature_hash" TEXT,
    "role_signing" TEXT,
    PRIMARY KEY("approval_id"),
    FOREIGN KEY("version_id") REFERENCES "versions"("version_id"),
    FOREIGN KEY("approver_id") REFERENCES "users"("user_id")
);

CREATE INDEX idx_audit_lookup ON "audit_log"("table_affected", "record_id");
CREATE INDEX idx_doc_num ON "documents"("doc_num");
CREATE INDEX idx_versions_doc ON "versions"("doc");