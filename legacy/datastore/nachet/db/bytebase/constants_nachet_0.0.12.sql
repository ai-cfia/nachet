--
-- Data for Name: seed; Type: TABLE DATA; Schema: nachet_0.0.12; Owner: nachet
--

INSERT INTO "nachet_0.0.12".seed (id, name) VALUES ('5883dd16-3a7c-4d20-81dc-37cbda2d3de4', 'Brassica napus');
INSERT INTO "nachet_0.0.12".seed (id, name) VALUES ('d8e0adb6-91c5-4fec-8c3c-6b49fe9a50ab', 'Brassica juncea');
INSERT INTO "nachet_0.0.12".seed (id, name) VALUES ('a446848b-397f-44a4-8dfe-7b1ce0e15f54', 'Cirsium arvense');
INSERT INTO "nachet_0.0.12".seed (id, name) VALUES ('7ceff9a5-b85e-47d7-9b76-3ad6849906fb', 'Cirsium vulgare');
INSERT INTO "nachet_0.0.12".seed (id, name) VALUES ('8307af51-2d4b-4f4b-8717-fb96ec3f77da', 'Carduus nutans');
INSERT INTO "nachet_0.0.12".seed (id, name) VALUES ('2fb4d847-b87a-4da9-939c-1d5b64b42d68', 'Bromus secalinus');
INSERT INTO "nachet_0.0.12".seed (id, name) VALUES ('411a74ba-fbac-4601-88bf-3b205b96e446', 'Bromus hordeaceus');
INSERT INTO "nachet_0.0.12".seed (id, name) VALUES ('aacf6f61-4c88-457e-aef3-78db94f4e4c9', 'Bromus japonicus');
INSERT INTO "nachet_0.0.12".seed (id, name) VALUES ('bee7c653-b61e-4f3c-928c-8d944cb266fa', 'Lolium temulentum');
INSERT INTO "nachet_0.0.12".seed (id, name) VALUES ('05d77efa-1e48-4b71-a101-9b59d28318b5', 'Solanum carolinense');
INSERT INTO "nachet_0.0.12".seed (id, name) VALUES ('08a68083-6177-4fa4-be87-6ed0511d505f', 'Solanum nigrum');
INSERT INTO "nachet_0.0.12".seed (id, name) VALUES ('b9130135-4610-467b-87e1-9e8adc9b715c', 'Solanum rostratum');
INSERT INTO "nachet_0.0.12".seed (id, name) VALUES ('14e96554-aadf-42e4-8665-d141354800d1', 'Ambrosia artemisiifolia');
INSERT INTO "nachet_0.0.12".seed (id, name) VALUES ('1b1884a2-311e-4413-8efb-5d3b7aebc78f', 'Ambrosia trifida');
INSERT INTO "nachet_0.0.12".seed (id, name) VALUES ('bfa5b85d-8ed4-44ca-8e8e-59d80812877e', 'Ambrosia psilostachya');
INSERT INTO "nachet_0.0.12".seed (id, name) VALUES ('951832c7-29a7-4cb5-8dc9-6fe37539f0a7', 'Tripleurospermum inodorum');
INSERT INTO "nachet_0.0.12".seed (id, name) VALUES ('e8ada4e4-badc-469d-9ae4-7c16930a83f9', 'Cyclachaena Xanthiifolia');
INSERT INTO "nachet_0.0.12".seed (id, name) VALUES ('0f49b332-5143-4217-af55-dc2309e2653d', 'Cuscuta gronovii');
INSERT INTO "nachet_0.0.12".seed (id, name) VALUES ('5fb93b08-95af-4604-a005-f0ffc8eed459', 'Cuscuta spp');
INSERT INTO "nachet_0.0.12".seed (id, name) VALUES ('3dffe793-f08b-41bf-83cd-a894f48e881f', 'Tripleurospermum maritimum');
INSERT INTO "nachet_0.0.12".seed (id, name) VALUES ('41bb67a0-7588-436e-97db-d780f7fe6325', 'Solanum elaeagnifolium');
INSERT INTO "nachet_0.0.12".seed (id, name) VALUES ('a612a387-fa22-435b-89c1-2065a498498b', 'Iva axillaris');
INSERT INTO "nachet_0.0.12".seed (id, name) VALUES ('e8be332f-cb67-4a35-bad3-a08ad2a172ab', 'Centaurea calcitrapa');
INSERT INTO "nachet_0.0.12".seed (id, name) VALUES ('72895766-296d-4045-a48a-2c9f694d655a', 'Centaurea diffusa');
INSERT INTO "nachet_0.0.12".seed (id, name) VALUES ('c07c46d4-a797-4f4d-b638-7d26c7ab6a6e', 'Centaurea melitensis');
INSERT INTO "nachet_0.0.12".seed (id, name) VALUES ('366fda7c-6440-4cd7-b3f6-919a8a4d8155', 'Centaurea solstitialis');
INSERT INTO "nachet_0.0.12".seed (id, name) VALUES ('f4a61d0e-03ba-49e1-9557-66f72e36456f', 'Centaurea solstitialis D');
INSERT INTO "nachet_0.0.12".seed (id, name) VALUES ('d539f2d4-3ddd-41b8-8f0d-dcfddfc4c243', 'Centaurea stoebe');


--
-- Data for Name: task; Type: TABLE DATA; Schema: nachet_0.0.12; Owner: nachet
--

INSERT INTO "nachet_0.0.12".task (id, name) VALUES (1, 'Object Detection');
INSERT INTO "nachet_0.0.12".task (id, name) VALUES (2, 'Classification');
INSERT INTO "nachet_0.0.12".task (id, name) VALUES (3, 'Segmentation');


--
-- Data for Name: object_type; Type: TABLE DATA; Schema: nachet_0.0.12; Owner: nachet
--

INSERT INTO "nachet_0.0.12".object_type (id, name) VALUES (1, 'seed');
