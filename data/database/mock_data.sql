INSERT INTO roles (role_id, role_name, description, permisions) VALUES 
(1, 'System Admin', 'IT Administrator with full system access', '["manage_users", "manage_system", "read_all"]'),
(2, 'Quality Manager', 'Responsible for QMS approval and release', '["approve_doc", "release_doc", "review_doc", "obsolete_doc", "manage_capa"]'),
(3, 'Regulatory Affairs', 'Ensures regulatory compliance (MDR/FDA)', '["approve_doc", "review_doc", "manage_external_standards"]'),
(4, 'Document Owner / Engineer', 'Technical author for SOPs and WIs', '["create_doc", "edit_draft", "submit_for_review"]'),
(5, 'General Employee', 'End user, read-only access to released docs', '["read_released", "sign_training"]');

INSERT INTO users (user_id, user_name, full_name, email, active_flag, password_hash) VALUES 
(2, 'albert.sevilleja', 'Albert Sevilleja', 'albert.sevilleja@meddevice.com', 1, 'hash_secret_albert_abc'),
(3, 'walter.white', 'Walter White', 'walter.white@meddevice.com', 1, 'hash_secret_heisenberg_blue'),
(4, 'jesse.pinkman', 'Jesse Pinkman', 'jesse.pinkman@meddevice.com', 1, 'hash_secret_jesse_science'),
(5, 'skyler.white', 'Skyler White', 'skyler.white@meddevice.com', 1, 'hash_secret_skyler_carwash'),
(6, 'hank.schrader', 'Hank Schrader', 'hank.schrader@meddevice.com', 1, 'hash_secret_hank_minerals'),
(7, 'gus.fring', 'Gustavo Fring', 'gus.fring@meddevice.com', 1, 'hash_secret_gus_pollos'),
(8, 'saul.goodman', 'Saul Goodman', 'saul.goodman@meddevice.com', 1, 'hash_secret_saul_lawyer'),
(9, 'mike.ehrmantraut', 'Mike Ehrmantraut', 'mike.ehrmantraut@meddevice.com', 1, 'hash_secret_mike_security'),
(10, 'tuco.salamanca', 'Tuco Salamanca', 'tuco.salamanca@meddevice.com', 0, 'hash_secret_tuco_tight');

INSERT INTO users_roles (user, role) VALUES 
(1, 5),
(2, 7),
(3, 8),
(4, 2),
(5, 3),
(5, 4),
(5, 6),
(5, 9),
(5, 10);