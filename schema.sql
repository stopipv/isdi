CREATE TABLE IF NOT EXISTS scan_res (
	id INTEGER PRIMARY KEY AUTOINCREMENT,
	clientid TEXT,
	device TEXT,
	notes TEXT,
	response TEXT,
  scanid INTEGER,
	serial TEXT,
	time DATETIME DEFAULT (datetime('now', 'localtime')),
	PRIMARY KEY (id)
);

CREATE TABLE IF NOT EXISTS  app_notes (
	id INTEGER PRIMARY KEY AUTOINCREMENT,
	serial TEXT,
	scanid INTEGER,
	appid TEXT,
	notes TEXT,
	time DATETIME DEFAULT (datetime('now', 'localtime')),
	device TEXT,
	FOREIGN KEY(scanid) REFERENCES scan_res(id)
);

-- CREATE TABLE IF NOT EXISTS notes (
-- 	id INTEGER PRIMARY KEY AUTOINCREMENT,
-- 	serial TEXT,
-- 	appid TEXT,
-- 	note TEXT,
-- 	time DATETIME DEFAULT (datetime('now', 'localtime')),
-- 	device TEXT,
-- 	PRIMARY KEY (id)
-- );

CREATE TABLE IF NOT EXISTS dblogs (
   id INTEGER PRIMARY KEY AUTOINCREMENT,
   res TEXT,
   time DATETIME DEFAULT (datetime('now', 'localtime')),
);