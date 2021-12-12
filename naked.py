import logging
import logging.config
import requests
import json
import datetime
import time
import yaml

from datetime import datetime
from configparser import ConfigParser

# Loading logging configuration
with open('./log_worker.yaml', 'r') as stream:
	log_config = yaml.safe_load(stream)

logging.config.dictConfig(log_config)
# Creating logger
logger = logging.getLogger('root')

logger.info('Asteroid processing service')

# Initiating and reading config values
logger.info('Loading configuration from file')
try:
	config = ConfigParser()
	config.read('config.ini')

	nasa_api_key = config.get('nasa', 'api_key')
	nasa_api_url = config.get('nasa', 'api_url')
except:
	logger.error('')
logger.info('DONE loading configurations')

# Getting todays date
dt = datetime.now()
request_date = str(dt.year) + "-" + str(dt.month).zfill(2) + "-" + str(dt.day).zfill(2)  
logger.debug("Generated today's date: " + str(request_date))

# Build request url with todays date and api key parameters
logger.debug("Request url: " + str(nasa_api_url + "rest/v1/feed?start_date=" + request_date + "&end_date=" + request_date + "&api_key=" + nasa_api_key))
r = requests.get(nasa_api_url + "rest/v1/feed?start_date=" + request_date + "&end_date=" + request_date + "&api_key=" + nasa_api_key)

logger.debug("Response status code: " + str(r.status_code))
logger.debug("Response headers: " + str(r.headers))
logger.debug("Response content: " + str(r.text))

