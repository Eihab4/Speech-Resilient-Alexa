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

CREATE TABLE IF NOT EXISTS requests (
    id TEXT PRIMARY KEY,
    conversation_id INTEGER NOT NULL REFERENCES conversations(id),
    intent TEXT,
    details TEXT NOT NULL,
    status TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS turns (
    id INTEGER PRIMARY KEY,
    conversation_id INTEGER NOT NULL REFERENCES conversations(id),
    request_id TEXT REFERENCES requests(id),
    seq INTEGER NOT NULL,
    heard TEXT NOT NULL,
    say TEXT NOT NULL,
    next_move TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE (conversation_id, seq)
);

CREATE TABLE IF NOT EXISTS summaries (
    conversation_id INTEGER PRIMARY KEY REFERENCES conversations(id),
    text TEXT NOT NULL,
    covers_up_to_seq INTEGER NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS actions (
    id INTEGER PRIMARY KEY,
    request_id TEXT NOT NULL REFERENCES requests(id),
    result TEXT NOT NULL,
    created_at TEXT NOT NULL
);

-- Who the person is, for the emergency alert ("SOS from Ahmed").
CREATE TABLE IF NOT EXISTS profiles (
    user_id INTEGER PRIMARY KEY REFERENCES users(id),
    name TEXT NOT NULL,
    home_address TEXT,
    updated_at TEXT NOT NULL
);

-- People who get the person's emergency alerts. A helper is linked once their Telegram chat is known.
CREATE TABLE IF NOT EXISTS helpers (
    id TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    name TEXT NOT NULL,
    link_code TEXT NOT NULL UNIQUE,
    telegram_chat_id TEXT,
    linked_at TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS alerts (
    id TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    heard TEXT NOT NULL,
    latitude REAL,
    longitude REAL,
    address TEXT,
    text TEXT NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL
);
