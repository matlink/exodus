# -*- coding: utf-8 -*-
from __future__ import absolute_import, unicode_literals
from .celery import app
from celery import group, chain, chord
import tempfile
import shutil
from xml.dom import minidom
import sys, os
import zipfile
import subprocess as sp
import yaml
import datetime
import string
from pathlib import Path
from django.conf import settings
import shutil
from reports.models import Report, Application, Apk, Permission, NetworkAnalysis
from trackers.models import Tracker
from minio import Minio
from minio.error import (ResponseError, BucketAlreadyOwnedByYou, BucketAlreadyExists)


def grep(folder, pattern):
    cmd = '/bin/grep -r "%s" %s/' % (pattern, folder)
    process = sp.Popen(cmd, shell=True, stdout=sp.PIPE, stderr=sp.STDOUT)
    output = process.communicate()[0]
    exitCode = process.returncode
    return exitCode == 0


def getIcon(decoded_dir, icon_name, apk_tmp):
    cmd = "aapt d --values badging %s | grep application-icon | tail -n1 | cut -d \"'\" -f2" % apk_tmp
    process = sp.Popen(cmd, shell=True, stdout=sp.PIPE, stderr=sp.STDOUT)
    icon = process.communicate()[0].decode(encoding='UTF-8').replace('\n', '')
    print(cmd)
    print(icon)
    exit_code = process.returncode
    if exit_code != 0 or icon == '':
        return ''

    source_icon_path = os.path.join(decoded_dir, icon)
    icon_file = Path(source_icon_path)
    if not icon_file.is_file():
        return ''
    
    # Upload icon in storage
    minio_client = Minio(settings.MINIO_URL,
                access_key=settings.MINIO_ACCESS_KEY,
                secret_key=settings.MINIO_SECRET_KEY,
                secure=settings.MINIO_SECURE)
    try:
        minio_client.fput_object(settings.MINIO_BUCKET, icon_name, source_icon_path)
    except ResponseError as err:
        print(err)
    return icon_name


def findTrackers(decoded_dir):
    trackers = Tracker.objects.order_by('name')
    found = []
    for t in trackers:
        for p in t.detectionrule_set.all():
            if grep(decoded_dir, p.pattern):
                found.append(t)
                break
    return found


def getVersion(decoded_dir):
    yml = os.path.join(decoded_dir, 'apktool.yml')
    yml_new = os.path.join(decoded_dir, 'apktool.yml.new')
    cmd = '/bin/cat %s | /bin/grep -v "\!\!" > %s' % (yml, yml_new)
    process = sp.Popen(cmd, shell=True, stdout=sp.PIPE, stderr=sp.STDOUT)
    output = process.communicate()[0]
    exitCode = process.returncode
    if exitCode != 0:
        return ''    
    with open(yml_new) as f:
        dataMap = yaml.safe_load(f)
        return dataMap['versionInfo']['versionName']


def getHandle(decoded_dir):
    xmldoc = minidom.parse(os.path.join(decoded_dir, 'AndroidManifest.xml'))
    man = xmldoc.getElementsByTagName('manifest')[0]
    return man.getAttribute('package')


def getPermissions(decoded_dir):
    xmldoc = minidom.parse(os.path.join(decoded_dir, 'AndroidManifest.xml'))
    permissions = xmldoc.getElementsByTagName('uses-permission')
    perms = []
    for perm in permissions:
        perms.append(perm.getAttribute('android:name'))
    return perms


def getSha256Sum(apk_path):
    cmd = '/usr/bin/sha256sum %s | head -c 64' % apk_path
    process = sp.Popen(cmd, shell=True, stdout=sp.PIPE, stderr=sp.STDOUT)
    return process.stdout.read()


def decodeAPK(apk_path, decoded_dir):
    root_dir = os.path.dirname(os.path.realpath(__file__))
    apktool = os.path.join(root_dir, "apktool.jar")
    cmd = '/usr/bin/java -jar %s d %s -s -o %s/' % (apktool, apk_path, decoded_dir)
    process = sp.Popen(cmd, shell=True, stdout=sp.PIPE, stderr=sp.STDOUT)
    output = process.communicate()[0]
    exitCode = process.returncode
    return exitCode == 0


def getApplicationInfos(handle):
    # Fix#12 - We have to remove the cached token :S
    shutil.rmtree(os.path.join(str(Path.home()), '.cache/gplaycli/'), ignore_errors=True)
    cmd = 'gplaycli -t -s %s -n 1' % handle
    lines = []
    with sp.Popen(cmd, shell=True, stdout=sp.PIPE, stderr=sp.STDOUT, universal_newlines=True) as p:
        for line in iter(p.stdout):
            if 'Traceback' in line or 'Error' in line:
                return None
            lines.append(line.replace('\n', ''))
        if len(lines) != 2:
            return None
        columns = []
        columns.append({'start':0, 'end':0, 'value':'', 'name':'title', 'text':'Title'})
        columns.append({'start':0, 'end':0, 'value':'', 'name':'creator', 'text':'Creator'})
        columns.append({'start':0, 'end':0, 'value':'', 'name':'size', 'text':'Size'})
        columns.append({'start':0, 'end':0, 'value':'', 'name':'downloads', 'text':'Downloads'})
        columns.append({'start':0, 'end':0, 'value':'', 'name':'update', 'text':'Last Update'})
        columns.append({'start':0, 'end':0, 'value':'', 'name':'handle', 'text':'AppID'})
        columns.append({'start':0, 'end':0, 'value':'', 'name':'version', 'text':'Version'})
        columns.append({'start':0, 'end':0, 'value':'', 'name':'rating', 'text':'Rating'})
        result = {}
        for i in range(0,len(columns)):
            v = columns[i]
            v['start'] = lines[0].find(v['text'])
            if i > 0:
                c = columns[i-1]
                c['end'] =  v['start']
                c['value'] = lines[1][c['start']:c['end']].strip(" ")
                result[c['name']] = c['value']
        if handle in result['handle']:
            return result
        else:
            return None