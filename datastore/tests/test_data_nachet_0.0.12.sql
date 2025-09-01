--
-- Data for Name: model; Type: TABLE DATA; Schema: nachet_0.0.12; Owner: nachet
-- Insert models without active_version first to avoid circular dependency
--

INSERT INTO "nachet_0.0.12".model (id, name, endpoint_name, task_id, upload_date, active_version) VALUES ('ecef8395-e6d5-47a3-8f3d-8424b4dd3816', 'swin-15e-spp', 'swin-15-spp-endpoint-2025', 2, '2025-03-04 05:44:08.393911', NULL);
INSERT INTO "nachet_0.0.12".model (id, name, endpoint_name, task_id, upload_date, active_version) VALUES ('e83ee51e-830e-403a-a48f-d216ae91abb9', 'swin-27-spp', 'swin-27-spp-endpoint-2025', 2, '2025-03-04 05:44:08.393911', NULL);
INSERT INTO "nachet_0.0.12".model (id, name, endpoint_name, task_id, upload_date, active_version) VALUES ('52fd7ca2-8101-4541-ae49-d6d92ac69196', 'seed-detector-rcnn-1', 'seed-detector-2024', 1, '2024-11-13 07:40:25.867369', NULL);


--
-- Data for Name: model_version; Type: TABLE DATA; Schema: nachet_0.0.12; Owner: nachet
--

INSERT INTO "nachet_0.0.12".model_version (id, model_id, data, version, upload_date) VALUES ('6bb13a0a-d292-49f7-b2dd-358c307f00e3', '52fd7ca2-8101-4541-ae49-d6d92ac69196', '{"endpoint": "gAAAAABoirefr9zXJJ0BCtwM8Zl2KBH6KJ7SK87lvCjFe3BDbXWiGzUEgrBrUccsdTeUcDjO93pVs8q3OX9T0gfO74Pr_qIvQyySYLKpATSMzhkVjyl4euZbrOvVNMPLkpRQUr2vUG01E_WZc-MTavMI42_ONfnCtQ==", "api_key": "gAAAAABnURjjQOZBtbUwSzIEoSYXF5TBldPMeajnzg4asdseC2Nh6-cjT2uEucshibeq_rQOkmsCEmHCRNoyH1fzlo-Fe1IRpztStGaNKTP2mEpTEtIuu509VvpARj31wLxnEG5-q7a7", "content_type": "application/json", "deployment_platform": "local-deployment", "created_by": "Test User", "creation_date": "2023-12-21", "description": "", "version": "1", "job_name": "", "dataset": ""}', '0.0.1', '2024-11-13 07:46:54.147204');
INSERT INTO "nachet_0.0.12".model_version (id, model_id, data, version, upload_date) VALUES ('744b2f56-5fb3-406a-b04a-5e66074ed688', 'e83ee51e-830e-403a-a48f-d216ae91abb9', '{"endpoint": "gAAAAABoirefTns-D531AsxXJnDygK7jjJOBxEDMe_PF_iguAih8gkwe5RG7oUi4WyWBCzvdCLeRW3wqmm-rc2g9zu2QIRMBk__vMIpFXqvvNYBQnMVw8FugIpl6Kd-lwTmCUlGKONigR1gMDWwQwauJGQegCaCUqQ==", "api_key": "gAAAAABnURjjQOZBtbUwSzIEoSYXF5TBldPMeajnzg4asdseC2Nh6-cjT2uEucshibeq_rQOkmsCEmHCRNoyH1fzlo-Fe1IRpztStGaNKTP2mEpTEtIuu509VvpARj31wLxnEG5-q7a7", "content_type": "application/json", "deployment_platform": "local-deployment", "created_by": "Test User", "creation_date": "2025-01-30", "description": "27spp", "version": "1", "job_name": "", "dataset": ""}', '0.0.1', '2025-03-04 05:46:53.56912');
INSERT INTO "nachet_0.0.12".model_version (id, model_id, data, version, upload_date) VALUES ('56234613-2790-42ba-8f32-85cec3129bbf', 'ecef8395-e6d5-47a3-8f3d-8424b4dd3816', '{"endpoint": "gAAAAABoirefaqYOaxirtYU71lHtE2GnD9OPbUnb1yOHXV7ToYAMcTkiMQQVIX04WwQ8DvUJXfPhCBB88N4ptKeZ0khuUtMzL5bDS34iP755gGeo1FJt7OU1eX4i47qsZ6xq7K2v0fmV300YMNUVxPHAR69P4zpQbA==", "api_key": "gAAAAABnURjjQOZBtbUwSzIEoSYXF5TBldPMeajnzg4asdseC2Nh6-cjT2uEucshibeq_rQOkmsCEmHCRNoyH1fzlo-Fe1IRpztStGaNKTP2mEpTEtIuu509VvpARj31wLxnEG5-q7a7", "content_type": "application/json", "deployment_platform": "local-deployment", "created_by": "Test User", "creation_date": "2025-01-30", "description": "15spp-e", "version": "1", "job_name": "", "dataset": ""}', '0.0.1', '2025-03-04 05:46:53.56912');

