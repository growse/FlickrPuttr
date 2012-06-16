#!/usr/bin/env python

import logging
import os,argparse
import flickrapi
from threading import Lock
from xml.etree import ElementTree


class FlickrPuttr:
    def __init__(self):
        self.FLICKR_API_KEY="0f1a333f06103708c067d450321c0bfc"
        self.FLICKR_API_SECRET="77b240d1ab6e7302"
        self.log = logging.getLogger('FlickrPuttr')
        self.tokenfile=".flickrtoken"
        pass
    def main(self,directory,dryrun,followlinks):
        log.info("Entering main")
        if not os.path.exists(directory):
            raise IOError("Directory %s not found"%directory)
        log.info("Get Flickr Client")
        self.getFlickrClient()
        log.info("Walking directory")
        for root,dirs,files in os.walk(directory,followlinks=followlinks):
            if not root == directory:
                log.debug("Root: %s"%root)
                setname = root.split(os.path.dirname(root))[1].lstrip('/')
                setid=0
                first=True
                        
                for thisfile in files:
                    fileName, fileExtension = os.path.splitext(thisfile)
                    log.debug("Filename: %s, FileExtension: %s"%(fileName,fileExtension))
                    if fileExtension.lower() in ['.jpg','.png','.mov','.wmv','.bmp','.avi','.3gp']:
                        log.info("seeing if this photo already exists")
                        existing = self.flickr.photos_search(user_id='me',tags="blasdifjalsdif",text=fileName,tag_mode='all')
                        ElementTree.dump(existing)
                        os._exit(0)
                        log.info("Uploading %s"%thisfile)
                        photoid=-1
                        if not dryrun:
                            photo = self.flickr.upload(filename=root+'/'+thisfile,title=fileName,tags="FlickrPuttr %s"%setname,is_public=0,is_family=1,is_friend=0,callback=self.upload_callback)
                            photoid = photo.findtext("photoid")
                            log.debug("Upload method returned with %s"%photoid)
                        if first:
                            first=False
                            log.info("Creating set %s"%setname)
                            if not dryrun:
                                photoset = self.flickr.photosets_create(title=setname,primary_photo_id=photoid)
                                setid = photoset.find('photoset').attrib.get('id')
                        else:
                            log.debug("Adding photo %s to set %s"%(photoid,setid))
                            if not dryrun:
                                self.flickr.photosets_addPhoto(photoset_id=setid,photo_id=photoid)
                    else:
                        log.warn("%s not supported"%thisfile)
    
    def upload_callback(self,progress,done):
        if done:
            log.info("Upload complete")
        else:
            log.info("Progress %s%%"%progress)
    
    def getFlickrClient(self):
        log.info("Entering getFlickrClient")
        token = self.getFlickrToken()
        if token != None:
            log.info("Token pulled from cache")
            self.flickr = flickrapi.FlickrAPI(self.FLICKR_API_KEY,self.FLICKR_API_SECRET,store_token=False,token=token)
            try:
                self.flickr.auth_checkToken()
                return
            except flickrapi.FlickrError:
                log.error("Cached token not valid")
                token = None
        self.flickr = flickrapi.FlickrAPI(self.FLICKR_API_KEY,self.FLICKR_API_SECRET,store_token=False)
        log.debug("Getting flickr token")
        (token, frob) = self.flickr.get_token_part_one(perms='write',auth_callback=self.flickrAuth)
        
        if not token: raw_input("Press ENTER after you authorized this program")
        token = self.flickr.get_token_part_two((token, frob))
        log.debug("Token obtained: %s"%token)
        self.setFlickrToken(token)
    
    def flickrAuth(self, frob, perms):
        log.info("Frob: %s"%frob)
        log.info("Perms: %s"%perms)
        log.info(self)
        print "Go to %s"%self.flickr.auth_url(perms,frob)
        
    
    def getFlickrToken(self):
        if not os.path.exists(self.tokenfile):
            return None
        f = open(self.tokenfile,'r')
        token = f.read()
        f.close()
        return token 
    
    def setFlickrToken(self,token):
        f = open(self.tokenfile,'w')
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
        parser.add_argument("--dry-run", default=False, action="store_true", dest="dryrun", help="Do a dry run, don't actually upload")
        parser.add_argument("--follow-links", default=False, action="store_true", dest="followlinks", help="Follow links in target directory")
        args = parser.parse_args()
        log.debug("Args: %s"%args)
        
        #Time to actually do something
        puttr = FlickrPuttr()
        puttr.main(args.directory,args.dryrun,args.followlinks)
    except KeyboardInterrupt, e:
        raise e
    except SystemExit, e:
        raise e
    except Exception, e:
        logging.exception(e)
        os._exit(1)
