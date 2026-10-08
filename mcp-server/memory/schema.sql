CREATE TABLE IF NOT EXISTS companies (
    id TEXT PRIMARY KEY
);

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    company_id TEXT NOT NULL REFERENCES companies(id),
    external_id TEXT NOT NULL,
    UNIQUE (company_id, external_id)
);

CREATE TABLE IF NOT EXISTS conversations (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    started_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS turns (
    id INTEGER PRIMARY KEY,
    conversation_id INTEGER NOT NULL REFERENCES conversations(id),
    seq INTEGER NOT NULL,
    heard TEXT NOT NULL,
    say TEXT NOT NULL,
    next_move TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE (conversation_id, seq)
);

CREATE TABLE IF NOT EXISTS requests (
    id TEXT PRIMARY KEY,
    conversation_id INTEGER NOT NULL REFERENCES conversations(id),
    intent TEXT,
    details TEXT NOT NULL,
    status TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS actions (
    id INTEGER PRIMARY KEY,
    request_id TEXT NOT NULL REFERENCES requests(id),
    result TEXT NOT NULL,
    created_at TEXT NOT NULL
);
