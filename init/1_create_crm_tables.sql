CREATE TABLE users (
                       id SERIAL PRIMARY KEY,
                       full_name VARCHAR(255) NOT NULL,
                       birth_date DATE NOT NULL,
                       city VARCHAR(100) NOT NULL,
                       created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                       email VARCHAR(200) not null
);

CREATE TABLE prosthesis_models (
                                   id SERIAL PRIMARY KEY,
                                   model_name VARCHAR(255) NOT NULL UNIQUE,
                                   release_date DATE NOT NULL,
                                   price DECIMAL(10, 2) NOT NULL CHECK (price > 0),
                                   description TEXT,
                                   created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE user_prostheses (
                                 id SERIAL PRIMARY KEY,
                                 user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                                 prosthesis_model_id INTEGER NOT NULL REFERENCES prosthesis_models(id) ON DELETE RESTRICT,
                                 order_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                                 status manufacturing_status NOT NULL DEFAULT 'ORDER_ACCEPTED',
                                 serial_number VARCHAR(100) NOT NULL UNIQUE,
                                 manufactured_at TIMESTAMP,
                                 delivered_at TIMESTAMP,
                                 created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_user_prostheses_user_id ON user_prostheses(user_id);
CREATE INDEX IF NOT EXISTS idx_user_prostheses_model_id ON user_prostheses(prosthesis_model_id);
CREATE INDEX IF NOT EXISTS idx_user_prostheses_status ON user_prostheses(status);
CREATE INDEX IF NOT EXISTS idx_user_prostheses_serial ON user_prostheses(serial_number);