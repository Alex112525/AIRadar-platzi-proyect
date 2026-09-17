-- Esquema relacional de AIRadar para Supabase (PostgreSQL).
-- Primera pasada: crea las dos tablas del modelo descrito en
-- docs/persistencia.md. Las columnas se llaman como los campos del contrato
-- de datos 2.0, salvo `evidence`, que se abre en dos columnas.
--
-- `lanzamientos.source` corresponde a `fuentes.source`, pero la clave foránea
-- no está declarada aquí todavía. El esquema no está aplicado sobre ningún
-- proyecto de Supabase.

create table fuentes (
    source      text        primary key,
    nombre      text        not null,
    source_type text        not null,
    url         text        not null,
    feed        text,
    revision    text        not null,
    activa      boolean     not null default true,
    created_at  timestamptz not null default now()
);

create table lanzamientos (
    id             text        primary key,
    title          text        not null,
    url            text        not null,
    source         text        not null,
    source_type    text        not null,
    category       text        not null,
    published_at   timestamptz not null,
    collected_at   timestamptz not null,
    evidence_url   text        not null,
    evidence_quote text        not null,
    dedup_key      text        not null unique,
    status         text        not null,
    status_note    text,
    summary        text,
    tags           text[]      not null default '{}',
    created_at     timestamptz not null default now()
);
