# -*- coding: UTF-8 -*-
"""Abstracts deleting a virtual machine from a user's lab"""
import uuid
import time
import random
import urllib3

import jwt
import requests
from vlab_api_common.std_logger import get_logger
from vlab_inf_common.vmware import vCenter, vim, virtual_machine

from vlab_quota.libs import const

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
log = get_logger(name=__name__, loglevel=const.QUOTA_LOG_LEVEL)


def _call_api(url, token, method='get', payload=None, task_call=True):
    """Make an HTTP request to a vLab API, and return the response body.

    :Returns: Dictionary

    :Raises: requests.exceptions.RequestException

    :param url: The complete URL to call
    :type url: String

    :param token: The vLab auth token to use
    :type token: Bytes

    :param method: The HTTP method to envoke
    :type method: String

    :param payload: Optional - the JSON body to send in the request
    :type payload: Dictionary

    :param task_call: Set to False if the initial request does not return a job task
    :type task_call: Boolean
    """
    headers = {'User-Agent': 'vLab Quota',
               'X-Auth': token,
               'X-Forwarded-For': const.VLAB_IP,
               'X-REQUEST-ID' : uuid.uuid4().hex}
    caller = getattr(requests, method.lower())
    resp = caller(url, headers=headers, json=payload, verify=False)
    task_url = None
    if task_call and resp.ok:
        task_url = resp.links['status']['url']
        while resp.status_code == 202:
            resp = requests.get(task_url, headers=headers, verify=False)
            time.sleep(1)
    if not resp.ok:
        url_used = task_url if task_url else url
        error = 'Failure for {} on {} - {}'.format(method, url_used, resp.content)
        log.error(error)
        resp.raise_for_status()
    return resp.json()


def _get_secret(location=const.AUTH_PRIVATE_KEY_LOCATION):
    """Reads a file containing some sort of secret/password

    :Returns: String

    :Raises: RuntimeError

    :param location: The filesystem path to the auth token secret.
    """
    if not location:
        raise RuntimeError('Must supply location of auth secret, supplied: {}'.format(location))
    else:
        with open(location) as the_file:
            secret = the_file.read().strip()
    return secret


def _generate_token(user, version=const.AUTH_TOKEN_VERSION, client_ip=const.VLAB_IP):
    """Create an auth token

    :Returns: String

    :param username: The user who's account has been disabled
    :type username: String

    :param version: The version of the auth token to create
    :type version: Integer

    :param client_ip: The IP of the machine that will send requests
    :type client_ip: String
    """
    issued_at_timestamp = time.time()
    claims = {'exp' : issued_at_timestamp + 1800, # 30 minutes
              'iat' : issued_at_timestamp,
              'iss' : const.VLAB_URL,
              'username' : user,
              'version' : version,
              'client_ip' : client_ip,
             }
    return jwt.encode(claims, _get_secret(), algorithm=const.AUTH_TOKEN_ALGORITHM)


def _delete_vm(user, vm_name, vm_type):
    """Delete the actual virtual machine

    :Returns: None

    :param user: The user that's getting some VMs deleted
    :type user: String

    :param vm_name: The name of the VM being deleted
    :type vm_name: String

    :param vm_type: The category of VM beging deleted. Provided so the correct
                    API can be called.
    :type vm_type: String
    """
    vm_url = 'https://{}/api/2/inf/{}'.format(const.VLAB_FQDN, vm_type.lower())
    token = _generate_token(user)
    payload = {'name': vm_name}
    _call_api(vm_url, token, method='DELETE', payload=payload, task_call=True)


def _delete_portmap_rules(user, vm_name):
    """Delete all portmapping rules associated to the VM getting deleted.

    :Returns: None

    :param user: The user that's getting some VMs deleted
    :type user: String

    :param vm_name: The name of the VM being deleted
    :type vm_name: String
    """
    user_gateway_url = 'https://{}.{}/api/1/ipam/portmap'.format(user, const.VLAB_FQDN)
    token = _generate_token(user)
    portmap_data = _call_api(user_gateway_url, token, method='GET', task_call=False)
    for conn_port, info in portmap_data['content']['ports'].items():
        if info['name'] == vm_name:
            payload = {'conn_port': int(conn_port)}
            _call_api(user_gateway_url, token, method='DELETE', payload=payload, task_call=False)


def destroy_vms(user, vcenter):
    """Delete enough VMs to resolve the soft-quota violation.

    The VMs deleted are randomly chosen, and this function returns a list of VM
    names that were deleted.

    :Returns: List

    :param user: The user that's getting some VMs deleted
    :type user: String

    :param vcenter: An object for interacting with the vCenter API.
    :type vcenter: vlab_inf_common.vmaware.vCenter
    """
    user_folder = vcenter.get_by_name(name=user, vimtype=vim.Folder)
    user_vms = set([x for x in user_folder.childEntity if not x.name == 'defaultGateway'])
    deleted_vms = []
    while len(user_vms) > const.VLAB_QUOTA_LIMIT:
        unlucky_vm = random.sample(user_vms, 1)[0] # b/c random.sample returns a list
        vm_info = virtual_machine.get_info(unlucky_vm)
        vm_name = unlucky_vm.name
        if vm_info['meta']['component'] == 'Unknown':
            log.info("Skipping VM %s owned by %s: VM cannot be deleted at this time", vm_name, user)
        else:
            _delete_portmap_rules(user, vm_name)
            log.info("Delete portmapping rules for VM %s owned by %s", vm_name, user)
            _delete_vm(user, vm_name, vm_info['meta']['component'].lower())
            deleted_vms.append(vm_name)
            log.info("Deleted VM %s, owned by %s", vm_name, user)
            # Removing the VM from the set *only* if we delete it avoids an
            # edge case where a user is over by 1 VM, and the one we randomly
            # choose to delete is either deploying or a failed deployment.
            # While this could potentially create an infinite loop, if it did
            # we'd probably have "bigger problems" going on, and fixing those
            # "bigger problems" would resolve the infinite loop.
            user_vms.discard(unlucky_vm)
    return deleted_vms
