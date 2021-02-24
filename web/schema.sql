CREATE TABLE IF NOT EXISTS clients_notes (
	id INTEGER NOT NULL,
	created_at DATETIME,
	clientid VARCHAR(100) DEFAULT '' NOT NULL,
	consultant_initials VARCHAR(100) DEFAULT '' NOT NULL,
	fjc VARCHAR(13) DEFAULT '' NOT NULL,
	preferred_language VARCHAR(100) DEFAULT 'English' NOT NULL,
	referring_professional VARCHAR(100) DEFAULT '' NOT NULL,
	referring_professional_email VARCHAR(255),
	referring_professional_phone VARCHAR(50),
	caseworker_present VARCHAR(23) DEFAULT '' NOT NULL,
	caseworker_present_safety_planning VARCHAR(3) DEFAULT '' NOT NULL,
	caseworker_recorded VARCHAR(3) DEFAULT '' NOT NULL,
	recorded VARCHAR(3) DEFAULT '' NOT NULL,
	chief_concerns VARCHAR(400) DEFAULT '' NOT NULL,
	chief_concerns_other TEXT DEFAULT '' NOT NULL,
	android_phones INTEGER DEFAULT '0' NOT NULL,
	android_tablets INTEGER DEFAULT '0' NOT NULL,
	iphone_devices INTEGER DEFAULT '0' NOT NULL,
	ipad_devices INTEGER DEFAULT '0' NOT NULL,
	macbook_devices INTEGER DEFAULT '0' NOT NULL,
	windows_devices INTEGER DEFAULT '0' NOT NULL,
	echo_devices INTEGER DEFAULT '0' NOT NULL,
	other_devices VARCHAR(400) DEFAULT '',
	checkups VARCHAR(400) DEFAULT '',
	checkups_other VARCHAR(400) DEFAULT '',
	vulnerabilities VARCHAR(600) DEFAULT '' NOT NULL,
	vulnerabilities_trusted_devices TEXT DEFAULT '',
	vulnerabilities_other TEXT DEFAULT '',
	safety_planning_onsite VARCHAR(14) DEFAULT '' NOT NULL,
	changes_made_onsite TEXT DEFAULT '',
	unresolved_issues TEXT DEFAULT '',
	follow_ups_todo TEXT DEFAULT '',
	general_notes TEXT DEFAULT '',
	case_summary TEXT DEFAULT '',
	PRIMARY KEY (id),
	CHECK (fjc IN ('', 'Brooklyn', 'Queens', 'The Bronx', 'Manhattan', 'Staten Island')),
	CHECK (caseworker_present IN ('', 'For entire consult', 'For part of the consult', 'No')),
	CHECK (caseworker_present_safety_planning IN ('', 'Yes', 'No')),
	CHECK (caseworker_recorded IN ('', 'Yes', 'No')),
	CHECK (recorded IN ('', 'Yes', 'No')),
	CHECK (safety_planning_onsite IN ('', 'Yes', 'No', 'Not applicable'))
);

CREATE TABLE IF NOT EXISTS clients (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  clientid TEXT,
  location TEXT,
  issues TEXT, -- JSON dump of checkboxed answers
  assessment TEXT,
  plan TEXT,
  the_rest TEXT, -- if structure changes, keep json dump in here
  time DATETIME DEFAULT (datetime('now', 'localtime'))
);

CREATE TABLE IF NOT EXISTS scan_res (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  clientid TEXT,
  serial TEXT,
  note TEXT,
  device TEXT,
  device_model TEXT,
  device_manufacturer TEXT,
  device_version TEXT,
  is_rooted INTEGER,
  rooted_reasons TEXT,
  last_full_charge DATETIME,
  device_primary_user TEXT,
  device_access TEXT, -- JSONdump of person, frequency of access / todo
  how_obtained TEXT, -- todo
  time DATETIME DEFAULT (datetime('now', 'localtime')),
  FOREIGN KEY(clientid) REFERENCES clients_notes(clientid)
  --FOREIGN KEY(clientid) REFERENCES clients(clientid)
  --battery_avg_last_charged INTEGER, -- take out maybe
);

CREATE TABLE IF NOT EXISTS app_info (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  scanid INTEGER,
  appid TEXT,
  flags TEXT,
  remark TEXT,
  action_taken TEXT,
  apk_path TEXT,
  install_date DATETIME,
  last_updated DATETIME,
  app_version TEXT,
  permissions TEXT,
  permissions_reason TEXT,
  permissions_used DATETIME,
  data_usage INTEGER, -- Mobile total received: Wifi-Total
  battery_usage INTEGER, -- in mAh. show "not more than average app on your device" rather than actual amount on front-end.
  time DATETIME DEFAULT (datetime('now', 'localtime')),
  FOREIGN KEY(scanid) REFERENCES scan_res(id)
);
-- see also, how battery usage is measured on phone app itself in settings. percent of battery used by app.E
-- https://stackoverflow.com/questions/45751387/how-do-i-calculate-the-battery-drain-for-a-particular-app-using-dumpsys-batterys
CREATE INDEX IF NOT EXISTS idx_clients_notes_clientid on clients_notes  (clientid);
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
-- This is a backup table to keep logs of everything. 
-- CREATE TABLE IF NOT EXISTS all_logs (
--        id INTEGER PRIMARY KEY AUTOINCREMENT,
--        args TEXT,
--        formargs TEXT,
--        httpmethod TEXT,
--        res TEXT,
--        time DATETIME DEFAULT (datetime('now', 'localtime'))
-- );

