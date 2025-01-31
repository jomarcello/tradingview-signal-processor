-- Create the villas table
CREATE TABLE villas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    location TEXT NOT NULL,
    email TEXT,
    instagram_handle TEXT,
    contact_status TEXT DEFAULT 'not_contacted'
);

-- Create the outreach table
CREATE TABLE outreach (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    villa_id INTEGER NOT NULL,
    contact_date DATE NOT NULL,
    response TEXT,
    FOREIGN KEY (villa_id) REFERENCES villas(id)
);

-- Create the visuals table
CREATE TABLE visuals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    villa_id INTEGER NOT NULL,
    type TEXT NOT NULL,
    date_created DATE NOT NULL,
    FOREIGN KEY (villa_id) REFERENCES villas(id)
);

-- Insert sample data into the villas table
INSERT INTO villas (name, location, email, instagram_handle)
VALUES ('Villa Serenity', 'Mykonos', 'info@villaserenity.com', '@villaserenity');

INSERT INTO villas (name, location, email, instagram_handle)
VALUES ('Villa Aether', 'Santorini', 'info@villaaether.com', '@villaaether');

-- Insert sample data into the outreach table
INSERT INTO outreach (villa_id, contact_date, response)
VALUES (1, '2024-11-28', 'positive');

INSERT INTO outreach (villa_id, contact_date, response)
VALUES (2, '2024-11-28', 'no_response');

-- Insert sample data into the visuals table
INSERT INTO visuals (villa_id, type, date_created)
VALUES (1, 'photo', '2024-11-28');

INSERT INTO visuals (villa_id, type, date_created)
VALUES (2, 'video', '2024-11-28');