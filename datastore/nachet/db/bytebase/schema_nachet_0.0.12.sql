create table if not exists "nachet_0.0.12".object_type
(
    id   serial
        primary key,
    name text not null
);

create table if not exists "nachet_0.0.12".picture_set
(
    id          uuid default gen_random_uuid() not null
        primary key,
    picture_set json                           not null,
    owner_id    uuid                           not null,
    upload_date date default CURRENT_TIMESTAMP not null,
    name        text
);

create table if not exists "nachet_0.0.12".picture
(
    id             uuid      default gen_random_uuid() not null
        primary key,
    picture        json                                not null,
    picture_set_id uuid                                not null
        references "nachet_0.0.12".picture_set
            on delete cascade,
    nb_obj         integer                             not null,
    verified       boolean   default false             not null,
    upload_date    timestamp default CURRENT_TIMESTAMP not null
);

create table if not exists "nachet_0.0.12".pipeline
(
    id         uuid    default gen_random_uuid() not null
        primary key,
    name       text                              not null,
    active     boolean default false             not null,
    is_default boolean default false             not null,
    data       json                              not null
);

create unique index if not exists "nachet_0.0.12_pipeline_default"
    on "nachet_0.0.12".pipeline (is_default)
    where (is_default = true);

create table if not exists "nachet_0.0.12".seed
(
    id             uuid default gen_random_uuid() not null
        primary key,
    name           text                           not null,
    object_type_id integer generated always as (1) stored
);

create table if not exists "nachet_0.0.12".picture_seed
(
    id          uuid      default gen_random_uuid() not null
        primary key,
    picture_id  uuid                                not null
        references "nachet_0.0.12".picture
            on delete cascade,
    seed_id     uuid                                not null
        references "nachet_0.0.12".seed,
    upload_date timestamp default CURRENT_TIMESTAMP not null
);

create table if not exists "nachet_0.0.12".task
(
    id   serial
        primary key,
    name text not null
);

create table if not exists "nachet_0.0.12".model
(
    id             uuid      default gen_random_uuid() not null
        primary key,
    name           text                                not null,
    endpoint_name  text                                not null,
    task_id        integer                             not null
        references "nachet_0.0.12".task,
    upload_date    timestamp default CURRENT_TIMESTAMP not null,
    active_version uuid
);

create table if not exists "nachet_0.0.12".model_version
(
    id          uuid      default gen_random_uuid() not null
        primary key,
    model_id    uuid                                not null
        references "nachet_0.0.12".model
            on delete cascade,
    data        json                                not null,
    version     text                                not null,
    upload_date timestamp default CURRENT_TIMESTAMP not null
);

alter table "nachet_0.0.12".model
    add foreign key (active_version) references "nachet_0.0.12".model_version
        on delete set null;

create table if not exists "nachet_0.0.12".pipeline_model
(
    id          uuid default gen_random_uuid() not null
        primary key,
    pipeline_id uuid                           not null
        references "nachet_0.0.12".pipeline,
    model_id    uuid                           not null
        references "nachet_0.0.12".model
);

create table if not exists "nachet_0.0.12".users
(
    id                uuid      default gen_random_uuid() not null
        primary key,
    email             varchar(255)                        not null,
    registration_date timestamp default CURRENT_TIMESTAMP not null,
    updated_at        timestamp default CURRENT_TIMESTAMP not null,
    default_set_id    uuid
        constraint "users-fk-yudjxqak"
            references "nachet_0.0.12".picture_set
);

create table if not exists "nachet_0.0.12".inference
(
    id               uuid      default gen_random_uuid() not null
        primary key,
    inference        json                                not null,
    picture_id       uuid                                not null
        references "nachet_0.0.12".picture
            on delete cascade,
    upload_date      timestamp default CURRENT_TIMESTAMP not null,
    user_id          uuid                                not null
        references "nachet_0.0.12".users,
    feedback_user_id uuid
        references "nachet_0.0.12".users,
    verified         boolean   default false             not null,
    pipeline_id      uuid
                                                         references "nachet_0.0.12".pipeline
                                                             on delete set null,
    update_at        timestamp default CURRENT_TIMESTAMP not null
);

