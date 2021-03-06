#!/usr/bin/env python
"""FlickrPuttr, a simple little script for dumping lots of images into sets on Flickr.

Copyright (c) 2012 Andrew Rowson. Licensed under the BSD two-clause license. See LICENSE.md for details."""

import time
import logging
import os
import argparse
import flickrapi
import json
from xml.etree import ElementTree
from httplib import BadStatusLine


class FlickrPuttr:
    def __init__(self):
        self.flickrApiKey = "0f1a333f06103708c067d450321c0bfc"
        self.flickrApiSecret = "77b240d1ab6e7302"
        self.log = logging.getLogger('FlickrPuttr')
        self.tokenfile = ".flickrtoken"
        self.pathsdb = 'puttr.db'
        self.path = []

    def ordersets(self):
        log.info("Entering ordersets")
        log.info("Get Flickr Client")
        self.getFlickrClient()
        log.info("Getting existing photosets")
        self.populatePhotosets()
        setids = []
        for key, value in sorted(self.sets.iteritems(), reverse=True):
            setids.append(value)
        log.info("Setting new set order")
        self.flickr.photosets_orderSets(photoset_ids=','.join(setids))
        log.info("Done")

    def main(self, directory, dryrun, followlinks):
        log.info("Entering main")
        if not os.path.exists(directory):
            raise IOError("Directory %s not found" % directory)
        log.info("Get Flickr Client")
        self.getFlickrClient()
        log.info("Getting existing photosets")
        self.populatePhotosets()

        log.info("Loading paths already examined")
        self.loadSeen()
        filecount = 0
        log.info("Walking directory")
        for root, dirs, files in os.walk(directory, followlinks=followlinks):
            if not root == directory:
                log.info("In directory: %s" % root)
                setname = root.split(os.path.dirname(root))[1].lstrip('/')
                setid = 0
                first = True

                for thisfile in files:
                    filecount += 1
                    if root + '/' + thisfile in self.paths:
                        log.info("Already seen this path: %s" % thisfile)
                    else:
                        fileName, fileExtension = os.path.splitext(thisfile)
                        log.info("Filename: %s, FileExtension: %s" % (fileName, fileExtension))
                        if fileExtension.lower() in ['.jpg', '.png', '.mov', '.wmv', '.bmp', '.avi', '.3gp']:
                            log.info("seeing if this photo already exists")
                            photo_exists = False
                            existing = self.flickr.photos_search(user_id='me', tags="FlickrPuttr", text=fileName, tag_mode='all').find('photos')
                            log.debug("Existing: %s" % ElementTree.tostring(existing))
                            existing_count = existing.attrib.get('total')
                            if existing_count != "":
                                log.debug("%s existing found" % existing_count)
                                for photo in existing.findall('photo'):
                                    photoid = photo.attrib.get('id')
                                    log.debug("Getting tags for photo id: %s" % photoid)
                                    attempts = 5
                                    while attempts > 0:
                                        try:
                                            photo_info = self.flickr.photos_getInfo(photo_id=photoid)
                                            attempts = 0
                                        except BadStatusLine, e:
                                            log.exception(e)
                                            log.error("Sleeping for 10 seconds due to error getting photo info")
                                            attempts -= 1
                                            if attempts == 0:
                                                raise e
                                            else:
                                                time.sleep(10)

                                    log.debug("Photo Info: %s" % ElementTree.tostring(photo_info))
                                    tags = photo_info.findall('photo/tags/tag')
                                    log.debug("%s tags found" % len(tags))
                                    for tag in tags:
                                        log.debug("Tag: %s" % tag.attrib.get('raw'))
                                        if tag.attrib.get('raw') == 'FlickrPuttr':
                                            photo_exists = True

                            if not photo_exists:
                                log.info("Uploading %s" % thisfile)
                                photoid = -1
                                if not dryrun:
                                    upload_complete = False
                                    while not upload_complete:
                                        try:
                                            photo = self.flickr.upload(filename=root + '/' + thisfile, title=fileName, tags="FlickrPuttr", is_public=0, is_family=1, is_friend=0, callback=self.upload_callback)
                                            log.info("Upload completed")
                                            upload_complete = True
                                        except BadStatusLine, e:
                                            log.exception(e)
                                            log.error("Sleeping for 10 seconds due to error uploading")
                                            time.sleep(10)
                                    photoid = photo.findtext("photoid")
                                    log.debug("Upload method returned with %s" % photoid)
                                if first:
                                    first = False
                                    if not setname in self.sets:
                                        log.info("Creating set %s" % setname)
                                        if not dryrun:
                                            photoset = self.flickr.photosets_create(title=setname, primary_photo_id=photoid)
                                            setid = photoset.find('photoset').attrib.get('id')
                                    else:
                                        log.info("%s already exists, so adding to that" % setname)
                                        setid = self.sets[setname]
                                else:
                                    log.debug("Adding photo %s to set %s" % (photoid, setid))
                                    if not dryrun:
                                        attempts = 5
                                        while attempts > 0:
                                            try:
                                                self.flickr.photosets_addPhoto(photoset_id=setid, photo_id=photoid)
                                                attempts = 0
                                            except flickrapi.FlickrError, e:
                                                log.exception(e)
                                                log.error("Waiting a bit to try again")
                                                attempts -= 1
                                                if attempts == 0:
                                                    raise e
                                                else:
                                                    time.sleep(5)
                            else:
                                log.warn("Photo exists. Skipping")
                        else:
                            log.warn("%s not supported" % thisfile)
                        log.info("Appending path to seen paths")
                        self.paths.append(root + '/' + thisfile)
                        log.info("Now seen %s paths total" % len(self.paths))
                        self.saveSeen()
        log.info("Complete. %s photos processed" % filecount)

    def loadSeen(self):
        if not os.path.exists(self.pathsdb):
            self.paths = []
            return
        f = open(self.pathsdb, 'r')
        self.paths = json.load(f)
        f.close()

    def saveSeen(self):
        log.info("Saving seen paths")
        f = open(self.pathsdb, 'w')
        json.dump(self.paths, f)
        f.close()

    def populatePhotosets(self):
        allphotosets = self.flickr.photosets_getList()
        self.sets = {}
        log.info("User has %s existing sets" % len(allphotosets.findall('photosets/photoset')))
        for photoset in allphotosets.findall('photosets/photoset'):
            self.sets[photoset.findtext('title')] = photoset.attrib.get('id')

    def upload_callback(self, progress, done):
        if done:
            log.info("Upload complete")
        else:
            log.info("Progress %s%%" % progress)

    def getFlickrClient(self):
        log.info("Entering getFlickrClient")
        token = self.getFlickrToken()
        if token is not None:
            log.info("Token pulled from cache")
            self.flickr = flickrapi.FlickrAPI(self.flickrApiKey, self.flickrApiSecret, store_token=False, token=token)
            try:
                self.flickr.auth_checkToken()
                return
            except flickrapi.FlickrError:
                log.error("Cached token not valid")
                token = None
        self.flickr = flickrapi.FlickrAPI(self.flickrApiKey, self.flickrApiSecret, store_token=False)
        log.debug("Getting flickr token")
        (token, frob) = self.flickr.get_token_part_one(perms='write', auth_callback=self.flickrAuth)

        if not token:
            raw_input("Press ENTER after you authorized this program")
        token = self.flickr.get_token_part_two((token, frob))
        log.debug("Token obtained: %s" % token)
        self.setFlickrToken(token)

    def flickrAuth(self, frob, perms):
        log.info("Frob: %s" % frob)
        log.info("Perms: %s" % perms)
        log.info(self)
        print "Go to %s" % self.flickr.auth_url(perms, frob)

    def getFlickrToken(self):
        if not os.path.exists(self.tokenfile):
            return None
        f = open(self.tokenfile, 'r')
        token = f.read()
        f.close()
        return token

    def setFlickrToken(self, token):
        f = open(self.tokenfile, 'w')
        f.write(token)
        f.close()

if __name__ == '__main__':
    try:
        #Set up logging
        logfile = logging.FileHandler('puttr.log')
        logfile.setLevel(logging.DEBUG)
        fileformatter = logging.Formatter('%(asctime)s %(module)-12s %(funcName)-2s %(levelname)-8s %(message)s')
        logfile.setFormatter(fileformatter)

        console = logging.StreamHandler()
        console.setLevel(logging.INFO)
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
        parser.add_argument("-x", "--dry-run", default=False, action="store_true", dest="dryrun", help="Do a dry run, don't actually upload")
        parser.add_argument("-L", "--follow-links", default=False, action="store_true", dest="followlinks", help="Follow links in target directory")
        parser.add_argument("-O", "--order-sets", default=False, action="store_true", dest="ordersets", help="Just order the sets alphabetically")
        args = parser.parse_args()
        log.debug("Args: %s" % args)

        #Time to actually do something
        puttr = FlickrPuttr()
        if args.ordersets:
            puttr.ordersets()
        else:
            puttr.main(args.directory, args.dryrun, args.followlinks)
    except KeyboardInterrupt, e:
        raise e
    except SystemExit, e:
        raise e
    except Exception, e:
        logging.exception(e)
        os._exit(1)
