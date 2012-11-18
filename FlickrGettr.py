#!/usr/bin/env python
"""FlickrGettr, a simple little script for caching lots of images on a  Flickr account to a filesystem.

Copyright (c) 2012 Andrew Rowson. Licensed under the BSD two-clause license. See LICENSE.md for details."""

import logging
import os
import argparse
import flickrapi
import urllib
import json


class FlickrGettr:
    def __init__(self):
        self.flickrApiKey = "0f1a333f06103708c067d450321c0bfc"
        self.flickrApiSecret = "77b240d1ab6e7302"
        self.log = logging.getLogger('FlickrGettr')
        self.tokenfile = ".flickrtoken"
        self.path = []
        self.pathsdb = "gettr.db"

    def main(self, directory, dryrun):
        log.info("Entering main")
        if not os.path.exists(directory):
            raise IOError("Directory %s not found" % directory)
        self.photosToDownload = {}
        self.flickrUrlCache = {}
        log.info("Get Flickr Client")
        self.getFlickrClient()
        log.info("Getting existing photosets")
        self.populatePhotosets()
        self.loadSeen()
        log.info("{} cached urls loaded".format(len(self.flickrUrlCache)))
        for photoset in self.sets:
            log.info("Set: %s" % photoset)
            photos = self.flickr.photosets_getPhotos(photoset_id=self.sets[photoset])
            for photo in photos.findall('photoset/photo'):
                photoid = photo.attrib.get('id')
                filename = directory + '/' + self.createFilename(photoset, photo.attrib.get('title'))
                if os.path.exists(filename):
                    log.warning("Photo already exists on disk")
                    break
                if photoid in self.photosToDownload:
                    log.error("Duplicate photo name found")
                    break
                if photoid not in self.flickrUrlCache:
                    farmid = photo.attrib.get('farm')
                    serverid = photo.attrib.get('server')
                    photoinfo = self.flickr.photos_getInfo(photo_id=photoid).find('photo')
                    secret = photoinfo.attrib.get('originalsecret')
                    extension = photoinfo.attrib.get('originalformat')
                    url = "http://farm{farmid}.staticflickr.com/{serverid}/{id}_{osecret}_o.{format}".format(farmid=farmid, serverid=serverid, id=photoid, osecret=secret, format=extension)
                    self.photosToDownload[photoid] = filename
                    self.flickrUrlCache[photoid] = url
                    self.saveSeen()
                else:
                    url = self.flickrUrlCache[photoid]
                log.info("Photo: %s is %s" % (filename, url))

        log.info("Complete. %s photos to download" % len(self.photosToDownload))
        for photoid in self.photosToDownload:
            log.info("Downloading {}".format(self.flickrUrlCache[photoid]))
            urllib.urlretrieve(self.flickrUrlCache[photoid], self.photosToDownload[photoid])

    def createFilename(self, photoset, title):
        if title.endswith('.jpg'):
            return photoset + '/' + title
        else:
            return photoset + '/' + title + '.jpg'

    def populatePhotosets(self):
        allphotosets = self.flickr.photosets_getList()
        self.sets = {}
        log.info("User has %s existing sets" % len(allphotosets.findall('photosets/photoset')))
        for photoset in allphotosets.findall('photosets/photoset'):
            self.sets[photoset.findtext('title')] = photoset.attrib.get('id')

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

    def loadSeen(self):
        if not os.path.exists(self.pathsdb):
            self.paths = []
            return
        f = open(self.pathsdb, 'r')
        self.flickrUrlCache = json.load(f)
        f.close()

    def saveSeen(self):
        log.info("Saving seen paths")
        f = open(self.pathsdb, 'w')
        json.dump(self.flickrUrlCache, f)
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
        parser = argparse.ArgumentParser(description="Downloads photos from Flickr and arranges by set")
        parser.add_argument("directory", help="Directory destination for downloaded images")
        parser.add_argument("-x", "--dry-run", default=False, action="store_true", dest="dryrun", help="Do a dry run, don't actually upload")
        args = parser.parse_args()
        log.debug("Args: %s" % args)

        #Time to actually do something
        gettr = FlickrGettr()
        gettr.main(args.directory, args.dryrun)
    except KeyboardInterrupt, e:
        raise e
    except SystemExit, e:
        raise e
    except Exception, e:
        logging.exception(e)
        os._exit(1)