create table if not exists "nachet_0.0.12".object
(
    id               uuid      default gen_random_uuid() not null
        primary key,
    box_metadata     json                                not null,
    inference_id     uuid                                not null
        references "nachet_0.0.12".inference
            on delete cascade,
    type_id          integer                             not null
        references "nachet_0.0.12".object_type,
    verified_id      uuid,
    valid            boolean,
    top_id           uuid,
    upload_date      timestamp default CURRENT_TIMESTAMP not null,
    manual_detection boolean   default false             not null,
    update_at        timestamp default CURRENT_TIMESTAMP not null,
    updated_at       timestamp default CURRENT_TIMESTAMP not null
);

alter table "nachet_0.0.12".picture_set
    add foreign key (owner_id) references "nachet_0.0.12".users;

create table if not exists "nachet_0.0.12".pipeline_default
(
    id          uuid default gen_random_uuid() not null
        primary key,
    pipeline_id uuid                           not null
        references "nachet_0.0.12".pipeline,
    user_id     uuid                           not null
        references "nachet_0.0.12".users
);

create table if not exists "nachet_0.0.12".seed_obj
(
    id        uuid default gen_random_uuid() not null
        primary key,
    seed_id   uuid                           not null
        references "nachet_0.0.12".seed,
    object_id uuid                           not null
        references "nachet_0.0.12".object
            on delete cascade,
    score     double precision               not null
);

create function "nachet_0.0.12".picture_set_default_name() returns trigger
    language plpgsql
as
$$
    BEGIN
        IF NEW.name IS NULL THEN
            NEW.name := NEW.id::text;
        END IF;
        RETURN NEW;
    END;
    $$;

create trigger picture_set_default_name_trigger
    before insert
    on "nachet_0.0.12".picture_set
    for each row
    when (new.name IS NULL)
execute procedure "nachet_0.0.12".picture_set_default_name();

create function "nachet_0.0.12".pipeline_default_trigger() returns trigger
    language plpgsql
as
$$
    BEGIN
        IF NEW.is_default THEN
            UPDATE "nachet_0.0.12".pipeline SET is_default=false WHERE is_default=true;
        END IF;
        RETURN NEW;
    END;
   $$;

create trigger pipeline_default_trigger
    before insert or update
    on "nachet_0.0.12".pipeline
    for each row
execute procedure "nachet_0.0.12".pipeline_default_trigger();

create function "nachet_0.0.12".update_inference_timestamp() returns trigger
    language plpgsql
as
$$
    BEGIN
    NEW.update_at = CURRENT_TIMESTAMP;
    RETURN NEW;
    END;
    $$;

create trigger fertilizer_update_before
    before update
    on "nachet_0.0.12".inference
    for each row
execute procedure "nachet_0.0.12".update_inference_timestamp();

create function "nachet_0.0.12".update_object_timestamp() returns trigger
    language plpgsql
as
$$
    BEGIN
    NEW.update_at = CURRENT_TIMESTAMP;
    RETURN NEW;
    END;
    $$;

create trigger fertilizer_update_before
    before update
    on "nachet_0.0.12".object
    for each row
execute procedure "nachet_0.0.12".update_object_timestamp();

create trigger object_update_before
    after update
    on "nachet_0.0.12".object
    for each row
execute procedure "nachet_0.0.12".update_object_timestamp();

create function "nachet_0.0.12".verified_inference() returns trigger
    language plpgsql
as
$$
  BEGIN
    IF NEW.verified = true THEN
        INSERT INTO "nachet_0.0.12".picture_seed (picture_id, seed_id)
          SELECT 
            New.picture_id, 
            so.seed_id  
          FROM "nachet_0.0.12".object obj 
            LEFT JOIN "nachet_0.0.12".seed_obj so 
              ON so.id = obj.verified_id  
          WHERE obj.inference_id = NEW.id and obj.verified_id is not null;
    END IF;
    RETURN NEW;
  END;
$$;

create trigger verified_inference_trigger
    after update
    on "nachet_0.0.12".inference
    for each row
    when (new.verified = true)
execute procedure "nachet_0.0.12".verified_inference();


