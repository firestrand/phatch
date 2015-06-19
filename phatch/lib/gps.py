# Copyright (C) 2009 Robin Mills, San Jose, California, www.stani.be
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see http://www.gnu.org/licenses/
#
# All rights donated to the open source project Phatch. This code may
# be published using a license acceptable to project Phatch.

# Follows PEP8

import os
import datetime
import xml.dom.minidom

from other import surd

try:
    import pyexiv2
except ImportError:
    pyexiv2 = None

# Rational number support


def r(f):
    """r(float) - get a Rational number for a float"""
    s = surd.surd(float(f))
    return pyexiv2.Rational(s.num, s.denom)


def d(angle):
    """d(any) - get degrees from a number :eg d(33.41) -> 33"""
    return int(angle)


def m(angle):
    """m(any) - get minutes from a number :eg d(33.41) -> 24"""
    return int(angle * 60 - d(angle) * 60)


def s(angle):
    """s(any) - get seconds from a number :eg s(33.41) -> 36"""
    return int(angle * 3600 - d(angle) * 3600 - m(angle) * 60)


# dictionary search (closest match)
def search(dict, target):
    """search(dict,taget) - search for closest match"""
    s = sorted(dict.keys())
    N = len(s)
    low = 0
    high = N - 1

    while low < high:
        mid = (low + high) / 2
        if s[mid] < target:
            low = mid + 1
        else:
            high = mid
    return s[low]


# XML functions
def get_xml_timez(phototime, timeshift):
    """getXMLtimez - convert a datetime to an XML formatted date"""
    #
    # phototime = timedate.timedate("2008-03-16 08:52:15")
    # timeshift = seconds
    # -----------------------

    timedelta = datetime.timedelta(0, timeshift, 0)
    newtime = phototime + timedelta
    return newtime.strftime('%Y-%m-%dT%H:%M:%SZ')


def get_text(nodelist,):
    """get_text(nodeList) - return the text in nodelist"""
    rc = ""
    for node in nodelist:
        if node.nodeType == node.TEXT_NODE:
            rc = rc + node.data
    return rc


def get_node_value(node):
    """get_node_value((node) - return the value of a node"""
    return get_text(node.childNodes)


def handle_trkpt(trkpt, timedict, ns):
    """handle_trkpt"""
    if ns:
        ele = get_node_value(
                    trkpt.getElementsByTagNameNS(ns, "ele")[0])
        time = get_node_value(
                    trkpt.getElementsByTagNameNS(ns, "time")[0])
        lat = trkpt.getAttributeNS(ns, "lat")
        lon = trkpt.getAttributeNS(ns, "lon")
        # Garmin .gpx doesn't use a ns on the lat and lon attributes!
        # Garmin bug?
        if not lat:
            lat = trkpt.getAttribute("lat")
        if not lon:
            lon = trkpt.getAttribute("lon")
    else:
        ele = get_node_value(trkpt.getElementsByTagName("ele")[0])
        time = get_node_value(trkpt.getElementsByTagName("time")[0])
        lat = trkpt.getAttribute("lat")
        lon = trkpt.getAttribute("lon")
    # print "lat, lon = %s %s ele,time = %s %s" % ( lat,lon  , ele,time)
    timedict[time] = [ele, lat, lon]


def handle_trkseg(trkseg, timedict, ns):
    """handle_trkseg"""
    if ns:
        trkpts = trkseg.getElementsByTagNameNS(ns, "trkpt")
    else:
        trkpts = trkseg.getElementsByTagName("trkpt")
    for trkpt in trkpts:
        handle_trkpt(trkpt, timedict, ns)


def handle_trk(trk, timedict, ns):
    """handle_trk"""
    if ns:
        trksegs = trk.getElementsByTagNameNS(ns, "trkseg")
    else:
        trksegs = trk.getElementsByTagName("trkseg")
    for trkseg in trksegs:
        handle_trkseg(trkseg, timedict, ns)


