CREATE TABLE IF NOT EXISTS scan_res (
       	id INTEGER PRIMARY KEY AUTOINCREMENT,
	clientid TEXT,
	serial TEXT,
	note TEXT,
	device TEXT,
        location TEXT, -- currently empty
	time DATETIME DEFAULT (datetime('now', 'localtime'))
);


-- This is a backup table to keep logs of everything. 
CREATE TABLE IF NOT EXISTS all_logs (
       id INTEGER PRIMARY KEY AUTOINCREMENT,
       args TEXT,
       formargs TEXT,
       httpmethod TEXT,
       res TEXT,
       time DATETIME DEFAULT (datetime('now', 'localtime'))
);

CREATE TABLE IF NOT EXISTS  app_info (
	id INTEGER PRIMARY KEY AUTOINCREMENT,
	scanid INTEGER,
	appid TEXT,
        flags TEXT,
	remark TEXT,
        action_taken TEXT,
	time DATETIME DEFAULT (datetime('now', 'localtime')),
	FOREIGN KEY(scanid) REFERENCES scan_res(id)
);

CREATE INDEX IF NOT EXISTS idx_scan_res_clientid on scan_res  (clientid);
CREATE INDEX IF NOT EXISTS idx_app_info_scanid on app_info  (scanid);




--
-- CREATE TABLE IF NOT EXISTS notes (
-- 	id INTEGER PRIMARY KEY AUTOINCREMENT,
-- 	serial TEXT,
-- 	appid TEXT,
-- 	note TEXT,
-- 	time DATETIME DEFAULT (datetime('now', 'localtime')),
-- 	device TEXT,
-- 	PRIMARY KEY (id)
-- );
--
