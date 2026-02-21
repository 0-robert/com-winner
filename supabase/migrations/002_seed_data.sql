-- Seed data: sample B2B contacts for demo/testing
-- Replace with real import data before production

INSERT INTO contacts (name, email, title, organization, status, district_website, linkedin_url)
VALUES
    ('Jane Smith',      'jane.smith@acme.com',         'VP of Operations',   'Acme Corp',       'unknown', 'https://acme.com',       NULL),
    ('Bob Johnson',     'bob.johnson@techfirm.io',     'Head of Engineering', 'TechFirm Inc',   'unknown', 'https://techfirm.io',    NULL),
    ('Maria Garcia',    'maria.garcia@globalops.co',   'Director of Sales',  'GlobalOps',       'unknown', 'https://globalops.co',   NULL),
    ('Chen Wei',        'chen.wei@innovate.ai',        'Chief Product Officer', 'Innovate AI',  'unknown', 'https://innovate.ai',    NULL),
    ('Alice Brown',     'alice.brown@buildco.net',     'Operations Manager', 'BuildCo',         'unknown', 'https://buildco.net',    NULL)
ON CONFLICT DO NOTHING;
