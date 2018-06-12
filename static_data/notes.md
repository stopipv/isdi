# The Spyware Used in Intimate Partner Violence
If you want to get the list of apps we found that can be used for intimate
partner surveillance (IPS), please contact at (rahul@cs.cornell.edu) with your
affiliation and a brief description of your purpose for obtaining the data.


## `app-info.db`
The app-info db contains all the app information we have crawled from Play Store
and App Store, and output of our ML and manual classification. 

The list of apps relevant for IPS is listed in
`appflags`.  The column `store` are {`playstore`, `appstore`, `offstore`}. AppId
column (`appId`) is an unique id assigned by the application stores. The flag
denotes whether or not the app is a overt spyware (that is they advertise for
spying on someone), or dual-use (apps that are not built for spying, but can be
very easily repurposed for spying on someone, especially an intimate partner).


More information about apps are provided in `apps` table, where  
most interesting collumns are `appId`, `summary`, `title`, `description`,
`relevant`, `ml_score`, and `class`.
* `ml_score` is the score assigned by our [ML
  classifier](https://github.com/rchatterjee/appscraper/tree/master/ml) for
  flagging apps as relevant for IPS. `relevant` column is post processing of ML
  data by human analysts.  The final list of flagged apps are in `appflags`, and
  I would recommend using that table to determine whether or not an app is
  relevant.
* `class` column sometimes contain a manually given class of the app based on
  their description, for example, parental control, child tracking, ff tracker
  (friends and family tracker), etc. The flags given in this column is not
  through a very thorough methodology. It's an intial attempt to classify all
  the apps we have seen. However, I am all ears for suggestion to improve it.
  will be happy to answer question if you have about this column. The column

```sqlite
sqlite> .schema apps
CREATE TABLE apps (
	"appId" TEXT, 
	application_icon TEXT, 
	appwebsite TEXT, 
	class TEXT, 
	comment TEXT, 
	contentrating TEXT, 
	description TEXT, 
	developerwebsite TEXT, 
	filename TEXT, 
	genreid TEXT, 
	genres TEXT, 
	id FLOAT, 
	launchable_activity_icon TEXT, 
	launchable_activity_label TEXT, 
	launchable_activity_name TEXT, 
	ml_score FLOAT, 
	package_platformbuildversionname TEXT, 
	package_versioncode FLOAT, 
	package_versionname TEXT, 
	permissions TEXT, 
	price FLOAT, 
	relevant TEXT, 
	relevant_old TEXT, 
	reviewer1_comment TEXT, 
	sha256sum TEXT, 
	store TEXT, 
	subclass TEXT, 
	summary TEXT, 
	title TEXT, 
	y FLOAT
);

sqlite> .schema appflags
CREATE TABLE appflags(
  "appId" TEXT,
  "store" TEXT,
  "flag" TEXT,
  "title" TEXT
);
```

We have built a basic [scaning
tool](https://github.com/rchatterjee/phone_scanner) to scan phones with these
list of flagged apps. 


You can get more informaiton about our research group https://www.ipvtechresearch.org/. 