def handle_gpx(gpx, timedict, ns):
    """handle_gpx"""
    if ns:
        trks = gpx.getElementsByTagNameNS(ns, "trk")
    else:
        trks = gpx.getElementsByTagName("trk")
    for trk in trks:
        handle_trk(trk, timedict, ns)

# GPS module API


# this code is heading for module core.lib.gps
def read_gpx(gpx_file):
    """read_gpx(string) -
    get a dictionary of time/position information"""
    timedict = {}
    #print "read_gpx = " + gpx_file
    file = open(gpx_file, "r")
    data = file.read(os.path.getsize(gpx_file))
    #print "reading ",gpx_file
    file.close()
    dom = xml.dom.minidom.parseString(data)

    # read the XML with and without the namepace
    handle_gpx(dom, timedict, False)
    ns = 'http://www.topografix.com/GPX/1/1'
    handle_gpx(dom, timedict, ns)

    return timedict


def write_header(report):
    #report.write("camera time          nearest gps          "\
    #    "latitude   longitude     elev photofile")
    report.write("camera time,nearest gps,latitude,longitude,elev,"\
        "photofile\n")


# returns the metadata dictionary for given exif date
# eg 'Exif_Image_DateTime'
def get_metadata(dateString, timedict, timeshift, path, report=None):
    """get_metadata(float) - get a dictionary of changes to the metadata
       dateString - EXIF date format string /* in */
       timeshift  - delta between GMT and local time (seconds.
                    Positive to West)
       path       - path to the image (only for stdout reporting)
       report     - log file
    """
    if not pyexiv2:
        raise ImportError('pyexiv2 is not installed')
    stamp = str(get_xml_timez(dateString, timeshift))

    timestamp = search(timedict, stamp)
    data = timedict[timestamp]
    ele = float(data[0])
    lat = float(data[1])
    lon = float(data[2])

    latR = 'N'
    lonR = 'E'
    eleR = 0
    if lat < 0:
        lat = -lat
        latR = 'S'
    if lon < 0:
        lon = -lon
        lonR = 'W'
    sele = "%6.1f" % (ele)
    if ele < 0:
        ele = -ele
        eleR = 1

    slat = "%02d.%02d'" '%02d"%s' % (d(lat), m(lat), s(lat), latR)
    slon = "%02d.%02d'" '%02d"%s' % (d(lon), m(lon), s(lon), lonR)
    if report:
        report.write(",".join([stamp, timestamp, slat, slon, sele, path])\
            + "\n")
    # get Rational number for ele
    # don't know why r(ele) is causing trouble!
    # it might be that the denominator is overflowing 32 bits!
    # and this would also import lat and lon
    rele = pyexiv2.Rational(int(ele * 10.0), 10)
    # create and return the dictionary of tags to be added to the image
    metadata = {}
    metadata['Exif_GPSInfo_GPSAltitude'] = rele
    metadata['Exif_GPSInfo_GPSAltitudeRef'] = eleR
    metadata['Exif_GPSInfo_GPSDateStamp'] = stamp
    metadata['Exif_GPSInfo_GPSLatitude'] = \
        [r(d(lat)), r(m(lat)), r(s(lat))]
    metadata['Exif_GPSInfo_GPSLatitudeRef'] = latR
    metadata['Exif_GPSInfo_GPSLongitude'] = \
        [r(d(lon)), r(m(lon)), r(s(lon))]
    metadata['Exif_GPSInfo_GPSLongitudeRef'] = lonR
    metadata['Exif_GPSInfo_GPSMapDatum'] = 'WGS-84'
    metadata['Exif_GPSInfo_GPSProcessingMethod'] = \
        '65 83 67 73 73 0 0 0 72 89 66 82 73 68 45 70 73 88 '
    metadata['Exif_GPSInfo_GPSTimeStamp'] = \
        [r(10), r(20), r(30)]
    metadata['Exif_GPSInfo.GPSVersionID'] = '2 2 0 0'
    return metadata
