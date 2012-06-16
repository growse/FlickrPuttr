#!/usr/bin/env python

import logging
import os,argparse
import flickrapi
from threading import Lock
from xml.etree import ElementTree

FLICKR_API_KEY="0f1a333f06103708c067d450321c0bfc"
FLICKR_API_SECRET="77b240d1ab6e7302"
tokenfile=".flickrtoken"
log = logging.getLogger('FlickrPuttr')

def main(directory):
	log.info("Entering main")
	if not os.path.exists(directory):
		raise IOError("Directory %s not found"%directory)
	log.info("Get Flickr Client")
	flickr = getFlickrClient()

	for root,dirs,files in os.walk(directory):
		if not root == directory:
			log.debug("Root: %s"%root)
			setname = root.split(os.path.dirname(root))[1].lstrip('/')
			setid=0
			first=True
					
			for thisfile in files:
				fileName, fileExtension = os.path.splitext(thisfile)
				log.debug("Filename: %s, FileExtension: %s"%(fileName,fileExtension))
				if fileExtension in ['.jpg','.png']:
					log.info("Uploading %s"%thisfile)
					photo = flickr.upload(filename=root+'/'+thisfile,title=fileName,tags="FlickrPuttr",is_public=0,is_family=1,is_friend=0,callback=upload_callback)
					photoid = photo.findtext("photoid")
					log.debug("Upload method returned with %s"%photoid)
					if first:
						first=False
						log.info("Creating set %s"%setname)
						photoset = flickr.photosets_create(title=setname,primary_photo_id=photoid)
						setid = photoset.find('photoset').attrib.get('id')
						ElementTree.dump(photoset)
					else:
						log.debug("Adding photo %s to set %s"%(photoid,setid))
						flickr.photosets_addPhoto(photoset_id=setid,photo_id=photoid)
				else:
					log.warn("%s not supported"%thisfile)

def upload_callback(progress,done):
	if done:
		log.info("Upload complete")
	else:
		log.info("Progress %s%%"%progress)

def getFlickrClient():
	log.info("Entering getFlickrClient")
	token = getFlickrToken()
	if token != None:
		log.info("Token pulled from cache")
		flickr = flickrapi.FlickrAPI(FLICKR_API_KEY,FLICKR_API_SECRET,store_token=False,token=token)
		try:
			flickr.auth_checkToken()
			return flickr
		except flickrapi.FlickrError:
			log.error("Cached token not valid")
			token = None
	flickr = flickrapi.FlickrAPI(FLICKR_API_KEY,FLICKR_API_SECRET,store_token=False)
	log.debug("Calling Get Flickr Token API Part 1")
	(token,frob) = flickr.get_token_part_one(perms='write')
	if not token: raw_input("Press ENTER after you authorized this program")
	log.debug("Calling Get Flickr Token API Part 2")
	token = flickr.get_token_part_two((token, frob))
	log.debug("Token obtained: %s"%token)
	setFlickrToken(token)
	return flickr	

def getFlickrToken():
	global tokenfile
	if not os.path.exists(tokenfile):
		return None
	f = open(tokenfile,'r')
	token = f.read()
	f.close()
	return token 

def setFlickrToken(token):
	global tokenfile
	f = open(tokenfile,'w')
	f.write(token)
	f.close()


if __name__=='__main__':
	try:
		#Set up logging
		logfile = logging.FileHandler('puttr.log')
		logfile.setLevel(logging.DEBUG)
		fileformatter = logging.Formatter('%(asctime)s %(module)-12s %(funcName)-2s %(levelname)-8s %(message)s')
		logfile.setFormatter(fileformatter)

		console = logging.StreamHandler()
		console.setLevel(logging.DEBUG)
		formatter = logging.Formatter('%(asctime)s - %(module)-12s %(funcName)-2s: %(levelname)-8s %(message)s')
		console.setFormatter(formatter)
		#logging.getLogger().addHandler(console)
	
		logging.basicConfig()
		for logger in logging.getLogger().handlers:
			logging.getLogger().removeHandler(logger)
		
		log = logging.getLogger('FlickrPuttr')
		log.addHandler(logfile)
		log.addHandler(console)
		log.setLevel(logging.DEBUG)
		

		#Parse the command line arguments
		parser = argparse.ArgumentParser(description="Uploads photos to Flickr and creates sets based on directory names")
		parser.add_argument("directory", help="Directory containing photos to upload")
		args = parser.parse_args()
		

		log.info("Received args: %s"%args.directory)
		
		#Time to actually do something
		main(args.directory)
	except KeyboardInterrupt, e:
		raise e
	except SystemExit, e:
		raise e
	except Exception, e:
		logging.exception(e)
		os._exit(1)
