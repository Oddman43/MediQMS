INSERT INTO roles (role_id, role_name, description, permisions) VALUES 
(1, 'System Admin', 'IT Administrator with full system access', '["manage_users", "manage_system", "read_all"]'),
(2, 'Quality Manager', 'Responsible for QMS approval and release', '["approve_doc", "release_doc", "review_doc", "obsolete_doc", "manage_capa"]'),
(3, 'Regulatory Affairs', 'Ensures regulatory compliance (MDR/FDA)', '["approve_doc", "review_doc", "manage_external_standards"]'),
(4, 'Document Owner / Engineer', 'Technical author for SOPs and WIs', '["create_doc", "edit_draft", "submit_for_review"]'),
(5, 'General Employee', 'End user, read-only access to released docs', '["read_released", "sign_training"]');

INSERT INTO users (user_id, user_name, full_name, email, active_flag, password_hash) VALUES 
(1, 'admin', 'System Administrator', 'admin@meddevice.com', 1, 'hash_secret_admin_123'),
(2, 'alice_qa', 'Alice Smith', 'alice.smith@meddevice.com', 1, 'hash_secret_alice_456'),
(3, 'bob_ra', 'Bob Jones', 'bob.jones@meddevice.com', 1, 'hash_secret_bob_789'),
(4, 'charlie_eng', 'Charlie Davis', 'charlie.davis@meddevice.com', 1, 'hash_secret_charlie_abc'),
(5, 'david_ops', 'David White', 'david.white@meddevice.com', 1, 'hash_secret_david_def');

INSERT INTO users_roles (user, role) VALUES 
(1, 1),
(2, 2),
(3, 3),
(4, 4),
(5, 5);