--
-- Update model active_version after model_version data is inserted
--

UPDATE "nachet_0.0.12".model SET active_version = '56234613-2790-42ba-8f32-85cec3129bbf' WHERE id = 'ecef8395-e6d5-47a3-8f3d-8424b4dd3816';
UPDATE "nachet_0.0.12".model SET active_version = '744b2f56-5fb3-406a-b04a-5e66074ed688' WHERE id = 'e83ee51e-830e-403a-a48f-d216ae91abb9';
UPDATE "nachet_0.0.12".model SET active_version = '6bb13a0a-d292-49f7-b2dd-358c307f00e3' WHERE id = '52fd7ca2-8101-4541-ae49-d6d92ac69196';


--
-- Data for Name: pipeline; Type: TABLE DATA; Schema: nachet_0.0.12; Owner: nachet
--

INSERT INTO "nachet_0.0.12".pipeline (id, name, active, is_default, data) VALUES ('cc901051-34e0-4e21-803f-76e159848046', '27 spp RCNN SWIN', true, true, '{"models": ["seed-detector-rcnn-1", "swin-27-spp", "swin-15e-spp"], "created_by": "Test User", "creation_date": "2025-01-30", "description": "Use a Swin transformer to classify the seeds", "job_name": "", "version": "1", "dataset": ""}');


--
-- Data for Name: pipeline_default; Type: TABLE DATA; Schema: nachet_0.0.12; Owner: nachet
--


--
-- Data for Name: pipeline_model; Type: TABLE DATA; Schema: nachet_0.0.12; Owner: nachet
--

INSERT INTO "nachet_0.0.12".pipeline_model (id, pipeline_id, model_id) VALUES ('0704a8a6-7853-4530-a49a-d98a884a3f71', 'cc901051-34e0-4e21-803f-76e159848046', '52fd7ca2-8101-4541-ae49-d6d92ac69196');
INSERT INTO "nachet_0.0.12".pipeline_model (id, pipeline_id, model_id) VALUES ('3dad6eb9-56c6-4bc1-b8ab-c683f186b874', 'cc901051-34e0-4e21-803f-76e159848046', 'e83ee51e-830e-403a-a48f-d216ae91abb9');
INSERT INTO "nachet_0.0.12".pipeline_model (id, pipeline_id, model_id) VALUES ('b2d0f715-7d64-48ed-8f5f-b3ce338918c4', 'cc901051-34e0-4e21-803f-76e159848046', 'ecef8395-e6d5-47a3-8f3d-8424b4dd3816');


--
-- Data for Name: users; Type: TABLE DATA; Schema: nachet_0.0.12; Owner: nachet
--

INSERT INTO "nachet_0.0.12".users (id, email, registration_date, updated_at, default_set_id) VALUES ('8ea46a6b-7d37-4fbb-a66f-775112376e16', 'test.user@inspection.gc.ca', '2024-10-30 19:59:56.653932', '2024-10-30 19:59:56.653932', null);


--
-- Data for Name: picture_set; Type: TABLE DATA; Schema: nachet_0.0.12; Owner: nachet
--

INSERT INTO "nachet_0.0.12".picture_set (id, name, picture_set, owner_id, upload_date) VALUES ('f47ac10b-58cc-4372-a567-0e02b2c3d479', 'default', '{}', '8ea46a6b-7d37-4fbb-a66f-775112376e16', '2024-10-30');


--
-- Update user default_set_id after picture_set is inserted
--

UPDATE "nachet_0.0.12".users SET default_set_id = 'f47ac10b-58cc-4372-a567-0e02b2c3d479' WHERE id = '8ea46a6b-7d37-4fbb-a66f-775112376e16';
