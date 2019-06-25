import os
import requests
import argparse
import getpass
import json

requests.packages.urllib3.disable_warnings()

def _upload(host, creds, fp):

    chunk_size = 512 * 1024
    headers = {
        'Content-Type': 'application/octet-stream'
    }
    fileobj = open(fp, 'rb')
    filename = os.path.basename(fp)
    if os.path.splitext(filename)[-1] == '.iso':
        uri = 'https://%s/mgmt/cm/autodeploy/software-image-uploads/%s' % (host, filename)
    else:
        uri = 'https://%s/mgmt/shared/file-transfer/uploads/%s' % (host, filename)

    
    size = os.path.getsize(fp)
    start = 0

    while True:
        file_slice = fileobj.read(chunk_size)
        if not file_slice:
            break

        current_bytes = len(file_slice)
        if current_bytes < chunk_size:
            end = size
        else:
            end = start + current_bytes

        content_range = "%s-%s/%s" % (start, end - 1, size)
        headers['Content-Range'] = content_range
        requests.post(uri,
                      auth=creds,
                      data=file_slice,
                      headers=headers,
                      verify=False)

        start += current_bytes

def _extract_ilx_file(host, creds, filename):
    headers = {
        'Content-Type': 'application/json'
    }
    uri = 'https://%s/mgmt/tm/util/bash' % (host)
    cmd = 'tar -xvzf /var/config/rest/downloads/%s --directory /var/ilx/workspaces/Common/' % filename
    payload = {
        "command": "run",
        "utilCmdArgs": "-c \'%s\'" % cmd}

    return requests.post(uri, auth=creds, data=json.dumps(payload), headers=headers, verify=False)

def _remove(host, creds, filename):
    headers = {
        'Content-Type': 'application/json'
    }
    uri = 'https://%s/mgmt/tm/util/bash' % (host)
    cmd = 'rm -f /var/config/rest/downloads/%s' % filename
    payload = {
        "command": "run",
        "utilCmdArgs": "-c \'%s\'" % cmd}

    return requests.post(uri, auth=creds, data=json.dumps(payload), headers=headers, verify=False)

def _create_ILX_plugin(host, creds, wsname):
    headers = {
        'Content-Type': 'application/json'
    }
    uri = 'https://%s/mgmt/tm/ilx/plugin' % (host)
    payload = {
        "name": wsname,
	    "partition": "Common",
	    "enabled": True,
	    "fromWorkspace": wsname,
	    "stagedDirectory": "/var/ilx/workspaces/Common/%s" % wsname    
    }

    return requests.post(uri, auth=creds, data=json.dumps(payload), headers=headers, verify=False)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Upload File to BIG-IP')

    parser.add_argument("--host", help='BIG-IP IP or Hostname', )
    parser.add_argument("--username", help='BIG-IP Username')
    parser.add_argument("--filepath", help='Source Filename with Absolute Path')
    args = vars(parser.parse_args())

    hostname = args['host']
    username = args['username']
    filepath = args['filepath']
    filename = filepath.split("/")[-1]
    wsname = filename.split(".")[0]


    print "%s, enter your password: " % args['username'],
    password = getpass.getpass()

    # Send file to the BIG-IP.  This script assumes the ILX upload with be a compressed tar file (.tgz)
    _upload(hostname, (username, password), filepath)

    # Extract the .tgz file on the BigIP to ILX directory.  The tar archive must contain the parent 
    #  directory of ILX workspace (i.e. /var/ilx/workspaces/Common/<PARENT DIRECTORY>)
    _extract_ilx_file(hostname, (username, password), filename)

    # Clean up uploaded tar archive 
    _remove(hostname, (username, password), filename)

    # Register ILX plugin referencing new workspace directory
    _create_ILX_plugin(hostname, (username, password), wsname)

