#!/usr/bin/python

import time
import os
import sys, traceback
import logging
import logging.handlers
import subprocess

from ConfigParser import SafeConfigParser

import urllib
import urllib2

###########################
# PERSONAL CONFIG FILE READ
###########################

parser = SafeConfigParser()
parser.read('health_monitor.ini')

# Read path to log file
LOG_FILENAME = parser.get('config', 'log_filename')

# monitoring period
MONITORING_PERIOD = parser.getint('config', 'monitoring_period')

# remote logging URL
REMOTELOG_URL = parser.get('config', 'remotelog_url')

MONITORED_DEVICES = parser.items('monitored_devices')

#################
#  LOGGING SETUP
#################
LOG_LEVEL = logging.INFO  # Could be e.g. "DEBUG" or "WARNING"

# Configure logging to log to a file, making a new file at midnight and keeping the last 3 day's data
# Give the logger a unique name (good practice)
logger = logging.getLogger(__name__)
# Set the log level to LOG_LEVEL
logger.setLevel(LOG_LEVEL)
# Make a handler that writes to a file, making a new file at midnight and keeping 3 backups
handler = logging.handlers.TimedRotatingFileHandler(LOG_FILENAME, when="midnight", backupCount=3)
# Format each log message like this
formatter = logging.Formatter('%(asctime)s %(levelname)-8s %(message)s')
# Attach the formatter to the handler
handler.setFormatter(formatter)
# Attach the handler to the logger
logger.addHandler(handler)

# Make a class we can use to capture stdout and sterr in the log
class MyLogger(object):
	def __init__(self, logger, level):
		"""Needs a logger and a logger level."""
		self.logger = logger
		self.level = level

	def write(self, message):
		# Only log if there is a message (not just a new line)
		if message.rstrip() != "":
			self.logger.log(self.level, message.rstrip())

# Replace stdout with logging to file at INFO level
sys.stdout = MyLogger(logger, logging.INFO)
# Replace stderr with logging to file at ERROR level
sys.stderr = MyLogger(logger, logging.ERROR)

logger.info('Starting LAN device health monitoring service')
logger.info("Monitoring period: %d seconds", MONITORING_PERIOD)

def remoteLog(dataId, value):
	
	values = {}
	values['dataId'] = str(dataId)
	values['value'] = str(value)

	data = urllib.urlencode(values)
	req = urllib2.Request(REMOTELOG_URL, data)
	response = urllib2.urlopen(req)
	result = response.read()

	if not result=='\"insert OK\"':
		logger.info('remote log FAILED, status=' + result)

def pingDevice(ipaddress, dataIdToLog):
	try:
		out_bytes = subprocess.check_output("ping -c 1 "+ ipaddress, shell=True, stderr=subprocess.STDOUT)
		logger.info("Ping to "+dataIdToLog+" is OK")
		remoteLog(dataIdToLog, "1.0")
		
	except subprocess.CalledProcessError as e:
		out_bytes = e.output       # Output generated before error
		code      = e.returncode   # Return code
		logger.info(out_bytes)
		logger.info("Ping to "+ipaddress+" is KO (code="+str(code)+")")
		remoteLog(dataIdToLog, "0.0")

while(True):

	try:
		logger.info('\n========= Checking LAN devices connectivity =========')

		for dataId, ipaddress in MONITORED_DEVICES:
			pingDevice(ipaddress, dataId)
	
		time.sleep(MONITORING_PERIOD)

	except:
		logger.info("*****Exception in main loop, continuing in 60 seconds******")
		exc_type, exc_value, exc_traceback = sys.exc_info()
		traceback.print_exception(exc_type, exc_value, exc_traceback,limit=2, file=sys.stdout)	
		del exc_traceback
		time.sleep(60.0)
		continue


