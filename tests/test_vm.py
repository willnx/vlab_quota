# -*- coding: UTF -*-
"""A suite of unit tests for the ``vm.py`` module"""
import unittest
from unittest.mock import patch, MagicMock

from vlab_quota.libs import vm


class TestCallApi(unittest.TestCase):
    """A suite of test cases for the ``_call_api`` function"""

    @classmethod
    def setUpClass(cls):
        """Runs once for the whole suite"""
        cls.token = b'aa.bb.cc'

    @patch.object(vm.time, 'sleep')
    @patch.object(vm.requests, 'get')
    def test_task_call(self, fake_get, fake_sleep):
        """``_call_api`` blocks on the async task API calls when task_call=True"""
        fake_resp1 = MagicMock()
        fake_resp1.ok = True
        fake_resp1.links = {'status': {'url': 'https://some-url'}}
        fake_resp1.status_code = 202
        fake_resp2 = MagicMock()
        fake_resp2.ok = True
        fake_resp2.status_code = 200
        fake_resp2.json.return_value = {'json-body': True}
        fake_get.side_effect = [fake_resp1, fake_resp2]

        vm._call_api('https://some-vlab-service', self.token, task_call=True)

        self.assertTrue(fake_sleep.called)

    @patch.object(vm.time, 'sleep')
    @patch.object(vm.requests, 'get')
    def test_no_task_call(self, fake_get, fake_sleep):
        """``_call_api`` does not blocks on the async task API calls when task_call=False"""
        fake_resp = MagicMock()
        fake_resp.ok = True
        fake_resp.status_code = 200
        fake_resp.json.return_value = {'json-body': True}
        fake_get.return_value = fake_resp

        vm._call_api('https://some-vlab-service', self.token, task_call=False)

        self.assertFalse(fake_sleep.called)

    @patch.object(vm.requests, 'get')
    def test_returns_json(self, fake_get):
        """``_call_api`` returns the deserialized JSON body"""
        fake_resp = MagicMock()
        fake_resp.ok = True
        fake_resp.status_code = 200
        fake_resp.json.return_value = {'json-body': True}
        fake_get.return_value = fake_resp

        output = vm._call_api('https://some-vlab-service', self.token, task_call=False)
        expected = {'json-body': True}

        self.assertEqual(output, expected)

    @patch.object(vm, 'log')
    @patch.object(vm.requests, 'get')
    def test_raises_exception(self, fake_get, fake_log):
        """``_call_api`` returns the deserialized JSON body"""
        fake_resp = MagicMock()
        fake_resp.ok = False
        fake_resp.status_code = 200
        fake_resp.json.return_value = {'json-body': True}
        fake_get.return_value = fake_resp

        vm._call_api('https://some-vlab-service', self.token, task_call=False)

        self.assertTrue(fake_resp.raise_for_status.called)

    @patch.object(vm, 'log')
    @patch.object(vm.requests, 'get')
    def test_logs_on_exception(self, fake_get, fake_log):
        """``_call_api`` returns the deserialized JSON body"""
        fake_resp = MagicMock()
        fake_resp.ok = False
        fake_resp.status_code = 200
        fake_resp.json.return_value = {'json-body': True}
        fake_get.return_value = fake_resp

        vm._call_api('https://some-vlab-service', self.token, task_call=False)

        self.assertTrue(fake_log.error.called)


class TestGetSecret(unittest.TestCase):
    """A suite of test cases for the ``_get_secret`` function"""
    def test_no_location(self):
        """``_get_secret`` raises RuntimeError if the 'location' parameter is not true"""
        with self.assertRaises(RuntimeError):
            vm._get_secret(location=None)

    @patch("vlab_quota.libs.vm.open", create=True)
    def test_reads_file(self, fake_open):
        """``_get_secret`` reads the secret out of the supplied file"""
        fake_file = MagicMock()
        fake_file.read.return_value = 'aa.bb.cc'
        fake_open.return_value.__enter__.return_value = fake_file

        secret = vm._get_secret(location='/some/path/location')
        expected = 'aa.bb.cc'

        self.assertEqual(secret, expected)


class TestGenerateToken(unittest.TestCase):
    """A suite of tests cases for the ``generate_token`` function"""
    @patch.object(vm, '_get_secret')
    @patch.object(vm.jwt, 'encode')
    def test_token(self, fake_encode, fake_get_secret):
        """``generate_token`` returns an encoded JSON Web Token"""
        fake_encode.return_value = 'aa.bb.cc'

        token = vm._generate_token(user='bob')
        expected = 'aa.bb.cc'

        self.assertEqual(token, expected)


