#!/usr/bin/env python

import logging
import sys,os,traceback,optparse
import time
import re

def main():
	raise Exception("Hi there")

if __name__=='__main__':
	try:
		#Set up logging
		logging.basicConfig(filename='puttr.log', level=logging.DEBUG,format='%(asctime)s %(module)-12s %(funcName)-2s %(levelname)-8s %(message)s',filemode='a')
		console = logging.StreamHandler()
		console.setLevel(logging.DEBUG)
		formatter = logging.Formatter('%(asctime)s - %(module)-12s %(funcName)-2s: %(levelname)-8s %(message)s')
		console.setFormatter(formatter)
		logging.getLogger('').addHandler(console)
		logging.info("Entering main")
		#Time to actually do something
		main()
	except KeyboardInterrupt, e:
		raise e
	except SystemExit, e:
		raise e
	except Exception, e:
		logging.exception(e)
		os._exit(1)