# Check if request was successful
if r.status_code == 200:

	# parse returned JSON
	json_data = json.loads(r.text)

    # initialize two lists to store safe and hazardous asteroids
	ast_safe = []
	ast_hazardous = []

    # check if key 'element_count' exists within data. if it does, get its value as total asteroid count
	if 'element_count' in json_data:
		ast_count = int(json_data['element_count'])
		logger.debug("Asteroid count today: " + str(ast_count))

		# check if there are at least one asteroid returned
		if ast_count > 0:
            # if at least one asteroid is returned, loop through them
			for val in json_data['near_earth_objects'][request_date]:
				# check if name, some url, est. diameter, whether its potentially hazardous and close approach data tags exist, and if the do, extract and store their values in variables
				if 'name' and 'nasa_jpl_url' and 'estimated_diameter' and 'is_potentially_hazardous_asteroid' and 'close_approach_data' in val:
					tmp_ast_name = val['name']
					tmp_ast_nasa_jpl_url = val['nasa_jpl_url']
					# if kilometers and min/max estimated values are available, extract and store those as well. do rounding for min/max values
					if 'kilometers' in val['estimated_diameter']:
						if 'estimated_diameter_min' and 'estimated_diameter_max' in val['estimated_diameter']['kilometers']:
							tmp_ast_diam_min = round(val['estimated_diameter']['kilometers']['estimated_diameter_min'], 3)
							tmp_ast_diam_max = round(val['estimated_diameter']['kilometers']['estimated_diameter_max'], 3)
						else:
							tmp_ast_diam_min = -2
							tmp_ast_diam_max = -2
					else:
						tmp_ast_diam_min = -1
						tmp_ast_diam_max = -1

					# store the flag whether this is potentially hazardous asteroid in temporary variable
					tmp_ast_hazardous = val['is_potentially_hazardous_asteroid']
                                        
                    # check if asteroid is considered close approach
					if len(val['close_approach_data']) > 0:
                        # if it is close approach, extract epoch date, relative vlocity and iss distanct if they are available
						if 'epoch_date_close_approach' and 'relative_velocity' and 'miss_distance' in val['close_approach_data'][0]:
							# convert epoch time to date time
							tmp_ast_close_appr_ts = int(val['close_approach_data'][0]['epoch_date_close_approach']/1000)
							tmp_ast_close_appr_dt_utc = datetime.utcfromtimestamp(tmp_ast_close_appr_ts).strftime('%Y-%m-%d %H:%M:%S')
							tmp_ast_close_appr_dt = datetime.fromtimestamp(tmp_ast_close_appr_ts).strftime('%Y-%m-%d %H:%M:%S')
                                                        
                            # extract asteroids speed and miss distance from earth if available and store in variables. otherwise store default values
							if 'kilometers_per_hour' in val['close_approach_data'][0]['relative_velocity']:
								tmp_ast_speed = int(float(val['close_approach_data'][0]['relative_velocity']['kilometers_per_hour']))
							else:
								tmp_ast_speed = -1

							if 'kilometers' in val['close_approach_data'][0]['miss_distance']:
								tmp_ast_miss_dist = round(float(val['close_approach_data'][0]['miss_distance']['kilometers']), 3)
							else:
								tmp_ast_miss_dist = -1
						else:
							tmp_ast_close_appr_ts = -1
							tmp_ast_close_appr_dt_utc = "1969-12-31 23:59:59"
							tmp_ast_close_appr_dt = "1969-12-31 23:59:59"
					else:
						logger.info("No close approach data in message")
						tmp_ast_close_appr_ts = 0
						tmp_ast_close_appr_dt_utc = "1970-01-01 00:00:00"
						tmp_ast_close_appr_dt = "1970-01-01 00:00:00"
						tmp_ast_speed = -1
						tmp_ast_miss_dist = -1

					# print extracted information about asteroid
					logger.debug("------------------------------------------------------- >>")
					logger.debug("Asteroid name: " + str(tmp_ast_name) + " | INFO: " + str(tmp_ast_nasa_jpl_url) + " | Diameter: " + str(tmp_ast_diam_min) + " - " + str(tmp_ast_diam_max) + " km | Hazardous: " + str(tmp_ast_hazardous))
					logger.debug("Close approach TS: " + str(tmp_ast_close_appr_ts) + " | Date/time UTC TZ: " + str(tmp_ast_close_appr_dt_utc) + " | Local TZ: " + str(tmp_ast_close_appr_dt))
					logger.debug("Speed: " + str(tmp_ast_speed) + " km/h" + " | MISS distance: " + str(tmp_ast_miss_dist) + " km")
					
					# Adding asteroid data to the corresponding array
					if tmp_ast_hazardous == True:
						ast_hazardous.append([tmp_ast_name, tmp_ast_nasa_jpl_url, tmp_ast_diam_min, tmp_ast_diam_max, tmp_ast_close_appr_ts, tmp_ast_close_appr_dt_utc, tmp_ast_close_appr_dt, tmp_ast_speed, tmp_ast_miss_dist])
					else:
						ast_safe.append([tmp_ast_name, tmp_ast_nasa_jpl_url, tmp_ast_diam_min, tmp_ast_diam_max, tmp_ast_close_appr_ts, tmp_ast_close_appr_dt_utc, tmp_ast_close_appr_dt, tmp_ast_speed, tmp_ast_miss_dist])

		else:
			logger.info("No asteroids are going to hit earth today")

	logger.info("Hazardous asteorids: " + str(len(ast_hazardous)) + " | Safe asteroids: " + str(len(ast_safe)))
        
    # if there are any hazardous asteroids, print some more information about them
	if len(ast_hazardous) > 0:

		# sort list of hazardous asteroids by their 4th key (impact times) and print
		ast_hazardous.sort(key = lambda x: x[4], reverse=False)

		logger.warning("Today's possible apocalypse (asteroid impact on earth) times:")
		for asteroid in ast_hazardous:
			logger.warning(str(asteroid[6]) + " " + str(asteroid[0]) + " " + " | more info: " + str(asteroid[1]))

		# sort list of hazardous asteroids by their 8th key (distance) and print
		ast_hazardous.sort(key = lambda x: x[8], reverse=False)
		logger.info("Closest passing distance is for: " + str(ast_hazardous[0][0]) + " at: " + str(int(ast_hazardous[0][8])) + " km | more info: " + str(ast_hazardous[0][1]))
	else:
		logger.info("No asteroids close passing earth today")

# if return code isn't 200 (request was successful) print error message and response code + content
else:
	logger.error("Unable to get response from API. Response code: " + str(r.status_code) + " | content: " + str(r.text))