class TestDeleteVM(unittest.TestCase):
    """A suite of test cases for the ``_delete_vm`` function"""
    @patch.object(vm, '_generate_token')
    @patch.object(vm, '_call_api')
    def test_delete_vm(self, fake_call_api, fake_generate_token):
        """``_delete_vm`` calls the right API to delete the virtual machine"""
        fake_generate_token.return_value = b'aa.bb.cc'
        vm._delete_vm(user='sam', vm_name='doh', vm_type='OneFS')

        the_args, _ = fake_call_api.call_args
        url = the_args[0]
        expected_url = 'https://vlab.local/api/2/inf/onefs'

        self.assertEqual(url, expected_url)


class TestDeletePortmapRules(unittest.TestCase):
    """A suite of test cases for the ``_delete_portmap_rules`` function"""

    @patch.object(vm, '_generate_token')
    @patch.object(vm, '_call_api')
    def notest_delete_portmap_rules(self, fake_call_api, fake_generate_token):
        """``_delete_portmap_rules`` constructs the correct URL to delete portmap rules"""
        fake_generate_token.return_value = b'aa.bb.cc'
        vm._delete_portmap_rules(user='max', vm_name='beer')

        the_args, _ = fake_call_api.call_args
        url = the_args[0]
        expected_url = 'https://max.vlab.local/api/1/ipam/portmap'

        self.assertEqual(url, expected_url)

    @patch.object(vm, '_generate_token')
    @patch.object(vm, '_call_api')
    def test_only_deletes_vm_rules(self, fake_call_api, fake_generate_token):
        """``_delete_portmap_rules`` only deletes portmap rules associated with the VM being deleted"""
        fake_generate_token.return_value = b'aa.bb.cc'
        data = {'content': {'ports': {'1234': {'name': 'beer'}, '2345': {'name': 'foo'}}}}
        fake_call_api.return_value = data

        vm._delete_portmap_rules(user='max', vm_name='beer')

        all_args = fake_call_api.call_args_list
        _, delete_kwarg = all_args[1]
        deleted_port = delete_kwarg['payload']['conn_port']
        expected_port = 1234

        self.assertEqual(len(all_args), 2) # One to lookup all rules, another to delete
        self.assertEqual(deleted_port, expected_port)


@patch.object(vm, 'log')
@patch.object(vm.virtual_machine, 'get_info')
@patch.object(vm, '_delete_portmap_rules')
@patch.object(vm, '_delete_vm')
class TestDestroyVMs(unittest.TestCase):
    """A suite of test cases for the ``destory_vms`` function"""
    @classmethod
    def setUp(cls):
        """Runs before every test case"""
        fake_folder = MagicMock()
        fake_vm1 = MagicMock()
        fake_vm1.name = 'defaultGateway'
        cls.fake_vm1 = fake_vm1
        fake_vm2 = MagicMock()
        fake_vm2.name = 'someVM'
        cls.fake_vm2 = fake_vm2
        fake_vm3 = MagicMock()
        fake_vm3.name = 'someOtherVM'
        cls.fake_vm3 = fake_vm3
        fake_folder.childEntity.__iter__.return_value = [fake_vm1, fake_vm2, fake_vm3]
        vcenter = MagicMock()
        vcenter.get_by_name.return_value = fake_folder
        cls.vcenter = vcenter

    @patch.object(vm, 'const')
    def test_skips_default_gateway(self, fake_const, fake_delete_vm, fake_delete_portmap_rules, fake_get_info, fake_log):
        """``destory_vms`` will not delete a users defaultGateway"""
        fake_const.VLAB_QUOTA_LIMIT = 0
        deleted_vms = []
        for _ in range(50):
            # avoid false negative due to random nature of "which VMs get deleted"
            deleted_vms += vm.destroy_vms('bill', self.vcenter)
        deleted_vms = set(deleted_vms)
        expected = {'someVM', 'someOtherVM'}

        self.assertEqual(deleted_vms, expected)

    @patch.object(vm, 'const')
    def test_skips_invalid_vms(self, fake_const, fake_delete_vm, fake_delete_portmap_rules, fake_get_info, fake_log):
        """``destory_vms`` will skip a VM that's deploying or failed to deploy"""
        fake_const.VLAB_QUOTA_LIMIT = 1
        good_info = {'meta': {'component': 'InsightIQ'}}
        bad_info = {'meta': {'component': 'Unknown'}}
        fake_get_info.side_effect = [bad_info, good_info]

        vm.destroy_vms('sandy', self.vcenter)

        all_args = fake_log.info.call_args_list
        skip_positional_args, _ = all_args[0]
        skip_msg = skip_positional_args[0]
        expected = 'Skipping VM %s owned by %s: VM cannot be deleted at this time'

        self.assertEqual(skip_msg, expected)



if __name__ == '__main__':
    unittest.main()
