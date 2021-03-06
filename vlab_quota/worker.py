# -*- coding: UTF-8 -*-
"""Enforces the vLab quota soft-limit policy"""
import time
import atexit

import ldap3
from vlab_inf_common.vmware import vCenter, vim
from vlab_api_common.std_logger import get_logger

from vlab_quota.libs.vm import destroy_vms
from vlab_quota.libs import const, Database, notify

LOOP_INTERVAL = 10 # seconds
log = get_logger(name=__name__, loglevel=const.QUOTA_LOG_LEVEL)


def _get_violators(vcenter):
    """Obtain a list of users who have exceeded their VM quota limit

    :Returns: List

    :param vcenter: An object for interacting with the vCenter API.
    :type vcenter: vlab_inf_common.vmaware.vCenter
    """
    users = vcenter.get_vm_folder(path=const.INF_VCENTER_TOP_LVL_DIR)
    vm_quota_limit = const.VLAB_QUOTA_LIMIT + 1 # +1 to account for the defaultGateway
    # len(x.childEntity) -1 to account for the defaultGateway "down/up the stack"
    return {x.name: len(x.childEntity) -1 for x in users.childEntity if len(x.childEntity) > vm_quota_limit}


def _grace_period_exceeded(violation_date):
    """Determines if the quota grace period has expired.

    :Returns: Boolean

    :param violation_date: The EPOCH timestamp when the user exceeded their VM quota.
    :type violation_date: Integer
    """
    if violation_date is 0:
        return False
    return int(time.time()) > (violation_date + const.QUOTA_GRACE_PERIOD)


def _get_user_email(user, ldap_conn):
    """Lookup a user's email so we can notify them.

    :Returns: Boolean

    :Raises: RuntimeError - If user not found in LDAP server

    :param user: The samAccountName of the vLab user
    :type user: String

    :param ldap_conn: An authenicated, bound connection to an LDAP server
    :type ldap_conn: ldap3.Connection
    """
    search_filter = '(&(objectclass=User)(sAMAccountName=%s))' % user
    ldap_conn.search(search_base=const.AUTH_SEARCH_BASE,
                     search_filter=search_filter,
                     attributes=['mail'])
    if ldap_conn.entries:
        user_email = ldap_conn.entries[0]['mail'].value
        return user_email
    else:
        raise RuntimeError('Unable to lookup email for %s', user)


def _get_ldap_password(location=const.AUTH_BIND_PASSWORD_LOCATION):
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


def _get_ldap_conn():
    """A simple factory to connect to an LDAP server.

    :Returns: ldap3.core.connection.Connection
    """
    server = ldap3.Server(const.AUTH_LDAP_URL)
    password = _get_ldap_password()
    conn = ldap3.Connection(server, const.AUTH_BIND_USER, password, auto_bind=True)
    return conn


def _enforce_quotas(vcenter, db, ldap_conn):
    """Main business logic for enforcing soft-quotas

    Returns a set of users with a quota violation

    :Returns: Set

    :param vcenter: An object for interacting with the vCenter API.
    :type vcenter: vlab_inf_common.vmaware.vCenter

    :param db: An established connection to the Quota database.
    :type db: vlab_quotas.libs.database.Database

    :param ldap_conn: An authenticated connection to an LDAP server.
    :type ldap_conn: ldap3.core.connection.Connection
    """
    violators = _get_violators(vcenter)
    log.info('Users exceeding quota: {}'.format(','.join(violators)))
    for violator, vm_count in violators.items():
        violation_date, last_time_notified = db.user_info(violator)
        user_email = _get_user_email(violator, ldap_conn)
        now = time.time()
        if _grace_period_exceeded(violation_date):
            log.info("Soft quota grace period expired for user %s. Deleting VMs", violator)
            vms_deleted = destroy_vms(violator, vcenter)
            notify.send_follow_up(user_email, now, vms_deleted)
            db.remove_user(violator)
        elif notify.should_send_warning(violation_date, last_time_notified):
            log.info("Sending user %s warning about soft quota violation", violator)
            if violation_date == 0:
                # the DB returns zero if the user does not exist; i.e. this
                # is the first time we detected a violation for them.
                violation_date = now
            exp_date = int(violation_date + const.QUOTA_GRACE_PERIOD)
            notify.send_warning(user_email, vm_count, exp_date)
            last_time_notified = now
            db.upsert_user(violator, violation_date, last_time_notified)
    return set(violators.keys())


def _cleanup_reconciled_users(current_users_in_violation, users_in_violation, db):
    """Remove the quota violation record if a user deleted VMs and is no longer
    violating the quota limit.

    :param current_users_in_violation: The most recent group of users that exceeded the quota limit
    :type current_users_in_violation: Set

    :param users_in_violation: The last group of users that exceeded the quota limit
    :type users_in_violation: Set

    :param db: An established connection to the Quota database.
    :type db: vlab_quotas.libs.database.Database
    """
    reconciled_users = [x for x in users_in_violation if x not in current_users_in_violation]
    for user in reconciled_users:
        db.remove_user(user)


def main():
    """Entry point for vLab Quota enforcement"""
    log.info('Quota Soft Limit: %s', const.VLAB_QUOTA_LIMIT)
    log.info('Quota Grace Period: %s seconds', const.QUOTA_GRACE_PERIOD)
    log.info('vSphere Server: %s', const.INF_VCENTER_SERVER)
    log.info('LDAP Server: %s', const.AUTH_LDAP_URL)
    log.info('LDAP User: %s', const.AUTH_BIND_USER)
    log.info('SMTP Server: %s', const.QUOTA_EMAIL_SERVER)
    log.info('Loop interval: %s', LOOP_INTERVAL)
    vcenter = vCenter(host=const.INF_VCENTER_SERVER,
                      user=const.INF_VCENTER_USER,
                      password=const.INF_VCENTER_PASSWORD)
    atexit.register(vcenter.close)
    db = Database()
    atexit.register(db.close)
    ldap_conn = _get_ldap_conn()
    atexit.register(ldap_conn.unbind)
    users_in_violation = set()
    while True:
        start_loop = int(time.time())
        current_users_in_violation = _enforce_quotas(vcenter, db, ldap_conn)
        _cleanup_reconciled_users(current_users_in_violation, users_in_violation, db)
        users_in_violation = current_users_in_violation
        loop_ran_for = max(0, int(time.time()) - start_loop)
        sleep_delta = max(0, (LOOP_INTERVAL - loop_ran_for))
        time.sleep(sleep_delta)


if __name__ == '__main__':
    main()
